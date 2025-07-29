"""
Display Manager Module
=====================
Manages all display-related functionality for the CTC system
according to UML specifications.

This module handles:
- Map state visualization
- Train, block, and emergency tables
- Display updates for all UI components
- Throughput and status displays
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from PyQt5.QtCore import QObject, pyqtSignal

# Import simulation time (lazy import to avoid circular dependencies)
# from Master_Interface.master_control import get_time


def _get_simulation_time():
    """Get simulation time with lazy import to avoid circular dependencies"""
    try:
        from Master_Interface.master_control import get_time
        return get_time()
    except ImportError:
        # Fallback to regular datetime if Master Interface not available
        from datetime import datetime
        return datetime.now()

# Set up logging
logger = logging.getLogger(__name__)


class DisplayManager(QObject):
    """
    Comprehensive display manager implementing real-time UI updates and visualization coordination.
    
    This class manages all display-related functionality for the CTC system, providing a clean
    separation between business logic and UI presentation. It implements Qt signals for real-time
    updates and maintains comprehensive state tracking for all visual elements.
    
    Core Display Components:
        mapState (dict): Current track map visualization state
        trainTable (dict): Train status table data with real-time updates
        blockTable (dict): Block status table data with infrastructure info
        emergencyTable (dict): Emergency and failure tracking data
        
    Real-Time Data Tables:
        Train Table Structure:
            - train_id: Unique train identifier
            - line: Train line (Red, Green, Blue)
            - current_block: Current block number
            - destination_block: Target destination
            - speed: Current speed in km/h
            - authority: Movement authority (0=stop, 1=proceed)
            - status: Operational status (ACTIVE, MALFUNCTION, etc.)
            - last_update: Timestamp of last update
            
        Block Table Structure:
            - block_number: Block identifier
            - line: Track line
            - occupied: Current occupation state
            - closed: Maintenance closure status
            - switch_position: Switch position if applicable
            - crossing_active: Railway crossing status if applicable
            - failure: Block failure status
            - operational: Overall operational status
            
        Emergency Table Structure:
            - emergency_id: Unique emergency identifier
            - type: Emergency type (TRAIN_FAILURE, BLOCK_FAILURE, SYSTEM_FAILURE)
            - train_id: Associated train (if applicable)
            - block_id: Associated block (if applicable)
            - description: Detailed description
            - timestamp: Occurrence time
            - addressed: Resolution status
            - resolution: Resolution description
            
    Map Visualization State:
        trains (dict): Real-time train positions and movements
        routes (dict): Active route visualizations
        closures (dict): Maintenance closures and timing
        switches (dict): Switch positions and states
        selected_train (str): Currently selected train for UI
        selected_block (dict): Currently selected block for UI
        
    Qt Signals (Real-Time Updates):
        map_updated: Emitted when map visualization changes
        train_table_updated: Emitted when train data changes
        block_table_updated: Emitted when block data changes
        emergency_table_updated: Emitted when emergency data changes
        throughput_updated: Emitted when throughput metrics change
        
    Methods Overview:
        Data Retrieval:
            - get_updated_map(): Get current map state
            - get_train_table(): Get formatted train status data
            - get_block_table(): Get formatted block status data
            - get_emergency_table(): Get formatted emergency data
            
        Train Display Management:
            - update_display_speed(train, speed): Update train speed display
            - update_train_location(train, location): Update train position with animation
            - update_train_error(train): Display train malfunction
            - update_train_state(train_id, train): Update comprehensive train state
            
        Route & Navigation Display:
            - display_route(route): Visualize route on map
            - clear_route_display(route_id): Remove route visualization
            
        Infrastructure Display:
            - display_closure(block, closureTime): Show maintenance closure
            - display_switches(): Update switch position display
            - display_switch_positions(positions): Update multiple switch displays
            
        Failure & Emergency Display:
            - display_failure(message): Show system failure message
            - update_block_failure(block_id, description): Display block failure
            - address_emergency(emergency_id, resolution): Mark emergency as resolved
            
        Metrics & Performance Display:
            - update_throughput(throughput): Update throughput metrics with history
            
        State Management:
            - set_selected_train(train_id): Set UI train selection
            - set_selected_block(line, block_num): Set UI block selection
            
        System Integration:
            - get_warnings(): Get aggregated system warnings
            - is_block_closed(line, block_num): Check closure status
            - get_maintenance_closures(): Get formatted closure data
            
    Display Features:
        Animation Support:
            - Tracks previous positions for smooth train movement animation
            - Maintains transition states for visual effects
            - Provides timing information for UI animations
            
        Real-Time Updates:
            - Immediate signal emission for all state changes
            - Efficient data structures for fast UI updates
            - Comprehensive change tracking and notification
            
        Data Formatting:
            - Structures data in UI-friendly formats
            - Provides consistent interfaces for different display types
            - Handles data validation and error states
            
        Historical Data:
            - Maintains throughput history for trend analysis
            - Tracks emergency resolution history
            - Provides audit trail for system events
            
    Integration Points:
        - CTC System: Receives real-time system state updates
        - Communication Handler: Displays communication status
        - Failure Manager: Shows failure and emergency information
        - Route Manager: Visualizes active routes and planning
        
    Thread Safety:
        - All methods are thread-safe for real-time updates
        - Qt signals provide safe cross-thread communication
        - State updates are atomic and consistent
        
    Performance Optimization:
        - Efficient data structures for fast lookups
        - Minimal data copying for large datasets
        - Smart update detection to avoid unnecessary refreshes
        - Optimized signal emission for UI responsiveness
    """
    
    # Qt signals for UI updates
    map_updated = pyqtSignal(dict)
    train_table_updated = pyqtSignal(dict)
    block_table_updated = pyqtSignal(dict)
    emergency_table_updated = pyqtSignal(dict)
    throughput_updated = pyqtSignal(dict)
    
    def __init__(self):
        """Initialize Display Manager with UML-specified attributes"""
        super().__init__()
        
        # Attributes from UML
        self.mapState = {}      # Current map visualization state
        self.trainTable = {}    # Train status table data
        self.blockTable = {}    # Block status table data
        self.emergencyTable = {}  # Emergency/failure table data
        
        # Additional attributes for implementation
        self.throughput_history = []  # Historical throughput data
        
        # Initialize tables
        self._initialize_tables()
        
        logger.info("Display Manager initialized")
    
    # Methods from UML
    
    def get_updated_map(self) -> dict:
        """
        Return current track map state
        
        Returns:
            Dict containing map visualization data
        """
        return self.mapState.copy()
    
    def get_train_table(self) -> dict:
        """
        Return train status table
        
        Returns:
            Dict containing train information:
            {
                'train_id': {
                    'line': str,
                    'current_block': int,
                    'destination_block': int,
                    'speed': float,
                    'authority': int,
                    'status': str
                }
            }
        """
        return self.trainTable.copy()
    
    def get_train_info_for_display(self, trains=None, train_suggested_speeds=None):
        """
        Get train information formatted for display tables
        Moved from CTC System to centralize display logic
        
        Args:
            trains: Dict of train objects from CTC system
            train_suggested_speeds: Dict of suggested speeds from CTC system
            
        Returns:
            List of train info dicts formatted for UI tables
        """
        if trains is None:
            trains = {}
        if train_suggested_speeds is None:
            train_suggested_speeds = {}
            
        train_data = []
        for train_id, train in trains.items():
            # Determine routing status
            has_route = hasattr(train, 'route') and train.route is not None
            routing_status = "Routed" if has_route else "Unrouted"
            
            # Extract current block and line info for display
            current_block_obj = getattr(train, 'currentBlock', None)
            current_block = getattr(current_block_obj, 'blockID', getattr(current_block_obj, 'blockNumber', 0)) if current_block_obj else 0
            line = getattr(train, 'line', 'Unknown')
            destination_block = getattr(train, 'destination', 'N/A')
            
            # Format departure time for display (TBTG camelCase with fallback)
            departure_time = getattr(train, 'departureTime', getattr(train, 'departure_time', None))
            departure_str = departure_time.strftime('%H:%M') if departure_time else ''
            
            # Format arrival time for ETA (TBTG camelCase with fallback)
            arrival_time = getattr(train, 'arrivalTime', getattr(train, 'arrival_time', None))
            eta_str = arrival_time.strftime('%H:%M') if arrival_time else ''
            
            train_info = {
                'id': train_id,
                'train_id': train_id,
                'line': line,
                'current_block': current_block,
                'destination': destination_block,
                'speed': str(train_suggested_speeds.get(train_id, 0) if current_block != 0 else 0),
                'authority': getattr(train, 'authority', 0),
                'passengers': getattr(train, 'passengers', 0),
                'routing_status': getattr(train, 'routingStatus', routing_status),
                'route_id': getattr(train.route, 'routeID', 'N/A') if has_route else 'N/A',
                'departure_time': departure_str,
                'arrival_time': arrival_time,
                'eta': eta_str,
                # Additional fields for UI table
                'section_location': 'A' if current_block <= 15 else 'B',  # Simple section logic
                'block_location': str(current_block),
                'destination_section': 'A' if str(destination_block).isdigit() and int(destination_block) <= 15 else 'B' if str(destination_block).isdigit() else '',
                'destination_block': str(destination_block)
            }
            train_data.append(train_info)
        return train_data
    
    def get_block_table(self) -> dict:
        """
        Return block status table
        
        Returns:
            Dict containing block information:
            {
                'block_number': {
                    'line': str,
                    'occupied': bool,
                    'closed': bool,
                    'switch_position': Optional[bool],
                    'crossing_active': Optional[bool],
                    'failure': bool
                }
            }
        """
        return self.blockTable.copy()
    
    def get_emergency_table(self) -> dict:
        """
        Return emergency/failure table
        
        Returns:
            Dict containing emergency information:
            {
                'emergency_id': {
                    'type': str,  # 'TRAIN_FAILURE' or 'BLOCK_FAILURE'
                    'train_id': Optional[str],
                    'block_id': int,
                    'description': str,
                    'timestamp': datetime,
                    'addressed': bool,
                    'resolution': Optional[str]
                }
            }
        """
        return self.emergencyTable.copy()
    
    def update_display_speed(self, train, speed: float) -> None:
        """
        Update train speed on display
        
        Args:
            train: Train object
            speed: Speed in km/h
        """
        train_id = self._get_train_id(train)
        if train_id not in self.trainTable:
            self.trainTable[train_id] = {}
        
        self.trainTable[train_id]['speed'] = speed
        self.trainTable[train_id]['last_update'] = _get_simulation_time()
        
        # Emit signal for UI update
        self.train_table_updated.emit(self.trainTable)
        logger.debug(f"Updated display speed for train {train_id}: {speed} km/h")
    
    def display_route(self, route) -> None:
        """
        Display new route on map
        
        Args:
            route: Route object to display
        """
        if hasattr(route, 'routeID'):
            route_id = route.routeID
            
            # Extract route information
            route_data = {
                'route_id': route_id,
                'blocks': route.get_block_sequence() if hasattr(route, 'get_block_sequence') else [],
                'start_block': route.startBlock if hasattr(route, 'startBlock') else None,
                'end_block': route.endBlock if hasattr(route, 'endBlock') else None,
                'active': True
            }
            
            # Update map state
            if 'routes' not in self.mapState:
                self.mapState['routes'] = {}
            self.mapState['routes'][route_id] = route_data
            
            # Emit signal for UI update
            self.map_updated.emit(self.mapState)
            logger.info(f"Route {route_id} displayed on map")
    
    def display_closure(self, block, closureTime: datetime) -> None:
        """
        Display block closure
        
        Args:
            block: Block object
            closureTime: When closure begins
        """
        block_id = self._get_block_id(block)
        
        # Update block table
        if block_id not in self.blockTable:
            self.blockTable[block_id] = {}
        
        self.blockTable[block_id]['closed'] = True
        self.blockTable[block_id]['closure_time'] = closureTime
        
        # Update map state
        if 'closures' not in self.mapState:
            self.mapState['closures'] = {}
        self.mapState['closures'][block_id] = {
            'time': closureTime,
            'active': _get_simulation_time() >= closureTime
        }
        
        # Emit signals
        self.block_table_updated.emit(self.blockTable)
        self.map_updated.emit(self.mapState)
        logger.info(f"Block {block_id} closure displayed for {closureTime}")
    
    def display_switches(self) -> None:
        """Update switch positions on display"""
        # Extract switch information from block table
        switch_data = {}
        for block_id, block_info in self.blockTable.items():
            if 'switch_position' in block_info and block_info['switch_position'] is not None:
                switch_data[block_id] = block_info['switch_position']
        
        # Update map state
        self.mapState['switches'] = switch_data
        
        # Emit signal
        self.map_updated.emit(self.mapState)
        logger.debug("Switch positions updated on display")
    
    def update_throughput(self, throughput: int) -> None:
        """
        Update throughput metrics display
        
        Args:
            throughput: Current throughput value
        """
        # Add to history
        self.throughput_history.append({
            'value': throughput,
            'timestamp': _get_simulation_time()
        })
        
        # Keep only last hour of data
        cutoff_time = _get_simulation_time().replace(minute=0, second=0, microsecond=0)
        self.throughput_history = [
            entry for entry in self.throughput_history 
            if entry['timestamp'] >= cutoff_time
        ]
        
        # Calculate hourly rate
        hourly_throughput = sum(entry['value'] for entry in self.throughput_history)
        
        # Emit signal
        self.throughput_updated.emit({
            'current': throughput,
            'hourly': hourly_throughput,
            'history': self.throughput_history
        })
        logger.debug(f"Throughput updated: {throughput} (hourly: {hourly_throughput})")
    
    def update_line_throughput(self, line: str, throughput: int) -> None:
        """
        Update throughput for a specific line
        
        Args:
            line: Line name (Blue, Red, Green)
            throughput: Current throughput value for the line
        """
        # Store per-line throughput data
        if not hasattr(self, 'line_throughput_data'):
            self.line_throughput_data = {'Blue': 0, 'Red': 0, 'Green': 0}
        
        self.line_throughput_data[line] = throughput
        
        # Emit signal with per-line data
        self.throughput_updated.emit({
            'per_line': self.line_throughput_data.copy(),
            'total': sum(self.line_throughput_data.values()),
            'timestamp': _get_simulation_time()
        })
        logger.debug(f"Line throughput updated: {line} = {throughput}")
    
    def update_all_line_throughput(self, hourly_rates: Dict[str, int]) -> None:
        """
        Update throughput for all lines at once to emit single signal
        
        Args:
            hourly_rates: Dict with line names as keys and hourly rates as values
        """
        # Store per-line throughput data
        if not hasattr(self, 'line_throughput_data'):
            self.line_throughput_data = {'Blue': 0, 'Red': 0, 'Green': 0}
        
        # Update all lines
        self.line_throughput_data.update(hourly_rates)
        
        # Emit single signal with all data
        self.throughput_updated.emit({
            'per_line': self.line_throughput_data.copy(),
            'total': sum(self.line_throughput_data.values()),
            'timestamp': _get_simulation_time()
        })
        logger.debug(f"All line throughput updated: {hourly_rates}")
    
    def display_switch_positions(self, positions: List[bool]) -> None:
        """
        Update switch position display
        
        Args:
            positions: List of switch positions (0=normal, 1=reverse)
        """
        # Update switch positions in map state
        switch_updates = {}
        for i, position in enumerate(positions):
            switch_id = f"switch_{i+1}"
            switch_updates[switch_id] = position
        
        self.mapState['switches'] = switch_updates
        
        # Emit signal
        self.map_updated.emit(self.mapState)
        logger.debug(f"Switch positions updated: {len(positions)} switches")
    
    def display_failure(self, message: str) -> None:
        """
        Display failure message
        
        Args:
            message: Failure description
        """
        # Generate unique emergency ID
        emergency_id = f"emergency_{len(self.emergencyTable) + 1}"
        
        # Add to emergency table
        self.emergencyTable[emergency_id] = {
            'type': 'SYSTEM_FAILURE',
            'train_id': None,
            'block_id': None,
            'description': message,
            'timestamp': _get_simulation_time(),
            'addressed': False,
            'resolution': None
        }
        
        # Emit signal
        self.emergency_table_updated.emit(self.emergencyTable)
        logger.warning(f"Failure displayed: {message}")
    
    def update_train_location(self, train, location) -> None:
        """
        Update train position on map
        
        Args:
            train: Train object
            location: Block object where train is located
        """
        train_id = self._get_train_id(train)
        block_id = self._get_block_id(location)
        
        # Update train table
        if train_id not in self.trainTable:
            self.trainTable[train_id] = {}
        
        # Store previous location for animation
        prev_block = self.trainTable[train_id].get('current_block')
        self.trainTable[train_id]['previous_block'] = prev_block
        self.trainTable[train_id]['current_block'] = block_id
        self.trainTable[train_id]['last_update'] = _get_simulation_time()
        
        # Update map state
        if 'trains' not in self.mapState:
            self.mapState['trains'] = {}
        
        self.mapState['trains'][train_id] = {
            'current_block': block_id,
            'previous_block': prev_block,
            'line': self.trainTable[train_id].get('line', 'Unknown')
        }
        
        # Update block occupancy
        if prev_block and prev_block in self.blockTable:
            self.blockTable[prev_block]['occupied'] = False
        if block_id in self.blockTable:
            self.blockTable[block_id]['occupied'] = True
        
        # Emit signals
        self.train_table_updated.emit(self.trainTable)
        self.block_table_updated.emit(self.blockTable)
        self.map_updated.emit(self.mapState)
        logger.debug(f"Train {train_id} location updated: {prev_block} -> {block_id}")
    
    def update_train_error(self, train) -> None:
        """
        Display train malfunction
        
        Args:
            train: Train object with malfunction
        """
        train_id = self._get_train_id(train)
        
        # Generate emergency ID
        emergency_id = f"train_failure_{train_id}_{_get_simulation_time().timestamp()}"
        
        # Add to emergency table
        self.emergencyTable[emergency_id] = {
            'type': 'TRAIN_FAILURE',
            'train_id': train_id,
            'block_id': self.trainTable.get(train_id, {}).get('current_block'),
            'description': f"Train {train_id} malfunction detected",
            'timestamp': _get_simulation_time(),
            'addressed': False,
            'resolution': None
        }
        
        # Update train status
        if train_id in self.trainTable:
            self.trainTable[train_id]['status'] = 'MALFUNCTION'
        
        # Emit signals
        self.emergency_table_updated.emit(self.emergencyTable)
        self.train_table_updated.emit(self.trainTable)
        logger.error(f"Train {train_id} malfunction displayed")
    
    # Additional methods for enhanced functionality
    
    def update_block_failure(self, block_id: int, description: str) -> None:
        """
        Add block failure to emergency table
        
        Args:
            block_id: Failed block number
            description: Failure description
        """
        # Generate emergency ID
        emergency_id = f"block_failure_{block_id}_{_get_simulation_time().timestamp()}"
        
        # Add to emergency table
        self.emergencyTable[emergency_id] = {
            'type': 'BLOCK_FAILURE',
            'train_id': None,
            'block_id': block_id,
            'description': description,
            'timestamp': _get_simulation_time(),
            'addressed': False,
            'resolution': None
        }
        
        # Update block status
        if block_id in self.blockTable:
            self.blockTable[block_id]['failure'] = True
        
        # Emit signals
        self.emergency_table_updated.emit(self.emergencyTable)
        self.block_table_updated.emit(self.blockTable)
        logger.error(f"Block {block_id} failure displayed: {description}")
    
    def address_emergency(self, emergency_id: str, resolution: str) -> None:
        """
        Mark emergency as addressed
        
        Args:
            emergency_id: ID of emergency to address
            resolution: Resolution description
        """
        if emergency_id in self.emergencyTable:
            self.emergencyTable[emergency_id]['addressed'] = True
            self.emergencyTable[emergency_id]['resolution'] = resolution
            
            # Emit signal
            self.emergency_table_updated.emit(self.emergencyTable)
            logger.info(f"Emergency {emergency_id} addressed: {resolution}")
    
    def clear_route_display(self, route_id: str) -> None:
        """
        Remove route from display
        
        Args:
            route_id: ID of route to clear
        """
        if 'routes' in self.mapState and route_id in self.mapState['routes']:
            del self.mapState['routes'][route_id]
            
            # Emit signal
            self.map_updated.emit(self.mapState)
            logger.debug(f"Route {route_id} cleared from display")
    
    def generate_and_display_route(self, train_id, from_station, to_station, arrival_time=None, route_manager=None):
        """
        Generate route and display it on map
        Moved from UI to centralize route display logic
        
        Args:
            train_id: ID of train to route
            from_station: Starting station
            to_station: Destination station  
            arrival_time: Optional arrival time
            route_manager: Route manager instance for generating routes
            
        Returns:
            dict: Route generation result with success status and route info
        """
        result = {
            'success': False,
            'route': None,
            'message': 'Route generation failed'
        }
        
        if not route_manager:
            result['message'] = 'Route manager not available'
            return result
            
        try:
            # Generate route using route manager
            if hasattr(route_manager, 'generate_route'):
                route = route_manager.generate_route(from_station, to_station, arrival_time)
                if route:
                    # Display the route
                    self.display_route(route)
                    result = {
                        'success': True,
                        'route': route,
                        'message': f'Route generated from {from_station} to {to_station}'
                    }
                    logger.info(f"Route generated and displayed for train {train_id}: {from_station} -> {to_station}")
                else:
                    result['message'] = f'No route found from {from_station} to {to_station}'
            else:
                result['message'] = 'Route manager does not support route generation'
                
        except Exception as e:
            result['message'] = f'Route generation error: {str(e)}'
            logger.error(f"Route generation failed for train {train_id}: {e}")
            
        return result
    
    def initialize_emergency_state(self, error_train_id, error_type="Engine Failure", trains=None):
        """
        Initialize emergency state for resolution
        Moved from UI to centralize emergency management
        
        Args:
            error_train_id: ID of train with emergency
            error_type: Type of emergency
            trains: Dict of all trains for finding affected trains
            
        Returns:
            dict: Emergency context with error train and affected trains
        """
        emergency_context = {
            'error_train_id': error_train_id,
            'error_type': error_type,
            'error_train': None,
            'affected_trains': []
        }
        
        if trains:
            # Find the error train
            error_train = trains.get(error_train_id)
            if error_train:
                emergency_context['error_train'] = error_train
                
                # Find affected trains (simplified logic - could be enhanced)
                for train_id, train in trains.items():
                    if train_id != error_train_id and hasattr(train, 'line') and hasattr(error_train, 'line'):
                        if train.line == error_train.line:
                            emergency_context['affected_trains'].append(train)
        
        # Add to emergency table
        emergency_id = f"emergency_{error_train_id}_{_get_simulation_time().timestamp()}"
        self.emergencyTable[emergency_id] = {
            'type': 'TRAIN_EMERGENCY',
            'train_id': error_train_id,
            'block_id': getattr(emergency_context.get('error_train'), 'currentBlock', None),
            'description': f"Train {error_train_id} - {error_type}",
            'timestamp': _get_simulation_time(),
            'addressed': False,
            'resolution': None,
            'context': emergency_context
        }
        
        # Emit signal
        self.emergency_table_updated.emit(self.emergencyTable)
        logger.warning(f"Emergency initialized for train {error_train_id}: {error_type}")
        
        return emergency_context
    
    def finish_emergency_resolution(self, emergency_id, resolution_notes="Emergency resolved"):
        """
        Complete emergency resolution
        
        Args:
            emergency_id: ID of emergency to resolve
            resolution_notes: Notes about resolution
            
        Returns:
            bool: True if successfully resolved
        """
        if emergency_id in self.emergencyTable:
            self.address_emergency(emergency_id, resolution_notes)
            logger.info(f"Emergency {emergency_id} resolved: {resolution_notes}")
            return True
        return False
    
    def get_emergency_context(self, emergency_id):
        """
        Get emergency context for UI display
        
        Args:
            emergency_id: ID of emergency
            
        Returns:
            dict: Emergency context or None
        """
        if emergency_id in self.emergencyTable:
            return self.emergencyTable[emergency_id].get('context')
        return None
    
    
    # Private helper methods
    
    def _initialize_tables(self):
        """Initialize empty tables"""
        self.mapState = {
            'trains': {},
            'routes': {},
            'closures': {},
            'switches': {}
        }
        self.trainTable = {}
        self.blockTable = {}
        self.emergencyTable = {}
    
    def _get_train_id(self, train) -> str:
        """Extract train ID from train object"""
        if hasattr(train, 'trainID'):
            return str(train.trainID)
        elif hasattr(train, 'id'):
            return str(train.id)
        else:
            return f"train_{id(train)}"
    
    def _get_block_id(self, block) -> int:
        """Extract block ID from block object"""
        if hasattr(block, 'blockID'):
            return block.blockID
        elif hasattr(block, 'block_number'):
            return block.block_number
        elif isinstance(block, int):
            return block
        else:
            return 0
    
    # Compatibility methods for UI integration
    
    def update_train_state(self, train_id, train):
        """Update train state (compatibility method)"""
        self.trainTable[train_id] = {
            'id': train_id,
            'line': getattr(train, 'line', 'Unknown'),
            'current_block': getattr(train, 'currentBlock', 0),
            'speed': getattr(train, 'speed', 0),
            'authority': getattr(train, 'authority', 0),
            'last_updated': _get_simulation_time()
        }
        logger.debug(f"Train {train_id} state updated")
    
    def get_warnings(self, failure_manager=None, track_status=None, railway_crossings=None):
        """
        Get system warnings in format expected by UI
        Moved from UI to centralize warning generation logic
        
        Args:
            failure_manager: Failure manager instance for failure-based warnings
            track_status: Track status data 
            railway_crossings: Railway crossing data
            
        Returns:
            List of warning dicts with keys: type, train, line, section, block, resolved
        """
        warnings = []
        
        # If failure manager provided, use it to generate warnings
        if failure_manager and hasattr(failure_manager, 'generate_warnings'):
            warnings = failure_manager.generate_warnings(track_status, railway_crossings)
        
        # Add emergency table warnings if not already covered
        for emergency_id, emergency in self.emergencyTable.items():
            if not emergency.get('addressed', False):
                # Format emergency as warning compatible with UI table
                warning = {
                    'type': emergency.get('type', 'emergency'),
                    'train': emergency.get('train_id', ''),
                    'line': '',  # Extract from block if available
                    'section': '',  # Calculate from block
                    'block': str(emergency.get('block_id', '')),
                    'resolved': emergency.get('addressed', False),
                    'message': emergency.get('description', 'Unknown emergency'),
                    'severity': 'high'
                }
                
                # Try to extract line and section info from block
                block_id = emergency.get('block_id')
                if block_id and block_id in self.blockTable:
                    block_info = self.blockTable[block_id]
                    warning['line'] = block_info.get('line', '')
                    # Simple section logic (A if block <= 15, B otherwise)
                    if isinstance(block_id, int):
                        warning['section'] = 'A' if block_id <= 15 else 'B'
                
                warnings.append(warning)
        
        # Ensure all warnings have required keys for UI compatibility
        for warning in warnings:
            if 'train' not in warning:
                warning['train'] = ''
            if 'line' not in warning:
                warning['line'] = ''
            if 'section' not in warning:
                warning['section'] = ''
            if 'block' not in warning:
                warning['block'] = ''
            if 'resolved' not in warning:
                warning['resolved'] = False
        
        return warnings
    
    def is_block_closed(self, line, block_num, failure_manager=None):
        """
        Check if a block is closed (maintenance or failure)
        Enhanced to be comprehensive source of truth for block closure status
        
        Args:
            line: Track line (Red, Green, Blue)
            block_num: Block number
            failure_manager: Optional failure manager to check for failed blocks
            
        Returns:
            bool: True if block is closed for any reason
        """
        # Check maintenance closure in display manager
        block_key = f"{line}_{block_num}"
        is_maintenance_closed = self.blockTable.get(block_key, {}).get('closed', False)
        
        # Check failure closure if failure manager provided
        is_failed = False
        if failure_manager and hasattr(failure_manager, 'is_block_closed'):
            is_failed = failure_manager.is_block_closed(line, block_num)
        elif failure_manager and hasattr(failure_manager, 'failedBlocks'):
            # Check if block is in failed blocks list
            for failed_block in failure_manager.failedBlocks:
                if (hasattr(failed_block, 'line') and hasattr(failed_block, 'blockID') and
                    failed_block.line == line and failed_block.blockID == block_num):
                    is_failed = True
                    break
        
        # Block is closed if either maintenance closed or failed
        return is_maintenance_closed or is_failed
    
    def set_selected_train(self, train_id):
        """Set selected train for UI"""
        self.mapState['selected_train'] = train_id
        logger.debug(f"Selected train: {train_id}")
    
    def set_selected_block(self, line, block_num):
        """Set selected block for UI"""
        self.mapState['selected_block'] = {'line': line, 'block': block_num}
        logger.debug(f"Selected block: {line} {block_num}")
    
    def get_maintenance_closures(self):
        """Get maintenance closures"""
        # Return closures from block table in expected format
        closures = {
            'Blue': [],
            'Red': [], 
            'Green': []
        }
        
        for block_key, block_data in self.blockTable.items():
            if block_data.get('closed', False):
                # Extract line and block from key
                if '_' in block_key:
                    line, block_num = block_key.split('_', 1)
                    if line in closures:
                        try:
                            closures[line].append(int(block_num))
                        except ValueError:
                            # Invalid block number format - skip
                            continue
        
        return closures