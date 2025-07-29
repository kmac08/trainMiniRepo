# FailureManager Class Documentation

## Overview
The FailureManager class (`failure_manager.py`) manages failure detection, tracking, and recovery for the CTC system according to UML specifications. This class consolidates functionality from the original maintenance manager.

## Attributes

### Core UML Attributes
- `failedBlocks` (List[Block]): List of failed block objects

### Implementation Attributes
- `failedTrains` (List[Train]): List of failed train objects
- `failure_history` (List): Historical failures
- `active_emergencies` (Dict): Current emergency situations (emergency_id -> emergency_details)
- `recovery_actions` (Dict): Recovery tracking (failure_id -> recovery_status)
- `stopped_trains` (Set): Set of train IDs stopped due to failures

### Maintenance Management Attributes (Migrated)
- `maintenanceClosures` (Dict[str, List[int]]): Active closures by line
- `scheduledClosures` (List): List of scheduled closure objects
- `scheduledOpenings` (List): List of scheduled opening objects

### Component References
- `ctc_system`: Reference to CTC System
- `communication_handler`: Reference to communication handler
- `display_manager`: Reference to display manager

## Methods

### Core UML Methods
- `find_affected_trains() -> List`: Find trains affected by current failures
- `check_for_failures()`: Check system for failures (failures currently reported manually)
- `add_failed_block(block)`: Register block failure
- `add_failed_train(train)`: Register train failure
- `reroute_trains()`: Attempt to reroute around failures
- `stop_trains()`: Emergency stop affected trains

### Enhanced Functionality Methods
- `generate_emergency_routes(affected_trains: List) -> Dict[str, any]`: Generate alternative routes for affected trains
- `clear_failure(failure_id: str)`: Mark failure as resolved
- `get_failure_impact(failure_id: str) -> dict`: Analyze impact of specific failure

### Maintenance Management Methods (Migrated)
- `close_block(line: str, block_number: int) -> Dict`: Close a track block for maintenance work
- `open_block(line: str, block_number: int) -> Dict`: Reopen a block after maintenance
- `get_closed_blocks(line: str = None) -> Dict[str, List[int]]`: Get list of closed blocks, optionally filtered by line
- `schedule_block_closure(line: str, block_number: int, scheduled_time: datetime, duration_hours: float) -> Dict`: Schedule a block closure for future maintenance
- `get_scheduled_closures()`: Get scheduled block closures
- `cancel_scheduled_closure(closure_id)`: Cancel a scheduled closure
- `process_scheduled_closures()`: Process any scheduled closures that are due
- `process_scheduled_openings()`: Process any scheduled openings that are due

### Utility Methods
- `generate_warnings(track_status=None, railway_crossings=None)`: Generate system warnings
- `remove_failed_block(block)`: Remove block from failed list (recovery)

### Private Helper Methods
- `_is_train_affected_by_blocks(train) -> bool`: Check if train is affected by any failed blocks
- `_emergency_stop_train(train)`: Send emergency stop command to train
- `_stop_affected_trains_for_block(failed_block)`: Stop all trains affected by a specific block failure
- `_generate_alternative_route(train)`: Generate alternative route avoiding failed blocks
- `_get_train_id(train) -> str`: Extract train ID from train object
- `_get_block_id(block) -> int`: Extract block ID from block object

### Removed Methods
The following methods have been removed as they were unimplemented:
- `_check_block_failures()`: Placeholder for block failure detection
- `_check_train_failures()`: Placeholder for train failure detection  
- `_check_communication_failures()`: Placeholder for communication failure detection
- `_update_emergency_displays()`: Placeholder for display updates

## Emergency Data Structures

### Emergency Record Format
```python
{
    'id': str,                    # Unique emergency ID
    'type': str,                  # 'BLOCK_FAILURE', 'TRAIN_FAILURE', 'SYSTEM_FAILURE'
    'train_id': Optional[str],    # Train ID if applicable
    'block_id': Optional[int],    # Block ID if applicable
    'description': str,           # Human-readable description
    'timestamp': datetime,        # When emergency was detected
    'addressed': bool,            # Whether emergency has been addressed
    'resolution': Optional[str],  # Resolution description
    'failure_object': object      # Reference to failed object
}
```

### Scheduled Closure Format
```python
{
    'id': str,                    # Unique closure ID
    'line': str,                  # Line name (Blue, Red, Green)
    'block_number': int,          # Block number to close
    'scheduled_time': datetime,   # When to close the block
    'end_time': datetime,         # When to reopen the block
    'duration_hours': float,      # Duration of closure
    'status': str,                # 'scheduled', 'active', 'completed', 'cancelled'
    'created_at': datetime        # When closure was scheduled
}
```

## Integration Notes
- Automatically detects and responds to system failures
- Integrates with communication handler for emergency stop commands
- Coordinates with display manager for emergency notifications
- Provides both automated responses and manual dispatcher control
- Maintains historical data for failure analysis and system improvement
- Supports scheduled maintenance operations with automatic execution
- Designed for real-time operation with immediate failure response capabilities
- Includes comprehensive logging for audit trails and debugging