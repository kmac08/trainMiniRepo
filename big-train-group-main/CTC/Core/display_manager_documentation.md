# DisplayManager Class Documentation

## Overview
The DisplayManager class (`display_manager.py`) manages all display-related functionality for the CTC system according to UML specifications, separating display logic from UI implementation.

## Attributes

### Core UML Attributes
- `mapState` (dict): Current map visualization state
- `trainTable` (dict): Train status table data
- `blockTable` (dict): Block status table data
- `emergencyTable` (dict): Emergency/failure table data

### Implementation Attributes
- `update_callbacks` (dict): UI update callbacks
- `throughput_history` (List): Historical throughput data
- `display_cache` (dict): Cache for performance

## Qt Signals
- `map_updated`: Emitted when map state changes
- `train_table_updated`: Emitted when train table updates
- `block_table_updated`: Emitted when block table updates
- `emergency_table_updated`: Emitted when emergency table updates
- `throughput_updated`: Emitted when throughput metrics update

## Methods

### Core UML Methods
- `get_updated_map() -> dict`: Return current track map state
- `get_train_table() -> dict`: Return train status table
- `get_block_table() -> dict`: Return block status table
- `get_emergency_table() -> dict`: Return emergency/failure table
- `update_display_speed(train, speed: float)`: Update train speed on display
- `display_route(route)`: Display new route on map
- `display_closure(block, closureTime: datetime)`: Display block closure
- `display_switches()`: Update switch positions on display
- `update_throughput(throughput: int)`: Update throughput metrics display
- `display_switch_positions(positions: List[bool])`: Update switch position display
- `display_failure(message: str)`: Display failure message

### Train and Location Methods
- `update_train_location(train, location)`: Update train position on map
- `update_train_error(train)`: Display train malfunction

### Emergency Management Methods
- `update_block_failure(block_id: int, description: str)`: Add block failure to emergency table
- `address_emergency(emergency_id: str, resolution: str)`: Mark emergency as addressed
- `clear_route_display(route_id: str)`: Remove route from display

### UI Integration Methods
- `register_ui_callback(callback_type: str, callback_func)`: Register callback for UI updates
- `update_train_state(train_id, train)`: Update train state (compatibility method)
- `get_warnings()`: Get system warnings
- `is_block_closed(line, block_num)`: Check if a block is closed
- `set_selected_train(train_id)`: Set selected train for UI
- `set_selected_block(line, block_num)`: Set selected block for UI
- `get_maintenance_closures()`: Get maintenance closures

### Private Helper Methods
- `_initialize_tables()`: Initialize empty tables
- `_get_train_id(train) -> str`: Extract train ID from train object
- `_get_block_id(block) -> int`: Extract block ID from block object

## Data Structures

### Train Table Format
```python
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
```

### Block Table Format
```python
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
```

### Emergency Table Format
```python
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
```

### Map State Format
```python
{
    'trains': {},      # Train positions
    'routes': {},      # Active routes
    'closures': {},    # Block closures
    'switches': {}     # Switch positions
}
```

## Integration Notes
- Inherits from QObject to support Qt signals for UI updates
- Designed to separate display logic from UI implementation
- Provides caching for performance optimization
- Supports both real-time updates and historical data tracking
- Compatible with various UI frameworks through callback system