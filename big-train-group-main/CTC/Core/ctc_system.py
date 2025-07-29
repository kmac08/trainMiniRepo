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
from PyQt5.QtCore import QObject, pyqtSignal

# Import the new UML-compliant classes
from .communication_handler import CommunicationHandler
from .display_manager import DisplayManager
from .failure_manager import FailureManager
from .route_manager import RouteManager
from .block import Block
from .route import Route
from .train import Train

# Migrated from collision_detector.py
class ConflictType(Enum):
    """Types of conflicts that can be detected"""
    SAME_BLOCK = "same_block"
    HEAD_ON = "head_on"
    REAR_END = "rear_end"
    SWITCH_CONFLICT = "switch_conflict"
    AUTHORITY_VIOLATION = "authority_violation"
    MAINTENANCE_CONFLICT = "maintenance_conflict"
    SPEED_VIOLATION = "speed_violation"

class ConflictSeverity(Enum):
    """Severity levels for conflicts"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    WARNING = 5

@dataclass
class ConflictDetails:
    """Detailed information about a detected conflict"""
    conflict_id: str
    conflict_type: ConflictType
    severity: ConflictSeverity
    train_ids: List[str]
    location_line: str
    location_block: int
    estimated_time_to_collision: float
    estimated_collision_speed: float
    suggested_actions: List[str]
    detection_timestamp: float
    train_speeds: Dict[str, float]
    train_positions: Dict[str, int]
    distance_between_trains: float
    closing_speed: float
    
    def is_collision_imminent(self) -> bool:
        return self.estimated_time_to_collision < 10.0
        
    def get_priority_score(self) -> int:
        base_score = self.severity.value
        if self.estimated_time_to_collision < 5.0:
            base_score -= 2
        elif self.estimated_time_to_collision < 15.0:
            base_score -= 1
        max_speed = max(self.train_speeds.values()) if self.train_speeds else 0
        if max_speed > 60:
            base_score -= 1
        return max(1, base_score)

# Set up logging
logger = logging.getLogger(__name__)


class CTCSystem(QObject):
    """
    CTC System implementing UML interface
    Central coordination and control system
    Includes migrated functionality from state_manager.py and train_id_manager.py
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
        self.throughputMetrics = []    # List[int]
        self.blockMetrics = []         # List[int]
        
        # Additional attributes needed for implementation
        self.blocks = {}               # Dict[int, Block] - block_number -> Block object
        self.routes = {}               # Dict[str, Route] - route_id -> Route object
        self.trains = {}               # Dict[str, Train] - train_id -> Train object
        
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
        self.system_time = datetime.now()
        self.system_running = True
        self.main_thread = None
        
        # Collision detection attributes (from collision_detector)
        self.lookahead_time = 300.0  # seconds to look ahead
        self.minimum_separation = 100.0  # meters minimum between trains
        self.safety_buffer_time = 15.0  # seconds safety buffer
        self.active_conflicts: Dict[str, ConflictDetails] = {}
        self.conflict_history: List[ConflictDetails] = []
        self.conflict_counter = 0
        self.detections_performed = 0
        self.conflicts_detected = 0
        self.collisions_prevented = 0
        
        # Initialize components
        self._initialize_components()
        
        # Initialize blocks from track layout
        if self.trackLayout:
            self._initialize_blocks()
        
        # Create some basic blocks for testing if none exist
        if not self.blocks:
            self._create_basic_blocks()
        
        logger.info("CTC System initialized")
    
    # Train ID Management Methods (from train_id_manager)
    
    
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
        """Get train object by ID (thread-safe)"""
        with self._lock:
            return self.trains.get(train_id)
    
    def get_all_trains(self) -> Dict[str, Train]:
        """Get copy of all active trains (thread-safe)"""
        with self._lock:
            return self.trains.copy()
    
    def set_selected_train(self, train_id: str) -> None:
        """Set currently selected train and notify observers"""
        with self._lock:
            if train_id != self.selected_train:
                self.selected_train = train_id
                self.train_selected.emit(train_id if train_id else "")
    
    def get_selected_train(self) -> Optional[str]:
        """Get currently selected train ID"""
        with self._lock:
            return self.selected_train
    
    def set_selected_block(self, line: str, block: int) -> None:
        """Set currently selected block and notify observers"""
        with self._lock:
            new_selection = (line, block)
            if new_selection != self.selected_block:
                self.selected_block = new_selection
                self.block_selected.emit(line, block)
    
    def get_selected_block(self) -> Optional[Tuple[str, int]]:
        """Get currently selected block"""
        with self._lock:
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
        with self._lock:
            return {
                line: list(blocks) 
                for line, blocks in self.maintenance_closures.items()
            }
    
    def is_block_closed(self, line: str, block: int) -> bool:
        """Check if a block is closed for maintenance"""
        with self._lock:
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
        with self._lock:
            return self.warnings.copy()
    
    def clear_warnings(self) -> None:
        """Clear all warnings"""
        with self._lock:
            self.warnings.clear()
            self.warnings_updated.emit()
            self.state_changed.emit()
    
    def update_track_status(self, line: str, block: int, status: str) -> None:
        """Update track status for a specific block"""
        with self._lock:
            if line not in self.trackStatus:
                self.trackStatus[line] = {}
            self.trackStatus[line][block] = status
            self.state_changed.emit()
    
    def get_track_status(self, line: str, block: int) -> Optional[str]:
        """Get track status for a specific block"""
        with self._lock:
            return self.trackStatus.get(line, {}).get(block)
    
    def update_railway_crossing(self, line: str, block: int, status: str) -> None:
        """Update railway crossing status"""
        with self._lock:
            self.railwayCrossings[(line, block)] = status
            self.state_changed.emit()
    
    def get_railway_crossing_status(self, line: str, block: int) -> Optional[str]:
        """Get railway crossing status"""
        with self._lock:
            return self.railwayCrossings.get((line, block))
    
    def update_switch_position(self, switch_id: str, line: str, block: int, position: str) -> None:
        """Update switch position"""
        with self._lock:
            self.switch_positions[switch_id] = {
                'line': line,
                'block': block,
                'position': position
            }
            self.state_changed.emit()
    
    def get_switch_position(self, switch_id: str) -> Optional[Dict]:
        """Get switch position data"""
        with self._lock:
            return self.switch_positions.get(switch_id)
    
    def set_time_multiplier(self, multiplier: float) -> None:
        """Set system time acceleration multiplier"""
        with self._lock:
            self.system_time_multiplier = max(0.1, min(10.0, multiplier))
            self.state_changed.emit()
    
    def get_time_multiplier(self) -> float:
        """Get current time acceleration multiplier"""
        with self._lock:
            return self.system_time_multiplier
    
    def set_active_lines(self, lines: List[str]) -> None:
        """Set which lines are active in the system"""
        with self._lock:
            valid_lines = ["Blue", "Red", "Green"]
            self.active_lines = [line for line in lines if line in valid_lines]
            self.state_changed.emit()
    
    def get_active_lines(self) -> List[str]:
        """Get list of currently active lines"""
        with self._lock:
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
    
    def generate_route(self, startBlock: Block, endBlock: Block) -> Optional[Route]:
        """
        Generate optimal route between blocks
        
        Args:
            startBlock: Starting block
            endBlock: Destination block
            
        Returns:
            Generated Route object, or None if no route possible
        """
        try:
            # Create new route
            route = Route()
            route.create_route(startBlock, endBlock, datetime.now() + timedelta(hours=1))
            
            # Validate route
            if route.validate_route():
                # Store route
                self.routes[route.routeID] = route
                logger.info(f"Route generated: {route.routeID}")
                return route
            else:
                logger.warning(f"Generated route failed validation")
                return None
                
        except Exception as e:
            logger.error(f"Error generating route: {e}")
            return None
    
    def update_throughput(self, tickets: int) -> str:
        """
        Update throughput metrics (implements calculateThroughput sequence)
        
        Args:
            tickets: Number of tickets to add to throughput
            
        Returns:
            Confirmation message
        """
        try:
            # Add to metrics with timestamp
            metric_entry = {
                'tickets': tickets,
                'timestamp': datetime.now(),
                'cumulative': sum(self.throughputMetrics) + tickets
            }
            
            self.throughputMetrics.append(tickets)
            
            # Keep only last hour of metrics
            cutoff_time = datetime.now() - timedelta(hours=1)
            self.throughputMetrics = [
                entry for entry in self.throughputMetrics 
                if isinstance(entry, int) or entry.get('timestamp', datetime.min) >= cutoff_time
            ]
            
            # Update display (step 3 of sequence)
            if self.displayManager:
                self.displayManager.update_throughput(tickets)
            
            logger.debug(f"Throughput updated: +{tickets} tickets")
            return "confirm"  # Step 5 of sequence
            
        except Exception as e:
            logger.error(f"Error updating throughput: {e}")
            return f"error: {str(e)}"
    
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
            if not route.validate_route():
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
    
    def validate_arrival(self, time: datetime) -> bool:
        """
        Validate arrival time feasibility
        
        Args:
            time: Proposed arrival time
            
        Returns:
            True if arrival time is feasible
        """
        # Check if time is in the future
        if time <= datetime.now():
            return False
        
        # Check if time is within reasonable scheduling window (e.g., next 24 hours)
        max_future = datetime.now() + timedelta(hours=24)
        if time > max_future:
            return False
        
        # Additional validation could check capacity constraints
        return True
    
    def confirm_closure(self) -> None:
        """Confirm block closure (part of closeBlock sequence)"""
        # This would implement the closure confirmation process
        # For now, just log the action
        logger.info("Block closure confirmed")
    
    def execute_close_block_sequence(self, line: str, block_number: int, closure_time: datetime, 
                                   dispatcher_confirms: bool = False) -> Dict[str, Any]:
        """
        Execute the closeBlock sequence diagram workflow
        
        Args:
            line: Line containing the block
            block_number: Block to close
            closure_time: When to close the block
            dispatcher_confirms: Whether dispatcher confirms the closure
            
        Returns:
            Dict with status, message, and details
        """
        try:
            logger.info(f"Starting closeBlock sequence: Block {block_number} on {line} at {closure_time}")
            
            # Get block
            block = self.get_block_by_line(line, block_number)
            if not block:
                return {
                    'status': 'error',
                    'message': f'Block {block_number} not found on {line} line',
                    'closure_possible': False
                }
            
            # Validate closure
            is_valid = self.validate_closure(block, closure_time)
            
            if not is_valid:
                return {
                    'status': 'invalid',
                    'message': f'Block {block_number} cannot be closed at {closure_time}',
                    'closure_possible': False,
                    'reason': 'Block occupied or scheduled conflicts exist'
                }
            else:
                # Closure is valid, show details
                closure_details = {
                    'block_number': block_number,
                    'line': line,
                    'closure_time': closure_time,
                    'current_status': 'operational' if block.block_operational() else 'non-operational',
                    'occupied': block.occupied,
                    'scheduled_occupations': block.scheduledOccupations
                }
                
                if dispatcher_confirms:
                    # Execute closure
                    if self.failureManager:
                        result = self.failureManager.schedule_block_closure(
                            line, block_number, closure_time
                        )
                        if result['success']:
                            # Notify display manager
                            if self.displayManager:
                                self.displayManager.display_closure(block_number, closure_time)
                            
                            return {
                                'status': 'success',
                                'message': f'Block {block_number} scheduled for closure',
                                'closure_details': closure_details,
                                'closure_id': result.get('closure_id')
                            }
                    
                return {
                    'status': 'ready',
                    'message': 'Closure validated - awaiting confirmation',
                    'closure_possible': True,
                    'closure_details': closure_details
                }
                
        except Exception as e:
            logger.error(f"Error in closeBlock sequence: {e}")
            return {
                'status': 'error',
                'message': f'Error: {str(e)}',
                'closure_possible': False
            }
    
    # Additional methods needed for implementation
    
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
        
        # Check for failures and conflicts
        self.check_system_state()
        
        # Process scheduled closures
        if self.failureManager:
            closure_actions = self.failureManager.process_scheduled_closures()
            opening_actions = self.failureManager.process_scheduled_openings()
            if closure_actions or opening_actions:
                logger.debug(f"Processed {len(closure_actions)} closures, {len(opening_actions)} openings")
        
        # Commands are now sent only on events (routing, rerouting, block occupation updates)
        # No continuous command sending
        
        # Update metrics
        self._update_metrics()
    
    def update_train_commands(self) -> None:
        """
        Legacy method - commands are now sent via events
        Use dispatch_train_from_yard() or activate_route() instead
        """
        logger.warning("update_train_commands() is deprecated - use event-driven commands instead")
    
    def check_system_state(self) -> None:
        """Check for failures and emergencies (includes collision detection)"""
        if self.failureManager:
            self.failureManager.check_for_failures()
        
        # Perform collision detection
        conflicts = self.detect_conflicts()
        if conflicts:
            logger.warning(f"Detected {len(conflicts)} conflicts")
            # Process critical conflicts
            for conflict in conflicts:
                if conflict.severity == ConflictSeverity.CRITICAL:
                    self._handle_critical_conflict(conflict)
    
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
                        pass
            
            # Get the Block object for the current block
            block_obj = self.blocks.get(block)
            if not block_obj:
                # Create a simple block object if not found
                block_obj = type('Block', (), {'blockID': block, 'blockNumber': block})()
            
            # Create mock train object following TBTG naming conventions
            train = type('Train', (), {
                'trainID': train_id,           # TBTG: camelCase for attributes
                'line': line,
                'currentBlock': block_obj,     # Store as Block object
                'route': None,
                'speed': 0,                    # Keep for compatibility
                'speedKmh': 0,                 # TBTG: camelCase for speed in km/h
                'authority': 1,
                'passengers': 0,
                'routingStatus': 'Unrouted',   # TBTG: camelCase
                'departureTime': None,         # TBTG: camelCase
                'arrivalTime': None           # TBTG: camelCase
            })()
            
            self.trains[train_id] = train
            self.trainAuthorities[train_id] = 1
            self.trainSuggestedSpeeds[train_id] = 0
            self.active_train_ids.add(train_id)
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
        
        Args:
            occupied_blocks: List of block occupation states
        """
        # Update block occupation states
        # Note: This would need proper mapping from wayside controller to blocks
        logger.debug(f"Processing {len(occupied_blocks)} block occupancy updates")
    
    def process_switch_positions(self, switch_positions: List[bool]) -> None:
        """
        Process switch positions update from wayside
        
        Args:
            switch_positions: List of switch positions
        """
        # Update switch positions in blocks
        logger.debug(f"Processing {len(switch_positions)} switch position updates")
    
    def process_railway_crossings(self, railway_crossings: List[bool]) -> None:
        """
        Process railway crossings update from wayside
        
        Args:
            railway_crossings: List of crossing states
        """
        # Update crossing states in blocks
        logger.debug(f"Processing {len(railway_crossings)} crossing state updates")
    
    def provide_wayside_controller(self, waysideControllerObject, blocksCovered: List[int]) -> None:
        """
        Register wayside controller with CTC system
        Called by wayside controllers to establish communication
        
        Args:
            waysideControllerObject: Wayside controller instance with command_train, command_switch, set_occupied methods
            blocksCovered: List of block numbers this controller manages
        """
        if self.communicationHandler:
            self.communicationHandler.provide_wayside_controller(waysideControllerObject, blocksCovered)
            logger.info(f"Wayside controller registered for blocks {blocksCovered[0]}-{blocksCovered[-1] if len(blocksCovered) > 1 else blocksCovered[0]}")
        else:
            logger.error("Cannot register wayside controller: Communication handler not initialized")
    
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
            self.failureManager.ctc_system = self
            self.failureManager.communication_handler = self.communicationHandler
            self.failureManager.display_manager = self.displayManager
            self.routeManager.ctc_system = self
            
            logger.info("CTC System components initialized")
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
    
    def _initialize_blocks(self):
        """Initialize blocks from track layout"""
        if not self.trackLayout:
            return
        
        try:
            # Get all blocks from track reader for each line
            lines = ['Blue', 'Red', 'Green']  # Could get from track reader
            
            for line in lines:
                try:
                    # Get blocks for this line
                    # This would use the actual track reader API
                    line_blocks = self._get_blocks_for_line(line)
                    
                    for block_data in line_blocks:
                        block = Block(block_data)
                        self.blocks[block.blockID] = block
                        
                except Exception as e:
                    logger.warning(f"Could not load blocks for {line} line: {e}")
            
            logger.info(f"Initialized {len(self.blocks)} blocks")
            
        except Exception as e:
            logger.error(f"Error initializing blocks: {e}")
    
    def _get_blocks_for_line(self, line: str) -> List:
        """Get block data for specific line from track reader"""
        if self.trackLayout and hasattr(self.trackLayout, 'lines'):
            return self.trackLayout.lines.get(line, [])
        return []
    
    def _create_basic_blocks(self):
        """Create basic blocks for testing when track layout isn't available"""
        from .block import Block
        
        try:
            # Create basic block data for each line
            lines = {'Blue': range(1, 16), 'Red': range(1, 25), 'Green': range(1, 31)}
            
            for line, block_range in lines.items():
                for block_num in block_range:
                    # Create basic block data object
                    block_data = type('BlockData', (), {
                        'block_number': block_num,
                        'length_m': 100,
                        'grade_percent': 0.0,
                        'speed_limit_kmh': 50,
                        'has_switch': block_num % 5 == 0,  # Every 5th block has a switch
                        'has_crossing': False,
                        'has_station': block_num in [5, 10, 15],  # Stations at specific blocks
                        'line': line,
                        'section': 'A' if block_num <= 15 else 'B',
                        'elevation_m': 100,
                        'direction': 'BIDIRECTIONAL',
                        'is_underground': False,
                        'station': type('Station', (), {'name': f'{line} Station {block_num}'})() if block_num in [5, 10, 15] else None,
                        'switch': None
                    })()
                    
                    # Create Block object
                    block = Block(block_data)
                    self.blocks[block_num] = block
            
            logger.info(f"Created {len(self.blocks)} basic blocks for testing")
            
        except Exception as e:
            logger.warning(f"Could not create basic blocks: {e}")
            # Create minimal blocks
            for i in range(1, 51):
                self.blocks[i] = type('MinimalBlock', (), {
                    'blockID': i,
                    'block_number': i,  # For UI compatibility
                    'block_operational': lambda: True,
                    'occupied': False,
                    'line': 'Blue' if i <= 15 else 'Red' if i <= 35 else 'Green'
                })()
    
    def _update_trains(self):
        """Update all trains in system"""
        for train in self.trains.values():
            # Update train position, speed, etc.
            # This would interface with train objects
            pass
    
    def _update_routes(self):
        """Update all active routes"""
        for route in self.routes.values():
            if route.isActive:
                # Update route conditions
                route.update_for_conditions({})
    
    def _update_train_commands(self):
        """Update train commands based on current state"""
        if self.communicationHandler:
            self.communicationHandler.send_train_info()
    
    def _update_metrics(self):
        """Update system metrics"""
        # Update block metrics
        occupied_count = sum(1 for block in self.blocks.values() if block.occupied)
        self.blockMetrics.append(occupied_count)
        
        # Keep only recent metrics
        if len(self.blockMetrics) > 3600:  # Keep 1 hour of data
            self.blockMetrics = self.blockMetrics[-3600:]
    
    def _route_uses_block_at_time(self, route: Route, block_id: int, time: datetime) -> bool:
        """Check if route uses specific block at given time"""
        # This would check route timing and block sequence
        # Simplified implementation
        if hasattr(route, 'blockSequence'):
            return any(block.blockID == block_id for block in route.blockSequence)
        return False
    
    def _get_train_id(self, train) -> str:
        """Extract train ID from train object"""
        if hasattr(train, 'trainID'):
            return str(train.trainID)
        elif hasattr(train, 'id'):
            return str(train.id)
        else:
            return f"train_{id(train)}"
    
    def get_train_info_for_display(self):
        """Get train information formatted for display"""
        train_data = []
        for train_id, train in self.trains.items():
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
                'speed': str(getattr(train, 'speedKmh', getattr(train, 'speed', 0))),
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
    
    def detect_conflicts(self) -> List[ConflictDetails]:
        """Comprehensive conflict detection (from collision_detector)"""
        self.detections_performed += 1
        all_conflicts = []
        
        # Clear expired conflicts
        self._cleanup_expired_conflicts()
        
        # Get all active trains
        trains = list(self.trains.values())
        
        # Check for same-block conflicts
        same_block_conflicts = self._detect_same_block_conflicts(trains)
        all_conflicts.extend(same_block_conflicts)
        
        # Check for rear-end conflicts
        rear_end_conflicts = self._detect_rear_end_conflicts(trains)
        all_conflicts.extend(rear_end_conflicts)
        
        # Check for authority violations
        authority_conflicts = self._detect_authority_violations(trains)
        all_conflicts.extend(authority_conflicts)
        
        # Check for maintenance conflicts
        maintenance_conflicts = self._detect_maintenance_conflicts(trains)
        all_conflicts.extend(maintenance_conflicts)
        
        # Check for speed violations
        speed_conflicts = self._detect_speed_violations(trains)
        all_conflicts.extend(speed_conflicts)
        
        # Update active conflicts
        for conflict in all_conflicts:
            self.active_conflicts[conflict.conflict_id] = conflict
            
        # Update statistics
        self.conflicts_detected += len(all_conflicts)
        
        # Sort by priority (most critical first)
        all_conflicts.sort(key=lambda c: c.get_priority_score())
        
        return all_conflicts
    
    def _detect_same_block_conflicts(self, trains: List[Train]) -> List[ConflictDetails]:
        """Detect trains in the same block"""
        conflicts = []
        block_occupancy = {}
        
        for train in trains:
            if hasattr(train, 'currentBlock'):
                block = train.currentBlock
                block_id = block.blockID if hasattr(block, 'blockID') else block
                line = train.line
                key = (line, block_id)
                
                if key not in block_occupancy:
                    block_occupancy[key] = []
                block_occupancy[key].append(train)
        
        for (line, block_id), block_trains in block_occupancy.items():
            # Skip yard block (block 1)
            if block_id == 1:
                continue
                
            if len(block_trains) > 1:
                train_ids = [t.trainID for t in block_trains]
                train_speeds = {t.trainID: getattr(t, 'current_speed', 0) for t in block_trains}
                max_speed = max(train_speeds.values())
                
                conflict = ConflictDetails(
                    conflict_id=f"same_block_{line}_{block_id}_{int(time.time())}",
                    conflict_type=ConflictType.SAME_BLOCK,
                    severity=ConflictSeverity.CRITICAL,
                    train_ids=train_ids,
                    location_line=line,
                    location_block=block_id,
                    estimated_time_to_collision=0.0,
                    estimated_collision_speed=max_speed,
                    suggested_actions=[
                        "EMERGENCY STOP all trains in block",
                        f"Immediately halt Train {train_ids[0]}",
                        "Investigate block occupancy"
                    ],
                    detection_timestamp=time.time(),
                    train_speeds=train_speeds,
                    train_positions={t.trainID: block_id for t in block_trains},
                    distance_between_trains=0.0,
                    closing_speed=max_speed
                )
                conflicts.append(conflict)
                
        return conflicts
    
    def _detect_rear_end_conflicts(self, trains: List[Train]) -> List[ConflictDetails]:
        """Detect faster trains catching up to slower ones"""
        conflicts = []
        
        # Group trains by line
        line_trains = {}
        for train in trains:
            if train.line not in line_trains:
                line_trains[train.line] = []
            line_trains[train.line].append(train)
            
        # Check each line
        for line, line_train_list in line_trains.items():
            if len(line_train_list) < 2:
                continue
                
            # Sort by block number
            sorted_trains = sorted(line_train_list, 
                key=lambda t: t.currentBlock.blockID if hasattr(t.currentBlock, 'blockID') else t.currentBlock)
            
            # Check adjacent trains
            for i in range(len(sorted_trains) - 1):
                following = sorted_trains[i]
                leading = sorted_trains[i + 1]
                
                # Get speeds
                follow_speed = getattr(following, 'current_speed', 0)
                lead_speed = getattr(leading, 'current_speed', 0)
                speed_diff = follow_speed - lead_speed
                
                if speed_diff <= 0:
                    continue
                    
                # Calculate distance
                follow_block = following.currentBlock.blockID if hasattr(following.currentBlock, 'blockID') else following.currentBlock
                lead_block = leading.currentBlock.blockID if hasattr(leading.currentBlock, 'blockID') else leading.currentBlock
                block_distance = lead_block - follow_block
                
                if block_distance <= 0 or block_distance > 5:
                    continue
                    
                estimated_distance = block_distance * 100.0
                speed_diff_ms = speed_diff * 1000 / 3600
                time_to_collision = estimated_distance / speed_diff_ms if speed_diff_ms > 0 else float('inf')
                
                if time_to_collision > self.lookahead_time:
                    continue
                    
                # Determine severity
                if time_to_collision < 15:
                    severity = ConflictSeverity.CRITICAL
                elif time_to_collision < 45:
                    severity = ConflictSeverity.HIGH
                elif time_to_collision < 90:
                    severity = ConflictSeverity.MEDIUM
                else:
                    severity = ConflictSeverity.LOW
                    
                conflict = ConflictDetails(
                    conflict_id=f"rear_end_{following.trainID}_{leading.trainID}_{int(time.time())}",
                    conflict_type=ConflictType.REAR_END,
                    severity=severity,
                    train_ids=[following.trainID, leading.trainID],
                    location_line=line,
                    location_block=follow_block,
                    estimated_time_to_collision=time_to_collision,
                    estimated_collision_speed=follow_speed,
                    suggested_actions=[
                        f"Reduce speed for Train {following.trainID}" if severity != ConflictSeverity.CRITICAL else f"EMERGENCY STOP Train {following.trainID}",
                        f"Maintain speed for Train {leading.trainID}",
                        "Monitor separation distance"
                    ],
                    detection_timestamp=time.time(),
                    train_speeds={following.trainID: follow_speed, leading.trainID: lead_speed},
                    train_positions={following.trainID: follow_block, leading.trainID: lead_block},
                    distance_between_trains=estimated_distance,
                    closing_speed=speed_diff
                )
                conflicts.append(conflict)
                
        return conflicts
    
    def _detect_authority_violations(self, trains: List[Train]) -> List[ConflictDetails]:
        """Detect trains exceeding movement authority"""
        conflicts = []
        
        for train in trains:
            authority = self.trainAuthorities.get(train.trainID, 0)
            speed = getattr(train, 'current_speed', 0)
            
            if authority == 0 and speed > 0:
                block = train.currentBlock
                block_id = block.blockID if hasattr(block, 'blockID') else block
                
                conflict = ConflictDetails(
                    conflict_id=f"authority_{train.trainID}_{int(time.time())}",
                    conflict_type=ConflictType.AUTHORITY_VIOLATION,
                    severity=ConflictSeverity.HIGH,
                    train_ids=[train.trainID],
                    location_line=train.line,
                    location_block=block_id,
                    estimated_time_to_collision=float('inf'),
                    estimated_collision_speed=speed,
                    suggested_actions=[
                        f"STOP Train {train.trainID} immediately",
                        "Verify movement authority",
                        "Check CTC-Wayside communication"
                    ],
                    detection_timestamp=time.time(),
                    train_speeds={train.trainID: speed},
                    train_positions={train.trainID: block_id},
                    distance_between_trains=0.0,
                    closing_speed=0.0
                )
                conflicts.append(conflict)
                
        return conflicts
    
    def _detect_maintenance_conflicts(self, trains: List[Train]) -> List[ConflictDetails]:
        """Detect trains in maintenance areas"""
        conflicts = []
        
        for train in trains:
            block = train.currentBlock
            block_id = block.blockID if hasattr(block, 'blockID') else block
            
            if self.is_block_closed(train.line, block_id):
                speed = getattr(train, 'current_speed', 0)
                
                conflict = ConflictDetails(
                    conflict_id=f"maintenance_{train.trainID}_{int(time.time())}",
                    conflict_type=ConflictType.MAINTENANCE_CONFLICT,
                    severity=ConflictSeverity.HIGH,
                    train_ids=[train.trainID],
                    location_line=train.line,
                    location_block=block_id,
                    estimated_time_to_collision=float('inf'),
                    estimated_collision_speed=speed,
                    suggested_actions=[
                        f"STOP Train {train.trainID} immediately",
                        "Remove train from maintenance area",
                        "Coordinate with maintenance crew"
                    ],
                    detection_timestamp=time.time(),
                    train_speeds={train.trainID: speed},
                    train_positions={train.trainID: block_id},
                    distance_between_trains=0.0,
                    closing_speed=0.0
                )
                conflicts.append(conflict)
                
        return conflicts
    
    def _detect_speed_violations(self, trains: List[Train]) -> List[ConflictDetails]:
        """Detect trains exceeding safe speeds"""
        conflicts = []
        
        for train in trains:
            block = train.currentBlock
            if hasattr(block, 'speedLimit'):
                speed_limit = block.speedLimit
                speed = getattr(train, 'current_speed', 0)
                
                if speed > speed_limit * 1.1:  # 10% tolerance
                    block_id = block.blockID if hasattr(block, 'blockID') else block
                    severity = ConflictSeverity.HIGH if speed > speed_limit * 1.3 else ConflictSeverity.MEDIUM
                    
                    conflict = ConflictDetails(
                        conflict_id=f"speed_{train.trainID}_{int(time.time())}",
                        conflict_type=ConflictType.SPEED_VIOLATION,
                        severity=severity,
                        train_ids=[train.trainID],
                        location_line=train.line,
                        location_block=block_id,
                        estimated_time_to_collision=float('inf'),
                        estimated_collision_speed=speed,
                        suggested_actions=[
                            f"Reduce speed for Train {train.trainID}",
                            f"Enforce speed limit of {speed_limit} km/h",
                            "Monitor train compliance"
                        ],
                        detection_timestamp=time.time(),
                        train_speeds={train.trainID: speed},
                        train_positions={train.trainID: block_id},
                        distance_between_trains=0.0,
                        closing_speed=0.0
                    )
                    conflicts.append(conflict)
                    
        return conflicts
    
    def _cleanup_expired_conflicts(self) -> None:
        """Remove old conflicts that are no longer relevant"""
        current_time = time.time()
        expired_ids = []
        
        for conflict_id, conflict in self.active_conflicts.items():
            # Remove conflicts older than 5 minutes
            if current_time - conflict.detection_timestamp > 300:
                expired_ids.append(conflict_id)
                self.conflict_history.append(conflict)
                
        for conflict_id in expired_ids:
            del self.active_conflicts[conflict_id]
            
        # Limit history size
        if len(self.conflict_history) > 100:
            self.conflict_history = self.conflict_history[-100:]
    
    def _handle_critical_conflict(self, conflict: ConflictDetails) -> None:
        """Handle critical conflicts requiring immediate action"""
        logger.critical(f"Critical conflict detected: {conflict.conflict_type.value}")
        
        # Send emergency stop commands
        for train_id in conflict.train_ids:
            if train_id in self.trains:
                train = self.trains[train_id]
                if self.communicationHandler:
                    self.communicationHandler.stop_train(train)
                    
        # Add warning
        self.add_warning(
            "collision",
            f"Critical {conflict.conflict_type.value} conflict: {', '.join(conflict.train_ids)}",
            severity="critical",
            conflict=conflict
        )
        
        self.collisions_prevented += 1
    
    def resolve_conflict(self, conflict_id: str, resolution: str = "") -> bool:
        """Resolve a specific conflict (from collision_detector)"""
        if conflict_id in self.active_conflicts:
            conflict = self.active_conflicts[conflict_id]
            # Move to history
            self.conflict_history.append(conflict)
            del self.active_conflicts[conflict_id]
            self.collisions_prevented += 1
            logger.info(f"Conflict {conflict_id} resolved: {resolution}")
            return True
        return False
    
    def get_critical_conflicts(self) -> List[ConflictDetails]:
        """Get only critical conflicts requiring immediate attention"""
        return [
            conflict for conflict in self.active_conflicts.values()
            if conflict.severity == ConflictSeverity.CRITICAL
        ]
    
    def get_conflict_statistics(self) -> Dict:
        """Get conflict detection statistics"""
        severity_counts = {severity.name: 0 for severity in ConflictSeverity}
        type_counts = {conflict_type.name: 0 for conflict_type in ConflictType}
        
        for conflict in self.active_conflicts.values():
            severity_counts[conflict.severity.name] += 1
            type_counts[conflict.conflict_type.name] += 1
            
        return {
            "total_detections": self.detections_performed,
            "total_conflicts_detected": self.conflicts_detected,
            "active_conflicts": len(self.active_conflicts),
            "critical_conflicts": len(self.get_critical_conflicts()),
            "collisions_prevented": self.collisions_prevented,
            "severity_breakdown": severity_counts,
            "type_breakdown": type_counts
        }
    
    def calculate_route(self, train_id, destination_block, route_type=None, scheduled_arrival=None):
        """Calculate route for train"""
        if train_id not in self.trains:
            return None
        
        train = self.trains[train_id]
        current_block_obj = getattr(train, 'currentBlock', None)
        start_block = getattr(current_block_obj, 'blockID', getattr(current_block_obj, 'blockNumber', 1)) if current_block_obj else 1
        
        # Try to get existing blocks or create simple mock blocks
        start_block_obj = self.blocks.get(start_block)
        end_block_obj = self.blocks.get(destination_block)
        
        # Create simple mock blocks if not found
        if not start_block_obj:
            start_block_obj = type('MockBlock', (), {
                'blockID': start_block,
                'block_operational': lambda: True,
                'length': 100,
                'speedLimit': 50
            })()
            
        if not end_block_obj:
            end_block_obj = type('MockBlock', (), {
                'blockID': destination_block,
                'block_operational': lambda: True,
                'length': 100,
                'speedLimit': 50
            })()
        
        # For now, create a simple mock route for UI compatibility
        from datetime import datetime, timedelta
        arrival_time = scheduled_arrival if scheduled_arrival else datetime.now() + timedelta(hours=1)
        
        # Calculate simple travel time based on distance
        distance = abs(destination_block - start_block) * 100  # 100m per block
        travel_time = distance / 20 * 3.6  # 20 m/s average speed, convert to seconds
        
        # Calculate departure time based on arrival time and travel time
        departure_time = arrival_time - timedelta(seconds=travel_time)
        
        # Create mock route object
        route = type('MockRoute', (), {
            'routeID': f"route_{start_block}_{destination_block}_{int(datetime.now().timestamp())}",
            'startBlock': start_block_obj,
            'endBlock': end_block_obj,
            'route_type': route_type,
            'total_time': travel_time,
            'estimatedTravelTime': travel_time,
            'scheduled_arrival': arrival_time,
            'scheduledArrival': arrival_time,
            'scheduledDeparture': departure_time,
            'blockSequence': [start_block_obj, end_block_obj],
            'trainID': train_id,
            'isActive': False,
            'validate_route': lambda: True,
            'totalDistance': distance,
            'actualArrival': None
        })()
        
        # Add methods that reference the route object
        def activate_route_func(tid):
            route.isActive = True
            route.trainID = tid
            
        def deactivate_route_func():
            route.isActive = False
            
        route.activate_route = activate_route_func
        route.deactivate_route = deactivate_route_func
        
        logger.info(f"Generated mock route {route.routeID} for train {train_id}")
        return route
    
    def activate_route(self, train_id, route):
        """Activate route for train and send commands to wayside"""
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
            
            # Update routing status (TBTG camelCase)
            train.routingStatus = "Routed"
            train.routing_status = "Routed"  # Keep for compatibility
            
            # Activate the route
            if hasattr(route, 'activate_route'):
                route.activate_route(train_id)
            
            # Send commands to wayside for new/updated route
            if self.communicationHandler:
                self.communicationHandler.send_train_commands_for_route(train_id, route)
            
            # Emit signals to update UI
            self.trains_updated.emit()
            self.state_changed.emit()
            
            logger.info(f"Route activated for train {train_id}: departure at {getattr(train, 'departure_time', 'N/A')}")
            return True
        return False
    
    def dispatch_train_from_yard(self, train_id: str) -> None:
        """
        Send commands when train departs from yard
        
        Args:
            train_id: ID of train departing from yard
        """
        if train_id in self.trains and self.communicationHandler:
            train = self.trains[train_id]
            if hasattr(train, 'route') and train.route:
                self.communicationHandler.send_departure_commands(train_id, train.route)
                logger.info(f"Train {train_id} dispatched from yard")
            else:
                logger.warning(f"Cannot dispatch train {train_id}: no route assigned")
        else:
            logger.error(f"Cannot dispatch train {train_id}: train not found or no communication handler")
    
    def add_temporary_train(self, line, block, train_id=None):
        """Add temporary train for route calculation"""
        if not train_id:
            train_id = f"temp_{line}_{block}"
        
        temp_train = type('TempTrain', (), {
            'trainID': train_id,
            'line': line,
            'currentBlock': block,
            'route': None
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