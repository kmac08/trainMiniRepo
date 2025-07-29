# RouteManager Class Documentation

## Overview
The RouteManager class (`route_manager.py`) manages route generation, validation, and scheduling according to UML specifications. This class consolidates functionality from multiple migrated modules including routing engine, time-based routing, and maintenance management.

## Attributes

### Core UML Attributes
- `activeRoutes` (List[Route]): List of currently active routes

### Implementation Attributes
- `route_algorithms` (Dict): Routing algorithm implementations
- `route_history` (List): Historical routes
- `block_reservations` (Dict): Block to route reservations mapping
- `route_cache` (Dict): Cache for frequently requested routes
- `scheduled_routes` (Dict): Time-based route scheduling
- `route_conflicts` (List): List of detected conflicts
- `optimization_weights` (Dict): Weights for route optimization

### Routing Engine Attributes (Migrated)
- `safety_buffer_blocks` (int): Minimum blocks between trains
- `lookahead_time` (float): Seconds to look ahead for conflicts
- `route_calculations` (int): Number of route calculations performed
- `cache_hits` (int): Number of cache hits
- `collision_avoidances` (int): Number of collision avoidances
- `calculated_routes` (Dict): Calculated routes by train ID
- `route_cache_timeout` (float): Cache timeout in seconds

### Time-based Routing Attributes (Migrated)
- `active_schedules` (Dict[str, TrainSchedule]): Active train schedules
- `schedule_points_by_block` (Dict): Schedule points indexed by block
- `schedule_buffer_seconds` (float): Schedule buffer time
- `transfer_window_seconds` (float): Transfer window duration
- `station_dwell_default` (float): Default station dwell time
- `schedules_created` (int): Number of schedules created
- `on_time_arrivals` (int): On-time arrival counter
- `delayed_arrivals` (int): Delayed arrival counter
- `early_arrivals` (int): Early arrival counter

### Performance Metrics
- `route_generation_times` (List): Route generation time history
- `successful_routes` (int): Successful route counter
- `failed_routes` (int): Failed route counter

## Methods

### Core UML Methods
- `generate_route(start: Block, end: Block, arrivalTime: datetime) -> Optional[Route]`: Generate optimal route between blocks
- `validate_destination(destination: Block) -> bool`: Check if destination is valid and reachable
- `initiate_route_generation()`: Start route generation process
- `update_scheduled_occupancy(route: Route)`: Update block occupancy schedules for route
- `check_arrival_time(route: Route, target_time: datetime) -> bool`: Validate arrival time feasibility for route
- `confirm_route(route: Route) -> bool`: Confirm and finalize route

### Route Calculation Methods (From Routing Engine)
- `calculate_route(train_id: str, destination_block: int, route_type: RouteType, priority: RoutePriority, scheduled_arrival: Optional[datetime]) -> Optional[CalculatedRoute]`: Calculate optimal route for a train
- `_calculate_shortest_route(train, destination_block: int, priority: RoutePriority) -> Optional[CalculatedRoute]`: Calculate shortest distance route
- `_calculate_fastest_route(train, destination_block: int, priority: RoutePriority) -> Optional[CalculatedRoute]`: Calculate fastest time route
- `_calculate_safest_route(train, destination_block: int, priority: RoutePriority) -> Optional[CalculatedRoute]`: Calculate safest route with maximum collision avoidance
- `_calculate_maintenance_aware_route(train, destination_block: int, priority: RoutePriority) -> Optional[CalculatedRoute]`: Calculate route avoiding maintenance areas

### Route Management Methods
- `find_alternative_routes(start: Block, end: Block, avoid_blocks: List[Block]) -> List[Route]`: Find alternative routes avoiding specific blocks
- `optimize_route_for_time(route: Route, target_time: datetime) -> Optional[Route]`: Optimize route for specific arrival time
- `reserve_blocks_for_route(route: Route) -> bool`: Reserve blocks for exclusive route use
- `release_route(route: Route)`: Release route and free up reserved blocks

