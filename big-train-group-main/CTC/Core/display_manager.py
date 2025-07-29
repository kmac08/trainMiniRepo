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

# Set up logging
logger = logging.getLogger(__name__)


class DisplayManager(QObject):
    """
    Display Manager implementing UML interface
    Separates display logic from UI implementation
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
        self.update_callbacks = {}  # UI update callbacks
        self.throughput_history = []  # Historical throughput data
        self.display_cache = {}  # Cache for performance
        
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
        self.trainTable[train_id]['last_update'] = datetime.now()
        
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
            'active': datetime.now() >= closureTime
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
            'timestamp': datetime.now()
        })
        
        # Keep only last hour of data
        cutoff_time = datetime.now().replace(minute=0, second=0, microsecond=0)
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
            'timestamp': datetime.now(),
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
        self.trainTable[train_id]['last_update'] = datetime.now()
        
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
        emergency_id = f"train_failure_{train_id}_{datetime.now().timestamp()}"
        
        # Add to emergency table
        self.emergencyTable[emergency_id] = {
            'type': 'TRAIN_FAILURE',
            'train_id': train_id,
            'block_id': self.trainTable.get(train_id, {}).get('current_block'),
            'description': f"Train {train_id} malfunction detected",
            'timestamp': datetime.now(),
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
        emergency_id = f"block_failure_{block_id}_{datetime.now().timestamp()}"
        
        # Add to emergency table
        self.emergencyTable[emergency_id] = {
            'type': 'BLOCK_FAILURE',
            'train_id': None,
            'block_id': block_id,
            'description': description,
            'timestamp': datetime.now(),
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
    
    def register_ui_callback(self, callback_type: str, callback_func) -> None:
        """
        Register callback for UI updates
        
        Args:
            callback_type: Type of update (e.g., 'map', 'train_table')
            callback_func: Function to call on update
        """
        self.update_callbacks[callback_type] = callback_func
        logger.debug(f"UI callback registered for {callback_type}")
    
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
            'last_updated': datetime.now()
        }
        logger.debug(f"Train {train_id} state updated")
    
    def get_warnings(self):
        """Get system warnings"""
        # This would typically aggregate warnings from various sources
        warnings = []
        
        # Check emergency table for unaddressed issues
        for emergency_id, emergency in self.emergencyTable.items():
            if not emergency.get('addressed', False):
                warnings.append({
                    'type': 'emergency',
                    'message': emergency.get('description', 'Unknown emergency'),
                    'severity': 'high'
                })
        
        return warnings
    
    def is_block_closed(self, line, block_num):
        """Check if a block is closed"""
        # Simple check - in a real system this would check actual block status
        block_key = f"{line}_{block_num}"
        return self.blockTable.get(block_key, {}).get('closed', False)
    
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
                            pass
        
        return closures