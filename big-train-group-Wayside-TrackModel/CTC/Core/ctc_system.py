"""
CTC System Module
================
Central coordination system implementing UML specifications.
Manages trains, routes, and system state according to the UML design.

This module handles:
- Train management and coordination
- Route generation and validation
- Throughput tracking
- System state management
- Integration with all other components
- Event-driven Wayside controller communication

Communication with Wayside Controllers:
- provide_wayside_controller(): Register controllers with block coverage
- Commands sent only on events: routing, rerouting, block occupation updates
- Block-specific commands with update flags and next station information
"""

from typing import List, Dict, Optional, Any, Set, Tuple, Callable
from datetime import datetime, timedelta
import logging
import threading
import json
import os
import time
import math
from dataclasses import dataclass
from enum import Enum

# Import simulation time (lazy import to avoid circular dependencies)
# from Master_Interface.master_control import get_time


def _get_simulation_time():
    """Get simulation time with lazy import to avoid circular dependencies"""
    from Master_Interface.master_control import get_time
    return get_time()
from PyQt5.QtCore import QObject, pyqtSignal

# Import the new UML-compliant classes
from .communication_handler import CommunicationHandler
from .display_manager import DisplayManager
from .failure_manager import FailureManager
from .route_manager import RouteManager
from .block import Block
from .route import Route
from .train import Train


# Set up logging
logger = logging.getLogger(__name__)


