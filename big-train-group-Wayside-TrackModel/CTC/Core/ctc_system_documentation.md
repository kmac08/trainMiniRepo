# CTCSystem Class Documentation

## Overview
The CTCSystem class (`ctc_system.py`) is the central coordination system implementing UML specifications. This class consolidates functionality from multiple migrated modules including state management, train ID management, and collision detection.

## Attributes

### Core UML Attributes
- `activeTrains` (List): List of active train IDs
- `trackLayout`: Track Model reference
- `routeManager` (RouteManager): Route Manager instance
- `throughputMetrics` (List[int]): Throughput metrics
- `blockMetrics` (List[int]): Block metrics

### System State Attributes
- `blocks` (Dict[int, Block]): Block number to Block object mapping
- `routes` (Dict[str, Route]): Route ID to Route object mapping
- `trains` (Dict[str, Train]): Train ID to Train object mapping
- `trainAuthorities` (Dict[str, int]): Train ID to authority mapping
- `trainSuggestedSpeeds` (Dict[str, int]): Train ID to speed mapping
- `trackStatus` (Dict): Track status information
- `railwayCrossings` (Dict): Railway crossing status

### State Management Attributes (Migrated)
- `maintenance_closures` (Dict): Active closures by line
- `warnings` (List): Active warnings
- `selected_train` (str): Currently selected train ID
- `selected_block` (Tuple[str, int]): Currently selected block
- `system_time_multiplier` (float): Time acceleration
- `active_lines` (List[str]): Lines currently active
- `switch_positions` (Dict): Switch position data

### Train ID Management Attributes (Migrated)
- `line_counters` (Dict[str, int]): ID counters by line
- `active_train_ids` (Set): Set of active train IDs
- `id_manager`: Simple ID manager for compatibility

### Component References
- `communicationHandler` (CommunicationHandler): Communication handler instance
- `displayManager` (DisplayManager): Display manager instance
- `failureManager` (FailureManager): Failure manager instance

### System Control
- `system_time` (datetime): Current system time
- `system_running` (bool): System running flag
- `main_thread`: Main system thread

### Collision Detection Attributes (Migrated)
- `lookahead_time` (float): Seconds to look ahead for conflicts
- `minimum_separation` (float): Minimum meters between trains
- `safety_buffer_time` (float): Safety buffer in seconds
- `active_conflicts` (Dict[str, ConflictDetails]): Active conflicts
- `conflict_history` (List[ConflictDetails]): Conflict history
- `conflict_counter` (int): Conflict counter
- `detections_performed` (int): Detection counter
- `conflicts_detected` (int): Conflicts detected counter
- `collisions_prevented` (int): Collisions prevented counter

## Qt Signals (from State Manager)
- `train_selected`: Emitted when train selection changes
- `block_selected`: Emitted when block selection changes
- `state_changed`: Emitted when system state changes
- `trains_updated`: Emitted when train data updates
- `maintenance_updated`: Emitted when maintenance data updates
- `warnings_updated`: Emitted when warnings update

## Methods

### Core UML Methods
- `validate_ID(trainID: str) -> bool`: Validate train ID uniqueness
- `get_train_list() -> List`: Get all active trains
- `get_route(trainID: str) -> Optional[Route]`: Get route for specific train
- `generate_route(startBlock: Block, endBlock: Block) -> Optional[Route]`: Generate optimal route between blocks
- `update_throughput(tickets: int) -> str`: Update throughput metrics
- `schedule_route(route: Route)`: Schedule route activation
- `confirm_route(route: Route) -> str`: Confirm route scheduling
- `validate_closure(block: Block, time: datetime) -> bool`: Validate block closure feasibility
- `validate_arrival(time: datetime) -> bool`: Validate arrival time feasibility
- `confirm_closure()`: Confirm block closure

### Train ID Management Methods (Migrated)
- `generate_train_id(line: str) -> str`: Generate next available train ID for given line
- `release_train_id(train_id: str)`: Mark train ID as no longer active
- `is_valid_train_id(train_id: str) -> bool`: Validate train ID format
- `get_line_from_train_id(train_id: str) -> str`: Extract line name from train ID
- `get_next_id_preview(line: str) -> str`: Preview next train ID without generating it

### State Management Methods (Migrated)
- `get_train(train_id: str) -> Optional[Train]`: Get train object by ID (thread-safe)
- `get_all_trains() -> Dict[str, Train]`: Get copy of all active trains (thread-safe)
- `set_selected_train(train_id: str)`: Set currently selected train
- `get_selected_train() -> Optional[str]`: Get currently selected train ID
- `set_selected_block(line: str, block: int)`: Set currently selected block
- `get_selected_block() -> Optional[Tuple[str, int]]`: Get currently selected block
- `update_train_state(train_id: str, train_obj: Train)`: Update train state and notify observers
- `add_maintenance_closure(line: str, block: int)`: Add maintenance closure
- `remove_maintenance_closure(line: str, block: int)`: Remove maintenance closure
- `get_maintenance_closures() -> Dict[str, List[int]]`: Get current maintenance closures
- `is_block_closed(line: str, block: int) -> bool`: Check if a block is closed for maintenance
- `add_warning(warning_type: str, message: str, **kwargs)`: Add a warning to the system
- `remove_warning(warning_id: str) -> bool`: Remove a warning from the system
- `get_warnings() -> List[Dict]`: Get copy of all active warnings
- `clear_warnings()`: Clear all warnings

### Train Management Methods
- `add_train(train_or_line, block=None, train_id=None) -> bool`: **UPDATED** - Add train to system and register with communication handler
- `remove_train(train_id: str) -> bool`: **UPDATED** - Remove train from system and clean up communication handler state

