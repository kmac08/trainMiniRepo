"""
Communication Handler Module
===========================
Manages all external communications between CTC and other subsystems
according to UML specifications with event-driven architecture.

This module handles:
- Wayside controller registration and communication
- Event-driven train command distribution (routing, rerouting, block updates)
- Block-specific commands with update flags and next station info
- Automatic switch control based on train routes
- Block closure/opening via set_occupied() 
- Ticket system throughput updates

Key Functions:
- provide_wayside_controller(): Register controllers with block coverage
- send_train_commands(): Send block-specific commands to wayside
- command_switch(): Send switch position commands
- set_occupied(): Manual block occupation control
- send_train_commands_for_route(): Event-driven command sending
- send_departure_commands(): Yard departure commands

NEW FULL LINE DATA TRANSMISSION BEHAVIOR:
==========================================
As of the latest update, the communication system implements full line data transmission:

CTC → Wayside Communication:
- CTC sends complete line data to ALL wayside controllers on that line
- Each controller receives full line information but only acts on blocks they manage
- Controllers use their blocksCovered boolean list to filter relevant commands
- This ensures all controllers have full situational awareness

Wayside → CTC Communication:
- Wayside controllers only send data for blocks they manage
- Data filtering is enforced at the CTC level using sending_controller parameter
- CTC discards any data from blocks the sending controller doesn't manage
- This prevents unauthorized or incorrect data from affecting the system

Benefits:
- Improved system reliability through full situational awareness
- Better coordination between adjacent controllers
- Simplified debugging and monitoring
- Enhanced safety through redundant information distribution
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from queue import Queue, Empty
import threading
import logging
import time

# Import simulation time (lazy import to avoid circular dependencies)
# from Master_Interface.master_control import get_time

# Set up logging
logger = logging.getLogger(__name__)


def _get_simulation_time():
    """Get simulation time with lazy import to avoid circular dependencies"""
    try:
        from Master_Interface.master_control import get_time
        return get_time()
    except ImportError:
        # Fallback to regular datetime if Master Interface not available
        from datetime import datetime
        return datetime.now()


class CommunicationHandler:
    """
    Advanced communication manager implementing full line data transmission and event-driven commands.
    
    This class manages all external communications between the CTC system and wayside controllers,
    implementing a sophisticated protocol with full situational awareness, event-driven command
    distribution, and comprehensive train control algorithms.
    
    Communication Architecture:
        - Event-Driven Commands: Only sends commands on routing, rerouting, and block occupation changes
        - Full Line Data Transmission: Sends complete line data to all controllers on that line
        - Block-Length Arrays: All data transmitted as block-length arrays for line consistency
        - Controller Filtering: Controllers filter data based on their managed blocks
        - Batched Command System: Optimizes command transmission for multiple trains
        
    Core Attributes:
        scheduledClosures (List[Tuple[Block, DateTime]]): Block closure schedule
        scheduledOpenings (List[Tuple[Block, DateTime]]): Block opening schedule  
        scheduledTrains (List[Route]): Scheduled train routes
        wayside_controllers (List[Controller]): Registered wayside controllers
        block_to_controller (Dict[int, Controller]): Block number to controller mapping
        
    State Tracking:
        current_occupied_blocks (Dict[int, bool]): Current block occupation states
        current_switch_positions (Dict[int, bool]): Current switch positions
        current_railway_crossings (Dict[int, bool]): Current crossing states
        active_train_routes (Dict[str, Route]): Active train routes for switch calculation
        
    Communication Data:
        message_queue (Queue): Thread-safe message processing queue
        throughput_by_line (Dict[str, int]): Throughput tracking by line
        
    Methods Overview:
        Wayside Integration:
            - provide_wayside_controller(controller, blocksCovered, redLine): Register controllers
            - update_occupied_blocks(occupiedBlocks, sender): Receive occupation updates
            - update_switch_positions(switchPositions, sender): Receive switch updates
            - update_railway_crossings(railwayCrossings, sender): Receive crossing updates
            
        Command Distribution:
            - send_train_commands(speeds, authorities, blocks, flags, stations, distances): Send block-specific commands
            - send_train_commands_for_route(train_id, route): Send commands for newly routed trains
            - send_departure_commands(train_id, route): Send yard departure sequences
            - send_updated_train_commands(line): Send batched updates for line
            
        Switch & Infrastructure Control:
            - command_switch(controller, switchPositions): Send switch commands
            - set_occupied(controller, blockList): Set manual block occupation
            - send_maintenance_closure(line, block, action): Send closure notifications
            
        Route & Schedule Management:
            - schedule_route(route): Store route for timed execution
            - schedule_closure(block, time): Schedule maintenance closure
            - schedule_opening(block, time): Schedule maintenance opening
            
        Throughput & Metrics:
            - tickets_purchased(line, numTickets): Handle ticket system updates
            - stop_train(train): Emergency stop specific train
            
        Advanced Command Features:
            - Batched Command System: Processes all trains on a line simultaneously
            - Route Distance Calculation: Uses actual route traversal distances (not arithmetic)
            - Target Block Commands: Sends commands TO current block FOR target block 4 positions ahead
            - Line-Aware Processing: Filters and routes commands by train line
            - Event-Driven Updates: Only sends commands when actual changes occur
            
        Authority & Speed Algorithms:
            - calculate_authority_and_speed(train_id, block_id, route): Comprehensive safety calculation
            - Authority Logic: Blocks trains based on occupation, bidirectional conflicts, switch conflicts
            - Speed Logic: Reduces speed based on stopped trains, stations, track conditions
            - Lookahead Safety: Analyzes up to 3 blocks ahead for obstacles and stations
            
        Junction Management:
            - manage_junctions(): Automatically manage junction blocks and switch positions
            - Priority-based routing through complex junctions
            - Conflict detection and resolution for multiple trains
            - Switch optimization for minimal delays
            
        Data Filtering & Validation:
            - Enforces strict protocol requirements for all controllers
            - Validates block-length arrays from wayside controllers
            - Filters incoming data based on controller's managed blocks
            - Prevents unauthorized data from affecting system state
            
        Performance Features:
            - Parallel command transmission to controllers on same line
            - Efficient line length calculation from track data
            - Dynamic switch anchor block identification
            - Optimized pathfinding for train command targets
            
        Safety Features:
            - Comprehensive bidirectional conflict detection
            - Switch position validation for train routes
            - Emergency stop capabilities with immediate response
            - Station approach speed reduction
            - Obstacle detection and avoidance
            
    Communication Protocol Compliance:
        - All controllers must implement command_train(), command_switch(), set_occupied()
        - Block coverage must be provided as List[bool] with proper indexing
        - Data filtering enforced at both transmission and reception
        - Full line data sent to all controllers for situational awareness
        - Controllers act only on blocks they manage
        
    Threading & Performance:
        - Background message processing thread
        - Thread-safe message queue operations
        - Asynchronous command distribution
        - Real-time data filtering and validation
        
    Integration Points:
        - CTC System: Real-time train and block data
        - Track Reader: Track layout and connectivity information
        - Route Objects: Advanced pathfinding and route distance calculation
        - Failure Manager: Emergency response and closure management
    """
    
    def __init__(self):
        """Initialize Communication Handler with UML-specified attributes"""
        # Attributes from UML
        self.scheduledClosures = []  # List[Tuple[Block, DateTime]]
        self.scheduledOpenings = []  # List[Tuple[Block, DateTime]]
        self.scheduledTrains = []    # List[Route]
        
        # Additional attributes needed for implementation
        self.wayside_controllers = []  # List[WaysideController]
        self.block_to_controller = {}  # Dict[int, WaysideController] - block_number -> controller
        self.controller_block_coverage = {}  # Dict[WaysideController, List[bool]] - controller -> blocksCovered
        self.message_queue = Queue()   # Thread-safe message queue
        self.ctc_system = None        # Reference to CTC System
        self.track_reader = None      # Reference to Track Reader
        
        # Track current state
        self.current_occupied_blocks = {}  # Dict[int, bool] - block_number -> occupied
        self.current_switch_positions = {} # Dict[int, bool] - switch_id -> position
        self.current_railway_crossings = {} # Dict[int, bool] - crossing_id -> active
        
        # Per-line state tracking for change detection
        self.previous_line_states = {
            'Red': {
                'occupied': None,      # List[bool] - previous occupation state for Red line
                'switches': None,      # List[bool] - previous switch state for Red line  
                'crossings': None      # List[bool] - previous crossing state for Red line
            },
            'Green': {
                'occupied': None,      # List[bool] - previous occupation state for Green line
                'switches': None,      # List[bool] - previous switch state for Green line
                'crossings': None      # List[bool] - previous crossing state for Green line
            }
        }
        
        # Basic train tracking - simplified
        self.active_train_routes = {}      # Dict[str, Route] - train_id -> route for switch calculation
        
        # Yard connection data removed - now managed by CTC system
        
        # Throughput tracking by line
        self.throughput_by_line = {
            'Blue': 0,
            'Red': 0,
            'Green': 0
        }
        
        # Thread management
        self._running = True
        self._message_thread = threading.Thread(target=self._process_messages)
        self._message_thread.daemon = True
        self._message_thread.start()
        
        logger.info("Communication Handler initialized")
    
    # Methods from UML
    
    def _reassemble_line_state(self, data_type: str, line_name: str) -> List[bool]:
        """
        Reassemble complete line state from all controllers for that line.
        
        Args:
            data_type: Type of data ('occupied', 'switches', 'crossings')
            line_name: Line name ('Red' or 'Green')
            
        Returns:
            Complete line state array assembled from all controllers on that line
        """
        # Get line length
        line_length = self._get_line_length(line_name)
        if line_length <= 0:
            return []
        
        # Initialize line state array
        line_state = [False] * line_length
        
        # Collect data from all controllers on this line
        for controller in self.wayside_controllers:
            # Determine controller's line
            controller_line = None
            if hasattr(controller, 'redLine'):
                controller_line = 'Red' if controller.redLine else 'Green'
            else:
                # Try to determine from controller ID
                controller_id = getattr(controller, 'controller_id', '')
                if 'Red' in controller_id:
                    controller_line = 'Red'
                else:
                    controller_line = 'Green'  # Default
            
            # Skip controllers not on this line
            if controller_line != line_name:
                continue
            
            # Get controller's block coverage
            if controller not in self.controller_block_coverage:
                continue
            
            blocks_covered = self.controller_block_coverage[controller]
            
            # Get controller's current data based on data type
            controller_data = None
            if data_type == 'occupied':
                controller_data = getattr(controller, 'block_occupancy', None)
            elif data_type == 'switches':
                controller_data = getattr(controller, 'switch_positions', None)
            elif data_type == 'crossings':
                controller_data = getattr(controller, 'railroad_crossings', None)
            
            # Merge controller's data into line state
            if controller_data and len(controller_data) == len(blocks_covered):
                for i, (covers_block, data_value) in enumerate(zip(blocks_covered, controller_data)):
                    if covers_block and i < line_length:
                        line_state[i] = data_value
        
        return line_state
    
    def update_occupied_blocks(self, occupiedBlocks: List[bool], sending_controller=None) -> None:
        """
        Receive occupation status from wayside controller
        
        Args:
            occupiedBlocks: List of boolean values indicating block occupation
            sending_controller: Controller that sent this data (optional, for filtering)
        """
        controller_id = getattr(sending_controller, 'controller_id', 'Unknown')
        
        # Determine the line from the sending controller  
        line_name = None
        if sending_controller:
            if hasattr(sending_controller, 'redLine'):
                line_name = 'Red' if sending_controller.redLine else 'Green'
            else:
                # Try to determine from controller ID
                if 'Red' in controller_id:
                    line_name = 'Red'
                else:
                    line_name = 'Green'  # Default
        
        if not line_name:
            logger.warning(f"Could not determine line for controller {controller_id}")
            return
        
        # Reassemble complete line state from all controllers on this line
        current_line_state = self._reassemble_line_state('occupied', line_name)
        previous_line_state = self.previous_line_states[line_name]['occupied']
        
        # Check for changes in the complete line state
        has_changes = False
        if previous_line_state is None:
            # First time receiving data - treat as change
            has_changes = True
        elif len(current_line_state) != len(previous_line_state):
            # Array length changed - treat as change
            has_changes = True
        else:
            # Compare line occupation states
            for i, (current, previous) in enumerate(zip(current_line_state, previous_line_state)):
                if current != previous:
                    has_changes = True
                    break
        
        # Only show debug output when the complete line state has changed
        if has_changes:
            occupied_count = sum(current_line_state) if current_line_state else 0
            occupied_blocks = [i for i, occupied in enumerate(current_line_state) if occupied] if current_line_state else []
            
            print(f"[CTC_DEBUG] WAYSIDE DATA CHANGED: update_occupied_blocks()")
            print(f"  Line: {line_name}")
            print(f"  Controller: {controller_id}")
            print(f"  Total blocks: {len(current_line_state) if current_line_state else 0}")
            print(f"  Occupied count: {occupied_count}")
            print(f"  Occupied blocks: {occupied_blocks[:10]}{'...' if len(occupied_blocks) > 10 else ''}")
            
            # Store current line state for next comparison
            self.previous_line_states[line_name]['occupied'] = current_line_state.copy() if current_line_state else []
        
        message = {
            'type': 'occupied_blocks_update',
            'data': occupiedBlocks,
            'sender': sending_controller,
            'timestamp': _get_simulation_time(),
            'has_changes': has_changes
        }
        self.message_queue.put(message)
        logger.debug(f"Received occupied blocks update: {len(occupiedBlocks)} blocks from {controller_id}")
    
    def _get_blocks_with_infrastructure_and_state(self, state_array: List[bool], sending_controller, infrastructure_type: str) -> List[int]:
        """
        Helper function to filter debug output to only show blocks that have the infrastructure AND are active
        
        Args:
            state_array: Block-length array of boolean states
            sending_controller: Controller that sent the data
            infrastructure_type: Type of infrastructure ('switchPresent' or 'crossingPresent')
        
        Returns:
            List of block numbers that have the infrastructure and are currently active
        """
        if not state_array or not sending_controller or not self.ctc_system:
            return []
        
        # Determine line from controller
        line_name = "Red" if getattr(sending_controller, 'redLine', False) else "Green"
        
        result = []
        for i, is_active in enumerate(state_array):
            if is_active:  # Only check blocks that are currently active
                # Get the block from CTC system
                try:
                    block = self.ctc_system.get_block_by_line_new(line_name, i)
                    if block and hasattr(block, infrastructure_type) and getattr(block, infrastructure_type):
                        result.append(i)
                except:
                    # If we can't get block info, include it in the output (fallback behavior)
                    result.append(i)
        
        return result
    
    def update_switch_positions(self, switchPositions: List[bool], sending_controller=None) -> None:
        """
        Receive switch positions from wayside controller
        
        switchPositions is a block-length array for the line.
        Switch positions are set at anchor blocks (where switch connections meet).
        Non-switch blocks are ignored. Controller will filter to only process blocks it manages.
        
        Args:
            switchPositions: Block-length array of boolean values (0=normal/lower, 1=reverse/higher)
                           Only blocks with actual switches have meaningful values
            sending_controller: Controller that sent this data (optional, for filtering)
        """
        controller_id = getattr(sending_controller, 'controller_id', 'Unknown')
        
        # Determine line name from controller
        line_name = "Red" if getattr(sending_controller, 'redLine', False) else "Green"
        
        # Reassemble complete line state from all controllers on this line
        current_line_state = self._reassemble_line_state('switches', line_name)
        
        # Get previous line state for comparison
        previous_line_state = self.previous_line_states[line_name]['switches']
        
        # Check for changes at line level
        has_changes = False
        if not previous_line_state:
            # First time receiving data for this line - treat as change
            has_changes = True
        elif len(current_line_state) != len(previous_line_state):
            # Array length changed - treat as change
            has_changes = True
        else:
            # Compare line states
            for i, (current, previous) in enumerate(zip(current_line_state, previous_line_state)):
                if current != previous:
                    has_changes = True
                    break
        
        # Only show debug output when line state changes are detected
        if has_changes:
            # Filter to only show blocks that both have switches AND are active
            active_switches_with_infrastructure = self._get_blocks_with_infrastructure_and_state(
                current_line_state, sending_controller, 'switchPresent'
            )
            
            # Get total switches for reference
            total_switches = 0
            if self.ctc_system and sending_controller:
                for i in range(len(current_line_state) if current_line_state else 0):
                    try:
                        block = self.ctc_system.get_block_by_line_new(line_name, i)
                        if block and hasattr(block, 'switchPresent') and getattr(block, 'switchPresent'):
                            total_switches += 1
                    except:
                        pass
            
            print(f"[CTC_DEBUG] WAYSIDE DATA CHANGED: update_switch_positions()")
            print(f"  Line: {line_name}")
            print(f"  Controller: {controller_id}")
            print(f"  Switch array length: {len(current_line_state) if current_line_state else 0}")
            print(f"  Active switches: {len(active_switches_with_infrastructure)}/{total_switches}")
            print(f"  Active switch blocks: {active_switches_with_infrastructure}")
            
            # Store current line state for next comparison
            self.previous_line_states[line_name]['switches'] = current_line_state.copy() if current_line_state else []
        
        message = {
            'type': 'switch_positions_update',
            'data': switchPositions,
            'sender': sending_controller,
            'timestamp': _get_simulation_time()
        }
        self.message_queue.put(message)
        logger.debug(f"Received switch positions update: {len(switchPositions)} block-length array from {controller_id}")
    
    def update_railway_crossings(self, railwayCrossings: List[bool], sending_controller=None) -> None:
        """
        Receive crossing status from wayside controller
        
        railwayCrossings is a block-length array for the line.
        Only blocks with railway crossings have meaningful values - other blocks are ignored.
        Controller will filter to only process blocks it manages.
        
        Args:
            railwayCrossings: Block-length array of boolean values indicating crossing activation
                            Only blocks with actual railway crossings have meaningful values
            sending_controller: Controller that sent this data (optional, for filtering)
        """
        controller_id = getattr(sending_controller, 'controller_id', 'Unknown')
        
        # Determine line name from controller
        line_name = "Red" if getattr(sending_controller, 'redLine', False) else "Green"
        
        # Reassemble complete line state from all controllers on this line
        current_line_state = self._reassemble_line_state('crossings', line_name)
        
        # Get previous line state for comparison
        previous_line_state = self.previous_line_states[line_name]['crossings']
        
        # Check for changes at line level
        has_changes = False
        if not previous_line_state:
            # First time receiving data for this line - treat as change
            has_changes = True
        elif len(current_line_state) != len(previous_line_state):
            # Array length changed - treat as change
            has_changes = True
        else:
            # Compare line states
            for i, (current, previous) in enumerate(zip(current_line_state, previous_line_state)):
                if current != previous:
                    has_changes = True
                    break
        
        # Only show debug output when line state changes are detected
        if has_changes:
            # Filter to only show blocks that both have railway crossings AND are active
            active_crossings_with_infrastructure = self._get_blocks_with_infrastructure_and_state(
                current_line_state, sending_controller, 'crossingPresent'
            )
            
            # Get total crossings for reference
            total_crossings = 0
            if self.ctc_system and sending_controller:
                for i in range(len(current_line_state) if current_line_state else 0):
                    try:
                        block = self.ctc_system.get_block_by_line_new(line_name, i)
                        if block and hasattr(block, 'crossingPresent') and getattr(block, 'crossingPresent'):
                            total_crossings += 1
                    except:
                        pass
            
            print(f"[CTC_DEBUG] WAYSIDE DATA CHANGED: update_railway_crossings()")
            print(f"  Line: {line_name}")
            print(f"  Controller: {controller_id}")
            print(f"  Crossing array length: {len(current_line_state) if current_line_state else 0}")
            print(f"  Active crossings: {len(active_crossings_with_infrastructure)}/{total_crossings}")
            print(f"  Active crossing blocks: {active_crossings_with_infrastructure}")
            
            # Store current line state for next comparison
            self.previous_line_states[line_name]['crossings'] = current_line_state.copy() if current_line_state else []
        
        message = {
            'type': 'railway_crossings_update',
            'data': railwayCrossings,
            'sender': sending_controller,
            'timestamp': _get_simulation_time()
        }
        self.message_queue.put(message)
        logger.debug(f"Received railway crossings update: {len(railwayCrossings)} block-length array from {controller_id}")
    
    def schedule_route(self, route) -> None:
        """
        Store accepted route for timed execution (no immediate wayside communication)
        Commands will be sent at departure time via send_departure_commands()
        
        Args:
            route: Route object to schedule
        """
        if not route or not hasattr(route, 'trainID'):
            logger.error("Cannot schedule route: missing route or trainID")
            return
            
        # Store route for timed command execution
        train_id = route.trainID
        self.active_train_routes[train_id] = route
        self.scheduledTrains.append(route)
        
        # Add terminal output for route storage
        print(f"📋 ROUTE STORED: Train {train_id} route stored in communication handler")
        if hasattr(route, 'blockSequence') and route.blockSequence:
            block_ids = [block.blockID for block in route.blockSequence]
            print(f"   Stored route blocks: {block_ids}")
        
        logger.info(f"Route stored for train {train_id}: {route.routeID if hasattr(route, 'routeID') else 'Unknown ID'}")
    
    def schedule_closure(self, block, time: datetime) -> None:
        """
        Schedule block closure
        
        Args:
            block: Block object to close
            time: DateTime when closure begins
        """
        self.scheduledClosures.append((block, time))
        
        # Find the wayside controller for this block
        block_id = block.blockID if hasattr(block, 'blockID') else None
        # Note: Controller notification removed - will be implemented when protocol is defined
        
        logger.info(f"Block closure scheduled: Block {block_id} at {time}")
    
    def schedule_opening(self, block, time: datetime) -> None:
        """
        Schedule block opening
        
        Args:
            block: Block object to open
            time: DateTime when opening occurs
        """
        self.scheduledOpenings.append((block, time))
        
        # Find the wayside controller for this block
        block_id = block.blockID if hasattr(block, 'blockID') else None
        # Note: Controller notification removed - will be implemented when protocol is defined
        
        logger.info(f"Block opening scheduled: Block {block_id} at {time}")
    
    
    def tickets_purchased(self, line: str, numTickets: int) -> None:
        """
        Handle throughput update from ticket system
        
        Args:
            line: Line name (Blue, Red, or Green)
            numTickets: Number of tickets purchased
        """
        if line in self.throughput_by_line:
            self.throughput_by_line[line] += numTickets
            
            # Execute calculateThroughput sequence diagram
            if (self.ctc_system and 
                hasattr(self.ctc_system, 'sequence_implementations') and 
                self.ctc_system.sequence_implementations):
                
                result = self.ctc_system.sequence_implementations.calculate_throughput_sequence(line, numTickets)
                logger.info(f"Calculate throughput sequence result: {result}")
            else:
                # Fallback to direct call
                if hasattr(self.ctc_system, 'update_throughput'):
                    self.ctc_system.update_throughput(numTickets, line)
            
            logger.info(f"Tickets purchased: {numTickets} for {line} line")
        else:
            logger.warning(f"Unknown line for ticket purchase: {line}")
    
    def stop_train(self, train) -> None:
        """
        Emergency stop a specific train
        
        Args:
            train: Train object to stop
        """
        if hasattr(train, 'currentBlock') and train.currentBlock:
            # Find controller for train's current block
            if train.currentBlock in self.block_to_controller:
                controller = self.block_to_controller[train.currentBlock]
                
                # Send emergency stop command
                block_index = controller.managedBlocks.index(train.currentBlock)
                num_blocks = len(controller.managedBlocks)
                
                # Create command arrays with stop command for train's block
                suggested_speeds = [3] * num_blocks  # Default full speed
                authorities = [1] * num_blocks       # Default authority
                suggested_speeds[block_index] = 0   # STOP
                authorities[block_index] = 0         # No authority
                
                # Send emergency stop via new command method
                blocks = controller.managedBlocks[:len(suggested_speeds)]
                updateFlags = [0] * len(suggested_speeds)  # All new commands
                nextStations = [0] * len(suggested_speeds)  # No station info needed
                blocksAway = [0] * len(suggested_speeds)  # No distance info needed
                
                self.send_train_commands(suggested_speeds, authorities, blocks, updateFlags, nextStations, blocksAway)
                logger.warning(f"Emergency stop sent for train {train}")
    
    def send_maintenance_closure(self, line: str, block_number: int, action: str) -> None:
        """
        Send maintenance closure notification to wayside controller using set_occupied()
        
        Args:
            line: Line name (Blue, Red, or Green)
            block_number: Block number being closed/opened
            action: "close" or "open"
        """
        # Find controller for the block
        if block_number in self.block_to_controller:
            controller = self.block_to_controller[block_number]
            
            # Create occupation list for this controller
            occupation_list = self._create_occupation_list_for_controller(controller, block_number, action == "close")
            
            # Send occupation update to controller via set_occupied()
            if hasattr(controller, 'set_occupied'):
                controller.set_occupied(occupation_list)
                logger.info(f"Block {block_number} {action} sent via set_occupied() on {line} line")
            else:
                logger.error(f"Controller does not support set_occupied() method")
        else:
            logger.warning(f"No controller found for block {block_number}")
    
    def _create_occupation_list_for_controller(self, controller, target_block: int, occupied: bool) -> List[bool]:
        """
        Create line-length occupation list for a specific controller with target block set
        
        Args:
            controller: Wayside controller object
            target_block: Block number to set occupation for
            occupied: True to mark as occupied (closed), False for open
            
        Returns:
            List of boolean values for all blocks on the controller's line (line-length array)
        """
        if not hasattr(controller, 'managedBlocks'):
            return []
        
        # Determine controller's line
        line_name = None
        if hasattr(controller, 'redLine'):
            line_name = 'Red' if controller.redLine else 'Green'
        else:
            # Try to determine from controller ID if redLine attribute missing
            controller_id = getattr(controller, 'controller_id', '')
            if 'Red' in controller_id:
                line_name = 'Red'
            elif 'Green' in controller_id:
                line_name = 'Green'
            elif 'Blue' in controller_id:
                line_name = 'Blue'
            else:
                logger.warning(f"Could not determine line for controller {controller_id}, defaulting to Green")
                line_name = 'Green'
        
        # Get dynamic line length
        line_length = self._get_line_length(line_name)
        
        # Create line-length array with current occupation state
        occupation_list = [False] * line_length
        for i in range(line_length):
            if i == target_block:
                occupation_list[i] = occupied
            else:
                # Preserve current occupation state for other blocks
                occupation_list[i] = self.current_occupied_blocks.get(i, False)
                
        logger.debug(f"Created line-length occupation array for {line_name} line (length {line_length}), target block {target_block} = {occupied}")
        return occupation_list
    
    # Additional methods needed for implementation
    
    def provide_wayside_controller(self, waysideController, blocksCovered: List[bool], redLine: bool) -> None:
        """
        Called by wayside to register controller and its blocks
        
        ENFORCES NEW COMMUNICATION PROTOCOL: Only accepts controllers that implement
        the block-length array protocol. No backward compatibility.
        
        Args:
            waysideController: Wayside controller object (must implement required methods)
            blocksCovered: List of booleans indicating which blocks this controller manages 
                          (True = controller manages this block, False = doesn't manage)
                          Index 0 is yard, index 1 is block 1, etc.
            redLine: True if this controller is for the red line, False if for green line
            
        Raises:
            ValueError: If controller doesn't meet protocol requirements
        """

        print(f"[CTC_DEBUG]  REGISTERING CONTROLLER: {waysideController.controller_id}")
        # STRICT PROTOCOL VALIDATION
        if not blocksCovered or not isinstance(blocksCovered, list):
            error_msg = f"PROTOCOL VIOLATION: blocksCovered must be a non-empty List[bool], got {type(blocksCovered)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        if not all(isinstance(x, bool) for x in blocksCovered):
            error_msg = f"PROTOCOL VIOLATION: blocksCovered must contain only boolean values"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Validate controller implements required methods for new protocol
        required_methods = ['command_train', 'set_occupied']
        missing_methods = []
        for method_name in required_methods:
            if not hasattr(waysideController, method_name) or not callable(getattr(waysideController, method_name)):
                missing_methods.append(method_name)
        
        if missing_methods:
            error_msg = f"PROTOCOL VIOLATION: Controller {getattr(waysideController, 'controller_id', 'Unknown')} missing required methods: {missing_methods}. New protocol requires all controllers to implement these methods."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Validate controller has an identifier
        if not hasattr(waysideController, 'controller_id'):
            error_msg = f"PROTOCOL VIOLATION: Controller must have 'controller_id' attribute for new protocol"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.wayside_controllers.append(waysideController)
        
        # Convert boolean list to actual block numbers for internal use
        managed_blocks = [i for i, is_managed in enumerate(blocksCovered) if is_managed]
        
        if not managed_blocks:
            error_msg = f"PROTOCOL VIOLATION: Controller {waysideController.controller_id} manages no blocks (all False in blocksCovered)"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Store both the boolean list and line information on the controller for later use (TBTG camelCase naming)
        waysideController.blocksCoveredBool = blocksCovered
        waysideController.redLine = redLine
        waysideController.managedBlocks = managed_blocks
        
        # Store block coverage in internal mapping for reliable access
        self.controller_block_coverage[waysideController] = blocksCovered
        
        # Enhanced debug output for controller registration
        line_name = "Red" if redLine else "Green"
        print(f"[CTC_DEBUG]   WAYSIDE CONTROLLER REGISTRATION:")
        print(f"[CTC_DEBUG]   Controller ID: {waysideController.controller_id}")
        print(f"[CTC_DEBUG]   Line: {line_name}")
        print(f"[CTC_DEBUG]   Managed blocks: {managed_blocks}")
        print(f"[CTC_DEBUG]   Includes yard (block 0): {'✓ YES' if 0 in managed_blocks else '✗ NO'}")
        print(f"[CTC_DEBUG]   Block coverage array length: {len(blocksCovered)}")
        print(f"[CTC_DEBUG]   ✓ Registration successful")
        
        # Map blocks to controller
        for block in managed_blocks:
            self.block_to_controller[block] = waysideController
        
        line_name = "Red" if redLine else "Green"
        logger.info(f"Wayside controller {waysideController.controller_id} registered for {line_name} line covering blocks {managed_blocks} (NEW PROTOCOL)")
        print(f"[PROTOCOL] Controller {waysideController.controller_id} registered with block-length array protocol for {line_name} line")
    
    
    # Yard connection management moved to CTC system
    
    def _get_train_line_from_route(self, route) -> str:
        """
        Determine which train line a route belongs to based on the route blocks
        """
        if not route or not hasattr(route, 'blockSequence') or not route.blockSequence:
            return None
            
        # Get route blocks (excluding yard)
        route_blocks = []
        for block in route.blockSequence:
            block_id = getattr(block, 'blockID', getattr(block, 'block_number', block))
            if block_id != 0:  # Exclude yard
                route_blocks.append(block_id)
        
        if not route_blocks:
            return None
            
        # Check which line contains most of the route blocks
        line_matches = {}
        if self.track_reader and hasattr(self.track_reader, 'lines'):
            for line_name, line_blocks in self.track_reader.lines.items():
                line_block_numbers = [getattr(b, 'block_number', 0) for b in line_blocks]
                matches = sum(1 for block_id in route_blocks if block_id in line_block_numbers)
                if matches > 0:
                    line_matches[line_name] = matches
        
        if line_matches:
            # Return the line with the most matching blocks
            best_line = max(line_matches, key=line_matches.get)
            logger.debug(f"Route determined to be on {best_line} line based on block matches: {line_matches}")
            return best_line
        
        return None
    
    def _get_yard_exit_block(self, line: str) -> int:
        """
        Get the first block a train enters when leaving the yard for a specific line
        Uses CTC system's yard connection data
        """
        if self.ctc_system and hasattr(self.ctc_system, 'get_yard_exit_block'):
            return self.ctc_system.get_yard_exit_block(line)
        
        logger.warning(f"Could not determine yard exit block for {line} line - CTC system not available")
        return None
    
    def send_train_commands(self, suggestedSpeed: List[int], authority: List[int], blockNum: List[int], 
                           updateBlockInQueue: List[int], nextStation: List[int], blocksAway: List[int]) -> None:
        """
        Send block-specific train commands to wayside controllers
        
        IMPORTANT: Command Array Structure
        - Array position [i] corresponds to the train's CURRENT block position
        - Commands are sent TO the controller managing the train's current block
        - blockNum[i] specifies the TARGET block that the commands apply to (typically 4 positions ahead in route)
        - blocksAway[i] is the route distance from current block to target block (NOT arithmetic difference)
        
        Example: Train currently in block 5, with target block 12:
        - Array position: 5 (current block)
        - blockNum[5] = 12 (target block for commands)
        - suggestedSpeed[5] = speed for when train reaches block 12
        - authority[5] = authority for when train reaches block 12
        - blocksAway[5] = route hops from block 5 to block 12
        
        Send commands for entire line to all wayside controllers on that line.
        Each wayside controller will receive the information for every block on the line,
        but should only pay attention to the blocks it manages.
        
        Args:
            suggestedSpeed: List of speed commands (0=stop, 1=1/3, 2=2/3, 3=full) indexed by current block
            authority: List of authority values (0=no, 1=yes) indexed by current block
            blockNum: List of TARGET block IDs that commands apply to (indexed by current block)
            updateBlockInQueue: List indicating if this overwrites previous command (0=new, 1=update)
            nextStation: List of next station IDs for each train (indexed by current block)
            blocksAway: List of route distances from current block to target block (indexed by current block)
        """
        # Group controllers by line instead of by individual blocks
        line_controllers = {'Red': [], 'Green': [], 'Blue': []}
        
        # Organize controllers by line
        for controller in self.wayside_controllers:
            if hasattr(controller, 'redLine'):
                if controller.redLine:
                    line_controllers['Red'].append(controller)
                else:
                    line_controllers['Green'].append(controller)
            else:
                # Try to determine line from controller ID if redLine attribute missing
                controller_id = getattr(controller, 'controller_id', '')
                if 'Red' in controller_id:
                    line_controllers['Red'].append(controller)
                elif 'Blue' in controller_id:
                    line_controllers['Blue'].append(controller)
                else:
                    # Default to Green for unknown controllers
                    line_controllers['Green'].append(controller)
        
        # Determine which line(s) are affected by these commands
        affected_lines = set()
        for block in blockNum:
            # Use Track Reader to determine line from block ID
            line_name = None
            if self.track_reader and hasattr(self.track_reader, 'get_line_for_block'):
                line_name = self.track_reader.get_line_for_block(block)
            
            if line_name:
                affected_lines.add(line_name)
        
        # Send complete line information to all controllers on each affected line
        for line_name in affected_lines:
            controllers_on_line = line_controllers.get(line_name, [])
            
            for controller in controllers_on_line:
                if hasattr(controller, 'command_train'):
                    # Enhanced debug logging
                    controller_id = getattr(controller, 'controller_id', 'Unknown')
                    active_commands = [(i, speed, auth, block) for i, (speed, auth, block) in enumerate(zip(suggestedSpeed, authority, blockNum)) if speed > 0 or auth > 0 or block > 0]
                    
                    print(f"[CTC_DEBUG]  SENDING TO WAYSIDE: command_train()")
                    print(f"  Controller: {controller_id}")
                    print(f"  Line: {line_name}")
                    print(f"  Total array length: {len(blockNum)}")
                    print(f"  Active commands: {len(active_commands)}")
                    print(f"  Command details: {active_commands[:5]}{'...' if len(active_commands) > 5 else ''}")
                    
                    # Send the entire command lists (for the whole line) to this controller
                    # The wayside controller will filter based on its blocks_covered_bool
                    controller.command_train(
                        suggestedSpeed,  # Full list for entire line
                        authority,       # Full list for entire line  
                        blockNum,        # Full list for entire line
                        updateBlockInQueue,  # Full list for entire line
                        nextStation,     # Full list for entire line
                        blocksAway       # Full list for entire line
                    )
                    logger.debug(f"Full line commands sent to {line_name} line controller {controller_id} for {len(blockNum)} blocks")
                else:
                    logger.error(f"Controller does not support command_train method")
    
    
    
    
    def remove_train_from_system(self, train_id: str) -> None:
        """
        Remove train from active route tracking (simplified)
        
        Args:
            train_id: ID of train to remove
        """
        # Remove from active routes
        if train_id in self.active_train_routes:
            del self.active_train_routes[train_id]
        
        logger.info(f"Train {train_id} removed from active route tracking")
    
    
    def set_occupied(self, controller, blockList: List[bool]) -> None:
        """
        Set block occupation for manual closures
        
        Args:
            controller: Wayside controller object
            blockList: List of occupation states to set
        """
        if hasattr(controller, 'set_occupied'):
            controller_id = getattr(controller, 'controller_id', 'Unknown')
            print(f"[WAYSIDE_DEBUG] Controller: {controller_id} - Function: set_occupied() - Block List: {blockList}")
            controller.set_occupied(blockList)
            logger.debug(f"Manual occupation set for controller")
        else:
            logger.error("Controller does not support set_occupied method")
    
    # Private helper methods
    
    def _process_messages(self):
        """Background thread to process incoming messages"""
        while self._running:
            try:
                message = self.message_queue.get(timeout=0.1)
                self._handle_message(message)
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    def _handle_message(self, message):
        """Process a single message"""
        msg_type = message.get('type')
        data = message.get('data')
        sender = message.get('sender')
        
        # Set the current message sender for filtering
        self._current_message_sender = sender
        
        try:
            if msg_type == 'occupied_blocks_update':
                self._update_occupied_blocks_internal(data, message)
            elif msg_type == 'switch_positions_update':
                self._update_switch_positions_internal(data)
            elif msg_type == 'railway_crossings_update':
                self._update_railway_crossings_internal(data)
        finally:
            # Clear the sender after processing
            self._current_message_sender = None
    
    def _update_occupied_blocks_internal(self, occupied_blocks, message):
        """
        Internal method to process occupied blocks update with data filtering
        
        Filter data based on which blocks the sending controller manages.
        Only accept data for blocks that the controller is responsible for.
        Only triggers command_train calls when actual changes are detected.
        """
        # Check if there are actual changes before processing
        has_changes = message.get('has_changes', False)
        
        # Identify which controller sent this data and filter appropriately
        filtered_blocks = self._filter_wayside_data(occupied_blocks, 'occupied_blocks')
        
        if not filtered_blocks:
            logger.warning("No valid occupied blocks data after filtering")
            return
        
        # Only process train commands when actual changes are detected
        if has_changes:
            # Update internal state with filtered data
            # Process train movements and send updated commands
            self._process_train_movements(filtered_blocks)
            
            # Send updated commands for affected trains using corrected batched approach
            print(f"  OCCUPANCY UPDATE: Sending updated batched train commands due to block occupancy changes")
            self.send_updated_train_commands()
            
            # Update switches based on new train positions
            self._update_switches_for_routes()
        
        # Forward filtered data to CTC System if connected (always forward for state consistency)
        if self.ctc_system and hasattr(self.ctc_system, 'process_occupied_blocks'):
            self.ctc_system.process_occupied_blocks(filtered_blocks)
    
    def _update_switch_positions_internal(self, switch_positions):
        """
        Internal method to process switch positions update with data filtering
        
        Filter data based on which blocks the sending controller manages.
        Only accept switch position data for switches that the controller is responsible for.
        """
        # Filter switch data based on controller's managed blocks
        filtered_switches = self._filter_wayside_data(switch_positions, 'switch_positions')
        
        if not filtered_switches:
            logger.warning("No valid switch position data after filtering")
            return
        
        # Update internal state with filtered data
        # Forward filtered data to CTC System if connected  
        if self.ctc_system and hasattr(self.ctc_system, 'process_switch_positions'):
            # Determine line from sending controller
            sending_controller = getattr(self, '_current_message_sender', None)
            line_name = "Red" if getattr(sending_controller, 'redLine', False) else "Green"
            self.ctc_system.process_switch_positions(filtered_switches, line_name)
    
    def _update_railway_crossings_internal(self, railway_crossings):
        """
        Internal method to process railway crossings update with data filtering
        
        Filter data based on which blocks the sending controller manages.
        Only accept crossing data for blocks that the controller is responsible for.
        """
        # Filter railway crossing data based on controller's managed blocks
        filtered_crossings = self._filter_wayside_data(railway_crossings, 'railway_crossings')
        
        if not filtered_crossings:
            logger.warning("No valid railway crossing data after filtering")
            return
        
        # Forward filtered data to CTC System if connected
        if self.ctc_system and hasattr(self.ctc_system, 'process_railway_crossings'):
            self.ctc_system.process_railway_crossings(filtered_crossings)
    
    def _filter_wayside_data(self, data, data_type):
        """
        Filter incoming wayside data to only include blocks managed by the sending controller
        
        ENFORCES NEW COMMUNICATION PROTOCOL: Only accepts block-length arrays from controllers
        with proper blocks_covered_bool attribute. No backward compatibility.
        
        Args:
            data: Incoming data from wayside controller (block-length array indexed by block number)
            data_type: Type of data ('occupied_blocks', 'switch_positions', 'railway_crossings')
            
        Returns:
            Filtered data containing only values for blocks the controller manages
            
        Raises:
            ValueError: If controller doesn't have blocks_covered_bool or data format is invalid
        """
        if not data:
            return data
            
        # Get the controller that sent this data from the current message context
        sending_controller = getattr(self, '_current_message_sender', None)
        
        if not sending_controller:
            error_msg = f"PROTOCOL VIOLATION: Could not identify sending controller for {data_type} data. New protocol requires controller identification."
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Use stored block coverage information from internal mapping
        if sending_controller not in self.controller_block_coverage:
            error_msg = f"PROTOCOL VIOLATION: Controller {getattr(sending_controller, 'controller_id', 'Unknown')} not found in block coverage mapping for {data_type}. Controller must be registered via provide_wayside_controller()."
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        blocks_covered = self.controller_block_coverage[sending_controller]
        
        # STRICT REQUIREMENT: Data must be block-length array
        if len(data) != len(blocks_covered):
            error_msg = f"PROTOCOL VIOLATION: {data_type} data length ({len(data)}) does not match expected block-length ({len(blocks_covered)}) for controller {getattr(sending_controller, 'controller_id', 'Unknown')}. New protocol requires block-length arrays."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Filter the data - only keep values for blocks the controller manages
        filtered_data = []
        for i, value in enumerate(data):
            if i < len(blocks_covered) and blocks_covered[i]:
                # Controller manages this block, keep the data
                filtered_data.append(value)
            else:
                # Controller doesn't manage this block, discard the data
                logger.debug(f"Discarding {data_type} data for block {i} (not managed by controller)")
                
        logger.debug(f"Filtered {data_type}: kept {len(filtered_data)} out of {len(data)} values from block-length array")
        return filtered_data
    
    def _calculate_train_commands(self, train, route):
        """
        Calculate suggested speed and authority for a train
        
        Returns:
            Tuple[int, int]: (suggested_speed, authority)
        """
        # Basic implementation - will be enhanced when full system is integrated
        # Note: Obstacle checking removed - will be implemented when monitoring system is integrated
        
        # Normal operation
        return 3, 1  # Full speed, full authority
    
    
    def send_train_commands_for_route(self, train_id: str, route) -> None:
        """
        Send commands when a train is newly routed or rerouted
        
        Args:
            train_id: ID of train being routed
            route: Route object with path and timing information
        """
        if not route or not hasattr(route, 'blockSequence'):
            return
            
        # Store route for switch calculations
        self.active_train_routes[train_id] = route
        
        # Calculate commands for route blocks
        suggested_speeds = []
        authorities = []
        block_nums = []
        update_flags = []
        next_stations = []
        blocks_away = []
        
        for block in route.blockSequence:
            block_id = getattr(block, 'blockID', block)
            
            # All commands are new (simplified - no state tracking)
            update_flag = 0
            
            # Calculate speed and authority for this block using consolidated method
            authority, speed = self.calculate_authority_and_speed(train_id, block_id, route)
            next_station = self._get_next_station_for_route(route, block_id)
            
            # Calculate blocks away from train's current position
            current_position = getattr(route, 'current_block_index', 0)
            blocks_away_distance = self._calculate_blocks_away(current_position, block_id, route)
            
            suggested_speeds.append(speed)
            authorities.append(authority)
            block_nums.append(block_id)
            update_flags.append(update_flag)
            next_stations.append(next_station)
            blocks_away.append(blocks_away_distance)
            
            # Note: Command tracking simplified - no persistent state
        
        # Send commands
        if block_nums:
            # Add terminal output for wayside command sending
            print(f"📡 WAYSIDE COMMANDS: Sending route commands for train {train_id}")
            print(f"   Command blocks: {block_nums}")
            
            self.send_train_commands(suggested_speeds, authorities, block_nums, update_flags, next_stations, blocks_away)
            logger.info(f"Route commands sent for train {train_id} covering blocks {block_nums}")
    
    def send_departure_commands(self, train_id: str, route) -> None:
        """
        Send commands when train departs from yard
        Sends commands for first 4 blocks with 2-second delays to all controllers on line
        
        Args:
            train_id: ID of departing train
            route: Train's route
        """
        import threading
        import time
        
        # DEBUG: Function entry
        print(f"DEBUG: send_departure_commands() called for train {train_id}")

        if not route:
            print(f"DEBUG: send_departure_commands() - No route provided for train {train_id}")
            return
            
        # Get the route blocks - use blockSequence consistently
        route_blocks = []
        if hasattr(route, 'blockSequence') and route.blockSequence:
            route_blocks = [getattr(block, 'blockID', getattr(block, 'block_number', block)) for block in route.blockSequence]
            print(f"DEBUG: Route has {len(route.blockSequence)} blocks in blockSequence")
        else:
            print(f"DEBUG: send_departure_commands() - Route for train {train_id} has no valid blockSequence")
            print(f"DEBUG: Route has blockSequence attr: {hasattr(route, 'blockSequence')}")
            if hasattr(route, 'blockSequence'):
                print(f"DEBUG: blockSequence value: {route.blockSequence}")
            logger.error(f"Route for train {train_id} has no valid block sequence (blockSequence or blocks)")
            return
        
        if not route_blocks:
            print(f"DEBUG: send_departure_commands() - No route blocks found for train {train_id}")
            print(f"DEBUG: route_blocks list: {route_blocks}")
            logger.warning(f"No route blocks found for train {train_id}")
            return
        
        # Determine train line once at outer level
        train_line = self._get_train_line_from_route(route)
        if not train_line:
            train_line = 'Green'  # Default fallback
            print(f"DEBUG: Could not determine train line, using default: {train_line}")
        else:
            print(f"DEBUG: Determined train line: {train_line}")
            
        # Get first 4 blocks for departure commands (excluding yard)
        first_4_blocks = route_blocks[1:5] if len(route_blocks) > 4 else route_blocks[1:]
        
        # Filter controllers to only include those for the train's line (once at outer level)
        line_controllers = []
        for controller in self.wayside_controllers:
            if hasattr(controller, 'redLine'):
                controller_line = 'Red' if controller.redLine else 'Green'
                if controller_line == train_line:
                    line_controllers.append(controller)
        
        if not line_controllers:
            print(f"DEBUG: send_departure_commands() - No controllers found for {train_line} line for train {train_id}")
            print(f"DEBUG: Total controllers available: {len(self.wayside_controllers)}")
            print(f"DEBUG: Available controller details:")
            for i, controller in enumerate(self.wayside_controllers):
                has_red_line = hasattr(controller, 'redLine')
                red_line_value = controller.redLine if has_red_line else 'N/A'
                controller_id = getattr(controller, 'controller_id', f'Controller_{i}')
                print(f"DEBUG:   Controller {controller_id}: redLine={red_line_value}")
            logger.warning(f"No controllers found for {train_line} line for train {train_id} departure")
            return
        
        # Get line length once at outer level
        line_length = self._get_line_length(train_line)
        
        # DEBUG: Success path information
        print(f"DEBUG: Found {len(line_controllers)} controllers for {train_line} line")
        print(f"DEBUG: Route blocks: {route_blocks}")
        print(f"DEBUG: First 4 blocks for departure: {first_4_blocks}")
        print(f"DEBUG: Line length: {line_length}")
        
        # Add terminal output for yard departure commands
        print(f"  YARD DEPARTURE: Sending commands for train {train_id} departure from yard")
        print(f"   Departure commands for blocks: {first_4_blocks}")
        logger.info(f"Departure commands for train {train_id} will be sent to all controllers on {train_line} line for blocks: {first_4_blocks}")
            
        # Send commands for first 4 blocks with simulation-time-aware delays
        def send_sequential_commands():
            for i in range(len(first_4_blocks)):
                
                if i > 0:
                    # Wait for 2 seconds in simulation time
                    start_time = _get_simulation_time()
                    target_time = start_time + timedelta(seconds=2)
                    
                    # Poll simulation time until 2 seconds have passed
                    while _get_simulation_time() < target_time:
                        time.sleep(0.1)  # Small real-time sleep to prevent CPU spinning
                
                block_id = first_4_blocks[i]
                next_station = self._get_next_station_for_route(route, block_id)
                
                # Calculate blocks away from train's current position (starting at yard = block 0)
                blocks_away_distance = i  # Distance from yard to this block (0 for first block, 1 for second, etc.)
                
                # Create dynamic line-length arrays with command at yard position (index 0)
                suggested_speeds = [0] * line_length  # Initialize with stop commands
                authorities = [0] * line_length       # Initialize with no authority
                block_nums = [0] * line_length        # Initialize with zeros - only commanded blocks get actual block numbers
                update_flags = [0] * line_length      # All new commands
                next_stations = [0] * line_length     # No station info by default
                blocks_away = [0] * line_length       # Initialize with zeros - only commanded blocks get actual distances
                
                # Calculate safe authority and speed using centralized method
                # This ensures consistency with regular train commands
                safe_authority, safe_speed = self.calculate_authority_and_speed(train_id, block_id, route)
                
                print(f"DEBUG: Block {block_id} - Safe authority: {safe_authority}, Safe speed: {safe_speed} (centralized calculation)")
                
                # CRITICAL FIX: Set authority at command position (index 0) not target block positions
                # This ensures the Wayside controller receives the correct authority for the departure command
                authorities[0] = safe_authority  # Authority for the command being sent FROM yard TO target block
                
                # Set command for yard position (index 0) with the current block's data using calculated values
                suggested_speeds[0] = safe_speed          # Use calculated safe speed
                block_nums[0] = block_id                  # Set the actual block being commanded
                update_flags[0] = 0                       # New command
                next_stations[0] = next_station           # Next station for this block
                blocks_away[0] = blocks_away_distance     # Distance from yard to this block
                
                # Send command to all controllers on the train's line
                controllers_sent = 0
                
                for controller in line_controllers:
                    try:
                        controller.command_train(
                            suggested_speeds, authorities, block_nums,
                            update_flags, next_stations, blocks_away
                        )
                        controllers_sent += 1
                    except Exception as e:
                        logger.error(f"Failed to send departure command to controller: {e}")
                
                logger.info(f"Departure command {i+1}/4 sent for train {train_id} to block {block_id} broadcasted to {controllers_sent} controllers on {train_line} line")
            
        
        # Start sequential command sending in background thread
        command_thread = threading.Thread(target=send_sequential_commands)
        command_thread.daemon = True
        command_thread.start()
        
        logger.info(f"Started sequential departure commands for train {train_id} from yard to all controllers on {train_line} line")
    
    def _process_train_movements(self, occupied_blocks):
        """Process train movements based on block occupation updates"""
        # Update current occupation state
        # This would map the occupied_blocks list to specific block numbers
        # For now, simplified implementation
        logger.debug("Processing train movements from occupation update")
    
    
    def send_updated_train_commands(self, line_name: str = None) -> None:
        """
        Send updated commands for all trains on specified line(s) when block occupations change.
        Commands are sent TO train's current block FOR block 4 positions ahead in route.
        All trains' commands are batched per line before transmission.
        
        IMPORTANT: Command Structure
        - Commands sent TO train's current block controller
        - blockNum[current_block] = target block 4 positions ahead in route
        - blocksAway[current_block] = route distance to target block (NOT arithmetic difference)
        - Array indexed by current block position, contains commands for target blocks
        
        Args:
            line_name: Specific line to update (Red/Green), or None for all lines
        """
        if not self.ctc_system or not hasattr(self.ctc_system, 'trains'):
            logger.debug("No CTC system available for updated train commands")
            return
        
        # Determine which lines to process
        lines_to_process = []
        if line_name:
            lines_to_process = [line_name]
        else:
            lines_to_process = ['Red', 'Green', 'Blue']  # Process all lines
        
        for line in lines_to_process:
            # Collect all trains on this line
            trains_on_line = []
            
            for train_id, train in self.ctc_system.trains.items():
                # Check if train has active route and is on this line
                if (hasattr(train, 'route') and train.route and 
                    hasattr(train.route, 'isActive') and train.route.isActive and
                    hasattr(train, 'currentBlock') and train.currentBlock):
                    
                    # Determine train's line from current block
                    current_block_id = getattr(train.currentBlock, 'blockID', train.currentBlock)
                    train_line = self._get_line_for_block(current_block_id)
                    
                    if train_line == line:
                        trains_on_line.append((train_id, train))
            
            if not trains_on_line:
                logger.debug(f"No active trains found on {line} line")
                continue
            
            # Get line length for command arrays
            line_length = self._get_line_length(line)
            if line_length <= 0:
                logger.error(f"Invalid line length for {line} line: {line_length}")
                continue
            
            # Initialize command arrays for entire line (indexed by current block)
            suggested_speeds = [0] * line_length    # Default to stop
            authorities = [0] * line_length         # Default to no authority  
            block_nums = [0] * line_length          # Target block IDs (4 positions ahead)
            update_flags = [0] * line_length        # All new commands
            next_stations = [0] * line_length       # Station IDs
            blocks_away = [0] * line_length         # Route distances
            
            # Process each train and add commands to arrays
            for train_id, train in trains_on_line:
                try:
                    # Get train's current position
                    current_block_id = getattr(train.currentBlock, 'blockID', train.currentBlock)
                    route = train.route
                    
                    # Validate current block is within line bounds
                    if current_block_id >= line_length:
                        logger.warning(f"Train {train_id} current block {current_block_id} exceeds line length {line_length}")
                        continue
                    
                    # Calculate target block (4 positions ahead in route)
                    # COMMAND LOGIC: Find the block that is 4 route positions ahead of train's current position
                    target_block_id = self._get_target_block_for_train(train_id, route, 4)
                    if target_block_id is None:
                        logger.debug(f"No target block found for train {train_id}")
                        continue
                    
                    # Calculate route distance using route's new method
                    # ROUTE DISTANCE: This is the number of route hops (not arithmetic difference)
                    # Example: route=[1,5,3,8], current=1, target=8 -> distance=3 hops (1->5->3->8)
                    route_distance = 0
                    if hasattr(route, 'calculate_route_distance'):
                        # Use new route-based distance calculation (preferred)
                        route_distance = route.calculate_route_distance(current_block_id, target_block_id)
                    else:
                        # Fallback calculation using older method
                        route_distance = self._calculate_blocks_away_for_train(train_id, target_block_id, route)
                    
                    # Calculate authority and speed for target block
                    # SAFETY LOGIC: These commands apply when train reaches the target block
                    authority, speed = self.calculate_authority_and_speed(train_id, target_block_id, route)
                    
                    # Get next station for train
                    # STATION LOGIC: Determine which station the train is heading to
                    next_station = self._get_next_station_for_route(route, target_block_id)
                    
                    # Set commands in arrays at current block position
                    # CRITICAL ARRAY STRUCTURE:
                    # - Array index = train's CURRENT block (where train is now)
                    # - Array values = commands for TARGET block (where train will be)
                    # - blockNum[current] = target block ID (NOT current block ID)
                    # - blocksAway[current] = route distance from current to target
                    # - Commands sent TO current block controller FOR target block
                    suggested_speeds[current_block_id] = speed            # Speed for target block
                    authorities[current_block_id] = authority             # Authority for target block  
                    block_nums[current_block_id] = target_block_id        # TARGET block ID (4 ahead)
                    update_flags[current_block_id] = 0                   # New command
                    next_stations[current_block_id] = next_station       # Station train is going to
                    blocks_away[current_block_id] = route_distance       # Route hops (not arithmetic)
                    
                    logger.debug(f"Commands set for train {train_id}: current={current_block_id}, target={target_block_id}, distance={route_distance}")
                    
                except Exception as e:
                    logger.error(f"Error processing commands for train {train_id}: {e}")
                    continue
            
            # Send batched commands for entire line
            if any(block_nums):  # Only send if we have actual commands
                print(f"📡 BATCHED COMMANDS: Sending updated commands for {len(trains_on_line)} trains on {line} line")
                print(f"   Target blocks: {[block_id for block_id in block_nums if block_id > 0]}")
                
                self.send_train_commands(
                    suggested_speeds, authorities, block_nums,
                    update_flags, next_stations, blocks_away
                )
                logger.info(f"Batched commands sent for {len(trains_on_line)} trains on {line} line")
            else:
                logger.debug(f"No commands to send for {line} line")
    
    def _get_line_for_block(self, block_id: int) -> str:
        """
        Determine which line a block belongs to
        
        Args:
            block_id: Block ID to check
            
        Returns:
            Line name ('Red', 'Green', 'Blue') or None if not found
        """
        # Check which controller manages this block
        if block_id in self.block_to_controller:
            controller = self.block_to_controller[block_id]
            if hasattr(controller, 'redLine'):
                return 'Red' if controller.redLine else 'Green'
            else:
                # Try to determine line from controller ID if red_line attribute missing
                controller_id = getattr(controller, 'controller_id', '')
                if 'Red' in controller_id:
                    return 'Red'
                elif 'Blue' in controller_id:
                    return 'Blue'
                else:
                    # Default to Green for unknown controllers
                    return 'Green'
        
        # Fallback: check CTC system blocks
        if self.ctc_system and hasattr(self.ctc_system, 'blocks'):
            for (line, block_num), block in self.ctc_system.blocks.items():
                if getattr(block, 'blockID', block_num) == block_id:
                    return line
        
        logger.warning(f"Could not determine line for block {block_id}")
        return None
    
    def _get_target_block_for_train(self, train_id: str, route, positions_ahead: int = 4) -> Optional[int]:
        """
        Get target block ID for train (positions_ahead blocks ahead in route)
        
        Args:
            train_id: Train ID
            route: Train's route object
            positions_ahead: Number of positions ahead to look (default 4)
            
        Returns:
            Target block ID or None if not found
        """
        if not route or not hasattr(route, 'blockSequence') or not route.blockSequence:
            return None
        
        # Get current position in route
        current_index = getattr(route, 'currentBlockIndex', 0)
        target_index = current_index + positions_ahead
        
        # Check if target index is within route bounds
        if target_index >= len(route.blockSequence):
            # Use last block in route if we've gone past the end
            target_index = len(route.blockSequence) - 1
        
        # Get target block
        target_block = route.blockSequence[target_index]
        target_block_id = getattr(target_block, 'blockID', getattr(target_block, 'block_number', target_block))
        
        logger.debug(f"Train {train_id} target block: index {target_index}, block {target_block_id}")
        return target_block_id
    
    def _update_switches_for_routes(self):
        """Update switch positions based on active train routes"""
        # First, manage all junctions
        self.manage_junctions()
        
        # Then update other switches
        switch_commands = {}
        
        # Switch positions are now determined by wayside controllers based on train commands
        logger.debug("Switch control delegated to wayside controllers")
    
    
    def _determine_switch_position(self, switch_block_id: int, switch_block) -> bool:
        """
        Determine required switch position for a specific switch
        Returns: False (0) for normal/lower block connection, True (1) for reverse/higher block
        """
        # Use generic junction switch calculation
        
        # Check all active routes to see which way the switch should be set
        for train_id, route in self.active_train_routes.items():
            if not route or not hasattr(route, 'blockSequence'):
                continue
                
            route_blocks = [getattr(b, 'blockID', b) for b in route.blockSequence]
            
            # Find if this switch is in the route
            try:
                switch_index = route_blocks.index(switch_block_id)
                
                # Determine which way train needs to go
                if switch_index > 0 and switch_index < len(route_blocks) - 1:
                    prev_block = route_blocks[switch_index - 1]
                    next_block = route_blocks[switch_index + 1]
                    
                    # Get connected blocks for this switch
                    connected_blocks = []
                    if hasattr(switch_block, 'connected_blocks'):
                        connected_blocks = switch_block.connected_blocks
                    elif hasattr(switch_block, 'switch') and switch_block.switch:
                        # Extract from switch object
                        switch_obj = switch_block.switch
                        if hasattr(switch_obj, 'connections'):
                            for conn in switch_obj.connections:
                                if hasattr(conn, 'from_block') and conn.from_block == switch_block_id:
                                    connected_blocks.append(conn.to_block)
                                elif hasattr(conn, 'to_block') and conn.to_block == switch_block_id:
                                    connected_blocks.append(conn.from_block)
                    
                    # Determine position based on next block
                    # Normal (0) typically connects to lower numbered block
                    # Reverse (1) connects to higher numbered block
                    if connected_blocks:
                        lower_connections = [b for b in connected_blocks if b < switch_block_id and b != 0]
                        higher_connections = [b for b in connected_blocks if b > switch_block_id]
                        
                        if next_block in higher_connections:
                            return True  # Reverse position
                        elif next_block in lower_connections:
                            return False  # Normal position
                        else:
                            # Check if coming from a higher/lower block
                            if prev_block > switch_block_id and next_block < switch_block_id:
                                return False  # Normal - going to lower
                            elif prev_block < switch_block_id and next_block > switch_block_id:
                                return True  # Reverse - going to higher
            except ValueError:
                # Switch not in this route
                continue
        
        # Default to normal position if no active route requires this switch
        return False
    
    def manage_junctions(self) -> None:
        """
        Manage junction blocks by analyzing train approaches and optimizing switch positions
        
        This method identifies junction blocks (blocks with switches and multiple connections),
        analyzes trains approaching these junctions, and calculates optimal configurations
        to minimize delays and conflicts.
        """
        if not self.ctc_system or not hasattr(self.ctc_system, 'blocks'):
            logger.debug("No CTC system available for junction management")
            return
        
        # Identify junction blocks (blocks with switches)
        junction_blocks = []
        # Iterate through line-aware block storage
        for (line, block_id), block in self.ctc_system.blocks.items():
            if hasattr(block, 'has_switch') and block.has_switch:
                junction_blocks.append(block_id)
        
        if not junction_blocks:
            logger.debug("No junction blocks found for management")
            return
        
        # Process each junction
        for junction_id in junction_blocks:
            try:
                # Find trains approaching this junction
                trains_near_junction = self._find_trains_near_junction(junction_id)
                
                if not trains_near_junction:
                    continue
                
                # Calculate optimal junction configuration
                config = self._calculate_optimal_junction_config(trains_near_junction, junction_id)
                
                if config:
                    # Apply the calculated configuration
                    self._apply_junction_configuration(config, junction_id)
                    logger.debug(f"Junction {junction_id} managed: {len(trains_near_junction)} trains coordinated")
            
            except Exception as e:
                logger.error(f"Error managing junction {junction_id}: {e}")
    
    def _find_trains_near_junction(self, junction_id: int) -> List[dict]:
        """
        Find trains that are approaching or at a specific junction
        
        Args:
            junction_id: ID of the junction block
            
        Returns:
            List of train info dictionaries with train_id, route, and priority
        """
        trains_near_junction = []
        
        # Check all active train routes
        for train_id, route in self.active_train_routes.items():
            if not route or not hasattr(route, 'blockSequence'):
                continue
            
            route_blocks = [getattr(b, 'blockID', b) for b in route.blockSequence]
            
            # Check if junction is in this train's route
            if junction_id in route_blocks:
                # Simplified: Use route information for position (no complex tracking)
                train_current_block = None
                if hasattr(route, 'currentBlockIndex') and hasattr(route, 'blockSequence'):
                    if route.currentBlockIndex < len(route.blockSequence):
                        current_block = route.blockSequence[route.currentBlockIndex]
                        train_current_block = getattr(current_block, 'blockID', current_block)
                
                if train_current_block is not None:
                    try:
                        # Calculate distance to junction
                        current_index = route_blocks.index(train_current_block)
                        junction_index = route_blocks.index(junction_id)
                        distance_to_junction = junction_index - current_index
                        
                        # Consider trains within 5 blocks of junction
                        if -2 <= distance_to_junction <= 5:
                            priority = self._calculate_train_priority(train_id, route, junction_id)
                            trains_near_junction.append({
                                'train_id': train_id,
                                'route': route,
                                'current_block': train_current_block,
                                'distance_to_junction': distance_to_junction,
                                'priority': priority
                            })
                    except ValueError:
                        # Block not found in route, skip
                        continue
        
        return trains_near_junction
    
    
    def _calculate_train_priority(self, train_id: str, route, junction_id: int = None) -> int:
        """
        Calculate priority for train at junction (higher number = higher priority)
        """
        priority = 1  # Base priority
        
        # Higher priority for trains already in the junction
        if hasattr(route, 'currentBlockIndex') and hasattr(route, 'blockSequence'):
            if route.currentBlockIndex < len(route.blockSequence):
                current_block = route.blockSequence[route.currentBlockIndex]
                current_block_id = getattr(current_block, 'blockID', current_block)
                if junction_id and current_block_id == junction_id:  # At this junction
                    priority += 10
        
        # Higher priority for trains with tight schedules
        if hasattr(route, 'scheduledArrival') and route.scheduledArrival:
            from datetime import datetime, timedelta
            time_to_arrival = route.scheduledArrival - _get_simulation_time()
            if time_to_arrival < timedelta(minutes=5):
                priority += 5
        
        # Higher priority for trains from main line
        route_blocks = []
        if hasattr(route, 'blockSequence'):
            route_blocks = [getattr(b, 'blockID', b) for b in route.blockSequence]
        
        main_line_blocks = set(range(1, 31))
        if any(block in main_line_blocks for block in route_blocks):
            priority += 3
        
        return priority
    
    def _calculate_optimal_junction_config(self, trains_near_junction: List[dict], junction_id: int = None) -> dict:
        """
        Calculate optimal junction configuration to minimize delays
        
        Args:
            trains_near_junction: List of train info dictionaries
            junction_id: ID of the junction block (extracted from train info if not provided)
        """
        if not trains_near_junction:
            return None
        
        # Extract junction_id from train info if not provided
        if junction_id is None and trains_near_junction:
            # Try to find a common junction from the train routes
            for train_info in trains_near_junction:
                route = train_info['route']
                if hasattr(route, 'blockSequence'):
                    route_blocks = [getattr(b, 'blockID', b) for b in route.blockSequence]
                    # Find junction blocks with switches
                    if self.ctc_system:
                        for block_id in route_blocks:
                            # Use new block lookup method
                            block = self.ctc_system.get_block_by_number(block_id)
                            if block and hasattr(block, 'has_switch') and block.has_switch:
                                junction_id = block_id
                                break
                    if junction_id:
                        break
        
        # Sort trains by priority
        trains_near_junction.sort(key=lambda t: t['priority'], reverse=True)
        
        # Analyze train movements through junction
        config = {
            'switch_position': False,  # Default to normal (main line)
            'train_sequence': [],
            'delays': []
        }
        
        # Determine optimal switch position based on highest priority train
        highest_priority_train = trains_near_junction[0]
        route = highest_priority_train['route']
        
        if junction_id and hasattr(route, 'blockSequence'):
            route_blocks = [getattr(b, 'blockID', b) for b in route.blockSequence]
            
            # Find junction in the route
            if junction_id in route_blocks:
                junction_index = route_blocks.index(junction_id)
                
                # Determine required switch position
                if junction_index > 0 and junction_index < len(route_blocks) - 1:
                    prev_block = route_blocks[junction_index - 1]
                    next_block = route_blocks[junction_index + 1]
                    
                    # Get junction block to determine switch position
                    if self.ctc_system:
                        # Use new block lookup method
                        junction_block = self.ctc_system.get_block_by_number(junction_id)
                        if junction_block:
                            config['switch_position'] = self._determine_switch_position(junction_id, junction_block)
        
        # Calculate sequence and delays for all trains
        total_delay = 0
        for i, train_info in enumerate(trains_near_junction):
            sequence_delay = i * 30  # 30 second separation between trains
            config['train_sequence'].append(train_info['train_id'])
            config['delays'].append(sequence_delay)
            total_delay += sequence_delay
        
        config['total_delay'] = total_delay
        return config
    
    def _apply_junction_configuration(self, config: dict, junction_id: int) -> None:
        """
        Apply the calculated junction configuration
        """
        # Find controller for this junction
        junction_controller = None
        for controller in self.wayside_controllers:
            if hasattr(controller, 'managedBlocks') and junction_id in controller.managedBlocks:
                junction_controller = controller
                break
        
        if junction_controller:
            # Note: Switch control has been removed from CTC - wayside controllers now handle switch positioning
            logger.info(f"Junction {junction_id} identified for configuration: switch={'reverse' if config['switch_position'] else 'normal'}, sequence={config['train_sequence']}")
    
    def calculate_authority_and_speed(self, train_id: str, block_id: int, route) -> tuple[int, int]:
        """
        Calculate authority and suggested speed for a train in a specific block using Block class methods.
        This is the centralized method used by both regular train commands and yard departures.
        
        Args:
            train_id: ID of the train
            block_id: Block number being commanded
            route: Train's route object
            
        Returns:
            Tuple of (authority, suggested_speed)
            authority: 0 = no authority, 1 = authority granted
            suggested_speed: 0=stop, 1=1/3, 2=2/3, 3=full speed
        """
        # Get the target block object from CTC system
        target_block = None
        if hasattr(self, 'ctc_system') and self.ctc_system:
            # Try both get_block and get_block_by_number methods for compatibility
            if hasattr(self.ctc_system, 'get_block'):
                # Determine line from route or block_id
                train_line = self._get_train_line_from_route(route) if route else 'Green'
                target_block = self.ctc_system.get_block_by_line(train_line, block_id)
            elif hasattr(self.ctc_system, 'get_block_by_number'):
                target_block = self.ctc_system.get_block_by_number(block_id)
        
        if not target_block:
            logger.warning(f"Block {block_id} not found for authority/speed calculation")
            return 0, 0
        
        # Use Block class methods for safety calculations (same as send_departure_commands)
        # Calculate safe authority using Block's built-in safety checks
        safe_authority = target_block.calculate_safe_authority()
        
        # Get next blocks from route for speed calculation
        next_block_1 = None
        next_block_2 = None
        
        if route and hasattr(route, 'blockSequence'):
            route_blocks = [getattr(block, 'blockID', getattr(block, 'block_number', block)) for block in route.blockSequence]
            
            # Find current block in route to get next blocks
            try:
                current_index = route_blocks.index(block_id)
                
                # Get next block objects for speed calculation
                if current_index + 1 < len(route.blockSequence):
                    next_block_1 = route.blockSequence[current_index + 1]
                if current_index + 2 < len(route.blockSequence):
                    next_block_2 = route.blockSequence[current_index + 2]
            except ValueError:
                # Block not found in route - use defaults
                pass
        
        # Calculate safe speed using Block's built-in safety checks with next block context
        safe_speed = target_block.calculate_suggested_speed(next_block_1, next_block_2)
        
        logger.debug(f"Train {train_id} Block {block_id}: Authority={safe_authority}, Speed={safe_speed} (using Block class methods)")
        return safe_authority, safe_speed
    
    
    
    def _get_block_by_id(self, block_id: int):
        """Get block object by ID from CTC system"""
        if self.ctc_system and hasattr(self.ctc_system, 'get_block_by_number'):
            return self.ctc_system.get_block_by_number(block_id)
        return None
    
    def _check_bidirectional_conflict(self, block_id: int, route) -> bool:
        """
        Check if block is on a bidirectional section with opposing traffic
        """
        # Get the block object
        block = self._get_block_by_id(block_id)
        if not block:
            return False
        
        # Check if this is a bidirectional block
        if not (hasattr(block, 'bidirectional') and block.bidirectional):
            return False
        
        # Check for trains moving in opposite direction on this bidirectional section
        if not self.ctc_system or not hasattr(self.ctc_system, 'trains'):
            return False
        
        # Get the direction this train is traveling
        route_blocks = []
        if hasattr(route, 'blockSequence'):
            route_blocks = [getattr(b, 'blockID', b) for b in route.blockSequence]
        
        if block_id not in route_blocks:
            return False
        
        block_index = route_blocks.index(block_id)
        train_direction = None
        
        # Determine direction based on surrounding blocks
        if block_index > 0:
            prev_block = route_blocks[block_index - 1]
            train_direction = 'increasing' if prev_block < block_id else 'decreasing'
        elif block_index < len(route_blocks) - 1:
            next_block = route_blocks[block_index + 1]
            train_direction = 'increasing' if block_id < next_block else 'decreasing'
        
        # Check other trains for opposite direction movement
        for other_train_id, other_train in self.ctc_system.trains.items():
            if not hasattr(other_train, 'route') or not other_train.route:
                continue
            
            other_route = other_train.route
            if not hasattr(other_route, 'blockSequence'):
                continue
            
            other_route_blocks = [getattr(b, 'blockID', b) for b in other_route.blockSequence]
            
            # Check if other train is also on this bidirectional section
            if block_id in other_route_blocks:
                other_block_index = other_route_blocks.index(block_id)
                other_direction = None
                
                # Determine other train's direction
                if other_block_index > 0:
                    other_prev_block = other_route_blocks[other_block_index - 1]
                    other_direction = 'increasing' if other_prev_block < block_id else 'decreasing'
                elif other_block_index < len(other_route_blocks) - 1:
                    other_next_block = other_route_blocks[other_block_index + 1]
                    other_direction = 'increasing' if block_id < other_next_block else 'decreasing'
                
                # Conflict if trains are moving in opposite directions
                if train_direction and other_direction and train_direction != other_direction:
                    logger.debug(f"Bidirectional conflict: train moving {train_direction}, other train moving {other_direction}")
                    return True
        
        return False
    
    def _check_switch_conflict(self, block_id: int, route) -> bool:
        """
        Check if block is on other side of switch that hasn't been flipped
        """
        # Get the block object
        block = self._get_block_by_id(block_id)
        if not block:
            return False
        
        # Get route blocks to understand train path
        route_blocks = []
        if hasattr(route, 'blockSequence'):
            route_blocks = [getattr(b, 'blockID', b) for b in route.blockSequence]
        
        if block_id not in route_blocks:
            return False
        
        block_index = route_blocks.index(block_id)
        
        # Check if there's a switch between this block and the previous block
        if block_index > 0:
            prev_block_id = route_blocks[block_index - 1]
            prev_block = self._get_block_by_id(prev_block_id)
            
            # Check if previous block has a switch
            if prev_block and hasattr(prev_block, 'has_switch') and prev_block.has_switch:
                # Check if switch is positioned correctly for this route
                required_position = self._determine_switch_position(prev_block_id, prev_block)
                current_position = self.current_switch_positions.get(prev_block_id, False)
                
                if required_position != current_position:
                    logger.debug(f"Switch conflict: block {prev_block_id} needs position {required_position}, currently {current_position}")
                    return True
        
        return False
    
    def _find_nearest_stopped_train(self, block_id: int, route) -> Optional[int]:
        """
        Find the nearest stopped train ahead on the route
        Returns distance in blocks (1, 2, 3) or None if no stopped train
        """
        if not self.ctc_system or not hasattr(self.ctc_system, 'trains'):
            return None
        
        # Get route blocks
        route_blocks = []
        if hasattr(route, 'blockSequence'):
            route_blocks = [getattr(b, 'blockID', b) for b in route.blockSequence]
        
        if block_id not in route_blocks:
            return None
        
        block_index = route_blocks.index(block_id)
        
        # Check blocks ahead (up to 3 blocks)
        for distance in range(1, 4):
            check_index = block_index + distance
            if check_index >= len(route_blocks):
                break
            
            check_block_id = route_blocks[check_index]
            
            # Check if any train is stopped in this block
            for train_id, train in self.ctc_system.trains.items():
                if hasattr(train, 'currentBlock') and hasattr(train, 'speedKmh'):
                    train_block = getattr(train.currentBlock, 'blockID', train.currentBlock)
                    train_speed = getattr(train, 'speedKmh', 0)
                    
                    if train_block == check_block_id and train_speed == 0:
                        return distance
        
        return None
    
    def _find_nearest_station(self, block_id: int, route) -> Optional[int]:
        """
        Find the nearest station ahead on the route
        Returns distance in blocks (1, 2) or None if no station
        """
        if not hasattr(route, 'blockSequence'):
            return None
        
        route_blocks = []
        if hasattr(route, 'blockSequence'):
            route_blocks = [getattr(b, 'blockID', b) for b in route.blockSequence]
        
        if block_id not in route_blocks:
            return None
        
        block_index = route_blocks.index(block_id)
        
        # Check blocks ahead (up to 2 blocks for station approach)
        for distance in range(1, 3):
            check_index = block_index + distance
            if check_index >= len(route_blocks):
                break
            
            check_block_id = route_blocks[check_index]
            check_block = self._get_block_by_id(check_block_id)
            
            if check_block and hasattr(check_block, 'has_station') and check_block.has_station:
                return distance
        
        return None
    
    def _get_station_id_for_block(self, block_number: int) -> int:
        """Get station ID for a given block number"""
        if not self.track_reader:
            logger.warning("Track reader not available for station lookup")
            return 0
            
        try:
            block = self.track_reader.get_block_by_number(block_number)
            if block and block.has_station and block.station:
                return block.station.station_id
        except Exception as e:
            logger.error(f"Error getting station ID for block {block_number}: {e}")
        
        return 0

    def _get_next_station_for_route(self, route, current_block: int) -> int:
        """Get next station ID for train on route"""
        if hasattr(route, 'endBlock'):
            destination_block_id = getattr(route.endBlock, 'blockID', 0)
            station_id = self._get_station_id_for_block(destination_block_id)
            
            # Add validation logging
            if station_id > 100:
                logger.warning(f"Station ID {station_id} seems too high - might be block number instead")
            elif station_id > 0:
                logger.debug(f"Route destination: Block {destination_block_id} -> Station ID {station_id}")
            else:
                logger.debug(f"No station found for destination block {destination_block_id}")
                
            return station_id
        return 0
    
    def _calculate_blocks_away(self, current_position: int, target_block_id: int, route) -> int:
        """
        Calculate blocks away from train's current position to target block
        Positive means higher block numbers, negative means lower block numbers
        """
        if not hasattr(route, 'blockSequence') or not route.blockSequence:
            return 0
        
        try:
            # Find current block in route sequence
            if current_position < len(route.blockSequence):
                current_block = route.blockSequence[current_position]
                current_block_id = getattr(current_block, 'blockID', current_block)
                
                # Find target block in route sequence  
                target_index = None
                for i, block in enumerate(route.blockSequence):
                    block_id = getattr(block, 'blockID', block)
                    if block_id == target_block_id:
                        target_index = i
                        break
                
                if target_index is not None:
                    # Calculate distance based on route sequence position
                    distance = target_index - current_position
                    return distance
                    
        except (AttributeError, IndexError, TypeError):
            logger.warning(f"Could not calculate blocks away for target {target_block_id}")
        
        # Fallback: simple block number difference
        if hasattr(route, 'blockSequence') and route.blockSequence:
            try:
                current_block = route.blockSequence[current_position] if current_position < len(route.blockSequence) else route.blockSequence[0]
                current_block_id = getattr(current_block, 'blockID', current_block)
                return target_block_id - current_block_id
            except (AttributeError, IndexError):
                # Route or position data invalid - return default
                return 0
                
        return 0
    
    def _calculate_blocks_away_for_train(self, train_id: str, target_block_id: int, route) -> int:
        """
        Calculate blocks away from a train's current position to target block (simplified)
        
        Args:
            train_id: ID of the train
            target_block_id: Block to calculate distance to
            route: Train's route
            
        Returns:
            Distance in blocks (positive = ahead, negative = behind)
        """
        # Simplified: Use route information for position (no complex tracking)
        train_current_block = None
        if hasattr(route, 'currentBlockIndex') and hasattr(route, 'blockSequence'):
            if route.currentBlockIndex < len(route.blockSequence):
                current_block = route.blockSequence[route.currentBlockIndex]
                train_current_block = getattr(current_block, 'blockID', current_block)
        
        if train_current_block is None:
            logger.warning(f"Could not determine current block for train {train_id} from route")
            return 0
        
        # Use the route sequence to calculate distance
        if hasattr(route, 'blockSequence') and route.blockSequence:
            try:
                # Find current block index in route
                current_index = route.currentBlockIndex if hasattr(route, 'currentBlockIndex') else 0
                target_index = None
                
                for i, block in enumerate(route.blockSequence):
                    block_id = getattr(block, 'blockID', block)
                    if block_id == target_block_id:
                        target_index = i
                        break
                
                if target_index is not None:
                    return target_index - current_index
            except (AttributeError, IndexError, TypeError):
                logger.warning(f"Could not calculate blocks away for train {train_id} to block {target_block_id}")
        
        # Fallback: simple block number difference
        return target_block_id - train_current_block
    
    def _check_block_obstacles(self, block_id: int) -> bool:
        """Check if block has obstacles"""
        return self.current_occupied_blocks.get(block_id, False)
    
    def _is_block_on_route(self, block_id: int, route) -> bool:
        """Check if block is part of the route"""
        if hasattr(route, 'blockSequence'):
            route_blocks = [getattr(b, 'blockID', b) for b in route.blockSequence]
            return block_id in route_blocks
        return False
    
    def _update_commands_for_train_position(self, train_id: str, route):
        """
        Update commands based on train's new position (simplified)
        
        Args:
            train_id: ID of train that moved
            route: Train's current route
        """
        if not route or train_id not in self.active_train_routes:
            return
            
        # Simplified: Just log the event, detailed tracking removed
        logger.debug(f"Position update for train {train_id} - using simplified event-driven communication")
    
    def _get_controller_line_name(self, controller) -> str:
        """Get line name for a controller"""
        if hasattr(controller, 'redLine'):
            return 'Red' if controller.redLine else 'Green'
        return None
    
    def _get_line_length(self, line_name: str) -> int:
        """
        Get total number of blocks for a line dynamically from track data
        
        Priority 1: Use track_reader.lines which includes yard (block 0) + actual track blocks
        Priority 2: Use ctc_system.blocks for dynamic counting
        Priority 3: Error handling - no hardcoded fallbacks
        
        Args:
            line_name: Name of the line ('Red', 'Green', 'Blue')
            
        Returns:
            Total number of blocks on the line including yard (block 0)
        """
        # Priority 1: Use track reader data (includes yard + track blocks)
        if self.track_reader and hasattr(self.track_reader, 'lines'):
            line_blocks = self.track_reader.lines.get(line_name, [])
            if line_blocks:
                line_length = len(line_blocks)
                logger.debug(f"Line length for {line_name}: {line_length} blocks (from track_reader)")
                return line_length
                
        # Priority 2: Use CTC system block data for dynamic counting
        elif self.ctc_system and hasattr(self.ctc_system, 'blocks'):
            line_blocks = [block_id for (line, block_id), block in self.ctc_system.blocks.items() if line == line_name]
            if line_blocks:
                line_length = max(line_blocks) + 1  # +1 because blocks are 0-indexed
                logger.debug(f"Line length for {line_name}: {line_length} blocks (from ctc_system)")
                return line_length
                
        # Priority 3: No track data available - this should not happen in normal operation
        logger.error(f"Cannot determine line length for {line_name} - no track data available from track_reader or ctc_system")
        logger.error(f"track_reader available: {self.track_reader is not None}, ctc_system available: {self.ctc_system is not None}")
        
        # Return 0 to indicate error - calling code should handle this
        return 0
    
    def _get_switch_anchor_blocks_for_line(self, line_name: str, controller) -> List[int]:
        """
        Get switch anchor blocks for a line that this controller manages
        
        Args:
            line_name: Name of the line ('Red', 'Green', 'Blue')
            controller: Controller to check for switches
            
        Returns:
            List of block numbers that are switch anchor blocks
        """
        anchor_blocks = []
        
        if not hasattr(controller, 'managedBlocks'):
            return anchor_blocks
            
        # Check each block the controller manages to see if it has a switch
        for block_id in controller.managedBlocks:
            if self.ctc_system:
                block = self.ctc_system.get_block_by_number(block_id)
                if block and hasattr(block, 'has_switch') and block.has_switch:
                    # This block has a switch, so it's an anchor block
                    anchor_blocks.append(block_id)
        
        return sorted(anchor_blocks)
    
    def shutdown(self):
        """Shutdown the communication handler"""
        self._running = False
        if self._message_thread.is_alive():
            self._message_thread.join()
        logger.info("Communication Handler shutdown complete")