### Time-based Routing Methods (Migrated)
- `create_schedule(train_id: str, schedule_points: List[SchedulePoint], service_type: str, priority: SchedulePriority) -> TrainSchedule`: Create a new schedule for a train
- `calculate_timed_route(train_id: str, destination_block: int, target_arrival_time: Optional[datetime], route_type: RouteType) -> Optional[TimedRoute]`: Calculate a route with detailed timing to meet schedule requirements
- `optimize_schedule_for_transfers(hub_block: int, connecting_trains: List[str], transfer_window: float) -> Dict[str, datetime]`: Optimize arrival times at a hub station to facilitate transfers
- `check_schedule_conflicts(train_id: str) -> List[Dict]`: Check for conflicts with scheduled maintenance or other trains
- `update_schedule_progress(train_id: str, current_block: int) -> Dict`: Update schedule progress and performance metrics

### Statistics and Monitoring Methods
- `get_route_statistics() -> Dict`: Get route management statistics
- `get_schedule_statistics() -> Dict`: Get schedule performance statistics

### Private Helper Methods
- `_initialize_algorithms()`: Initialize routing algorithms
- `_get_block_info(line: str, block_num: int)`: Get block information
- `_check_block_conflicts(train_id: str, block_num: int, speed: float) -> List[str]`: Check for conflicts with other trains at block
- `_is_block_closed_for_maintenance(line: str, block_num: int) -> bool`: Check if block is closed for maintenance
- `_is_station_block(line: str, block_num: int) -> bool`: Check if block has a station
- `_calculate_safe_authority(train, remaining_blocks: List[int], conflicts: List[str]) -> int`: Calculate safe authority based on track ahead
- `_get_maintenance_blocks(line: str) -> Set[int]`: Get all blocks under maintenance for a line

## Data Classes

### RouteSegment
Represents a single segment in a calculated route:
- `block_number` (int): Block number
- `suggested_speed` (float): Suggested speed in km/h
- `authority` (int): Authority in blocks ahead
- `estimated_time` (float): Estimated traversal time in seconds
- `conflicts` (List[str]): Conflicting train IDs
- `maintenance_risk` (bool): Maintenance risk flag

### CalculatedRoute
Complete route calculation result:
- `train_id` (str): Train identifier
- `line` (str): Line name
- `origin_block` (int): Starting block
- `destination_block` (int): Destination block
- `segments` (List[RouteSegment]): Route segments
- `total_time` (float): Total travel time
- `total_distance` (float): Total distance
- `safety_score` (float): Safety score (0.0 to 1.0)
- `route_type` (RouteType): Type of route
- `conflicts_detected` (List[str]): Detected conflicts

### TrainSchedule
Complete schedule for a train:
- `train_id` (str): Train identifier
- `line` (str): Line name
- `schedule_points` (List[SchedulePoint]): Scheduled points
- `service_type` (str): Service type
- `priority` (SchedulePriority): Schedule priority

### SchedulePoint
A scheduled point along a route:
- `block_number` (int): Block number
- `scheduled_arrival` (datetime): Scheduled arrival time
- `train_id` (str): Train identifier
- `scheduled_departure` (Optional[datetime]): Scheduled departure time
- `minimum_dwell_seconds` (float): Minimum dwell time
- `maximum_dwell_seconds` (float): Maximum dwell time
- `priority` (SchedulePriority): Priority level
- `constraint_type` (TimingConstraint): Type of timing constraint

## Enumerations

### RouteType
- `SHORTEST_DISTANCE`: Optimize for minimum distance
- `FASTEST_TIME`: Optimize for minimum travel time
- `SAFEST_PATH`: Optimize for maximum safety
- `MAINTENANCE_AWARE`: Avoid maintenance areas

### RoutePriority
- `EMERGENCY`: Emergency priority
- `HIGH`: High priority
- `NORMAL`: Normal priority
- `LOW`: Low priority

### SchedulePriority
- `CRITICAL`: Critical schedule adherence
- `HIGH`: High priority
- `NORMAL`: Normal priority
- `LOW`: Low priority

## Integration Notes
- Consolidates multiple routing subsystems into unified interface
- Supports both basic route generation and complex schedule-aware routing
- Provides extensive conflict detection and resolution capabilities
- Integrates with maintenance systems for route planning around closures
- Offers comprehensive performance monitoring and statistics
- Designed for real-time operation with caching for performance optimization