### Removed Methods
The following deprecated methods have been removed:
- `update_train_commands()`: Deprecated legacy method replaced by event-driven commands
- `_update_train_commands()`: Private method that called deprecated send_train_info()

### Block Management Methods
- `get_block(block_id: int) -> Optional[Block]`: Get block by ID
- `get_block_by_line(line: str, block_number: int) -> Optional[Block]`: Get block by line and block number
- `get_all_blocks() -> Dict[int, Block]`: Get all blocks in system

### System Operation Methods
- `system_tick(current_time: datetime)`: Main update cycle called every simulated second
- `check_system_state()`: Check for failures and emergencies (includes collision detection)
- `shutdown()`: Shutdown CTC System

### Collision Detection Methods (Migrated)
- `detect_conflicts() -> List[ConflictDetails]`: Comprehensive conflict detection
- `resolve_conflict(conflict_id: str, resolution: str) -> bool`: Resolve a specific conflict
- `get_critical_conflicts() -> List[ConflictDetails]`: Get only critical conflicts requiring immediate attention
- `get_conflict_statistics() -> Dict`: Get conflict detection statistics

### Sequence Implementation Methods
- `execute_close_block_sequence(line: str, block_number: int, closure_time: datetime, dispatcher_confirms: bool) -> Dict[str, Any]`: Execute the closeBlock sequence diagram workflow

### Wayside Integration Methods
- `process_occupied_blocks(occupied_blocks: List[bool])`: Process occupied blocks update from wayside
- `process_switch_positions(switch_positions: List[bool])`: Process switch positions update from wayside
- `process_railway_crossings(railway_crossings: List[bool])`: Process railway crossings update from wayside

### Route and Schedule Methods
- **REMOVED**: `calculate_route()` function removed - UI now calls RouteManager.generate_route() directly using BFS pathfinding
- `activate_route(train_id, route)`: **UPDATED** - Activate route for train with improved command timing
- `dispatch_train_from_yard(train_id: str)`: **KEY METHOD** - Send departure commands when train actually leaves yard
- `add_temporary_train(line, block, train_id=None)`: Add temporary train for route calculation

### Utility Methods
- `get_train_info_for_display()`: Get train information formatted for display
- `get_system_stats() -> Dict`: Get comprehensive system statistics

### Private Helper Methods
- `_initialize_components()`: Initialize all system components
- `_initialize_blocks()`: Initialize blocks from track layout
- `_create_basic_blocks()`: Create basic blocks for testing
- `_update_trains()`: Update all trains in system
- `_update_routes()`: Update all active routes
- `_update_metrics()`: Update system metrics
- `_route_uses_block_at_time(route: Route, block_id: int, time: datetime) -> bool`: Check if route uses specific block at given time
- `_get_train_id(train) -> str`: Extract train ID from train object

## Data Classes

### ConflictDetails (Migrated from Collision Detector)
Detailed information about a detected conflict:
- `conflict_id` (str): Unique conflict identifier
- `conflict_type` (ConflictType): Type of conflict
- `severity` (ConflictSeverity): Severity level
- `train_ids` (List[str]): Involved train IDs
- `location_line` (str): Line where conflict occurs
- `location_block` (int): Block where conflict occurs
- `estimated_time_to_collision` (float): Time until potential collision
- `estimated_collision_speed` (float): Estimated collision speed
- `suggested_actions` (List[str]): Recommended actions
- `detection_timestamp` (float): When conflict was detected
- `train_speeds` (Dict[str, float]): Train speeds
- `train_positions` (Dict[str, int]): Train positions
- `distance_between_trains` (float): Distance between trains
- `closing_speed` (float): Relative closing speed

## Enumerations

### ConflictType (Migrated)
- `SAME_BLOCK`: Trains in same block
- `HEAD_ON`: Head-on collision potential
- `REAR_END`: Rear-end collision potential
- `SWITCH_CONFLICT`: Switch conflict
- `AUTHORITY_VIOLATION`: Authority violation
- `MAINTENANCE_CONFLICT`: Maintenance area conflict
- `SPEED_VIOLATION`: Speed limit violation

### ConflictSeverity (Migrated)
- `CRITICAL`: Immediate action required
- `HIGH`: High priority
- `MEDIUM`: Medium priority
- `LOW`: Low priority
- `WARNING`: Warning level

## **NEW: Communication Handler Integration Improvements**

### **Enhanced Train Lifecycle Management**
- `add_train()` now automatically registers trains with communication handler when added to track (not yard)
- `remove_train()` properly cleans up all communication handler state
- Train movement tracking integrated with wayside command coordination

### **Improved Route Activation Timing**
- `activate_route()` separated from departure command sending
- Yard trains: Route activated but commands sent only on `dispatch_train_from_yard()` call
- Track trains: Route activation immediately sends commands since train already positioned

### **Event-Driven Command Architecture**
- Commands sent only when system state changes (routing, movement, departures)
- No continuous command polling - reduces system load and improves responsiveness
- Multi-train coordination prevents command conflicts

### **Dynamic Wayside Integration**
- No hardcoded controller assumptions - works with any wayside configuration
- Automatic yard detection and routing based on actual controller registrations
- Complete command arrays always sent to maintain wayside controller consistency

## Integration Notes
- Central coordination point for all CTC subsystems
- Consolidates multiple previously separate managers into unified system
- Provides thread-safe state management with Qt signals for UI integration
- Supports both automated and manual operations
- Includes comprehensive conflict detection and prevention
- Designed for real-time operation with multiple update frequencies
- Provides extensive logging and monitoring capabilities
- **NEW**: Enhanced wayside integration with dynamic configuration support and improved command timing