class CTCSystem(QObject):
    """
    ✅ REFACTORED: Central Coordinated Train Control (CTC) system implementing comprehensive railway operations management.
    
    This class serves as the main coordination hub for the entire CTC system, integrating train management,
    route generation, communication handling, failure management, and real-time system monitoring.
    After refactoring, it now owns scheduled maintenance operations and acts as the single API for UI interactions.
    
    REFACTORING CHANGES:
        ✅ Added scheduled closure/opening management (moved from FailureManager)
        ✅ Added UI delegation methods for block operations
        ✅ Now processes scheduled closures/openings in system tick
        ✅ Acts as single entry point for all UI maintenance operations
    
    Core System Components:
        - Train Management: Complete train lifecycle management
        - Route Generation: Advanced pathfinding and route validation
        - Communication: Wayside controller integration and command distribution
        - Failure Management: Comprehensive failure detection and emergency response
        - Display Management: Real-time UI updates and visualization
        - State Management: Thread-safe system state tracking
        - ✅ Scheduled Maintenance: Centralized scheduling and execution of maintenance operations
        
    Primary Attributes:
        activeTrains (List[str]): List of active train IDs
        trackLayout (TrackLayoutReader): Track model reference
        routeManager (RouteManager): Route generation and management
        throughputMetrics (List[int]): System throughput tracking
        blockMetrics (List[int]): Block utilization metrics
        
    Data Storage:
        blocks (Dict[Tuple[str, int], Block]): Line-aware block storage (line, block_number) -> Block
        routes (Dict[str, Route]): Active routes by route ID
        trains (Dict[str, Train]): Active trains by train ID
        trainAuthorities (Dict[str, int]): Train authority tracking
        trainSuggestedSpeeds (Dict[str, int]): Train speed commands
        
    ✅ NEW: Scheduled Maintenance Management:
        scheduledClosures (List[dict]): Scheduled maintenance closures (moved from FailureManager)
        scheduledOpenings (List[dict]): Scheduled maintenance openings (moved from FailureManager)
        
    Yard Management:
        yard_connections (Dict[str, List[Dict]]): Centralized yard connection data
        line_yard_blocks (Dict[str, int]): Yard exit blocks by line
        
    State Management (Thread-Safe):
        maintenance_closures (Dict[str, Set[int]]): Active closures by line
        warnings (List[Dict]): System warnings and alerts
        selected_train (str): Currently selected train for UI
        selected_block (Tuple[str, int]): Currently selected block for UI
        switch_positions (Dict[str, Dict]): Switch position tracking
        
    Train ID Management:
        line_counters (Dict[str, int]): Train ID counters by line
        active_train_ids (Set[str]): Active train ID tracking
        
    Emergency Management:
        emergency_stops (Set[str]): Trains with emergency stops
        departure_triggered (Set[str]): Trains with triggered departures
        
    Methods Overview:
        Train Management:
            - add_train(line/train, block, train_id): Add train to system
            - remove_train(train_id): Remove train from system
            - validate_ID(trainID): Validate train ID uniqueness
            - get_train_list(): Get all active trains
            
        Route Management:
            - generate_route(startBlock, endBlock, arrivalTime=None): Generate optimal route
            - activate_route(train_id, route): Activate route for train
            - confirm_route(route): Confirm route scheduling
            - dispatch_train_from_yard(train_id): Send departure commands
            
        Block & Infrastructure:
            - get_block_by_line_new(line, block_number): Get block by line
            - get_block_by_number(block_number, preferred_line): Find block across lines
            - validate_block_exists(block_number, line): Validate block existence
            - process_occupied_blocks(occupied_blocks): Handle occupation updates
            
        Communication & Control:
            - provide_wayside_controller(controller, blocksCovered, redLine): Register controllers
            - system_tick(current_time): Main system update cycle
            - check_system_state(): System health monitoring
            
        State Management:
            - get_train(train_id): Get train by ID
            - set_selected_train(train_id): Set UI selection
            - add_maintenance_closure(line, block): Add closure
            - add_warning(type, message): Add system warning
            
        Throughput & Metrics:
            - update_throughput(tickets): Update throughput metrics
            - get_system_stats(): Get comprehensive statistics
            
        Failure & Emergency:
            - validate_closure(block, time): Validate closure feasibility
            - execute_close_block_sequence(line, block, time): Execute closure workflow
            - handle_emergency_stop(train_id, reason): Emergency stop procedures
            
        Yard Operations:
            - get_yard_connections(line): Get yard connection data
            - get_yard_exit_block(line): Get yard exit block for line
            
        Train ID Management:
            - generate_train_id(line): Generate unique train ID
            - is_valid_train_id(train_id): Validate ID format
            - get_line_from_train_id(train_id): Extract line from ID
            
    Qt Signals (Real-time UI Updates):
        - train_selected: Train selection changed
        - block_selected: Block selection changed
        - state_changed: General state update
        - trains_updated: Train data updated
        - maintenance_updated: Maintenance status changed
        - warnings_updated: Warnings list changed
        
    Integration Features:
        - Thread-safe operations with RLock protection
        - Event-driven communication with wayside controllers
        - Real-time block occupation processing
        - Automatic departure scheduling and triggering
        - Comprehensive failure detection and emergency response
        - Multi-line support with proper block organization
        - Yard connection management and routing
        
    Communication Protocol:
        - Commands sent only on events (routing, rerouting, occupation changes)
        - Block-specific commands with update flags and station information
        - Full line data transmission to all controllers
        - Batched command system for optimal performance
    """
    
    # Signals for UI updates (from state_manager)
    train_selected = pyqtSignal(str)  # train_id
    block_selected = pyqtSignal(str, int)  # line, block
    state_changed = pyqtSignal()
    trains_updated = pyqtSignal()
    maintenance_updated = pyqtSignal()
    warnings_updated = pyqtSignal()
    
    def __init__(self, track_reader=None):
        """
        Initialize CTC System with UML-specified attributes
        
        Args:
            track_reader: Track layout reader for getting track information
        """
        super().__init__()
        
        # Thread lock for safe state access (from state_manager)
        self._lock = threading.RLock()
        
        # Attributes from UML
        self.activeTrains = []         # List[Train]
        self.trackLayout = track_reader # Track Model reference
        self.routeManager = None       # Route Manager (will be set later)
        self.throughputMetrics = []    # List[int] - Legacy compatibility
        self.ticket_purchase_history = []  # List[Dict] - New ticket-based throughput tracking
        self.blockMetrics = []         # List[int]
        
        # Additional attributes needed for implementation
        self.blocks = {}               # Dict[Tuple[str, int], Block] - (line, block_number) -> Block object
        self.routes = {}               # Dict[str, Route] - route_id -> Route object
        self.trains = {}               # Dict[str, Train] - train_id -> Train object
        
        # Yard connection management (centralized in CTC system)
        self.yard_connections = {}     # Dict[str, List[Dict]] - line -> yard connection info
        self.line_yard_blocks = {}     # Dict[str, int] - line -> first block after yard
        
        # Train control attributes for compatibility
        self.trainAuthorities = {}     # Dict[str, int] - train_id -> authority
        self.trainSuggestedSpeeds = {} # Dict[str, int] - train_id -> speed
        self.trackStatus = {}          # Dict - track status information
        self.railwayCrossings = {}     # Dict - railway crossing status
        
        # State management attributes (from state_manager)
        with self._lock:
            self.maintenance_closures = {}  # Active closures by line {line: set(blocks)}
            self.warnings = []  # Active warnings [{type, message, timestamp, ...}]
            self.selected_train = None  # Currently selected train ID
            
            # Scheduled maintenance management (moved from FailureManager)
            self.scheduledClosures = []  # List of scheduled closure objects
            self.scheduledOpenings = []  # List of scheduled opening objects
            self.selected_block = None  # Currently selected block (line, block)
            self.system_time_multiplier = 1.0  # Time acceleration
            self.active_lines = getattr(track_reader, 'selected_lines', ["Blue"])  # Lines currently active
            self.switch_positions = {}  # {switch_id: {line, block, position}}
            
        # Train ID management attributes (from train_id_manager)
        self.line_counters = {"Blue": 1, "Green": 1, "Red": 1}
        self.active_train_ids = set()
        
        # Simple ID manager for compatibility
        self.id_manager = type('IDManager', (), {
            'is_valid_train_id': lambda _, train_id: self.is_valid_train_id(train_id),
            'get_line_from_train_id': lambda _, train_id: self.get_line_from_train_id(train_id),
            'get_next_id_preview': lambda _, line: self.get_next_id_preview(line)
        })()
        self.id_manager.trains = self.trains  # Reference to trains dict for ID generation
        
        # Component references
        self.communicationHandler = None
        self.displayManager = None
        self.failureManager = None
        self.time_manager = None       # System time management
        
        # System state
        self.system_time = _get_simulation_time()
        self.system_running = True
        self.main_thread = None
        
        # Basic emergency detection - simplified
        self.emergency_stops = set()  # Set of train IDs with emergency stops
        
        # Departure time tracking for automatic departure triggering
        self.departure_triggered = set()  # Set of train IDs that have already triggered departure
        
        # Initialize components
        self._initialize_components()
        
        # Initialize blocks from track layout
        if self.trackLayout:
            self._initialize_blocks()
        
        # Create some basic blocks for testing if none exist
        # if not self.blocks:
        #     self._create_basic_blocks()
        
        # Give RouteManager access to blocks after they're created
        if hasattr(self, 'routeManager') and self.routeManager:
            self.routeManager.blocks = self.blocks
            logger.info(f"Passed {len(self.blocks)} blocks to RouteManager for pathfinding")
        
        logger.info("CTC System initialized")
    
    def _debug_log_blocks_with_switches(self):
        """Debug method to log which blocks have switches during initialization"""
        logger.info("=== BLOCKS WITH SWITCHES DEBUG ===")
        
        # Count switches by line for summary
        switch_counts = {'Red': 0, 'Green': 0, 'Blue': 0}
        switch_details = {'Red': [], 'Green': [], 'Blue': []}
        
        for (line, block_num), block in sorted(self.blocks.items()):
            if hasattr(block, 'switchPresent') and block.switchPresent:
                switch_info = "unknown"
                if hasattr(block, 'switch') and block.switch:
                    switch_info = str(block.switch)
                logger.info(f"SWITCH BLOCK FOUND: {line} line, block {block_num} - {switch_info}")
                print(f"🔄 SWITCH: {line} line block {block_num} - {switch_info}")
                
                if line in switch_counts:
                    switch_counts[line] += 1
                    switch_details[line].append(block_num)
        
        # Show summary with active/total counts format
        for line in ['Red', 'Green', 'Blue']:
            switch_blocks = self._get_blocks_with_switches(line)
            track_reader_count = len(switch_blocks) if switch_blocks else 0
            block_count = switch_counts[line]
            
            if track_reader_count > 0 or block_count > 0:
                logger.info(f"{line} line switches: {block_count}/{track_reader_count} (blocks: {switch_details[line]})")
                print(f"📊 {line} line switches: {block_count}/{track_reader_count} blocks")
        
        logger.info("=== END SWITCHES DEBUG ===")
        print("🔧 Switch discovery complete - check logs above for details")
    
    # Block management helper methods
    
    def get_block_by_line_new(self, line: str, block_number: int):
        """Get block by line and block number using efficient line-aware storage"""
        return self.blocks.get((line, block_number))
    
    def get_block_by_number(self, block_number: int, preferred_line: str = None):
        """
        Get block by number, optionally preferring a specific line.
        Returns first match if multiple lines have the same block number.
        """
        if preferred_line:
            block = self.blocks.get((preferred_line, block_number))
            if block:
                return block
        
        # Search all lines for this block number
        for (line, num), block in self.blocks.items():
            if num == block_number:
                return block
        
        return None
    
    def find_block_for_destination(self, destination_block_number: int, train_id: str = None) -> Optional[Block]:
        """
        Find a block object for a given destination block number.
        If train_id is provided, prefer the train's line.
        
        Args:
            destination_block_number: The block number to find
            train_id: Optional train ID to determine preferred line
            
        Returns:
            Block object or None if not found
        """
        try:
            # If train_id is provided, try to get the train's line first
            preferred_line = None
            if train_id and train_id in self.trains:
                train = self.trains[train_id]
                preferred_line = train.line
            elif train_id:
                # Extract line from train ID format (e.g., B001 -> Blue)
                line_letter = train_id[0].upper()
                if line_letter == 'B':
                    preferred_line = 'Blue'
                elif line_letter == 'G':
                    preferred_line = 'Green'
                elif line_letter == 'R':
                    preferred_line = 'Red'
            
            # Use the existing get_block_by_number method with preferred line
            return self.get_block_by_number(destination_block_number, preferred_line)
            
        except Exception as e:
            logger.error(f"Error finding block for destination {destination_block_number}: {e}")
            return None
    
    
    def generate_train_id(self, line: str) -> str:
        """Generate next available train ID for given line"""
        if line not in self.line_counters:
            raise ValueError(f"Invalid line name: {line}")
        
        line_letter = line[0].upper()
        train_id = f"{line_letter}{self.line_counters[line]:03d}"
        
        self.line_counters[line] += 1
        self.active_train_ids.add(train_id)
        
        return train_id
    
    def release_train_id(self, train_id: str) -> None:
        """Mark train ID as no longer active"""
        self.active_train_ids.discard(train_id)
    
    def is_valid_train_id(self, train_id: str) -> bool:
        """Validate train ID format"""
        if not train_id or len(train_id) != 4:
            return False
        if train_id[0] not in ['B', 'G', 'R']:
            return False
        try:
            int(train_id[1:4])
            return True
        except ValueError:
            return False
    
    def get_line_from_train_id(self, train_id: str) -> str:
        """Extract line name from train ID"""
        if not self.is_valid_train_id(train_id):
            raise ValueError(f"Invalid train ID format: {train_id}")
        line_map = {"B": "Blue", "G": "Green", "R": "Red"}
        return line_map[train_id[0]]
    
    def get_next_id_preview(self, line: str) -> str:
        """Preview next train ID without generating it"""
        if line not in self.line_counters:
            raise ValueError(f"Invalid line name: {line}")
        return f"{line[0].upper()}{self.line_counters[line]:03d}"
    
    # State Management Methods (from state_manager)
    
    def get_train(self, train_id: str) -> Optional[Train]:
        """Get train object by ID"""
        return self.trains.get(train_id)
    
    def get_all_trains(self) -> Dict[str, Train]:
        """Get copy of all active trains"""
        return self.trains.copy()
    
    def set_selected_train(self, train_id: str) -> None:
        """Set currently selected train and notify observers"""
        if train_id != self.selected_train:
            self.selected_train = train_id
            self.train_selected.emit(train_id if train_id else "")
    
    def get_selected_train(self) -> Optional[str]:
        """Get currently selected train ID"""
        return self.selected_train
    
    def set_selected_block(self, line: str, block: int) -> None:
        """Set currently selected block and notify observers"""
        new_selection = (line, block)
        if new_selection != self.selected_block:
            self.selected_block = new_selection
            self.block_selected.emit(line, block)
    
    def get_selected_block(self) -> Optional[Tuple[str, int]]:
        """Get currently selected block"""
        return self.selected_block
    
    def update_train_state(self, train_id: str, train_obj: Train) -> None:
        """Update train state and notify observers"""
        with self._lock:
            self.trains[train_id] = train_obj
            self.trains_updated.emit()
            self.state_changed.emit()
    
    def add_maintenance_closure(self, line: str, block: int) -> None:
        """Add maintenance closure and notify observers"""
        with self._lock:
            if line not in self.maintenance_closures:
                self.maintenance_closures[line] = set()
            self.maintenance_closures[line].add(block)
            self.maintenance_updated.emit()
            self.state_changed.emit()
    
    def remove_maintenance_closure(self, line: str, block: int) -> None:
        """Remove maintenance closure and notify observers"""
        with self._lock:
            if line in self.maintenance_closures:
                self.maintenance_closures[line].discard(block)
                if not self.maintenance_closures[line]:
                    del self.maintenance_closures[line]
                self.maintenance_updated.emit()
                self.state_changed.emit()
    
    def get_maintenance_closures(self) -> Dict[str, List[int]]:
        """Get current maintenance closures"""
        return {
            line: list(blocks) 
            for line, blocks in self.maintenance_closures.items()
        }
    
    def is_block_closed(self, line: str, block: int) -> bool:
        """Check if a block is closed for maintenance"""
        return block in self.maintenance_closures.get(line, set())
    
    def add_warning(self, warning_type: str, message: str, **kwargs) -> None:
        """Add a warning to the system"""
        import time
        with self._lock:
            warning = {
                'type': warning_type,
                'message': message,
                'timestamp': time.time(),
                'id': f"{warning_type}_{len(self.warnings)}_{int(time.time())}",
                **kwargs
            }
            self.warnings.append(warning)
            self.warnings_updated.emit()
            self.state_changed.emit()
    
    def remove_warning(self, warning_id: str) -> bool:
        """Remove a warning from the system"""
        with self._lock:
            for i, warning in enumerate(self.warnings):
                if warning.get('id') == warning_id:
                    del self.warnings[i]
                    self.warnings_updated.emit()
                    self.state_changed.emit()
                    return True
            return False
    
    def get_warnings(self) -> List[Dict]:
        """Get copy of all active warnings"""
        return self.warnings.copy()
    
    def clear_warnings(self) -> None:
        """Clear all warnings"""
        with self._lock:
            self.warnings.clear()
            self.warnings_updated.emit()
            self.state_changed.emit()
    
    def update_track_status(self, line: str, block: int, status: str) -> None:
        """Update track status for a specific block"""
        if line not in self.trackStatus:
            self.trackStatus[line] = {}
        self.trackStatus[line][block] = status
        self.state_changed.emit()
    
    def get_track_status(self, line: str, block: int) -> Optional[str]:
        """Get track status for a specific block"""
        return self.trackStatus.get(line, {}).get(block)
    
    def update_railway_crossing(self, line: str, block: int, status: str) -> None:
        """Update railway crossing status"""
        self.railwayCrossings[(line, block)] = status
        self.state_changed.emit()
    
    def get_railway_crossing_status(self, line: str, block: int) -> Optional[str]:
        """Get railway crossing status"""
        return self.railwayCrossings.get((line, block))
    
    def update_switch_position(self, switch_id: str, line: str, block: int, position: str) -> None:
        """Update switch position"""
        self.switch_positions[switch_id] = {
            'line': line,
            'block': block,
            'position': position
        }
        self.state_changed.emit()
    
    def get_switch_position(self, switch_id: str) -> Optional[Dict]:
        """Get switch position data"""
        return self.switch_positions.get(switch_id)
    
    def set_time_multiplier(self, multiplier: float) -> None:
        """Set system time acceleration multiplier"""
        self.system_time_multiplier = max(0.1, min(10.0, multiplier))
        self.state_changed.emit()
    
    def get_time_multiplier(self) -> float:
        """Get current time acceleration multiplier"""
        return self.system_time_multiplier
    
    def set_active_lines(self, lines: List[str]) -> None:
        """Set which lines are active in the system"""
        valid_lines = ["Blue", "Red", "Green"]
        self.active_lines = [line for line in lines if line in valid_lines]
        self.state_changed.emit()
    
    def get_active_lines(self) -> List[str]:
        """Get list of currently active lines"""
        return self.active_lines.copy()
    
    def get_system_stats(self) -> Dict:
        """Get comprehensive system statistics"""
        with self._lock:
            return {
                'active_trains': len(self.trains),
                'maintenance_closures': sum(len(blocks) for blocks in self.maintenance_closures.values()),
                'active_warnings': len(self.warnings),
                'active_lines': self.active_lines.copy(),
                'time_multiplier': self.system_time_multiplier,
                'selected_train': self.selected_train,
                'selected_block': self.selected_block
            }
    
    # Methods from UML
    
    def validate_ID(self, trainID: str) -> bool:
        """
        Validate train ID uniqueness
        
        Args:
            trainID: Train ID to validate
            
        Returns:
            True if train ID is valid and unique
        """
        # Use the migrated train ID validation
        if not self.is_valid_train_id(trainID):
            return False
        
        # Check for uniqueness
        if trainID in self.trains:
            return False
        
        logger.debug(f"Train ID {trainID} validated successfully")
        return True
    
    def get_train_list(self) -> List:
        """
        Get all active trains
        
        Returns:
            List of active Train objects
        """
        return list(self.trains.values())
    
    def get_route(self, trainID: str) -> Optional[Route]:
        """
        Get route for specific train
        
        Args:
            trainID: ID of train to get route for
            
        Returns:
            Route object for train, or None if not found
        """
        if trainID in self.trains:
            train = self.trains[trainID]
            if hasattr(train, 'route'):
                return train.route
        
        return None
    
    def generate_route(self, startBlock: Block, endBlock: Block, arrivalTime: datetime = None) -> Optional[Route]:
        """
        Generate optimal route between blocks using Route Manager
        
        Args:
            startBlock: Starting block
            endBlock: Destination block
            arrivalTime: Desired arrival time (defaults to current time + 1 hour if None)
            
        Returns:
            Generated Route object, or None if no route possible
        """
        try:
            # Use Route Manager for pathfinding (Route Manager handles BFS)
            if not hasattr(self, 'routeManager') or not self.routeManager:
                logger.error("No Route Manager available for route generation")
                return None
            
            # Set CTC system reference in Route Manager for block access
            self.routeManager.ctc_system = self
            
            # Use provided arrival time or default to 1 hour from current time
            if arrivalTime is None:
                arrivalTime = _get_simulation_time() + timedelta(hours=1)
            
            # Generate route using Route Manager's BFS pathfinding
            route = self.routeManager.generate_route(
                startBlock,
                endBlock,
                arrivalTime
            )
            
            if route:
                # Store route
                self.routes[route.routeID] = route
                logger.info(f"Route generated: {route.routeID}")
                return route
            else:
                logger.warning(f"Generated route failed")
                return None
                
        except Exception as e:
            logger.error(f"Error generating route: {e}")
            return None
    
    def update_throughput(self, tickets: int, line: str = None) -> str:
        """
        Update throughput metrics with ticket purchase data
        
        Args:
            tickets: Number of tickets purchased
            line: Line name (Blue, Red, Green) for line-specific tracking
            
        Returns:
            Confirmation message
        """
        try:
            current_time = _get_simulation_time()
            
            # Add to new ticket purchase history with line tracking
            purchase_entry = {
                'tickets': tickets,
                'line': line,
                'timestamp': current_time
            }
            self.ticket_purchase_history.append(purchase_entry)
            
            # Legacy support - keep old throughputMetrics for compatibility
            self.throughputMetrics.append(tickets)
            
            # Clean up old data (older than 1 hour)
            self._cleanup_old_throughput_data()
            
            # Calculate current hourly throughput
            hourly_rates = self.calculate_hourly_throughput()
            
            # Update display with calculated rates - use per-line data for proper display
            if self.displayManager:
                # Use the new update_line_throughput method to send per-line data
                for line, rate in hourly_rates.items():
                    if hasattr(self.displayManager, 'update_line_throughput'):
                        self.displayManager.update_line_throughput(line, rate)
            
            logger.debug(f"Throughput updated: +{tickets} tickets for {line or 'unknown'} line")
            return "confirm"
            
        except Exception as e:
            logger.error(f"Error updating throughput: {e}")
            return f"error: {str(e)}"
    
    def calculate_hourly_throughput(self, line: str = None) -> Dict[str, int]:
        """
        Calculate hourly throughput based on ticket purchases in the last hour
        
        Args:
            line: Optional line filter. If None, returns all lines
            
        Returns:
            Dictionary with line names as keys and hourly ticket counts as values
        """
        try:
            current_time = _get_simulation_time()
            cutoff_time = current_time - timedelta(hours=1)
            
            # Filter purchases from last hour
            recent_purchases = [
                purchase for purchase in self.ticket_purchase_history
                if purchase['timestamp'] >= cutoff_time
            ]
            
            # Calculate throughput by line
            hourly_rates = {'Blue': 0, 'Red': 0, 'Green': 0}
            
            for purchase in recent_purchases:
                purchase_line = purchase.get('line')
                tickets = purchase.get('tickets', 0)
                
                if purchase_line in hourly_rates:
                    hourly_rates[purchase_line] += tickets
            
            # Return specific line or all lines
            if line:
                return {line: hourly_rates.get(line, 0)}
            else:
                return hourly_rates
                
        except Exception as e:
            logger.error(f"Error calculating hourly throughput: {e}")
            return {'Blue': 0, 'Red': 0, 'Green': 0} if not line else {line: 0}
    
    def get_throughput_by_line(self, line: str) -> int:
        """
        Get current hourly throughput for a specific line
        
        Args:
            line: Line name (Blue, Red, Green)
            
        Returns:
            Number of tickets purchased in the last hour for the line
        """
        hourly_rates = self.calculate_hourly_throughput(line)
        return hourly_rates.get(line, 0)
    
    def _cleanup_old_throughput_data(self):
        """
        Remove throughput data older than 1 hour to prevent memory buildup
        """
        try:
            current_time = _get_simulation_time()
            cutoff_time = current_time - timedelta(hours=1)
            
            # Clean up new ticket purchase history
            self.ticket_purchase_history = [
                purchase for purchase in self.ticket_purchase_history
                if purchase['timestamp'] >= cutoff_time
            ]
            
            # Clean up legacy throughputMetrics (keep only recent entries)
            if len(self.throughputMetrics) > 3600:  # Keep 1 hour of data assuming 1 entry per second
                self.throughputMetrics = self.throughputMetrics[-3600:]
                
        except Exception as e:
            logger.error(f"Error cleaning up throughput data: {e}")
    
    def schedule_route(self, route: Route) -> None:
        """
        Schedule route activation
        
        Args:
            route: Route object to schedule
        """
        # Store route
        self.routes[route.routeID] = route
        
        # Schedule with communication handler
        if self.communicationHandler:
            self.communicationHandler.schedule_route(route)
        
        # Update display
        if self.displayManager:
            self.displayManager.display_route(route)
        
        logger.info(f"Route {route.routeID} scheduled")
    
    def confirm_route(self, route: Route) -> str:
        """
        Confirm route scheduling
        
        Args:
            route: Route object to confirm
            
        Returns:
            Confirmation message or error
        """
        try:
            if route.routeID not in self.routes:
                return "ERROR: Route not found"
            
            # Validate route is still feasible
            if not self.routeManager.validate_route(route):
                return "ERROR: Route no longer valid"
            
            # Activate route
            if route.trainID:
                route.activate_route(route.trainID)
                self.activeTrains.append(route.trainID)
            
            return f"CONFIRMED: Route {route.routeID} activated"
            
        except Exception as e:
            return f"ERROR: {str(e)}"
    
    def validate_closure(self, block: Block, time: datetime) -> bool:
        """
        Validate block closure feasibility
        
        Args:
            block: Block to close
            time: Closure time
            
        Returns:
            True if closure is feasible
        """
        # Check if block exists and is operational
        if not block or not hasattr(block, 'blockID'):
            return False
        
        block_id = block.blockID
        if block_id not in self.blocks:
            return False
        
        actual_block = self.blocks[block_id]
        
        # Check if block is currently occupied
        if actual_block.occupied:
            logger.warning(f"Block {block_id} closure denied: currently occupied")
            return False
        
        # Check scheduled occupations
        for train in self.trains.values():
            if hasattr(train, 'route') and train.route:
                route = train.route
                # Check if train's route uses this block at the closure time
                if self._route_uses_block_at_time(route, block_id, time):
                    logger.warning(f"Block {block_id} closure denied: scheduled train conflict")
                    return False
        
        logger.info(f"Block {block_id} closure validated for {time}")
        return True

    def system_tick(self, current_time: datetime) -> None:
        """
        Main update cycle called every simulated second (from update_worker)
        
        Args:
            current_time: Current system time
        """
        self.system_time = current_time
        logger.debug(f"System tick: {current_time}")
        
        # Update all trains
        self._update_trains()
        
        # Update routes
        self._update_routes()
        
        # Check for scheduled departures and automatically trigger dispatch_train_from_yard
        self._check_departure_times(current_time)
        
        # Check for failures and conflicts
        self.check_system_state()
        
        # Process scheduled closures (moved from FailureManager)
        closure_actions = self.process_scheduled_closures()
        opening_actions = self.process_scheduled_openings()
        if closure_actions or opening_actions:
            logger.debug(f"Processed {len(closure_actions)} closures, {len(opening_actions)} openings")
        
        # Commands are now sent only on events (routing, rerouting, block occupation updates)
        # No continuous command sending
        
        # Update metrics including throughput cleanup and calculation
        self._update_metrics()
        
        # Clean up old throughput data and calculate current rates
        self._cleanup_old_throughput_data()
        
        # Calculate current hourly throughput per line
        hourly_rates = self.calculate_hourly_throughput()
        
        # Update display manager with per-line throughput if available
        if self.displayManager and hourly_rates:
            # Update all line throughput data at once to emit single signal
            if hasattr(self.displayManager, 'update_all_line_throughput'):
                self.displayManager.update_all_line_throughput(hourly_rates)
            elif hasattr(self.displayManager, 'throughput_updated'):
                # Direct signal emission with proper format
                self.displayManager.throughput_updated.emit({
                    'per_line': hourly_rates.copy(),
                    'total': sum(hourly_rates.values()),
                    'timestamp': _get_simulation_time()
                })
    
    
    def check_system_state(self) -> None:
        """Basic system state check - checks for failures and simple emergencies"""
        if self.failureManager:
            self.failureManager.check_for_failures()
            
            # Perform train emergency detection using the new threshold-based system
            emergencies = self.failureManager.detect_train_emergencies()
            if emergencies:
                logger.warning(f"Detected {len(emergencies)} potential train emergencies")
                # Handle emergencies by logging them
                for emergency in emergencies:
                    logger.warning(f"Emergency detected: {emergency['description']}")
                    # Emergency already logged in failure_manager, no additional action needed here
    
    def add_train(self, train_or_line, block=None, train_id=None) -> bool:
        """
        Add train to system (supports multiple call signatures for compatibility)
        
        Args:
            train_or_line: Train object OR line name
            block: Block number (if first arg is line)
            train_id: Train ID (if first arg is line)
            
        Returns:
            True if train added successfully, or train ID if creating new train
        """
        # Handle different call signatures for compatibility
        if isinstance(train_or_line, str) and block is not None:
            # Called as add_train(line, block, train_id=None)
            line = train_or_line
            if not train_id:
                train_id = self.generate_train_id(line)
            else:
                # If train_id is provided, ensure counter is updated
                if self.is_valid_train_id(train_id):
                    # Extract number from train ID and update counter if needed
                    try:
                        train_number = int(train_id[1:4])
                        if train_number >= self.line_counters[line]:
                            self.line_counters[line] = train_number + 1
                    except (ValueError, KeyError):
                        # Invalid train ID format - use next available number
                        print(f"WARNING: Invalid train ID format for {line}: {train_id}")
            
            # Get the Block object for the current block
            block_obj = self.blocks.get(block)
            if not block_obj:
                # Create a simple block object if not found
                block_obj = type('Block', (), {'blockID': block, 'blockNumber': block})()
            
            # Create proper Train object using Train class
            train = Train(
                trainID=train_id,
                currentBlock=block_obj
            )
            # Set additional attributes following TBTG naming conventions
            train.line = line
            train.authority = 1
            train.passengers = 0
            train.routingStatus = 'Unrouted'   # TBTG: camelCase
            train.departureTime = None         # TBTG: camelCase
            train.arrivalTime = None          # TBTG: camelCase
            
            self.trains[train_id] = train
            self.trainAuthorities[train_id] = 1
            self.trainSuggestedSpeeds[train_id] = 0
            self.active_train_ids.add(train_id)
            
            # Train location tracking is handled by wayside controller reports
            # The communication handler will update train locations only when it receives
            # actual block occupation data from wayside controllers
            
            self.trains_updated.emit()
            self.state_changed.emit()
            logger.info(f"Train {train_id} added to system on {line} line at block {block}")
            return train_id
        else:
            # Called with train object
            train = train_or_line
            train_id = self._get_train_id(train)
            
            if not self.validate_ID(train_id):
                logger.error(f"Cannot add train {train_id}: invalid ID")
                return False
            
            self.trains[train_id] = train
            self.trainAuthorities[train_id] = getattr(train, 'authority', 1)
            self.trainSuggestedSpeeds[train_id] = getattr(train, 'speed', 0)
            self.active_train_ids.add(train_id)
            self.trains_updated.emit()
            self.state_changed.emit()
            logger.info(f"Train {train_id} added to system")
            return True
    
    def remove_train(self, train_id: str) -> bool:
        """
        Remove train from system
        
        Args:
            train_id: ID of train to remove
            
        Returns:
            True if train removed successfully
        """
        if train_id in self.trains:
            train = self.trains[train_id]
            
            # Clear train from any blocks
            if hasattr(train, 'currentBlock') and train.currentBlock:
                if train.currentBlock in self.blocks:
                    block = self.blocks[train.currentBlock]
                    # Only remove if this train is actually occupying the block
                    if hasattr(block, 'occupyingTrain') and block.occupyingTrain == train:
                        block.remove_train()
                    else:
                        logger.debug(f"Train {train_id} not occupying block {train.currentBlock}, skipping removal")
            
            # Deactivate route
            if hasattr(train, 'route') and train.route:
                train.route.deactivate_route()
            
            del self.trains[train_id]
            
            # Remove from authority and speed tracking
            if train_id in self.trainAuthorities:
                del self.trainAuthorities[train_id]
            if train_id in self.trainSuggestedSpeeds:
                del self.trainSuggestedSpeeds[train_id]
            
            # Remove from active trains
            if train_id in self.activeTrains:
                self.activeTrains.remove(train_id)
            
            # Release train ID
            self.release_train_id(train_id)
            
            # Remove from communication handler tracking
            if self.communicationHandler:
                self.communicationHandler.remove_train_from_system(train_id)
            
            # Clear selection if this train was selected
            if self.selected_train == train_id:
                self.selected_train = None
                self.train_selected.emit("")
            
            self.trains_updated.emit()
            self.state_changed.emit()
            
            logger.info(f"Train {train_id} removed from system")
            return True
        
        return False
    
    def get_block(self, block_id: int) -> Optional[Block]:
        """
        Get block by ID
        
        Args:
            block_id: Block number
            
        Returns:
            Block object or None if not found
        """
        return self.blocks.get(block_id)
    
    def get_block_by_line(self, line: str, block_number: int) -> Optional[Block]:
        """
        Get block by line and block number to avoid cross-line conflicts
        
        Args:
            line: Line name (Blue, Red, Green)
            block_number: Block number
            
        Returns:
            Block object for the specific line or None if not found
        """
        for block in self.blocks.values():
            if (hasattr(block, 'line') and block.line == line and 
                block.blockID == block_number):
                return block
        
        return None
    
    def get_all_blocks(self) -> Dict[int, Block]:
        """Get all blocks in system"""
        return self.blocks.copy()
    
    def process_occupied_blocks(self, occupied_blocks: List[bool]) -> None:
        """
        Process occupied blocks update from wayside
        Updates block objects, train objects, and route objects based on occupation changes
        
        Args:
            occupied_blocks: List of block occupation states (block index -> occupation)
        """
        logger.debug(f"Processing {len(occupied_blocks)} block occupancy updates")
        
        # Track trains that moved for route updates
        trains_moved = set()
        
        # Process each block in the occupied_blocks array
        for block_index, is_occupied in enumerate(occupied_blocks):
            # Find the corresponding block object
            block_obj = self._get_block_by_index(block_index)
            if not block_obj:
                logger.debug(f"No block object found for index {block_index}")
                continue
            
            block_id = block_obj.blockID
            old_occupation = block_obj.occupied
            
            # Update block occupation status
            block_obj.update_occupation(is_occupied)
            
            # Handle occupation changes
            if old_occupation != is_occupied:
                if is_occupied:
                    # Block became occupied - find which train entered
                    train = self._find_train_for_occupied_block(block_obj)
                    if train:
                        # Update block with train reference
                        block_obj.add_train(train)
                        
                        # Update train location
                        old_block = train.currentBlock
                        train.update_location(block_obj, 0.0)
                        
                        # Update train movement history for emergency detection
                        train.update_movement_history(block_id)
                        
                        # Track train for route updates
                        trains_moved.add(train.trainID)
                        
                        logger.info(f"Train {train.trainID} entered block {block_id}")
                        
                        # Remove train from old block if different
                        if old_block and old_block.blockID != block_id:
                            old_block_obj = self.get_block_by_number(old_block.blockID)
                            if old_block_obj and old_block_obj.occupyingTrain == train:
                                old_block_obj.remove_train()
                    else:
                        logger.warning(f"Block {block_id} became occupied but no train found")
                
                else:
                    # Block became unoccupied
                    if block_obj.occupyingTrain:
                        departing_train = block_obj.occupyingTrain
                        
                        # Update train movement history
                        departing_train.update_movement_history(block_id)
                        
                        # Remove train from block
                        block_obj.remove_train()
                        
                        logger.info(f"Train {departing_train.trainID} left block {block_id}")
            
            # Always update movement history for trains currently in blocks
            elif is_occupied and block_obj.occupyingTrain:
                # Train still in same block - update movement history for emergency detection
                train = block_obj.occupyingTrain
                train.update_movement_history(block_id)
        
        # Update route progress for all trains that moved
        for train_id in trains_moved:
            train = self.trains.get(train_id)
            if train and train.route:
                train.route.update_location(train.currentBlock)
                logger.debug(f"Route progress updated for train {train_id}")
        
        # CRITICAL FIX: Send updated commands for trains based on current positions
        # Commands sent TO train's current block FOR block 4 positions ahead
        # This replaces the old system that sent commands to yard/first block
        if trains_moved and hasattr(self, 'communication_handler') and self.communication_handler:
            print(f"📡 OCCUPANCY TRIGGER: {len(trains_moved)} trains moved, sending updated batched commands")
            
            # Use new batched command system that sends commands to current blocks
            # for targets 4 positions ahead with proper route distance calculation
            self.communication_handler.send_updated_train_commands()
            
            logger.info(f"Updated commands sent for {len(trains_moved)} moved trains using batched system")
        elif trains_moved:
            logger.warning("Trains moved but no communication handler available for command updates")
        
        # Emit signal for UI updates if available
        if hasattr(self, 'block_updates_signal'):
            self.block_updates_signal.emit()
        
        logger.debug(f"Completed processing {len(occupied_blocks)} block occupancy updates")
    
    def _get_blocks_with_switches(self, line: str) -> List[int]:
        """
        Get list of block numbers that have switches on the specified line
        
        Args:
            line: Line name ("Red" or "Green")
            
        Returns:
            List of block numbers that have switches
        """
        blocks_with_switches = []
        
        # Use track layout reader to identify blocks with switches
        if hasattr(self.trackLayout, 'lines') and line in self.trackLayout.lines:
            for block_data in self.trackLayout.lines[line]:
                if hasattr(block_data, 'has_switch') and block_data.has_switch:
                    blocks_with_switches.append(block_data.block_number)
                    
        # Alternative method if blocks are stored differently
        elif hasattr(self.trackLayout, 'export_for_display'):
            display_data = self.trackLayout.export_for_display(line)
            for block_info in display_data:
                if block_info.get('has_switch', False):
                    blocks_with_switches.append(block_info['block_number'])
        
        # Fallback: check our own blocks storage
        else:
            for (block_line, block_num), block in self.blocks.items():
                if block_line == line and hasattr(block, 'switchPresent') and block.switchPresent:
                    blocks_with_switches.append(block_num)
        
        blocks_with_switches.sort()
        logger.debug(f"Found {len(blocks_with_switches)} blocks with switches on {line} line: {blocks_with_switches}")
        return blocks_with_switches

    def process_switch_positions(self, switch_positions: List[bool], line: str) -> None:
        """
        Process switch positions update from wayside
        
        Args:
            switch_positions: List of switch positions (array indexed by block number)
                            Only positions for blocks with switches are meaningful
                            Array may be shorter than total blocks due to wayside filtering
            line: The line name ("Red", "Green", "Blue") that this data is for
        """
        logger.debug(f"Processing {len(switch_positions)} switch position updates for {line} line")
        
        if not switch_positions:
            logger.warning(f"Empty switch positions array received for {line} line")
            return
            
        # Get blocks that actually have switches on this line
        switch_blocks = self._get_blocks_with_switches(line)
        
        if not switch_blocks:
            logger.warning(f"No blocks with switches found on {line} line")
            return
            
        updates_applied = 0
        
        # Process switch positions only for blocks that have switches
        for block_num in switch_blocks:
            if block_num < len(switch_positions):
                switch_position = switch_positions[block_num]
                
                # Update block switch position if block exists
                block_key = (line, block_num)
                if block_key in self.blocks:
                    block = self.blocks[block_key]
                    if hasattr(block, 'set_switch_position'):
                        old_position = getattr(block, 'switchPosition', None)
                        block.set_switch_position(switch_position)
                        
                        if old_position != switch_position:
                            position_name = "reverse" if switch_position else "normal"
                            logger.info(f"{line} line block {block_num} switch updated to {position_name} position")
                            updates_applied += 1
                
                # Update switch positions tracking
                switch_id = f"{line}_Block_{block_num}"
                position_name = "reverse" if switch_position else "normal"
                self.update_switch_position(switch_id, line, block_num, position_name)
            else:
                logger.debug(f"Switch block {block_num} not in wayside data (block {block_num} >= array length {len(switch_positions)}) - expected when wayside controller doesn't control this switch")
        
        logger.debug(f"Applied {updates_applied} switch position updates on {line} line (blocks with switches: {switch_blocks})")
    
    def process_railway_crossings(self, railway_crossings: List[bool]) -> None:
        """
        Process railway crossings update from wayside
        
        Args:
            railway_crossings: List of crossing states
        """
        # Update crossing states in blocks
        logger.debug(f"Processing {len(railway_crossings)} crossing state updates")
    
    def provide_wayside_controller(self, waysideControllerObject, blocksCovered: List[bool], redLine: bool):
        """
        Register wayside controller with CTC system
        Called by wayside controllers to establish communication
        
        The communication system sends full line data to all controllers on that line,
        but each controller should only act on blocks it manages and only send data for managed blocks.
        
        Args:
            waysideControllerObject: Wayside controller instance with command_train, command_switch, set_occupied methods
            blocksCovered: List of booleans indicating which blocks this controller manages 
                          (True = controller manages this block, False = doesn't manage)
                          Index 0 is yard, index 1 is block 1, etc.
                          Controller will receive commands for entire line but should only act on managed blocks.
                          Controller should only send data (occupied blocks, switches, crossings) for managed blocks.
            redLine: True if this controller is for the red line, False if for green line
            
        Returns:
            CommunicationHandler: Reference to the communication handler for wayside controller to use
        """
        if self.communicationHandler:
            # Convert boolean list to actual block numbers for internal use
            managed_blocks = [i for i, is_managed in enumerate(blocksCovered) if is_managed]
            
            self.communicationHandler.provide_wayside_controller(waysideControllerObject, blocksCovered, redLine)
            line_name = "Red" if redLine else "Green"
            logger.info(f"Wayside controller registered for {line_name} line covering blocks {managed_blocks}")
            return self.communicationHandler
        else:
            logger.error("Cannot register wayside controller: Communication handler not initialized")
            return None
    
    # Private helper methods
    
    def _initialize_components(self):
        """Initialize all system components"""
        try:
            # Create core components
            self.communicationHandler = CommunicationHandler()
            self.displayManager = DisplayManager()
            self.failureManager = FailureManager()
            self.routeManager = RouteManager(self.trackLayout)
            
            
            # Set up component references
            self.communicationHandler.ctc_system = self
            self.communicationHandler.track_reader = self.trackLayout
            # Initialize yard connections after track reader is set
            self._initialize_yard_connections()
            self.failureManager.ctc_system = self
            self.failureManager.communication_handler = self.communicationHandler
            self.failureManager.display_manager = self.displayManager
            self.routeManager.ctc_system = self
            
            logger.info("CTC System components initialized")
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
    
    def _initialize_blocks(self):
        """Initialize blocks from track layout with comprehensive error handling"""
        logger.info("Starting block initialization...")
        logger.info(f"TrackLayout object: {self.trackLayout}")
        logger.info(f"TrackLayout type: {type(self.trackLayout)}")
        
        if not self.trackLayout:
            logger.warning("No track layout available - will use fallback basic blocks")
            return
        
        try:
            # Get selected lines from track reader
            logger.debug("Getting selected lines from track reader...")
            lines = getattr(self.trackLayout, 'selected_lines', ['Blue', 'Red', 'Green'])
            logger.info(f"Initializing blocks for lines: {lines}")
            
            # Check if trackLayout has the expected attributes
            logger.debug(f"TrackLayout attributes: {[attr for attr in dir(self.trackLayout) if not attr.startswith('_')]}")
            
            total_blocks_loaded = 0
            line_block_counts = {}
            
            for line in lines:
                try:
                    # Get blocks for this line from track reader
                    line_blocks = self._get_blocks_for_line(line)
                    logger.debug(f"Found {len(line_blocks)} blocks for {line} line")
                    
                    blocks_loaded_for_line = 0
                    
                    for track_block in line_blocks:
                        try:
                            logger.debug(f"Processing track block for {line} line: {getattr(track_block, 'block_number', '?')}")
                            
                            # Debug the track_block data structure
                            if hasattr(track_block, 'block_number'):
                                logger.debug(f"Track block {track_block.block_number} type: {type(track_block)}")
                                logger.debug(f"Track block {track_block.block_number} attributes: {[attr for attr in dir(track_block) if not attr.startswith('_')]}")
                            
                            # Create proper Block object from TrackBlock data
                            logger.debug(f"Attempting to create Block object from track_block")
                            block = Block(track_block)
                            logger.debug(f"Successfully created Block object")
                            
                            block_number = track_block.block_number
                            
                            # Store in line-aware structure
                            self.blocks[(line, block_number)] = block
                            
                            blocks_loaded_for_line += 1
                            total_blocks_loaded += 1
                            
                            # Debug high-numbered blocks specifically
                            if block_number >= 90:
                                logger.info(f"Loaded high-numbered block: {line} line block {block_number}")
                                
                        except Exception as e:
                            logger.error(f"CRITICAL ERROR creating Block object for {line} line block {getattr(track_block, 'block_number', '?')}: {e}")
                            logger.error(f"Track block type: {type(track_block)}")
                            logger.error(f"Track block str: {str(track_block)}")
                            logger.error(f"Track block attributes: {dir(track_block) if hasattr(track_block, '__dict__') else 'No __dict__'}")
                            import traceback
                            logger.error(f"Full traceback: {traceback.format_exc()}")
                    
                    line_block_counts[line] = blocks_loaded_for_line
                    logger.info(f"Successfully loaded {blocks_loaded_for_line} blocks for {line} line")
                        
                except Exception as e:
                    logger.error(f"Could not load blocks for {line} line: {e}")
                    line_block_counts[line] = 0
            
            # Add yard blocks based on actual track data - find blocks that connect to yard
            for line in lines:
                if (line, 0) not in self.blocks:
                    # Find all blocks on this line that connect to yard
                    yard_connected_blocks = []
                    line_blocks = [block for (l, b_num), block in self.blocks.items() if l == line]
                    
                    for block in line_blocks:
                        if hasattr(block, 'has_yard_connection') and block.has_yard_connection:
                            yard_connected_blocks.append(block.blockID)
                    
                    # Also include blocks from yard connections data
                    if line in self.yard_connections:
                        for connection in self.yard_connections[line]:
                            from_block = connection.get('from_block')
                            to_block = connection.get('to_block')
                            # If yard connects TO a block, include it
                            if from_block == "yard" and isinstance(to_block, int):
                                if to_block not in yard_connected_blocks:
                                    yard_connected_blocks.append(to_block)
                            # If a block connects TO yard, include it
                            elif to_block == "yard" and isinstance(from_block, int):
                                if from_block not in yard_connected_blocks:
                                    yard_connected_blocks.append(from_block)
                    
                    # Use only actual track data connections - no hardcoded fallbacks
                    
                    # Only create yard block if we have actual connections from track data
                    if yard_connected_blocks:
                        yard_data = type('YardBlock', (), {
                            'block_number': 0,
                            'length_m': 200,
                            'grade_percent': 0.0,
                            'speed_limit_kmh': 25,
                            'has_switch': False,
                            'has_crossing': False,
                            'has_station': True,
                            'line': line,
                            'section': 'Y',
                            'elevation_m': 100,
                            'direction': 'BIDIRECTIONAL',
                            'is_underground': False,
                            'station': type('YardStation', (), {'name': f'{line} Yard'})(),
                            'switch': None,
                            'connected_blocks': yard_connected_blocks  # Use actual track data connections
                        })()
                        yard_block = Block(yard_data)
                        
                        # Store in line-aware structure
                        self.blocks[(line, 0)] = yard_block
                        logger.info(f"Created yard block for {line} line with connections to blocks: {yard_connected_blocks}")
                    else:
                        logger.warning(f"No yard connections found for {line} line in track data")
                    
                    
                    total_blocks_loaded += 1
                    logger.debug(f"Added yard block for {line} line")
            
            logger.info(f"Initialized {total_blocks_loaded} total blocks from track layout")
            logger.info(f"Blocks per line: {line_block_counts}")
            
            # DEBUG: Show which blocks have switches
            self._debug_log_blocks_with_switches()
            
            # Verify Castle Shannon block specifically
            castle_shannon_block = self.get_block_by_line_new('Green', 96)
            if castle_shannon_block:
                logger.info("Castle Shannon block (Green line, block 96) successfully loaded")
            else:
                logger.warning("Castle Shannon block (Green line, block 96) NOT found in loaded blocks")
            
        except Exception as e:
            logger.error(f"Critical error initializing blocks from track layout: {e}")
            logger.error("This will cause route generation to fail - check track layout file and TrackLayoutReader")
    
    def _get_blocks_for_line(self, line: str) -> List:
        """Get block data for specific line from track reader"""
        if self.trackLayout and hasattr(self.trackLayout, 'lines'):
            return self.trackLayout.lines.get(line, [])
        return []
    
    def _initialize_yard_connections(self) -> None:
        """
        Initialize yard connection data from track reader and block connections
        Centralized yard connection management in CTC system
        """
        if not self.trackLayout:
            logger.warning("Track reader not available - yard connections will not be initialized")
            return
            
        try:
            # Get yard connections from track reader (for switch-based connections)
            if hasattr(self.trackLayout, 'get_yard_connections'):
                yard_connections = self.trackLayout.get_yard_connections()
            else:
                yard_connections = []
                
            # Initialize yard connections storage
            self.yard_connections = {}
            self.line_yard_blocks = {}
            
            # Organize by line
            for connection in yard_connections:
                line = connection.get('line')
                if line:
                    if line not in self.yard_connections:
                        self.yard_connections[line] = []
                    self.yard_connections[line].append(connection)
                    
                    # Track the first block after yard for each line
                    from_block = connection.get('from_block')
                    to_block = connection.get('to_block')
                    
                    if from_block == "yard" and isinstance(to_block, int):
                        # Yard connects to this block
                        self.line_yard_blocks[line] = to_block
                    elif to_block == "yard" and isinstance(from_block, int):
                        # This block connects to yard (reverse direction)
                        if line not in self.line_yard_blocks:
                            self.line_yard_blocks[line] = from_block
            
            # Additionally, check for direct yard connections in block data
            # This finds blocks where connected_blocks includes 0 (yard)
            for (line, block_number), block in self.blocks.items():
                if block_number == 0:  # Skip yard blocks themselves
                    continue
                    
                if hasattr(block, 'connected_blocks') and 0 in block.connected_blocks:
                    # This block connects to yard
                    if line not in self.yard_connections:
                        self.yard_connections[line] = []
                    
                    # Add direct connection info
                    connection_info = {
                        'type': 'direct',
                        'line': line,
                        'from_block': block_number,
                        'to_block': 0,
                        'connection_type': 'yard_access'
                    }
                    self.yard_connections[line].append(connection_info)
                    
                    # Update line yard blocks if not already set
                    if line not in self.line_yard_blocks:
                        self.line_yard_blocks[line] = block_number
                    
                    logger.info(f"Found direct yard connection: {line} line block {block_number} connects to yard")
            
            # Debug output for yard connections
            print(f"YARD CONNECTIONS: Initialized yard connections for lines: {list(self.yard_connections.keys())}")
            logger.info(f"Initialized yard connections for lines: {list(self.yard_connections.keys())}")
            
            for line, connections in self.yard_connections.items():
                print(f"   {line} line: {len(connections)} yard connections")
                logger.info(f"  {line} line: {len(connections)} yard connections")
                for i, conn in enumerate(connections):
                    from_block = conn.get('from_block', 'Unknown')
                    to_block = conn.get('to_block', 'Unknown')
                    conn_type = conn.get('type', 'switch')
                    print(f"     Connection {i+1}: {from_block} -> {to_block} ({conn_type})")
                    logger.debug(f"    Connection {i+1}: {conn}")
            
            print(f"   Line yard exit blocks: {self.line_yard_blocks}")
            logger.info(f"Line yard blocks: {self.line_yard_blocks}")
            
            # Additional validation output
            if not self.yard_connections:
                print("   WARNING: No yard connections found - routing from yard may fail")
                logger.warning("No yard connections found - routing from yard may fail")
            
        except Exception as e:
            logger.error(f"Error initializing yard connections: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
    
    def get_yard_connections(self, line: str = None) -> Dict:
        """
        Get yard connection information for a specific line or all lines
        
        Args:
            line: Line name (optional, returns all if None)
            
        Returns:
            Dict of yard connection information
        """
        if line:
            return {
                'connections': self.yard_connections.get(line, []),
                'yard_block': self.line_yard_blocks.get(line)
            }
        else:
            return {
                'all_connections': self.yard_connections,
                'yard_blocks': self.line_yard_blocks
            }
    
    def get_yard_exit_block(self, line: str) -> Optional[int]:
        """
        Get the first block a train enters when leaving the yard for a specific line
        
        Args:
            line: Line name
            
        Returns:
            Block number of yard exit block, or None if not found
        """
        if line in self.line_yard_blocks:
            return self.line_yard_blocks[line]
        
        # Fallback: try to find from yard connections
        if line in self.yard_connections:
            for connection in self.yard_connections[line]:
                from_block = connection.get('from_block')
                to_block = connection.get('to_block')
                if from_block == "yard" and isinstance(to_block, int):
                    return to_block
                elif to_block == "yard" and isinstance(from_block, int):
                    return from_block
        
        logger.warning(f"Could not determine yard exit block for {line} line")
        return None
    
    def _update_trains(self):
        """Update all trains in system"""
        for train in self.trains.values():
            # Train updates are handled by individual train objects
            # No additional processing needed here currently
            return
    
    def _update_routes(self):
        """Update all active routes"""
        for route in self.routes.values():
            if route.isActive:
                # Update route conditions
                route.update_for_conditions({})
    
    
    def _update_metrics(self):
        """Update system metrics"""
        # Update block metrics
        occupied_count = sum(1 for block in self.blocks.values() if block.occupied)
        self.blockMetrics.append(occupied_count)
        
        # Keep only recent metrics
        if len(self.blockMetrics) > 3600:  # Keep 1 hour of data
            self.blockMetrics = self.blockMetrics[-3600:]
    
    def _check_departure_times(self, current_time: datetime) -> None:
        """
        Check for scheduled departures and automatically trigger dispatch_train_from_yard
        
        Args:
            current_time: Current system time
        """
        timestamp = current_time.strftime("%H:%M:%S.%f")[:-3] if current_time else "??:??:??"
        
        # Check all trains for scheduled departures
        for train_id, train in self.trains.items():
            # Skip trains that have already had their departure triggered
            if train_id in self.departure_triggered:
                continue
                
            # Check if train has a route with scheduled departure
            if not hasattr(train, 'route') or not train.route:
                continue
                
            route = train.route
            scheduled_departure = getattr(route, 'scheduledDeparture', None)
            
            if not scheduled_departure:
                continue
                
            # Check if train is starting from yard (block 0)
            starting_from_yard = (hasattr(route, 'startBlock') and route.startBlock and 
                                getattr(route.startBlock, 'blockID', None) == 0)
            
            if not starting_from_yard:
                continue  # Only handle yard departures automatically
                
            # Check if departure time has arrived (with small tolerance for timing precision)
            time_diff = (current_time - scheduled_departure).total_seconds()
            
            # Trigger departure if current time is at or past departure time (within 1 minute tolerance)
            if -5 <= time_diff <= 60:  # Allow 5 seconds early, up to 60 seconds late
                print(f"[{timestamp}]   DEPARTURE SCHEDULER: Triggering departure for train {train_id}")
                print(f"[{timestamp}]   Scheduled: {scheduled_departure.strftime('%H:%M:%S')}")
                print(f"[{timestamp}]   Current:   {current_time.strftime('%H:%M:%S')}")
                print(f"[{timestamp}]   Time diff: {time_diff:.1f} seconds")
                
                # Mark departure as triggered to prevent duplicate calls
                self.departure_triggered.add(train_id)
                
                # Call dispatch_train_from_yard to send departure commands
                try:
                    self.dispatch_train_from_yard(train_id)
                    logger.info(f"Automatic departure triggered for train {train_id} at scheduled time")
                except Exception as e:
                    logger.error(f"Error triggering automatic departure for train {train_id}: {e}")
                    # Remove from triggered set so it can be retried
                    self.departure_triggered.discard(train_id)
    
    def _route_uses_block_at_time(self, route: Route, block_id: int, time: datetime) -> bool:
        """Check if route uses specific block at given time"""
        # This would check route timing and block sequence
        # Simplified implementation
        if hasattr(route, 'blockSequence'):
            return any(block.blockID == block_id for block in route.blockSequence)
        return False
    
    def _get_block_by_index(self, block_index: int) -> Optional[Block]:
        """
        Find block object by index from occupied_blocks array
        Maps array index to actual block objects based on controller coverage
        
        Args:
            block_index: Index in the occupied_blocks array
            
        Returns:
            Block object if found, None otherwise
        """
        # For now, assume index directly maps to block number
        # This should be enhanced to handle proper controller-to-block mapping
        for (line, block_number), block_obj in self.blocks.items():
            if block_number == block_index:
                return block_obj
        
        logger.debug(f"No block found for index {block_index}")
        return None
    
    def _find_train_for_occupied_block(self, block_obj: Block) -> Optional[Train]:
        """
        Find which train should occupy the given block based on routing and proximity.
        Enhanced to handle trains spanning multiple blocks and prioritize frontmost block.
        
        Args:
            block_obj: Block that became occupied
            
        Returns:
            Train object that should be in this block, or None if no train found
        """
        block_id = block_obj.blockID
        logger.debug(f"Finding train for newly occupied block {block_id}")
        
        # Check trains with active routes for this block
        candidate_trains = []
        
        for train in self.trains.values():
            if not hasattr(train, 'route') or not train.route:
                continue
                
            route = train.route
            if not hasattr(route, 'blockSequence') or not route.blockSequence:
                continue
                
            # Check if this block is in the train's route
            for i, route_block in enumerate(route.blockSequence):
                if route_block.blockID == block_id:
                    current_index = getattr(route, 'currentBlockIndex', 0)
                    
                    # Calculate progression from current position
                    blocks_ahead = i - current_index
                    
                    # Accept trains that are progressing forward (0 to 2 blocks ahead)
                    # This handles trains advancing normally or spanning multiple blocks
                    if 0 <= blocks_ahead <= 2:
                        candidate_trains.append((train, blocks_ahead, i))
                        logger.debug(f"Train {train.trainID} candidate: route_pos={i}, current_index={current_index}, blocks_ahead={blocks_ahead}")
        
        # If we have route-based candidates, choose the best one
        if candidate_trains:
            # Sort by progression distance (prefer trains advancing forward)
            # Then by route position (prefer frontmost block for spanning trains)
            candidate_trains.sort(key=lambda x: (x[1], -x[2]))
            chosen_train = candidate_trains[0][0]
            logger.debug(f"Chose train {chosen_train.trainID} for block {block_id} based on route progression")
            return chosen_train
        
        # Fallback: Check for trains whose current block connects to this block
        for train in self.trains.values():
            if not hasattr(train, 'currentBlock') or not train.currentBlock:
                continue
                
            current_block = train.currentBlock
            current_block_id = getattr(current_block, 'blockID', current_block)
            
            # Skip if train is already in the target block
            if current_block_id == block_id:
                continue
            
            # Check if current block connects to the newly occupied block
            if hasattr(current_block, 'connected_blocks'):
                if block_id in current_block.connected_blocks:
                    logger.debug(f"Train {train.trainID} found via connected blocks: {current_block_id} -> {block_id}")
                    return train
            
            # Simple adjacency check as fallback (for sequential blocks)
            if abs(current_block_id - block_id) == 1:
                logger.debug(f"Train {train.trainID} found via adjacency: {current_block_id} -> {block_id}")
                return train
        
        logger.debug(f"No train found for newly occupied block {block_id}")
        return None

    def _get_train_id(self, train) -> str:
        """Extract train ID from train object"""
        if hasattr(train, 'trainID'):
            return str(train.trainID)
        elif hasattr(train, 'id'):
            return str(train.id)
        else:
            return f"train_{id(train)}"
    
    def handle_emergency_stop(self, train_id: str, reason: str = "Emergency detected") -> bool:
        """Simple emergency stop for a specific train"""
        if train_id in self.trains:
            train = self.trains[train_id]
            
            # Add to emergency stops set
            self.emergency_stops.add(train_id)
            
            # Send stop command through communication handler
            if self.communicationHandler:
                self.communicationHandler.stop_train(train)
            
            # Add warning
            self.add_warning(
                "emergency",
                f"Emergency stop activated for Train {train_id}: {reason}",
                severity="critical",
                train_id=train_id
            )
            
            logger.critical(f"Emergency stop activated for train {train_id}: {reason}")
            return True
        
        logger.error(f"Cannot emergency stop train {train_id}: train not found")
        return False
    
    def clear_emergency_stop(self, train_id: str) -> bool:
        """Clear emergency stop for a specific train"""
        if train_id in self.emergency_stops:
            self.emergency_stops.remove(train_id)
            logger.info(f"Emergency stop cleared for train {train_id}")
            return True
        return False
    
    
    def get_emergency_statistics(self) -> Dict:
        """Get simple emergency detection statistics"""
        return {
            "active_emergency_stops": len(self.emergency_stops),
            "emergency_trains": list(self.emergency_stops)
        }
    
    # OLD calculate_route() function removed - UI now uses RouteManager.generate_route() directly
    
    def activate_route(self, train_id, route):
        """Activate route for train and send commands to wayside"""
        # DEBUG: Function entry logging
        timestamp = _get_simulation_time().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}]  DEBUG: activate_route() called for train {train_id}")
        
        if train_id in self.trains and route:
            train = self.trains[train_id]
            
            # Set route on train
            train.route = route
            route.trainID = train_id
            
            # Set departure time and destination on train for display (TBTG camelCase)
            if hasattr(route, 'scheduledDeparture'):
                train.departureTime = route.scheduledDeparture
                train.departure_time = route.scheduledDeparture  # Keep for compatibility
            if hasattr(route, 'scheduledArrival'):
                train.arrivalTime = route.scheduledArrival
                train.arrival_time = route.scheduledArrival      # Keep for compatibility
            if hasattr(route, 'endBlock'):
                train.destination = getattr(route.endBlock, 'blockID', 'Unknown')

            # DEBUG: Log route details
            route_id = getattr(route, 'routeID', 'Unknown')
            departure_time = getattr(route, 'scheduledDeparture', None)
            print(f"[{timestamp}]   DEBUG: Route details - ID: {route_id}, Departure: {departure_time}")
            
            # Update routing status (TBTG camelCase)
            train.routingStatus = "Routed"
            train.routing_status = "Routed"  # Keep for compatibility
            
            # Activate the route
            if hasattr(route, 'activate_route'):
                route.activate_route(train_id)
                print(f"[{timestamp}]  DEBUG: Route object activated for train {train_id}")
            
            # Only send route commands for trains already on track
            # Departure commands for yard trains are sent separately via dispatch_train_from_yard()
            if self.communicationHandler:
                # Check if train is starting from yard (block 0)
                starting_from_yard = (hasattr(route, 'startBlock') and route.startBlock and 
                                    getattr(route.startBlock, 'blockID', None) == 0)
                
                print(f"[{timestamp}] DEBUG: Communication handler available. Starting from yard: {starting_from_yard}")
                
                if not starting_from_yard:
                    # Train already on track - send regular route commands
                    self.communicationHandler.send_train_commands_for_route(train_id, route)
                    logger.debug(f"Route commands sent for train {train_id} already on track")
                    print(f"[{timestamp}]   DEBUG: Route commands sent for train {train_id} already on track")
                else:
                    # Train starting from yard - commands will be sent when dispatch_train_from_yard() is called
                    logger.debug(f"Train {train_id} starting from yard - departure commands will be sent on dispatch")
                    print(f"[{timestamp}]  DEBUG: Train {train_id} starting from yard - waiting for dispatch_train_from_yard() call")
            else:
                print(f"[{timestamp}]   DEBUG: No communication handler available!")
            
            # Emit signals to update UI
            self.trains_updated.emit()
            self.state_changed.emit()
            
            logger.info(f"Route activated for train {train_id}: departure at {getattr(train, 'departure_time', 'N/A')}")
            print(f"[{timestamp}]  DEBUG: Route activation completed for train {train_id}")
            return True
        else:
            print(f"[{timestamp}]  DEBUG: Route activation failed - Train {train_id} not found or route is None")
        return False
    
    def dispatch_train_from_yard(self, train_id: str) -> None:
        """
        Send commands when train departs from yard
        
        Args:
            train_id: ID of train departing from yard
        """
        # DEBUG: Function entry logging with timestamp
        timestamp = _get_simulation_time().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}]  DEBUG: dispatch_train_from_yard() called for train {train_id}")
        
        # DEBUG: Check if train exists
        if train_id not in self.trains:
            print(f"[{timestamp}]   DEBUG: Train {train_id} not found in system")
            logger.error(f"Cannot dispatch train {train_id}: train not found")
            return
            
        # DEBUG: Check if communication handler exists
        if not self.communicationHandler:
            print(f"[{timestamp}]   DEBUG: Communication handler not available")
            logger.error(f"Cannot dispatch train {train_id}: no communication handler")
            return
            
        train = self.trains[train_id]
        print(f"[{timestamp}]   DEBUG: Train {train_id} found in system")
        
        # DEBUG: Check if train has route
        if not hasattr(train, 'route') or not train.route:
            print(f"[{timestamp}]   DEBUG: Train {train_id} has no route assigned")
            logger.warning(f"Cannot dispatch train {train_id}: no route assigned")
            return
            
        route = train.route
        route_id = getattr(route, 'routeID', 'Unknown')
        print(f"[{timestamp}]   DEBUG: Train {train_id} has route {route_id}")
        
        # DEBUG: Log route details for departure
        if hasattr(route, 'blockSequence') and route.blockSequence:
            first_blocks = [block.blockID for block in route.blockSequence[:4]]
            print(f"[{timestamp}]   DEBUG: Route first 4 blocks: {first_blocks}")
        else:
            print(f"[{timestamp}]   DEBUG: Route has no blockSequence")
            
        # DEBUG: Check departure time
        departure_time = getattr(route, 'scheduledDeparture', None)
        current_time = _get_simulation_time()
        print(f"[{timestamp}]   DEBUG: Departure time: {departure_time}, Current time: {current_time}")
        
        # Call communication handler to send departure commands
        print(f"[{timestamp}]   DEBUG: Calling communication_handler.send_departure_commands()")
        try:
            self.communicationHandler.send_departure_commands(train_id, train.route)
            print(f"[{timestamp}]   DEBUG: send_departure_commands() completed successfully")
            logger.info(f"Train {train_id} dispatched from yard")
        except Exception as e:
            print(f"[{timestamp}]   DEBUG: send_departure_commands() failed with error: {e}")
            logger.error(f"Error dispatching train {train_id} from yard: {e}")
    
    def process_scheduled_closures(self) -> List[str]:
        """
        Process any scheduled closures that are due
        System-wide coordination of scheduled maintenance closures
        
        Returns:
            List of action messages for what was processed
        """
        current_time = _get_simulation_time()
        actions = []
        
        logger.debug(f"Processing scheduled closures. Current time: {current_time}, Scheduled closures: {len(self.scheduledClosures)}")
        
        for scheduled in self.scheduledClosures[:]:  # Copy list to allow modifications
            if scheduled['status'] == 'scheduled' and scheduled['scheduled_time'] <= current_time:
                logger.info(f"Executing scheduled closure: Block {scheduled['block_number']} on {scheduled['line']} line")
                
                # Get the block object
                block = self.get_block_by_line_new(scheduled['line'], scheduled['block_number'])
                if block:
                    # Use block's own method to close
                    block.set_block_open(False)
                    scheduled['status'] = 'active'
                    
                    # Add to maintenance closures tracking
                    self.add_maintenance_closure(scheduled['line'], scheduled['block_number'])
                    
                    # Notify communication handler if needed
                    # Communication handler will be notified through wayside updates
                    
                    logger.info(f"Successfully executed scheduled closure of block {scheduled['block_number']} on {scheduled['line']} line")
                    actions.append(f"Executed scheduled closure of block {scheduled['block_number']} on {scheduled['line']} line")
                else:
                    # Mark as failed if block not found
                    scheduled['status'] = 'failed'
                    logger.error(f"Failed to execute closure of block {scheduled['block_number']}: Block not found")
                    actions.append(f"Failed to execute closure of block {scheduled['block_number']}: Block not found")
        
        return actions
    
    def process_scheduled_openings(self) -> List[str]:
        """
        Process any scheduled openings that are due
        System-wide coordination of scheduled maintenance openings
        
        Returns:
            List of action messages for what was processed
        """
        current_time = _get_simulation_time()
        actions = []
        
        logger.debug(f"Processing scheduled openings. Current time: {current_time}, Scheduled openings: {len(self.scheduledOpenings)}")
        
        for scheduled in self.scheduledOpenings[:]:  # Copy list to allow modifications
            if scheduled['scheduled_time'] <= current_time:
                logger.info(f"Executing scheduled opening: Block {scheduled['block_number']} on {scheduled['line']} line")
                
                # Get the block object
                block = self.get_block_by_line_new(scheduled['line'], scheduled['block_number'])
                if block:
                    # Use block's own method to open
                    block.set_block_open(True)
                    
                    # Remove from scheduled openings list
                    self.scheduledOpenings.remove(scheduled)
                    
                    # Mark related closure as completed
                    for closure in self.scheduledClosures:
                        if closure['id'] == scheduled.get('related_closure'):
                            closure['status'] = 'completed'
                    
                    # Remove from maintenance closures tracking
                    self.remove_maintenance_closure(scheduled['line'], scheduled['block_number'])
                    
                    # Notify communication handler if needed
                    # Communication handler will be notified through wayside updates
                    
                    logger.info(f"Successfully executed scheduled opening of block {scheduled['block_number']} on {scheduled['line']} line")
                    actions.append(f"Executed scheduled opening of block {scheduled['block_number']} on {scheduled['line']} line")
                else:
                    logger.error(f"Failed to execute opening of block {scheduled['block_number']}: Block not found")
                    actions.append(f"Failed to execute opening of block {scheduled['block_number']}: Block not found")
        
        return actions
    
    def schedule_block_closure(self, line: str, block_number: int, closure_time: datetime, duration: timedelta = None) -> dict:
        """
        Simple delegation to Block's schedule_closure method
        
        Args:
            line: Track line
            block_number: Block number to close
            closure_time: When to close the block
            duration: Optional duration after which to reopen
            
        Returns:
            Dict with success status and message
        """
        block = self.get_block_by_line_new(line, block_number)
        if not block:
            return {'success': False, 'message': f'Block {block_number} not found on {line} line'}
        
        # Delegate to block's method
        result = block.schedule_closure(closure_time)
        
        if result['success']:
            # Track in CTC system for process_scheduled_closures
            import uuid
            closure_id = str(uuid.uuid4())
            
            self.scheduledClosures.append({
                'id': closure_id,
                'line': line,
                'block_number': block_number,
                'scheduled_time': closure_time,
                'status': 'scheduled'
            })
            
            # Schedule automatic reopening if duration specified
            if duration:
                opening_time = closure_time + duration
                block.schedule_opening(opening_time)
                
                self.scheduledOpenings.append({
                    'line': line,
                    'block_number': block_number,
                    'scheduled_time': opening_time,
                    'related_closure': closure_id
                })
        
        return result
    
    def cancel_scheduled_closure(self, line: str, block_number: int) -> dict:
        """
        Cancel any scheduled closures for a specific block
        
        Args:
            line: Track line
            block_number: Block number
            
        Returns:
            Dict with success status and message
        """
        block = self.get_block_by_line_new(line, block_number)
        if not block:
            return {'success': False, 'message': f'Block {block_number} not found on {line} line'}
        
        # Cancel in block
        result = block.clear_scheduled_closure()
        
        # Also remove from CTC tracking
        cancelled_count = 0
        for scheduled in self.scheduledClosures[:]:
            if scheduled['line'] == line and scheduled['block_number'] == block_number and scheduled['status'] == 'scheduled':
                self.scheduledClosures.remove(scheduled)
                cancelled_count += 1
                
                # Remove related opening
                for opening in self.scheduledOpenings[:]:
                    if opening.get('related_closure') == scheduled['id']:
                        self.scheduledOpenings.remove(opening)
        
        if cancelled_count > 0:
            return {'success': True, 'message': f'Cancelled {cancelled_count} scheduled closures for block {block_number}'}
        
        return result
    
    def close_block_immediately(self, line: str, block_number: int) -> dict:
        """
        Simple delegation to Block's set_block_open method for immediate closure
        
        Args:
            line: Track line
            block_number: Block number to close
            
        Returns:
            Dict with success status and message
        """
        block = self.get_block_by_line_new(line, block_number)
        if not block:
            return {'success': False, 'message': f'Block {block_number} not found on {line} line'}
        
        # Check safety first
        safety_check = block.can_close_safely()
        if not safety_check['success']:
            return safety_check
        
        # Close the block
        block.set_block_open(False)
        self.add_maintenance_closure(line, block_number)
        
        # Notify other systems if needed
        # Communication handler will be notified through wayside updates
        
        return {'success': True, 'message': f'Block {block_number} closed'}
    
    def open_block_immediately(self, line: str, block_number: int) -> dict:
        """
        Simple delegation to Block's set_block_open method for immediate opening
        
        Args:
            line: Track line
            block_number: Block number to open
            
        Returns:
            Dict with success status and message
        """
        block = self.get_block_by_line_new(line, block_number)
        if not block:
            return {'success': False, 'message': f'Block {block_number} not found on {line} line'}
        
        # Open the block
        block.set_block_open(True)
        self.remove_maintenance_closure(line, block_number)
        
        # Notify other systems if needed
        # Communication handler will be notified through wayside updates
        
        return {'success': True, 'message': f'Block {block_number} opened'}
    
    def add_temporary_train(self, line, block, train_id=None):
        """Add temporary train for route calculation"""
        if not train_id:
            train_id = f"temp_{line}_{block}"
        
        # Create block object for the starting position
        block_obj = self.blocks.get(block) if block is not None else None
        if not block_obj:
            block_obj = type('Block', (), {'blockID': block, 'blockNumber': block})()
        
        temp_train = type('TempTrain', (), {
            'trainID': train_id,
            'line': line,
            'currentBlock': block_obj,
            'route': None,
            'routingStatus': 'Unrouted'
        })()
        
        self.trains[train_id] = temp_train
        return train_id
    
    def get_train(self, train_id):
        """Get train by ID"""
        return self.trains.get(train_id)

    def shutdown(self):
        """Shutdown CTC System"""
        self.system_running = False
        
        # Shutdown components
        if self.communicationHandler:
            self.communicationHandler.shutdown()
        
        logger.info("CTC System shutdown complete")    
    # PHASE 4: UI delegation methods for travel time and scheduling
    
    def calculate_travel_time_for_train(self, train_id: str, destination_block_number: int) -> float:
        """
        Calculate travel time for a train to reach destination
        
        Args:
            train_id: Train identifier
            destination_block_number: Block number destination
            
        Returns:
            Travel time in seconds, or 0 if route not possible
        """
        try:
            # Get train info
            if train_id in self.trains:
                train = self.trains[train_id]
                line = train.line
                start_block_number = getattr(train.currentBlock, 'blockNumber', 1)
            else:
                # For new trains, get line from train ID
                line = self.id_manager.get_line_from_train_id(train_id) if hasattr(self, 'id_manager') else 'Green'
                start_block_number = 1  # Yard position
            
            # Generate route
            if train_id in self.trains:
                route = self.calculate_route(train_id, destination_block_number, 'SAFEST_PATH')
            else:
                # Create temporary train for route calculation
                temp_train_id = self.add_temporary_train(line, start_block_number, train_id)
                route = self.calculate_route(temp_train_id, destination_block_number, 'SAFEST_PATH')
                if temp_train_id in self.trains:
                    self.remove_train(temp_train_id)
            
            if not route:
                return 0.0
            
            # Use Route's built-in travel time calculation
            if hasattr(route, 'calculate_travel_time'):
                return route.calculate_travel_time()
            elif hasattr(route, 'estimatedTravelTime'):
                return route.estimatedTravelTime
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Error calculating travel time for train {train_id}: {e}")
            return 0.0
    
    def calculate_departure_time_for_arrival(self, train_id: str, destination_block_number: int, arrival_time_str: str) -> str:
        """
        Calculate required departure time to reach destination at specified arrival time
        
        Args:
            train_id: Train identifier
            destination_block_number: Block number destination
            arrival_time_str: Desired arrival time as "HH:MM" string
            
        Returns:
            Departure time as "HH:MM" string, or empty string if not possible
        """
        try:
            if not arrival_time_str:
                return ""
            
            # Parse arrival time
            hour, minute = map(int, arrival_time_str.split(':'))
            
            # Get travel time
            travel_time_seconds = self.calculate_travel_time_for_train(train_id, destination_block_number)
            
            if travel_time_seconds <= 0:
                return ""  # Route not possible
            
            # Calculate departure time = arrival time - travel time
            from datetime import datetime, time, timedelta
            today = _get_simulation_time().date()
            arrival_datetime = datetime.combine(today, time(hour, minute))
            departure_datetime = arrival_datetime - timedelta(seconds=travel_time_seconds)
            
            # Handle day boundary crossing - if departure is before current time, assume next day arrival
            current_time = _get_simulation_time()
            if departure_datetime < current_time:
                arrival_datetime += timedelta(days=1)
                departure_datetime = arrival_datetime - timedelta(seconds=travel_time_seconds)
            
            return departure_datetime.strftime("%H:%M")
            
        except Exception as e:
            logger.error(f"Error calculating departure time for train {train_id}: {e}")
            return ""
    
    def calculate_eta_for_train(self, train_id: str) -> str:
        """
        Calculate estimated time of arrival for a train to its destination
        
        Args:
            train_id: Train identifier
            
        Returns:
            ETA as formatted string ("X min", "TBD", etc.)
        """
        try:
            # Input validation
            if not train_id or train_id not in self.trains:
                return "TBD"
                
            train = self.trains[train_id]
            
            # Check if train has ETA already set
            if hasattr(train, 'eta') and train.eta:
                return train.eta
                
            # Check if train has destination and current position
            if not (hasattr(train, 'destinationBlock') and hasattr(train, 'currentBlock')):
                return "TBD"
                
            if not train.destinationBlock or not train.currentBlock:
                return "TBD"
                
            # Get travel time using existing calculation
            travel_time_seconds = self.calculate_travel_time_for_train(train_id, train.destinationBlock)
            
            if travel_time_seconds <= 0:
                return "TBD"
                
            # Convert to human-readable format
            time_minutes = int(travel_time_seconds / 60)
            if time_minutes < 1:
                return "<1min"
            elif time_minutes < 60:
                return f"{time_minutes}min"
            else:
                hours = time_minutes // 60
                minutes = time_minutes % 60
                return f"{hours}h {minutes}min" if minutes > 0 else f"{hours}h"
                
        except Exception as e:
            logger.error(f"Error calculating ETA for train {train_id}: {e}")
            return "TBD"
    
    def can_close_block_safely(self, line: str, block_number: int, close_time: datetime = None) -> tuple:
        """
        Check if block can be closed safely at requested time
        
        Args:
            line: Track line name
            block_number: Block number to close
            close_time: Optional time to check (defaults to now)
            
        Returns:
            Tuple of (can_close: bool, reason: str)
        """
        try:
            block = self.get_block_by_line_new(line, block_number)
            if not block:
                return False, f"Block {block_number} not found on {line} line"
            
            # Use Block's built-in safety check
            if hasattr(block, 'can_close_safely'):
                result = block.can_close_safely(close_time)
                if isinstance(result, dict):
                    return result.get('success', False), result.get('message', '')
                else:
                    return result, ""
            else:
                # Fallback check for occupied blocks
                if hasattr(block, 'occupied') and block.occupied:
                    return False, "Block currently occupied by train"
                return True, ""
                
        except Exception as e:
            logger.error(f"Error checking block closure safety: {e}")
            return False, f"Error checking block safety: {str(e)}"

    # ========================================
    # UI DELEGATION METHODS
    # ========================================
    # These methods provide a clean API for the UI layer
    # All business logic is delegated to appropriate core classes
    
    def create_route_for_ui(self, start_block_id: int, end_block_id: int, 
                           start_line: str = None, end_line: str = None, 
                           arrival_time: datetime = None) -> dict:
        """
        Create route for UI with simplified parameters
        
        Args:
            start_block_id: Starting block number
            end_block_id: Destination block number
            start_line: Starting line (optional, will search if not provided)
            end_line: Destination line (optional, will search if not provided)
            arrival_time: Desired arrival time (optional)
            
        Returns:
            Dict with success status, route_id, and message
        """
        try:
            # Find start block
            if start_line:
                start_block = self.get_block_by_line_new(start_line, start_block_id)
            else:
                start_block = self.get_block_by_number(start_block_id)
            
            if not start_block:
                return {
                    'success': False,
                    'message': f'Start block {start_block_id} not found',
                    'route_id': None
                }
            
            # Find end block
            if end_line:
                end_block = self.get_block_by_line_new(end_line, end_block_id)
            else:
                end_block = self.get_block_by_number(end_block_id)
            
            if not end_block:
                return {
                    'success': False,
                    'message': f'End block {end_block_id} not found',
                    'route_id': None
                }
            
            # Generate route using existing method
            route = self.generate_route(start_block, end_block, arrival_time)
            
            if route:
                return {
                    'success': True,
                    'message': f'Route created successfully',
                    'route_id': route.routeID,
                    'route': route
                }
            else:
                return {
                    'success': False,
                    'message': 'No route possible between specified blocks',
                    'route_id': None
                }
                
        except Exception as e:
            logger.error(f"Error creating route for UI: {e}")
            return {
                'success': False,
                'message': f'Error creating route: {str(e)}',
                'route_id': None
            }
    
    def get_route_info_for_ui(self, route_id: str) -> dict:
        """
        Get route information formatted for UI display
        
        Args:
            route_id: Route identifier
            
        Returns:
            Dict with route information or error message
        """
        try:
            if route_id not in self.routes:
                return {
                    'success': False,
                    'message': f'Route {route_id} not found'
                }
            
            route = self.routes[route_id]
            
            # Calculate route information using RouteManager if available
            travel_time = 0
            if self.routeManager and hasattr(self.routeManager, 'calculate_precise_travel_time'):
                travel_time = self.routeManager.calculate_precise_travel_time(route)
            
            return {
                'success': True,
                'route_id': route_id,
                'start_block': route.startBlock.blockID if route.startBlock else None,
                'end_block': route.endBlock.blockID if route.endBlock else None,
                'block_count': len(route.blockSequence) if route.blockSequence else 0,
                'travel_time': travel_time,
                'scheduled_departure': getattr(route, 'scheduledDeparture', None),
                'scheduled_arrival': getattr(route, 'scheduledArrival', None),
                'block_sequence': [block.blockID for block in route.blockSequence] if route.blockSequence else []
            }
            
        except Exception as e:
            logger.error(f"Error getting route info for UI: {e}")
            return {
                'success': False,
                'message': f'Error retrieving route info: {str(e)}'
            }
    
    def cancel_route_for_ui(self, route_id: str) -> dict:
        """
        Cancel a route and clean up associated resources
        
        Args:
            route_id: Route identifier to cancel
            
        Returns:
            Dict with success status and message
        """
        try:
            if route_id not in self.routes:
                return {
                    'success': False,
                    'message': f'Route {route_id} not found'
                }
            
            # Remove route from system
            route = self.routes.pop(route_id)
            
            # Find any trains using this route and update them
            for train_id, train in self.trains.items():
                if hasattr(train, 'route') and train.route and getattr(train.route, 'routeID', None) == route_id:
                    train.route = None
                    logger.info(f"Removed route {route_id} from train {train_id}")
            
            logger.info(f"Route {route_id} cancelled successfully")
            return {
                'success': True,
                'message': f'Route {route_id} cancelled successfully'
            }
            
        except Exception as e:
            logger.error(f"Error cancelling route for UI: {e}")
            return {
                'success': False,
                'message': f'Error cancelling route: {str(e)}'
            }
    
    def close_block_for_ui(self, line: str, block_number: int, scheduled_time: datetime = None) -> dict:
        """
        Close block for UI with optional scheduling
        
        Args:
            line: Track line name
            block_number: Block number to close
            scheduled_time: Optional time to schedule closure (None for immediate)
            
        Returns:
            Dict with success status and message
        """
        try:
            if scheduled_time:
                # Schedule closure for later
                return self.schedule_block_closure(line, block_number, scheduled_time)
            else:
                # Close immediately
                return self.close_block_immediately(line, block_number)
                
        except Exception as e:
            logger.error(f"Error closing block for UI: {e}")
            return {
                'success': False,
                'message': f'Error closing block: {str(e)}'
            }
    
    def open_block_for_ui(self, line: str, block_number: int) -> dict:
        """
        Open block for UI (always immediate)
        
        Args:
            line: Track line name
            block_number: Block number to open
            
        Returns:
            Dict with success status and message
        """
        try:
            return self.open_block_immediately(line, block_number)
            
        except Exception as e:
            logger.error(f"Error opening block for UI: {e}")
            return {
                'success': False,
                'message': f'Error opening block: {str(e)}'
            }
    
    def get_block_status_for_ui(self, line: str, block_number: int) -> dict:
        """
        Get block status information formatted for UI
        
        Args:
            line: Track line name
            block_number: Block number
            
        Returns:
            Dict with block status information
        """
        try:
            block = self.get_block_by_line_new(line, block_number)
            if not block:
                return {
                    'success': False,
                    'message': f'Block {block_number} not found on {line} line'
                }
            
            # Get status using Block's infrastructure info method if available
            if hasattr(block, 'get_infrastructure_info'):
                infrastructure_info = block.get_infrastructure_info()
            else:
                infrastructure_info = {}
            
            # Build comprehensive status
            status = {
                'success': True,
                'block_number': block_number,
                'line': line,
                'is_open': getattr(block, 'is_open', True),
                'occupied': getattr(block, 'occupied', False),
                'occupying_train': getattr(block.occupyingTrain, 'trainID', None) if hasattr(block, 'occupyingTrain') and block.occupyingTrain else None,
                'has_station': getattr(block, 'station', None) is not None,
                'station_name': getattr(block.station, 'name', None) if hasattr(block, 'station') and block.station else None,
                'has_switch': getattr(block, 'switch', None) is not None,
                'has_crossing': getattr(block, 'crossing', None) is not None,
                'speed_limit': getattr(block, 'speedLimit', 0),
                'length': getattr(block, 'length', 0),
                'infrastructure_info': infrastructure_info,
                'maintenance_closed': self.is_block_closed(line, block_number)
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting block status for UI: {e}")
            return {
                'success': False,
                'message': f'Error getting block status: {str(e)}'
            }
    
    def get_train_info_for_ui(self, train_id: str) -> dict:
        """
        Get train information formatted for UI display
        
        Args:
            train_id: Train identifier
            
        Returns:
            Dict with train information or error message
        """
        try:
            if train_id not in self.trains:
                return {
                    'success': False,
                    'message': f'Train {train_id} not found'
                }
            
            train = self.trains[train_id]
            
            # Extract current block and line info for display
            current_block_obj = getattr(train, 'currentBlock', None)
            current_block = getattr(current_block_obj, 'blockID', getattr(current_block_obj, 'blockNumber', 0)) if current_block_obj else 0
            line = getattr(train, 'line', 'Unknown')
            destination_block = getattr(train, 'destination', 'N/A')
            
            # Determine routing status
            has_route = hasattr(train, 'route') and train.route is not None
            routing_status = getattr(train, 'routingStatus', "Routed" if has_route else "Unrouted")
            
            # Format departure time for display 
            departure_time = getattr(train, 'departureTime', getattr(train, 'departure_time', None))
            departure_str = departure_time.strftime('%H:%M') if departure_time else ''
            
            # Format arrival time for ETA
            arrival_time = getattr(train, 'arrivalTime', getattr(train, 'arrival_time', None))
            eta_str = arrival_time.strftime('%H:%M') if arrival_time else ''
            
            return {
                'success': True,
                'train_id': train_id,
                'line': line,
                'current_block': current_block,
                'destination': destination_block,
                'speed': str(self.trainSuggestedSpeeds.get(train_id, 0) if current_block != 0 else 0),
                'authority': getattr(train, 'authority', 0),
                'passengers': getattr(train, 'passengers', 0),
                'routing_status': routing_status,
                'route_id': getattr(train.route, 'routeID', 'N/A') if has_route else 'N/A',
                'departure_time': departure_str,
                'arrival_time': arrival_time,
                'eta': eta_str,
                'has_route': has_route
            }
            
        except Exception as e:
            logger.error(f"Error getting train info for UI: {e}")
            return {
                'success': False,
                'message': f'Error getting train info: {str(e)}'
            }
    
    def dispatch_train_for_ui(self, train_id: str, route_id: str = None, departure_time: datetime = None) -> dict:
        """
        Dispatch train for UI with simplified parameters
        
        Args:
            train_id: Train identifier
            route_id: Optional route to assign before dispatch
            departure_time: Optional departure time (None for immediate)
            
        Returns:
            Dict with success status and message
        """
        try:
            if train_id not in self.trains:
                return {
                    'success': False,
                    'message': f'Train {train_id} not found'
                }
            
            train = self.trains[train_id]
            
            # Assign route if provided
            if route_id:
                if route_id not in self.routes:
                    return {
                        'success': False,
                        'message': f'Route {route_id} not found'
                    }
                
                route = self.routes[route_id]
                self.activate_route(train_id, route)
            
            # Check if train has a route
            if not hasattr(train, 'route') or not train.route:
                return {
                    'success': False,
                    'message': f'Train {train_id} has no route assigned'
                }
            
            # Set departure time if provided
            if departure_time:
                train.route.scheduledDeparture = departure_time
                train.departureTime = departure_time
                train.departure_time = departure_time
            
            # Check if train is in yard (for automatic dispatch)
            current_block = getattr(train.currentBlock, 'blockID', getattr(train.currentBlock, 'blockNumber', 0)) if train.currentBlock else 0
            
            if current_block == 0:
                # Train in yard - use dispatch_train_from_yard
                self.dispatch_train_from_yard(train_id)
                return {
                    'success': True,
                    'message': f'Train {train_id} dispatched from yard'
                }
            else:
                # Train already on track - just send route commands
                if self.communicationHandler:
                    self.communicationHandler.send_train_commands_for_route(train_id, train.route)
                
                return {
                    'success': True,
                    'message': f'Train {train_id} route commands sent'
                }
                
        except Exception as e:
            logger.error(f"Error dispatching train for UI: {e}")
            return {
                'success': False,
                'message': f'Error dispatching train: {str(e)}'
            }
    
    def stop_train_for_ui(self, train_id: str, reason: str = "Manual stop") -> dict:
        """
        Stop train for UI
        
        Args:
            train_id: Train identifier
            reason: Reason for stopping
            
        Returns:
            Dict with success status and message
        """
        try:
            if train_id not in self.trains:
                return {
                    'success': False,
                    'message': f'Train {train_id} not found'
                }
            
            train = self.trains[train_id]
            
            # Send stop command through communication handler
            if self.communicationHandler:
                self.communicationHandler.stop_train(train)
            
            # Set speed to 0
            self.trainSuggestedSpeeds[train_id] = 0
            
            # Add to emergency stops if reason indicates emergency
            if "emergency" in reason.lower():
                self.emergency_stops.add(train_id)
                self.add_warning(
                    "emergency",
                    f"Emergency stop activated for Train {train_id}: {reason}",
                    severity="critical",
                    train_id=train_id
                )
            
            logger.info(f"Train {train_id} stopped: {reason}")
            return {
                'success': True,
                'message': f'Train {train_id} stopped'
            }
            
        except Exception as e:
            logger.error(f"Error stopping train for UI: {e}")
            return {
                'success': False,
                'message': f'Error stopping train: {str(e)}'
            }

    # ===== SYSTEM STATE OPERATIONS =====
    
    def get_system_status_for_ui(self) -> dict:
        """
        Get comprehensive system status for UI dashboard.
        Provides high-level overview of entire CTC system.
        
        Returns:
            dict: Complete system status including all subsystems
        """
        try:
            # Count operational blocks by line
            line_status = {}
            total_blocks = 0
            operational_blocks = 0
            
            for line_name, blocks in self.blocks.items():
                line_operational = 0
                line_total = len(blocks)
                
                for block in blocks:
                    if block.blockOpen and not block.blockOccupied:
                        line_operational += 1
                
                line_status[line_name] = {
                    'total_blocks': line_total,
                    'operational_blocks': line_operational,
                    'operational_percentage': round((line_operational / line_total * 100) if line_total > 0 else 0, 1),
                    'has_issues': line_operational < line_total
                }
                
                total_blocks += line_total
                operational_blocks += line_operational
            
            # Count active trains and routes
            active_trains = len([t for t in self.trains.values() if t.currentSpeed > 0])
            total_trains = len(self.trains)
            active_routes = len([r for r in self.routes.values() if hasattr(r, 'active') and r.active])
            total_routes = len(self.routes)
            
            # System health assessment
            system_health = "Excellent"
            if operational_blocks < total_blocks * 0.95:
                system_health = "Good"
            if operational_blocks < total_blocks * 0.85:
                system_health = "Fair"
            if operational_blocks < total_blocks * 0.7:
                system_health = "Poor"
            
            return {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'system_health': system_health,
                'overall_status': {
                    'total_blocks': total_blocks,
                    'operational_blocks': operational_blocks,
                    'operational_percentage': round((operational_blocks / total_blocks * 100) if total_blocks > 0 else 0, 1)
                },
                'line_status': line_status,
                'train_status': {
                    'total_trains': total_trains,
                    'active_trains': active_trains,
                    'idle_trains': total_trains - active_trains
                },
                'route_status': {
                    'total_routes': total_routes,
                    'active_routes': active_routes
                },
                'failure_manager_status': {
                    'active': hasattr(self, 'failureManager') and self.failureManager is not None,
                    'pending_failures': len(getattr(self.failureManager, 'pending_failures', [])) if hasattr(self, 'failureManager') else 0
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get system status: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    def get_all_active_routes_for_ui(self) -> dict:
        """
        Get all currently active routes formatted for UI display.
        Provides comprehensive route information for dispatcher monitoring.
        
        Returns:
            dict: All active routes with details
        """
        try:
            active_routes = []
            
            for route_id, route in self.routes.items():
                # Check if route is active (has assigned train or scheduled)
                is_active = False
                assigned_train = None
                
                # Check for assigned trains
                for train_id, train in self.trains.items():
                    if hasattr(train, 'currentRoute') and train.currentRoute == route:
                        is_active = True
                        assigned_train = train_id
                        break
                
                # Include scheduled routes
                if hasattr(route, 'scheduledDeparture') and route.scheduledDeparture:
                    if route.scheduledDeparture > datetime.now():
                        is_active = True
                
                if is_active:
                    # Get route line
                    route_line = None
                    if hasattr(route, 'startBlock') and route.startBlock:
                        for line_name, blocks in self.blocks.items():
                            if route.startBlock.blockID in [b.blockID for b in blocks]:
                                route_line = line_name
                                break
                    
                    route_info = {
                        'route_id': route_id,
                        'line': route_line,
                        'start_block': route.startBlock.blockID if hasattr(route, 'startBlock') and route.startBlock else None,
                        'end_block': route.endBlock.blockID if hasattr(route, 'endBlock') and route.endBlock else None,
                        'assigned_train': assigned_train,
                        'scheduled_departure': route.scheduledDeparture.isoformat() if hasattr(route, 'scheduledDeparture') and route.scheduledDeparture else None,
                        'scheduled_arrival': route.scheduledArrival.isoformat() if hasattr(route, 'scheduledArrival') and route.scheduledArrival else None,
                        'total_blocks': len(route.blockSequence) if hasattr(route, 'blockSequence') else 0,
                        'estimated_travel_time': getattr(route, 'precise_travel_time', None)
                    }
                    active_routes.append(route_info)
            
            return {
                'success': True,
                'active_routes': active_routes,
                'total_active': len(active_routes),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get active routes: {str(e)}',
                'active_routes': []
            }
    
    def get_maintenance_schedule_for_ui(self) -> dict:
        """
        Get maintenance schedule and closure information for UI.
        Provides dispatcher with upcoming and current maintenance activities.
        
        Returns:
            dict: Maintenance schedule and closure information
        """
        try:
            current_closures = []
            scheduled_closures = []
            
            # Check all blocks for maintenance status
            for line_name, blocks in self.blocks.items():
                for block in blocks:
                    # Current closures
                    if not block.blockOpen:
                        closure_info = {
                            'line': line_name,
                            'block_id': block.blockID,
                            'section': getattr(block, 'section', 'Unknown'),
                            'closure_reason': getattr(block, 'closure_reason', 'Maintenance'),
                            'closed_since': getattr(block, 'closure_time', datetime.now()).isoformat(),
                            'estimated_reopening': getattr(block, 'estimated_reopening', None)
                        }
                        
                        if closure_info['estimated_reopening']:
                            closure_info['estimated_reopening'] = closure_info['estimated_reopening'].isoformat()
                        
                        current_closures.append(closure_info)
                    
                    # Scheduled closures
                    if hasattr(block, 'scheduled_closure_time') and block.scheduled_closure_time:
                        if block.scheduled_closure_time > datetime.now():
                            scheduled_info = {
                                'line': line_name,
                                'block_id': block.blockID,
                                'section': getattr(block, 'section', 'Unknown'),
                                'scheduled_closure': block.scheduled_closure_time.isoformat(),
                                'scheduled_opening': getattr(block, 'scheduled_opening_time', None),
                                'closure_duration': None
                            }
                            
                            if scheduled_info['scheduled_opening']:
                                scheduled_info['scheduled_opening'] = scheduled_info['scheduled_opening'].isoformat()
                                duration = block.scheduled_opening_time - block.scheduled_closure_time
                                scheduled_info['closure_duration'] = str(duration)
                            
                            scheduled_closures.append(scheduled_info)
            
            return {
                'success': True,
                'current_closures': current_closures,
                'scheduled_closures': scheduled_closures,
                'total_current': len(current_closures),
                'total_scheduled': len(scheduled_closures),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get maintenance schedule: {str(e)}',
                'current_closures': [],
                'scheduled_closures': []
            }
    
    def get_system_warnings_for_ui(self) -> dict:
        """
        Get current system warnings and alerts for UI notification panel.
        Provides critical information requiring dispatcher attention.
        
        Returns:
            dict: System warnings categorized by severity
        """
        try:
            warnings = {
                'critical': [],
                'warning': [],
                'info': []
            }
            
            # Check for critical issues
            # 1. Trains stopped unexpectedly
            for train_id, train in self.trains.items():
                if hasattr(train, 'emergencyBrake') and train.emergencyBrake:
                    warnings['critical'].append({
                        'type': 'train_emergency',
                        'message': f'Train {train_id} has emergency brake activated',
                        'train_id': train_id,
                        'location': f'Block {train.currentBlock.blockID}',
                        'timestamp': datetime.now().isoformat()
                    })
                
                if train.currentSpeed == 0 and hasattr(train, 'targetSpeed') and train.targetSpeed > 0:
                    warnings['warning'].append({
                        'type': 'train_stopped',
                        'message': f'Train {train_id} is stopped but should be moving',
                        'train_id': train_id,
                        'location': f'Block {train.currentBlock.blockID}',
                        'timestamp': datetime.now().isoformat()
                    })
            
            # 2. Block issues
            closed_blocks = 0
            for line_name, blocks in self.blocks.items():
                for block in blocks:
                    if not block.blockOpen:
                        closed_blocks += 1
                        if not hasattr(block, 'planned_closure') or not block.planned_closure:
                            warnings['warning'].append({
                                'type': 'unexpected_closure',
                                'message': f'{line_name} Line Block {block.blockID} is unexpectedly closed',
                                'line': line_name,
                                'block_id': block.blockID,
                                'timestamp': datetime.now().isoformat()
                            })
            
            # 3. System capacity warnings
            total_blocks = sum(len(blocks) for blocks in self.blocks.values())
            if closed_blocks > total_blocks * 0.15:  # More than 15% closed
                warnings['critical'].append({
                    'type': 'system_capacity',
                    'message': f'High number of closed blocks: {closed_blocks}/{total_blocks} ({round(closed_blocks/total_blocks*100, 1)}%)',
                    'closed_blocks': closed_blocks,
                    'total_blocks': total_blocks,
                    'timestamp': datetime.now().isoformat()
                })
            
            # 4. Route conflicts
            active_routes = [r for r in self.routes.values() if hasattr(r, 'active') and r.active]
            if len(active_routes) > len(self.trains) * 1.5:  # More routes than reasonable
                warnings['warning'].append({
                    'type': 'route_overload',
                    'message': f'High number of active routes: {len(active_routes)} routes for {len(self.trains)} trains',
                    'active_routes': len(active_routes),
                    'total_trains': len(self.trains),
                    'timestamp': datetime.now().isoformat()
                })
            
            # 5. Communication issues (if failure manager exists)
            if hasattr(self, 'failureManager') and self.failureManager:
                pending_failures = getattr(self.failureManager, 'pending_failures', [])
                if len(pending_failures) > 0:
                    warnings['warning'].append({
                        'type': 'pending_failures',
                        'message': f'{len(pending_failures)} pending failure reports require attention',
                        'pending_count': len(pending_failures),
                        'timestamp': datetime.now().isoformat()
                    })
            
            # Count warnings by severity
            warning_counts = {
                'critical': len(warnings['critical']),
                'warning': len(warnings['warning']),
                'info': len(warnings['info']),
                'total': len(warnings['critical']) + len(warnings['warning']) + len(warnings['info'])
            }
            
            return {
                'success': True,
                'warnings': warnings,
                'warning_counts': warning_counts,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get system warnings: {str(e)}',
                'warnings': {'critical': [], 'warning': [], 'info': []},
                'warning_counts': {'critical': 0, 'warning': 0, 'info': 0, 'total': 0}
            }
    
    def get_throughput_metrics_for_ui(self) -> dict:
        """
        Get system throughput and performance metrics for UI dashboard.
        Provides operational efficiency data for management reporting.
        
        Returns:
            dict: Throughput and performance metrics
        """
        try:
            # Calculate current throughput
            active_trains = len([t for t in self.trains.values() if t.currentSpeed > 0])
            total_capacity = len(self.trains)
            
            # Calculate route efficiency
            active_routes = len([r for r in self.routes.values() if hasattr(r, 'active') and r.active])
            completed_routes_today = 0  # Would need historical data
            
            # Calculate block utilization
            total_blocks = sum(len(blocks) for blocks in self.blocks.values())
            occupied_blocks = sum(len([b for b in blocks if b.blockOccupied]) for blocks in self.blocks.values())
            closed_blocks = sum(len([b for b in blocks if not b.blockOpen]) for blocks in self.blocks.values())
            available_blocks = total_blocks - occupied_blocks - closed_blocks
            
            # Line-specific metrics
            line_metrics = {}
            for line_name, blocks in self.blocks.items():
                line_occupied = len([b for b in blocks if b.blockOccupied])
                line_closed = len([b for b in blocks if not b.blockOpen])
                line_total = len(blocks)
                line_available = line_total - line_occupied - line_closed
                
                line_metrics[line_name] = {
                    'total_blocks': line_total,
                    'occupied_blocks': line_occupied,
                    'closed_blocks': line_closed,
                    'available_blocks': line_available,
                    'utilization_percentage': round((line_occupied / line_total * 100) if line_total > 0 else 0, 1),
                    'availability_percentage': round((line_available / line_total * 100) if line_total > 0 else 0, 1)
                }
            
            # Performance indicators
            system_utilization = round((occupied_blocks / total_blocks * 100) if total_blocks > 0 else 0, 1)
            train_utilization = round((active_trains / total_capacity * 100) if total_capacity > 0 else 0, 1)
            
            # Efficiency rating
            efficiency_score = (train_utilization + system_utilization) / 2
            if efficiency_score >= 80:
                efficiency_rating = "Excellent"
            elif efficiency_score >= 60:
                efficiency_rating = "Good"
            elif efficiency_score >= 40:
                efficiency_rating = "Fair"
            else:
                efficiency_rating = "Poor"
            
            return {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'overall_metrics': {
                    'system_utilization': system_utilization,
                    'train_utilization': train_utilization,
                    'efficiency_score': round(efficiency_score, 1),
                    'efficiency_rating': efficiency_rating
                },
                'capacity_metrics': {
                    'total_blocks': total_blocks,
                    'occupied_blocks': occupied_blocks,
                    'closed_blocks': closed_blocks,
                    'available_blocks': available_blocks,
                    'total_trains': total_capacity,
                    'active_trains': active_trains,
                    'idle_trains': total_capacity - active_trains
                },
                'line_metrics': line_metrics,
                'route_metrics': {
                    'active_routes': active_routes,
                    'completed_today': completed_routes_today,
                    'total_routes': len(self.routes)
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get throughput metrics: {str(e)}',
                'overall_metrics': {},
                'capacity_metrics': {},
                'line_metrics': {}
            }