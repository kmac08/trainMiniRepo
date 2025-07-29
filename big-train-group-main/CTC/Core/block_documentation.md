# Block Class Documentation

## Overview
The Block class (`block.py`) represents individual track blocks in the CTC system and manages their operational state.

## Attributes

### Core Attributes
- `blockID` (int): Unique identifier for the block
- `block_number` (int): Block number for UI compatibility 
- `length` (float): Block length in meters
- `grade` (float): Block grade as percentage
- `speedLimit` (float): Speed limit in km/h
- `stationaryStatus` (bool): Operational status (True = operational)
- `switchPosition` (bool): Current switch position if applicable
- `switchPresent` (bool): Whether block has a switch
- `crossingPresent` (bool): Whether block has a railway crossing
- `crossingStatus` (bool): Railway crossing active status
- `circuitPresent` (bool): Whether block has track circuits (always True)
- `scheduledOccupations` (List[datetime]): Scheduled occupation times
- `scheduledClosures` (List[datetime]): Scheduled closure times
- `occupyingTrain` (Train): Train object currently in block

### Additional Implementation Attributes
- `authority` (int): Current authority (0 or 1)
- `suggestedSpeed` (int): Current speed command (0-3)
- `track_circuit_failed` (bool): Track circuit failure status
- `power_rail_status` (bool): Power rail operational status
- `line` (str): Line name (Blue, Red, Green)
- `section` (str): Section identifier
- `elevation` (float): Block elevation in meters
- `direction` (str): Track direction
- `is_underground` (bool): Whether block is underground
- `station` (Station): Station object if present
- `switch` (Switch): Switch object if present
- `occupied` (bool): Current occupation status
- `last_occupancy_change` (datetime): Time of last occupancy change
- `occupancy_history` (List[dict]): Historical occupancy data
- `maintenance_mode` (bool): Maintenance mode status
- `failure_mode` (bool): Failure mode status
- `last_maintenance` (datetime): Last maintenance time

## Methods

### Core Methods
- `update_occupation(occupied: bool)`: Update block occupation status
- `get_switch_info() -> bool`: Get current switch position
- `setCrossing_status(status: bool)`: Set railway crossing status
- `setBlock_status(status: bool)`: Set block operational status
- `block_operational() -> bool`: Check if block is operational
- `update_scheduled_occupancy(times: List[datetime])`: Update scheduled occupations
- `block_occupation() -> List[datetime]`: Get scheduled occupations
- `add_train(train)`: Add train to block
- `remove_train()`: Remove train from block
- `get_occupying_train()`: Get current occupying train

### Safety and Authority Methods
- `calculate_safe_authority(next_blocks: List['Block']) -> int`: Calculate safe authority based on ahead conditions
- `calculate_suggested_speed(train_state: dict, track_conditions: dict) -> int`: Calculate speed command based on conditions

### Infrastructure Methods
- `set_switch_position(position: bool)`: Set switch position
- `schedule_closure(start_time: datetime, end_time: datetime)`: Schedule block closure for maintenance
- `is_closed_at_time(check_time: datetime) -> bool`: Check if block is closed at specific time
- `get_next_valid_blocks(direction: str = None) -> List[int]`: Get list of valid next blocks based on track layout
- `get_infrastructure_info() -> dict`: Get complete infrastructure information

### Helper Methods
- `_switch_aligned_for_route(next_blocks: List['Block']) -> bool`: Check if switch is properly aligned for route
- `_get_train_id(train) -> str`: Extract train ID from train object
- `__str__() -> str`: String representation of block
- `__repr__() -> str`: Detailed representation of block

