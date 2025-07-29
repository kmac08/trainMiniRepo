# Route Class Documentation

## Overview
The Route class (`route.py`) represents a train route with all associated control information according to UML specifications. The Route class focuses on route data management and validation, while pathfinding is handled by the Route Manager.

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

## Methods

### Core UML Methods
- `create_route(start, end, arrivalTime: datetime, block_sequence: List = None)`: Create route from start to end with optional pre-calculated block sequence
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

### Management Methods
- `activate_route(train_id: str)`: Activate route for a specific train
- `deactivate_route()`: Deactivate route when train reaches destination

### Private Helper Methods
- `_calculate_route_parameters()`: Calculate route distance, time, and other parameters
- `_blocks_connected(block1, block2) -> bool`: Check if two blocks are connected
- `_validate_timing() -> bool`: Validate route timing is feasible
- `_speed_command_to_kmh(speed_command: int, speed_limit: float) -> float`: Convert speed command to actual speed
- `_recalculate_travel_time()`: Recalculate travel time based on current speed restrictions
- `_validate_switch_compatibility() -> bool`: Validate switch positions for route
- `_validate_junction_routing() -> bool`: Validate routing through junctions
- `_validate_loop_routing() -> bool`: Validate loop routing conflicts

### Utility Methods
- `__str__() -> str`: String representation of route
- `__repr__() -> str`: Detailed representation of route

## Integration Notes
- Routes work closely with Block and Train objects
- **Route Manager handles pathfinding** - Route class expects pre-calculated block sequences
- Authority and speed sequences are automatically calculated based on track conditions
- Route validation checks block connectivity and operational status
- Progress tracking enables real-time monitoring of train movement

## Architecture Changes
As of the recent refactoring:
- **Pathfinding responsibility moved to Route Manager** - BFS algorithms now reside in RouteManager class
- **Route class simplified** - focuses on route data management and validation
- **create_route() accepts optional block_sequence** - Route Manager calculates paths and passes them to Route
- **Single Responsibility Principle** - Route Manager handles route generation, Route class handles route management