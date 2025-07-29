# Route Class Documentation

## Overview
The Route class (`route.py`) represents a train route with all associated control information according to UML specifications.

## Attributes

### Core UML Attributes
- `routeID` (str): Unique route identifier
- `startBlock` (Block): Starting block object
- `endBlock` (Block): Destination block object
- `blockSequence` (List[Block]): List of blocks in route order
- `estimatedTravelTime` (float): Estimated travel time in seconds

### Implementation Attributes
- `authoritySequence` (List[int]): Authority for each block (0 or 1)
- `speedSequence` (List[int]): Speed for each block (0-3)
- `currentBlockIndex` (int): Current position in route
- `isActive` (bool): Route activation status
- `trainID` (str): Assigned train ID
- `scheduledDeparture` (datetime): Scheduled departure time
- `actualDeparture` (datetime): Actual departure time
- `scheduledArrival` (datetime): Scheduled arrival time
- `actualArrival` (datetime): Actual arrival time

### Metadata Attributes
- `routeType` (str): Route type (NORMAL, EMERGENCY, MAINTENANCE)
- `priority` (int): Priority level (1=low, 2=medium, 3=high)
- `createdTime` (datetime): Route creation time
- `lastUpdate` (datetime): Last update time
- `totalDistance` (float): Total route distance in meters
- `maxSpeed` (int): Maximum speed for route
- `grade_profile` (List): Grade information for each block
- `station_stops` (List): List of station stops

## Methods

### Core UML Methods
- `create_route(start, end, arrivalTime: datetime)`: Create route from start to end
- `validate_route() -> bool`: Validate route is traversable
- `get_next_block()`: Get next block in sequence
- `update_location(newBlock)`: Update train position in route
- `get_block_sequence() -> List`: Get full block sequence

### Authority and Speed Methods
- `calculate_authority_speed()`: Calculate authority and speed for each block in route
- `update_for_conditions(track_conditions: dict)`: Update authority/speed based on current conditions
- `get_lookahead_info(numBlocks: int) -> Tuple[List[int], List[int]]`: Get authority/speed for next N blocks

### Progress and Timing Methods
- `get_remaining_blocks() -> List`: Get blocks remaining in route from current position
- `get_progress_percentage() -> float`: Get route completion percentage
- `get_estimated_arrival() -> Optional[datetime]`: Get estimated arrival time based on current conditions

### Station and Management Methods
- `add_station_stop(block, stop_duration: float)`: Add station stop to route
- `activate_route(train_id: str)`: Activate route for a specific train
- `deactivate_route()`: Deactivate route when train reaches destination

### Private Helper Methods
- `_calculate_block_sequence(start_block, end_block) -> List`: Calculate sequence of blocks from start to end
- `_calculate_route_parameters()`: Calculate route distance, time, and other parameters
- `_calculate_block_authority(block, block_index: int) -> int`: Calculate authority for specific block
- `_calculate_block_speed(block, block_index: int) -> int`: Calculate speed command for specific block
- `_blocks_connected(block1, block2) -> bool`: Check if two blocks are connected
- `_validate_timing() -> bool`: Validate route timing is feasible
- `_speed_command_to_kmh(speed_command: int, speed_limit: float) -> float`: Convert speed command to actual speed
- `_recalculate_travel_time()`: Recalculate travel time based on current speed restrictions

### Utility Methods
- `__str__() -> str`: String representation of route
- `__repr__() -> str`: Detailed representation of route

## Integration Notes
- Routes work closely with Block and Train objects
- Authority and speed sequences are automatically calculated based on track conditions
- Route validation checks block connectivity and operational status
- Station stops can be added for passenger service routes
- Progress tracking enables real-time monitoring of train movement