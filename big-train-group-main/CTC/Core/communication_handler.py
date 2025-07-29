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
- command_train(): Send block-specific commands to wayside
- command_switch(): Send switch position commands
- set_occupied(): Manual block occupation control
- send_train_commands_for_route(): Event-driven command sending
- send_departure_commands(): Yard departure commands
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime
from queue import Queue, Empty
import threading
import logging

# Set up logging
logger = logging.getLogger(__name__)


class CommunicationHandler:
    """
    Communication Handler implementing UML interface
    Manages all external communications for the CTC system
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
        self.message_queue = Queue()   # Thread-safe message queue
        self.ctc_system = None        # Reference to CTC System
        
        # Track current state
        self.current_occupied_blocks = {}  # Dict[int, bool] - block_number -> occupied
        self.current_switch_positions = {} # Dict[int, bool] - switch_id -> position
        self.current_railway_crossings = {} # Dict[int, bool] - crossing_id -> active
        
        # Track previous commands for updatePreviousFlag detection
        self.previous_block_commands = {}  # Dict[int, Dict] - block_num -> {speed, authority, timestamp}
        self.active_train_routes = {}      # Dict[str, Route] - train_id -> route for switch calculation
        
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
    
    def update_occupied_blocks(self, occupiedBlocks: List[bool]) -> None:
        """
        Receive occupation status from wayside controller
        
        Args:
            occupiedBlocks: List of boolean values indicating block occupation
        """
        message = {
            'type': 'occupied_blocks_update',
            'data': occupiedBlocks,
            'timestamp': datetime.now()
        }
        self.message_queue.put(message)
        logger.debug(f"Received occupied blocks update: {len(occupiedBlocks)} blocks")
    
    def update_switch_positions(self, switchPositions: List[bool]) -> None:
        """
        Receive switch positions from wayside controller
        
        Args:
            switchPositions: List of boolean values (0=normal/lower, 1=reverse/higher)
        """
        message = {
            'type': 'switch_positions_update',
            'data': switchPositions,
            'timestamp': datetime.now()
        }
        self.message_queue.put(message)
        logger.debug(f"Received switch positions update: {len(switchPositions)} switches")
    
    def update_railway_crossings(self, railwayCrossings: List[bool]) -> None:
        """
        Receive crossing status from wayside controller
        
        Args:
            railwayCrossings: List of boolean values indicating crossing activation
        """
        message = {
            'type': 'railway_crossings_update',
            'data': railwayCrossings,
            'timestamp': datetime.now()
        }
        self.message_queue.put(message)
        logger.debug(f"Received railway crossings update: {len(railwayCrossings)} crossings")
    
    def schedule_route(self, route) -> None:
        """
        Schedule a train route with wayside
        
        Args:
            route: Route object to schedule
        """
        self.scheduledTrains.append(route)
        
        # Notify wayside controllers about the new route
        for controller in self.wayside_controllers:
            # Check if route passes through this controller's blocks
            route_blocks = route.get_block_sequence() if hasattr(route, 'get_block_sequence') else []
            controller_blocks = set(controller.blocks_covered) if hasattr(controller, 'blocks_covered') else set()
            
            if any(block.blockID in controller_blocks for block in route_blocks if hasattr(block, 'blockID')):
                # This controller needs to know about the route
                self._send_route_to_controller(controller, route)
        
        logger.info(f"Route scheduled: {route}")
    
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
        if block_id and block_id in self.block_to_controller:
            controller = self.block_to_controller[block_id]
            # Notify controller about scheduled closure
            self._send_closure_to_controller(controller, block, time)
        
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
        if block_id and block_id in self.block_to_controller:
            controller = self.block_to_controller[block_id]
            # Notify controller about scheduled opening
            self._send_opening_to_controller(controller, block, time)
        
        logger.info(f"Block opening scheduled: Block {block_id} at {time}")
    
    def send_train_info(self) -> None:
        """
        Legacy method - commands are now sent via events
        Use send_train_commands_for_route() or send_departure_commands() instead
        """
        logger.warning("send_train_info() is deprecated - use event-driven command methods instead")
        
        # For backward compatibility, trigger command updates for all active routes
        for train_id, route in self.active_train_routes.items():
            if route and hasattr(route, 'isActive') and route.isActive:
                self.send_train_commands_for_route(train_id, route)
    
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
                    self.ctc_system.update_throughput(numTickets)
            
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
                block_index = controller.blocks_covered.index(train.currentBlock)
                num_blocks = len(controller.blocks_covered)
                
                # Create command arrays with stop command for train's block
                suggested_speeds = [3] * num_blocks  # Default full speed
                authorities = [1] * num_blocks       # Default authority
                suggested_speeds[block_index] = 0   # STOP
                authorities[block_index] = 0         # No authority
                
                # Use legacy method for emergency stop
                self._legacy_command_train(controller, suggested_speeds, authorities, [0] * num_blocks)
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
        Create occupation list for a specific controller with target block set
        
        Args:
            controller: Wayside controller object
            target_block: Block number to set occupation for
            occupied: True to mark as occupied (closed), False for open
            
        Returns:
            List of boolean values for all blocks in controller's coverage
        """
        if not hasattr(controller, 'blocks_covered'):
            return []
            
        occupation_list = []
        for block in controller.blocks_covered:
            if block == target_block:
                occupation_list.append(occupied)
            else:
                # Preserve current occupation state for other blocks
                occupation_list.append(self.current_occupied_blocks.get(block, False))
                
        return occupation_list
    
    # Additional methods needed for implementation
    
    def provide_wayside_controller(self, waysideController, blocksCovered: List[int]) -> None:
        """
        Called by wayside to register controller and its blocks
        
        Args:
            waysideController: Wayside controller object
            blocksCovered: List of block numbers this controller manages
        """
        self.wayside_controllers.append(waysideController)
        
        # Map blocks to controller
        for block in blocksCovered:
            self.block_to_controller[block] = waysideController
        
        logger.info(f"Wayside controller registered for blocks {blocksCovered[0]}-{blocksCovered[-1]}")
    
    def command_train(self, suggestedSpeed: List[int], authority: List[int], blockNum: List[int], 
                     updatePreviousFlag: List[int], nextStation: List[int]) -> None:
        """
        Send block-specific train commands to wayside controllers
        
        Args:
            suggestedSpeed: List of speed commands (0=stop, 1=1/3, 2=2/3, 3=full) for each block
            authority: List of authority values (0=no, 1=yes) for each block
            blockNum: List of block numbers these commands apply to
            updatePreviousFlag: List indicating if this overwrites previous command (0=new, 1=update)
            nextStation: List of next station IDs for each block's train
        """
        # Group commands by controller
        controller_commands = {}
        
        for i in range(len(blockNum)):
            block = blockNum[i]
            if block in self.block_to_controller:
                controller = self.block_to_controller[block]
                
                if controller not in controller_commands:
                    controller_commands[controller] = {
                        'suggestedSpeed': [],
                        'authority': [],
                        'blockNum': [],
                        'updatePreviousFlag': [],
                        'nextStation': []
                    }
                
                controller_commands[controller]['suggestedSpeed'].append(suggestedSpeed[i])
                controller_commands[controller]['authority'].append(authority[i])
                controller_commands[controller]['blockNum'].append(blockNum[i])
                controller_commands[controller]['updatePreviousFlag'].append(updatePreviousFlag[i])
                controller_commands[controller]['nextStation'].append(nextStation[i])
        
        # Send commands to each controller
        for controller, commands in controller_commands.items():
            if hasattr(controller, 'command_train'):
                controller.command_train(
                    commands['suggestedSpeed'],
                    commands['authority'], 
                    commands['blockNum'],
                    commands['updatePreviousFlag'],
                    commands['nextStation']
                )
                logger.debug(f"Block-specific train commands sent to controller for blocks {commands['blockNum']}")
            else:
                logger.error("Controller does not support command_train method")
    
    def _legacy_command_train(self, controller, suggestedSpeed: List[int], 
                             authority: List[int], numBlocksAhead: List[int]) -> None:
        """
        Legacy method for backward compatibility - converts to new format
        """
        # Convert legacy format to new block-specific format
        if hasattr(controller, 'blocks_covered'):
            blocks = controller.blocks_covered[:len(suggestedSpeed)]
            updateFlags = [0] * len(suggestedSpeed)  # All new commands
            nextStations = [0] * len(suggestedSpeed)  # No station info in legacy
            
            self.command_train(suggestedSpeed, authority, blocks, updateFlags, nextStations)
    
    def command_switch(self, controller, switchPositions: List[bool]) -> None:
        """
        Send switch commands to specific wayside controller
        
        Args:
            controller: Wayside controller object
            switchPositions: List of switch positions (0=normal/lower, 1=reverse/higher)
        """
        if hasattr(controller, 'command_switch'):
            controller.command_switch(switchPositions)
            logger.debug(f"Switch commands sent to controller")
        else:
            logger.error("Controller does not support command_switch method")
    
    def set_occupied(self, controller, blockList: List[bool]) -> None:
        """
        Set block occupation for manual closures
        
        Args:
            controller: Wayside controller object
            blockList: List of occupation states to set
        """
        if hasattr(controller, 'set_occupied'):
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
        
        if msg_type == 'occupied_blocks_update':
            self._update_occupied_blocks_internal(data)
        elif msg_type == 'switch_positions_update':
            self._update_switch_positions_internal(data)
        elif msg_type == 'railway_crossings_update':
            self._update_railway_crossings_internal(data)
    
    def _update_occupied_blocks_internal(self, occupied_blocks):
        """Internal method to process occupied blocks update"""
        # Update internal state
        # TODO: Map to specific blocks based on which controller sent update
        
        # Process train movements and send updated commands
        self._process_train_movements(occupied_blocks)
        
        # Send updated commands for affected trains
        self._send_commands_for_moved_trains()
        
        # Update switches based on new train positions
        self._update_switches_for_routes()
        
        # Forward to CTC System if connected
        if self.ctc_system and hasattr(self.ctc_system, 'process_occupied_blocks'):
            self.ctc_system.process_occupied_blocks(occupied_blocks)
    
    def _update_switch_positions_internal(self, switch_positions):
        """Internal method to process switch positions update"""
        # Update internal state
        # TODO: Map to specific switches based on which controller sent update
        
        # Forward to CTC System if connected
        if self.ctc_system and hasattr(self.ctc_system, 'process_switch_positions'):
            self.ctc_system.process_switch_positions(switch_positions)
    
    def _update_railway_crossings_internal(self, railway_crossings):
        """Internal method to process railway crossings update"""
        # Update internal state
        # TODO: Map to specific crossings based on which controller sent update
        
        # Forward to CTC System if connected
        if self.ctc_system and hasattr(self.ctc_system, 'process_railway_crossings'):
            self.ctc_system.process_railway_crossings(railway_crossings)
    
    def _calculate_train_commands(self, train, route):
        """
        Calculate suggested speed and authority for a train
        
        Returns:
            Tuple[int, int]: (suggested_speed, authority)
        """
        # Basic implementation - will be enhanced when full system is integrated
        # Check for obstacles ahead
        if self._check_obstacles_ahead(train, route):
            return 0, 0  # Stop, no authority
        
        # Normal operation
        return 3, 1  # Full speed, full authority
    
    def _check_obstacles_ahead(self, train, route):
        """Check for obstacles in train's path"""
        # TODO: Implement full obstacle checking
        # - Check for other trains
        # - Check for closed blocks
        # - Check for switch conflicts
        return False
    
    def _send_route_to_controller(self, controller, route):
        """Send route information to a specific controller"""
        # TODO: Implement route communication protocol
        pass
    
    def _send_closure_to_controller(self, controller, block, time):
        """Send closure information to a specific controller"""
        # TODO: Implement closure communication protocol
        pass
    
    def _send_opening_to_controller(self, controller, block, time):
        """Send opening information to a specific controller"""
        # TODO: Implement opening communication protocol
        pass
    
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
        
        for block in route.blockSequence:
            block_id = getattr(block, 'blockID', block)
            
            # Check if this overwrites previous command
            update_flag = 1 if block_id in self.previous_block_commands else 0
            
            # Calculate speed and authority for this block
            speed = self._calculate_speed_for_block(train_id, block_id, route)
            authority = self._calculate_authority_for_block(train_id, block_id, route)
            next_station = self._get_next_station_for_route(route, block_id)
            
            suggested_speeds.append(speed)
            authorities.append(authority)
            block_nums.append(block_id)
            update_flags.append(update_flag)
            next_stations.append(next_station)
            
            # Update command tracking
            self.previous_block_commands[block_id] = {
                'speed': speed,
                'authority': authority,
                'timestamp': datetime.now(),
                'train_id': train_id
            }
        
        # Send commands
        if block_nums:
            self.command_train(suggested_speeds, authorities, block_nums, update_flags, next_stations)
            logger.info(f"Route commands sent for train {train_id} covering blocks {block_nums}")
    
    def send_departure_commands(self, train_id: str, route) -> None:
        """
        Send commands when train departs from yard
        Sends commands for first 4 blocks with 2-second delays between each command
        
        Args:
            train_id: ID of departing train
            route: Train's route
        """
        import threading
        import time
        
        if not route:
            return
            
        # Get the route blocks
        route_blocks = []
        if hasattr(route, 'blocks') and route.blocks:
            route_blocks = [getattr(block, 'blockID', block) for block in route.blocks]
        elif hasattr(route, 'startBlock'):
            # Fallback: assume sequential blocks starting from startBlock
            start_block = getattr(route, 'startBlock', None)
            if start_block:
                start_id = getattr(start_block, 'blockID', start_block)
                route_blocks = list(range(start_id, start_id + 10))  # Assume 10 blocks for safety
        
        if not route_blocks:
            logger.warning(f"No route blocks found for train {train_id}")
            return
            
        # Send commands for first 4 blocks with delays
        def send_sequential_commands():
            for i in range(min(4, len(route_blocks))):
                if i > 0:
                    time.sleep(2)  # 2-second delay between commands
                
                block_id = route_blocks[i]
                next_station = self._get_next_station_for_route(route, block_id)
                
                # Send command for this single block
                self.command_train([3], [1], [block_id], [0], [next_station])  # Full speed, authority granted
                logger.info(f"Departure command {i+1}/4 sent for train {train_id} to block {block_id}")
        
        # Start sequential command sending in background thread
        command_thread = threading.Thread(target=send_sequential_commands)
        command_thread.daemon = True
        command_thread.start()
        
        logger.info(f"Started sequential departure commands for train {train_id} from yard")
    
    def _process_train_movements(self, occupied_blocks):
        """Process train movements based on block occupation updates"""
        # Update current occupation state
        # This would map the occupied_blocks list to specific block numbers
        # For now, simplified implementation
        logger.debug("Processing train movements from occupation update")
    
    def _send_commands_for_moved_trains(self):
        """Send updated commands for trains that have moved"""
        # Recalculate commands for trains whose positions have changed
        for train_id, route in self.active_train_routes.items():
            if route and hasattr(route, 'isActive') and route.isActive:
                # Check if train needs updated commands based on new position
                self._update_commands_for_train_position(train_id, route)
    
    def _update_switches_for_routes(self):
        """Update switch positions based on active train routes"""
        switch_commands = {}
        
        # Calculate required switch positions for each controller
        for controller in self.wayside_controllers:
            switch_positions = self._calculate_switch_positions_for_controller(controller)
            if switch_positions:
                self.command_switch(controller, switch_positions)
                logger.debug(f"Switch positions updated for controller")
    
    def _calculate_switch_positions_for_controller(self, controller):
        """Calculate required switch positions for trains in controller's territory"""
        if not hasattr(controller, 'blocks_covered'):
            return []
            
        # Simple implementation - would need detailed track layout for full implementation
        switch_positions = []
        
        # Check each active route to determine switch requirements
        for train_id, route in self.active_train_routes.items():
            if route and hasattr(route, 'blockSequence'):
                # Check if route passes through this controller's blocks
                route_blocks = [getattr(b, 'blockID', b) for b in route.blockSequence]
                controller_blocks = set(controller.blocks_covered)
                
                if any(block in controller_blocks for block in route_blocks):
                    # This route affects this controller - calculate switch needs
                    # Simplified: assume switches need to be in "normal" position
                    switch_positions = [False] * len(controller.blocks_covered)  # Normal position
                    break
        
        return switch_positions
    
    def _calculate_speed_for_block(self, train_id: str, block_id: int, route) -> int:
        """Calculate suggested speed for train in specific block"""
        # Check for obstacles, speed limits, etc.
        if self._check_block_obstacles(block_id):
            return 0  # Stop
        return 3  # Full speed (simplified)
    
    def _calculate_authority_for_block(self, train_id: str, block_id: int, route) -> int:
        """Calculate authority for train in specific block"""
        # Check if block is clear and on route
        if self._is_block_on_route(block_id, route):
            return 1  # Authority granted
        return 0  # No authority
    
    def _get_next_station_for_route(self, route, current_block: int) -> int:
        """Get next station ID for train on route"""
        if hasattr(route, 'endBlock'):
            # Simplified: return destination block as station
            return getattr(route.endBlock, 'blockID', 0)
        return 0
    
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
        """Update commands based on train's new position"""
        # Simplified implementation - would recalculate based on current position
        pass
    
    def shutdown(self):
        """Shutdown the communication handler"""
        self._running = False
        if self._message_thread.is_alive():
            self._message_thread.join()
        logger.info("Communication Handler shutdown complete")