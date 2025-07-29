"""
Route Manager Module
==================
Manages route generation, validation, and scheduling according to UML specifications.
Separate from the routing engine to handle higher-level route management.

This module handles:
- Route generation and optimization
- Route validation and scheduling
- Block reservation management
- Alternative route finding
- Route conflict resolution
"""

from typing import List, Dict, Optional, Set, Tuple, TYPE_CHECKING
from datetime import datetime, timedelta
import logging
import time
import heapq
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from .route import Route
from .block import Block

# Migrated from routing_engine.py
class RouteType(Enum):
    """Types of routes that can be calculated"""
    SHORTEST_DISTANCE = "shortest_distance"
    FASTEST_TIME = "fastest_time" 
    SAFEST_PATH = "safest_path"
    MAINTENANCE_AWARE = "maintenance_aware"

class RoutePriority(Enum):
    """Priority levels for route requests"""
    EMERGENCY = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4

@dataclass
class RouteSegment:
    """A single segment in a calculated route"""
    block_number: int
    suggested_speed: float  # km/h
    authority: int  # blocks ahead
    estimated_time: float  # seconds to traverse
    conflicts: List[str]  # train IDs that may conflict
    maintenance_risk: bool = False
    
@dataclass 
class CalculatedRoute:
    """Complete route calculation result"""
    train_id: str
    line: str
    origin_block: int
    destination_block: int
    segments: List[RouteSegment]
    total_time: float  # seconds
    total_distance: float  # meters
    safety_score: float  # 0.0 to 1.0, higher is safer
    route_type: RouteType
    timestamp: float
    conflicts_detected: List[str]  # train IDs with potential conflicts
    scheduled_arrival: Optional[datetime] = None
    scheduled_departure: Optional[datetime] = None
    
    def get_block_numbers(self) -> List[int]:
        """Get list of block numbers in route order"""
        return [segment.block_number for segment in self.segments]
        
    def get_suggested_speeds(self) -> List[float]:
        """Get list of suggested speeds for each block"""
        return [segment.suggested_speed for segment in self.segments]
        
    def get_authorities(self) -> List[int]:
        """Get list of authorities for each block"""
        return [segment.authority for segment in self.segments]

# Migrated from time_based_routing.py
class SchedulePriority(Enum):
    """Priority levels for schedule adherence"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4

class TimingConstraint(Enum):
    """Types of timing constraints"""
    ARRIVAL_TIME = "arrival_time"
    DEPARTURE_TIME = "departure_time"
    DWELL_TIME = "dwell_time"
    TRANSFER_TIME = "transfer_time"
    MAINTENANCE_WINDOW = "maintenance_window"

@dataclass
class SchedulePoint:
    """A scheduled point along a route with timing requirements"""
    block_number: int
    scheduled_arrival: datetime
    train_id: str = ""
    scheduled_departure: Optional[datetime] = None
    minimum_dwell_seconds: float = 0.0
    maximum_dwell_seconds: float = 300.0
    priority: SchedulePriority = SchedulePriority.NORMAL
    constraint_type: TimingConstraint = TimingConstraint.ARRIVAL_TIME
    transfer_connections: List[str] = None
    
    def __post_init__(self):
        if self.transfer_connections is None:
            self.transfer_connections = []

@dataclass
class TrainSchedule:
    """Complete schedule for a train with timing requirements"""
    train_id: str
    line: str
    schedule_points: List[SchedulePoint]
    service_type: str = "regular"
    priority: SchedulePriority = SchedulePriority.NORMAL
    created_time: datetime = None
    
    def __post_init__(self):
        if self.created_time is None:
            self.created_time = datetime.now()
            
    def get_next_schedule_point(self, current_block: int) -> Optional[SchedulePoint]:
        for point in self.schedule_points:
            if point.block_number > current_block:
                return point
        return None
        
    def get_schedule_point_at_block(self, block_number: int) -> Optional[SchedulePoint]:
        for point in self.schedule_points:
            if point.block_number == block_number:
                return point
        return None

@dataclass
class TimedRoute:
    """Route with detailed timing information"""
    base_route: CalculatedRoute
    schedule: TrainSchedule
    timed_segments: List[Tuple[RouteSegment, datetime, datetime]]
    schedule_adherence_score: float
    total_delay_seconds: float
    critical_points_missed: int
    alternative_routes: List['TimedRoute'] = None
    
    def __post_init__(self):
        if self.alternative_routes is None:
            self.alternative_routes = []

# Set up logging
logger = logging.getLogger(__name__)


class RouteManager:
    """
    Route Manager implementing UML interface
    Handles high-level route management and coordination
    """
    
    def __init__(self, track_reader=None):
        """
        Initialize Route Manager with UML-specified attributes
        
        Args:
            track_reader: Track layout reader for routing calculations
        """
        # Attributes from UML
        self.activeRoutes = []         # List[Route]
        
        # Additional attributes needed for implementation
        self.route_algorithms = {}     # Routing algorithm implementations
        self.route_history = []        # Historical routes
        self.block_reservations = {}   # Block -> List[Route] reservations
        self.route_cache = {}          # Cache for frequently requested routes
        
        # Route planning data
        self.scheduled_routes = {}     # time -> List[Route]
        self.route_conflicts = []      # List of detected conflicts
        self.optimization_weights = {  # Weights for route optimization
            'distance': 0.3,
            'time': 0.4,
            'traffic': 0.2,
            'grade': 0.1
        }
        
        # Migrated from routing_engine.py
        self.safety_buffer_blocks = 2  # minimum blocks between trains
        self.lookahead_time = 120.0   # seconds to look ahead for conflicts
        self.route_calculations = 0
        self.cache_hits = 0
        self.collision_avoidances = 0
        self.calculated_routes = {}   # Calculated routes by train ID
        self.route_cache_timeout = 30.0  # seconds
        
        # Track layout reference
        self.track_reader = track_reader
        self.track_graph = {}          # Block connectivity graph
        
        # Performance metrics
        self.route_generation_times = []
        self.successful_routes = 0
        self.failed_routes = 0
        
        # Time-based routing attributes (from time_based_routing)
        self.active_schedules: Dict[str, TrainSchedule] = {}
        self.schedule_points_by_block: Dict[Tuple[str, int], List[SchedulePoint]] = {}
        self.schedule_buffer_seconds = 30.0
        self.transfer_window_seconds = 180.0
        self.station_dwell_default = 60.0
        self.schedules_created = 0
        self.on_time_arrivals = 0
        self.delayed_arrivals = 0
        self.early_arrivals = 0
        
        # Initialize routing algorithms
        self._initialize_algorithms()
        
        if self.track_reader:
            self._build_track_graph()
        
        logger.info("Route Manager initialized")
    
    # Methods from UML
    
    def calculate_route(self, train_id: str, destination_block: int,
                       route_type: RouteType = RouteType.SAFEST_PATH,
                       priority: RoutePriority = RoutePriority.NORMAL,
                       scheduled_arrival: Optional[datetime] = None) -> Optional[CalculatedRoute]:
        """
        Calculate optimal route for a train to reach destination (from routing_engine)
        
        Args:
            train_id: ID of train to route
            destination_block: Target block number
            route_type: Type of route optimization to use
            priority: Priority level for this route request
            scheduled_arrival: Optional scheduled arrival time at destination
            
        Returns:
            CalculatedRoute object or None if no valid route found
        """
        self.route_calculations += 1
        
        # Get train information from CTC system
        if hasattr(self, 'ctc_system') and self.ctc_system:
            train = self.ctc_system.get_train(train_id)
            if not train:
                return None
        else:
            logger.warning("No CTC system reference for train lookup")
            return None
            
        # Check cache first
        cache_key = f"{train_id}_{train.currentBlock.blockID}_{destination_block}_{route_type.value}"
        if scheduled_arrival:
            cache_key += f"_{scheduled_arrival.strftime('%H:%M')}"
        
        if cache_key in self.route_cache:
            cached_entry = self.route_cache[cache_key]
            if time.time() - cached_entry['timestamp'] < self.route_cache_timeout:
                self.cache_hits += 1
                return cached_entry['route']
            else:
                del self.route_cache[cache_key]
                
        # Calculate new route based on type
        if route_type == RouteType.SHORTEST_DISTANCE:
            calculated_route = self._calculate_shortest_route(train, destination_block, priority)
        elif route_type == RouteType.FASTEST_TIME:
            calculated_route = self._calculate_fastest_route(train, destination_block, priority)
        elif route_type == RouteType.SAFEST_PATH:
            calculated_route = self._calculate_safest_route(train, destination_block, priority)
        elif route_type == RouteType.MAINTENANCE_AWARE:
            calculated_route = self._calculate_maintenance_aware_route(train, destination_block, priority)
        else:
            calculated_route = self._calculate_safest_route(train, destination_block, priority)
            
        # Set scheduled times if provided
        if calculated_route and scheduled_arrival:
            calculated_route.scheduled_arrival = scheduled_arrival
            if calculated_route.total_time < float('inf'):
                calculated_route.scheduled_departure = scheduled_arrival - timedelta(seconds=calculated_route.total_time)
        
        # Cache the result
        if calculated_route:
            self.route_cache[cache_key] = {
                'route': calculated_route,
                'timestamp': time.time()
            }
            self.calculated_routes[train_id] = calculated_route
            
        return calculated_route
    
    def generate_route(self, start: Block, end: Block, arrivalTime: datetime) -> Optional[Route]:
        """
        Generate optimal route between blocks
        
        Args:
            start: Starting block
            end: Destination block
            arrivalTime: Desired arrival time
            
        Returns:
            Generated Route object, or None if no route possible
        """
        start_time = datetime.now()
        
        try:
            # Check cache first
            cache_key = f"{start.blockID}_{end.blockID}_{arrivalTime.hour}"
            if cache_key in self.route_cache:
                cached_route = self.route_cache[cache_key]
                if self._route_still_valid(cached_route):
                    logger.debug(f"Returning cached route for {start.blockID} -> {end.blockID}")
                    return self._clone_route(cached_route, arrivalTime)
            
            # Generate new route
            route = Route()
            route.create_route(start, end, arrivalTime)
            
            # Optimize route using available algorithms
            optimized_route = self._optimize_route(route)
            
            if optimized_route and optimized_route.validate_route():
                # Add to active routes
                self.activeRoutes.append(optimized_route)
                
                # Reserve blocks
                self._reserve_blocks_for_route(optimized_route)
                
                # Cache the route
                self.route_cache[cache_key] = optimized_route
                
                # Update metrics
                generation_time = (datetime.now() - start_time).total_seconds()
                self.route_generation_times.append(generation_time)
                self.successful_routes += 1
                
                logger.info(f"Route generated successfully: {optimized_route.routeID}")
                return optimized_route
            else:
                self.failed_routes += 1
                logger.warning(f"Route generation failed: {start.blockID} -> {end.blockID}")
                return None
                
        except Exception as e:
            self.failed_routes += 1
            logger.error(f"Error generating route: {e}")
            return None
    
    def validate_destination(self, destination: Block) -> bool:
        """
        Check if destination is valid and reachable
        
        Args:
            destination: Destination block to validate
            
        Returns:
            True if destination is valid
        """
        if not destination or not hasattr(destination, 'blockID'):
            return False
        
        # Check if block exists in track layout
        if destination.blockID not in self.track_graph:
            return False
        
        # Check if block is operational
        if not destination.block_operational():
            return False
        
        # Check if block is permanently closed
        if hasattr(destination, 'maintenance_mode') and destination.maintenance_mode:
            return False
        
        # Check if destination has station (optional validation)
        if hasattr(destination, 'station') and destination.station:
            # Valid station destination
            return True
        
        # Allow any operational block as destination
        return True
    
    def initiate_route_generation(self) -> None:
        """
        Start route generation process
        Called when new route request is received
        """
        logger.info("Route generation process initiated")
        
        # Clean up old/expired routes
        self._cleanup_expired_routes()
        
        # Check for route conflicts
        self._detect_route_conflicts()
        
        # Update block reservations
        self._update_block_reservations()
    
    def update_scheduled_occupancy(self, route: Route) -> None:
        """
        Update block occupancy schedules for route
        
        Args:
            route: Route to schedule block occupancy for
        """
        if not route.isActive or not route.blockSequence:
            return
        
        current_time = route.scheduledDeparture or datetime.now()
        
        for i, block in enumerate(route.blockSequence):
            # Calculate when train will occupy this block
            if i == 0:
                occupancy_time = current_time
            else:
                # Estimate based on travel time to this block
                prev_blocks = route.blockSequence[:i]
                travel_time = self._calculate_travel_time(prev_blocks, route)
                occupancy_time = current_time + timedelta(seconds=travel_time)
            
            # Schedule the occupancy
            block.scheduledOccupations.append(occupancy_time)
            
            # Add to reservations
            if block.blockID not in self.block_reservations:
                self.block_reservations[block.blockID] = []
            self.block_reservations[block.blockID].append(route)
        
        logger.debug(f"Scheduled occupancy updated for route {route.routeID}")
    
    def check_arrival_time(self, route: Route, target_time: datetime) -> bool:
        """
        Validate arrival time feasibility for route
        
        Args:
            route: Route to check
            target_time: Desired arrival time
            
        Returns:
            True if arrival time is achievable
        """
        if not route.blockSequence:
            return False
        
        # Calculate minimum travel time
        min_travel_time = self._calculate_minimum_travel_time(route)
        earliest_arrival = datetime.now() + timedelta(seconds=min_travel_time)
        
        # Check if target time is achievable
        if target_time < earliest_arrival:
            logger.warning(f"Target arrival time too early for route {route.routeID}")
            return False
        
        # Check if target time is reasonable (not too far in future)
        max_future = datetime.now() + timedelta(hours=24)
        if target_time > max_future:
            logger.warning(f"Target arrival time too far in future for route {route.routeID}")
            return False
        
        return True
    
    def confirm_route(self, route: Route) -> bool:
        """
        Confirm and finalize route
        
        Args:
            route: Route to confirm
            
        Returns:
            True if route confirmed successfully
        """
        try:
            # Final validation
            if not route.validate_route():
                logger.error(f"Route {route.routeID} failed final validation")
                return False
            
            # Check for conflicts with other routes
            if self._has_route_conflicts(route):
                logger.error(f"Route {route.routeID} has conflicts with existing routes")
                return False
            
            # Reserve blocks
            if not self.reserve_blocks_for_route(route):
                logger.error(f"Could not reserve blocks for route {route.routeID}")
                return False
            
            # Update scheduled occupancy
            self.update_scheduled_occupancy(route)
            
            # Add to route history
            self.route_history.append({
                'route': route,
                'confirmed_time': datetime.now(),
                'status': 'CONFIRMED'
            })
            
            logger.info(f"Route {route.routeID} confirmed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error confirming route {route.routeID}: {e}")
            return False
    
    # Additional methods needed for implementation
    
    def find_alternative_routes(self, start: Block, end: Block, avoid_blocks: List[Block]) -> List[Route]:
        """
        Find alternative routes avoiding specific blocks
        
        Args:
            start: Starting block
            end: Destination block
            avoid_blocks: List of blocks to avoid
            
        Returns:
            List of alternative Route objects
        """
        alternatives = []
        avoid_block_ids = {block.blockID for block in avoid_blocks}
        
        try:
            # Use different routing algorithms
            for algorithm_name, algorithm in self.route_algorithms.items():
                try:
                    # Generate route avoiding specified blocks
                    route_path = algorithm(start.blockID, end.blockID, avoid_block_ids)
                    
                    if route_path and not any(block_id in avoid_block_ids for block_id in route_path):
                        # Create route object
                        route = self._create_route_from_path(route_path, start, end)
                        if route and route.validate_route():
                            alternatives.append(route)
                            
                except Exception as e:
                    logger.warning(f"Algorithm {algorithm_name} failed: {e}")
                    continue
            
            # Sort by quality (shortest, fastest, etc.)
            alternatives.sort(key=lambda r: (len(r.blockSequence), r.estimatedTravelTime))
            
            logger.info(f"Found {len(alternatives)} alternative routes")
            return alternatives
            
        except Exception as e:
            logger.error(f"Error finding alternative routes: {e}")
            return []
    
    def optimize_route_for_time(self, route: Route, target_time: datetime) -> Optional[Route]:
        """
        Optimize route for specific arrival time
        
        Args:
            route: Route to optimize
            target_time: Target arrival time
            
        Returns:
            Optimized Route object
        """
        try:
            # Calculate required average speed
            total_distance = route.totalDistance
            available_time = (target_time - datetime.now()).total_seconds()
            
            if available_time <= 0:
                logger.warning("Target time is in the past")
                return None
            
            required_speed = (total_distance / 1000.0) / (available_time / 3600.0)  # km/h
            
            # Check if required speed is achievable
            max_possible_speed = min(block.speedLimit for block in route.blockSequence)
            if required_speed > max_possible_speed:
                logger.warning(f"Required speed {required_speed} exceeds max speed {max_possible_speed}")
                return None
            
            # Adjust speed sequence
            optimized_route = self._clone_route(route, target_time)
            optimized_route.scheduledArrival = target_time
            
            # Recalculate speed commands based on target time
            self._optimize_speed_profile(optimized_route, target_time)
            
            logger.info(f"Route optimized for arrival at {target_time}")
            return optimized_route
            
        except Exception as e:
            logger.error(f"Error optimizing route for time: {e}")
            return None
    
    def reserve_blocks_for_route(self, route: Route) -> bool:
        """
        Reserve blocks for exclusive route use
        
        Args:
            route: Route to reserve blocks for
            
        Returns:
            True if all blocks reserved successfully
        """
        try:
            reserved_blocks = []
            
            for block in route.blockSequence:
                block_id = block.blockID
                
                # Check if block is available for reservation
                if self._is_block_available(block_id, route.scheduledDeparture):
                    # Reserve the block
                    if block_id not in self.block_reservations:
                        self.block_reservations[block_id] = []
                    self.block_reservations[block_id].append(route)
                    reserved_blocks.append(block_id)
                else:
                    # Cannot reserve - rollback previous reservations
                    self._rollback_reservations(reserved_blocks, route)
                    logger.warning(f"Could not reserve block {block_id} for route {route.routeID}")
                    return False
            
            logger.debug(f"Reserved {len(reserved_blocks)} blocks for route {route.routeID}")
            return True
            
        except Exception as e:
            logger.error(f"Error reserving blocks: {e}")
            return False
    
    def release_route(self, route: Route) -> None:
        """
        Release route and free up reserved blocks
        
        Args:
            route: Route to release
        """
        try:
            # Remove from active routes
            if route in self.activeRoutes:
                self.activeRoutes.remove(route)
            
            # Release block reservations
            for block in route.blockSequence:
                block_id = block.blockID
                if block_id in self.block_reservations:
                    if route in self.block_reservations[block_id]:
                        self.block_reservations[block_id].remove(route)
                    
                    # Clean up empty reservations
                    if not self.block_reservations[block_id]:
                        del self.block_reservations[block_id]
            
            # Deactivate route
            route.deactivate_route()
            
            logger.info(f"Route {route.routeID} released")
            
        except Exception as e:
            logger.error(f"Error releasing route {route.routeID}: {e}")
    
    def get_route_statistics(self) -> Dict:
        """Get route management statistics"""
        return {
            'active_routes': len(self.activeRoutes),
            'total_generated': self.successful_routes + self.failed_routes,
            'success_rate': self.successful_routes / max(1, self.successful_routes + self.failed_routes),
            'avg_generation_time': sum(self.route_generation_times) / max(1, len(self.route_generation_times)),
            'cached_routes': len(self.route_cache),
            'block_reservations': len(self.block_reservations),
            'route_conflicts': len(self.route_conflicts)
        }
    
    # Private helper methods
    
    def _initialize_algorithms(self):
        """Initialize routing algorithms"""
        # Simple algorithms for demonstration
        self.route_algorithms = {
            'shortest_path': self._shortest_path_algorithm,
            'fastest_route': self._fastest_route_algorithm,
            'least_traffic': self._least_traffic_algorithm
        }
    
    def _calculate_shortest_route(self, train, destination_block: int, priority: RoutePriority) -> Optional[CalculatedRoute]:
        """Calculate shortest distance route (from routing_engine)"""
        if not train or not hasattr(train, 'currentBlock'):
            return None
            
        current_block = train.currentBlock.blockID if hasattr(train.currentBlock, 'blockID') else train.currentBlock
        line = train.line
        
        # Simple linear route for now
        if current_block == destination_block:
            segment = RouteSegment(
                block_number=current_block,
                suggested_speed=0.0,
                authority=0,
                estimated_time=0.0,
                conflicts=[]
            )
            return CalculatedRoute(
                train_id=train.trainID,
                line=line,
                origin_block=current_block,
                destination_block=destination_block,
                segments=[segment],
                total_time=0.0,
                total_distance=0.0,
                safety_score=1.0,
                route_type=RouteType.SHORTEST_DISTANCE,
                timestamp=time.time(),
                conflicts_detected=[]
            )
        
        # Calculate route segments
        segments = []
        total_distance = 0.0
        total_time = 0.0
        conflicts_detected = []
        
        # Generate block sequence
        start = min(current_block, destination_block)
        end = max(current_block, destination_block)
        route_blocks = list(range(start, end + 1))
        
        if current_block > destination_block:
            route_blocks.reverse()
            
        for i, block_num in enumerate(route_blocks):
            # Get block info
            block = self._get_block_info(line, block_num)
            if not block:
                # Create minimal block info
                block = type('Block', (), {
                    'speedLimit': 50,
                    'length': 100,
                    'blockID': block_num
                })()
            
            # Calculate suggested speed
            suggested_speed = getattr(block, 'speedLimit', 50)
            
            # Check for conflicts
            block_conflicts = self._check_block_conflicts(train.trainID, block_num, suggested_speed)
            if block_conflicts:
                conflicts_detected.extend(block_conflicts)
                suggested_speed = min(suggested_speed, 30.0)
                
            # Check maintenance
            if self._is_block_closed_for_maintenance(line, block_num):
                suggested_speed = 0.0
                
            # Calculate authority
            authority = self._calculate_safe_authority(train, route_blocks[i:], block_conflicts)
            
            # Calculate time
            if suggested_speed > 0:
                speed_ms = suggested_speed * 1000 / 3600
                estimated_time = getattr(block, 'length', 100) / speed_ms
                if self._is_station_block(line, block_num):
                    estimated_time += 60  # Station stop
            else:
                estimated_time = float('inf')
                
            segment = RouteSegment(
                block_number=block_num,
                suggested_speed=suggested_speed,
                authority=authority,
                estimated_time=estimated_time,
                conflicts=block_conflicts
            )
            
            segments.append(segment)
            total_distance += getattr(block, 'length', 100)
            total_time += estimated_time
            
        # Calculate safety score
        safety_score = max(0.0, 1.0 - (len(conflicts_detected) * 0.2))
        
        return CalculatedRoute(
            train_id=train.trainID,
            line=line,
            origin_block=current_block,
            destination_block=destination_block,
            segments=segments,
            total_time=total_time,
            total_distance=total_distance,
            safety_score=safety_score,
            route_type=RouteType.SHORTEST_DISTANCE,
            timestamp=time.time(),
            conflicts_detected=list(set(conflicts_detected))
        )
    
    def _calculate_fastest_route(self, train, destination_block: int, priority: RoutePriority) -> Optional[CalculatedRoute]:
        """Calculate fastest time route (from routing_engine)"""
        # Start with shortest route
        base_route = self._calculate_shortest_route(train, destination_block, priority)
        if not base_route:
            return None
            
        # Optimize speeds for minimum travel time
        optimized_segments = []
        for segment in base_route.segments:
            block = self._get_block_info(train.line, segment.block_number)
            if not block:
                optimized_segments.append(segment)
                continue
                
            # Use maximum safe speed
            max_speed = getattr(block, 'speedLimit', 50)
            if segment.conflicts:
                max_speed = min(max_speed, 40.0)
                
            # Recalculate time
            if max_speed > 0:
                speed_ms = max_speed * 1000 / 3600
                estimated_time = getattr(block, 'length', 100) / speed_ms
                if self._is_station_block(train.line, segment.block_number):
                    estimated_time += 60
            else:
                estimated_time = float('inf')
                
            optimized_segment = RouteSegment(
                block_number=segment.block_number,
                suggested_speed=max_speed,
                authority=segment.authority,
                estimated_time=estimated_time,
                conflicts=segment.conflicts
            )
            optimized_segments.append(optimized_segment)
            
        # Recalculate total time
        total_time = sum(seg.estimated_time for seg in optimized_segments if seg.estimated_time != float('inf'))
        
        return CalculatedRoute(
            train_id=train.trainID,
            line=train.line,
            origin_block=base_route.origin_block,
            destination_block=base_route.destination_block,
            segments=optimized_segments,
            total_time=total_time,
            total_distance=base_route.total_distance,
            safety_score=base_route.safety_score,
            route_type=RouteType.FASTEST_TIME,
            timestamp=time.time(),
            conflicts_detected=base_route.conflicts_detected
        )
    
    def _calculate_safest_route(self, train, destination_block: int, priority: RoutePriority) -> Optional[CalculatedRoute]:
        """Calculate safest route with maximum collision avoidance (from routing_engine)"""
        # Start with shortest route
        base_route = self._calculate_shortest_route(train, destination_block, priority)
        if not base_route:
            return None
            
        # Optimize for safety
        safe_segments = []
        total_time = 0.0
        
        for segment in base_route.segments:
            block = self._get_block_info(train.line, segment.block_number)
            if not block:
                safe_segments.append(segment)
                continue
                
            # Conservative speed for safety
            base_speed = getattr(block, 'speedLimit', 50) * 0.8
            
            # Further reduce for conflicts
            if segment.conflicts:
                safe_speed = base_speed * 0.5
            else:
                safe_speed = base_speed
                
            # Increase authority for safety
            safe_authority = min(segment.authority + self.safety_buffer_blocks, 10)
            
            # Calculate time
            if safe_speed > 0:
                speed_ms = safe_speed * 1000 / 3600
                estimated_time = getattr(block, 'length', 100) / speed_ms
                if self._is_station_block(train.line, segment.block_number):
                    estimated_time += 60
            else:
                estimated_time = float('inf')
                
            total_time += estimated_time
            
            safe_segment = RouteSegment(
                block_number=segment.block_number,
                suggested_speed=safe_speed,
                authority=safe_authority,
                estimated_time=estimated_time,
                conflicts=segment.conflicts,
                maintenance_risk=False
            )
            safe_segments.append(safe_segment)
            
        # Improved safety score for conservative approach
        safety_score = min(1.0, base_route.safety_score + 0.2)
        
        return CalculatedRoute(
            train_id=train.trainID,
            line=train.line,
            origin_block=base_route.origin_block,
            destination_block=base_route.destination_block,
            segments=safe_segments,
            total_time=total_time,
            total_distance=base_route.total_distance,
            safety_score=safety_score,
            route_type=RouteType.SAFEST_PATH,
            timestamp=time.time(),
            conflicts_detected=base_route.conflicts_detected
        )
    
    def _calculate_maintenance_aware_route(self, train, destination_block: int, priority: RoutePriority) -> Optional[CalculatedRoute]:
        """Calculate route avoiding maintenance areas (from routing_engine)"""
        # Get maintenance closures
        maintenance_blocks = self._get_maintenance_blocks(train.line)
        
        # Try to find route avoiding maintenance
        # For now, use safest route and mark maintenance risks
        route = self._calculate_safest_route(train, destination_block, priority)
        if not route:
            return None
            
        # Mark segments with maintenance risk
        for segment in route.segments:
            if segment.block_number in maintenance_blocks:
                segment.maintenance_risk = True
                segment.suggested_speed = min(segment.suggested_speed, 20.0)
                
        route.route_type = RouteType.MAINTENANCE_AWARE
        return route
    
    def _get_block_info(self, line: str, block_num: int):
        """Get block information"""
        if hasattr(self, 'ctc_system') and self.ctc_system:
            return self.ctc_system.get_block_by_line(line, block_num)
        return None
    
    def _check_block_conflicts(self, train_id: str, block_num: int, speed: float) -> List[str]:
        """Check for conflicts with other trains at block"""
        conflicts = []
        if hasattr(self, 'ctc_system') and self.ctc_system:
            # Check all other trains
            for other_id, other_train in self.ctc_system.get_all_trains().items():
                if other_id != train_id:
                    # Simple conflict check - same block or adjacent
                    other_block = getattr(other_train, 'currentBlock', None)
                    if other_block:
                        other_block_num = other_block.blockID if hasattr(other_block, 'blockID') else other_block
                        if abs(other_block_num - block_num) <= self.safety_buffer_blocks:
                            conflicts.append(other_id)
        return conflicts
    
    def _is_block_closed_for_maintenance(self, line: str, block_num: int) -> bool:
        """Check if block is closed for maintenance"""
        if hasattr(self, 'ctc_system') and self.ctc_system:
            return self.ctc_system.is_block_closed(line, block_num)
        return False
    
    def _is_station_block(self, line: str, block_num: int) -> bool:
        """Check if block has a station"""
        block = self._get_block_info(line, block_num)
        if block and hasattr(block, 'station'):
            return block.station is not None
        return False
    
    def _calculate_safe_authority(self, train, remaining_blocks: List[int], conflicts: List[str]) -> int:
        """Calculate safe authority based on track ahead"""
        if conflicts:
            return min(1, len(remaining_blocks))  # Minimal authority with conflicts
        return min(self.safety_buffer_blocks + 2, len(remaining_blocks))
    
    def _get_maintenance_blocks(self, line: str) -> Set[int]:
        """Get all blocks under maintenance for a line"""
        if hasattr(self, 'ctc_system') and self.ctc_system:
            closures = self.ctc_system.get_maintenance_closures()
            return set(closures.get(line, []))
        return set()
    
    def _shortest_path_algorithm(self, start_id: int, end_id: int, avoid_blocks: Set[int]) -> List[int]:
        """Simple shortest path algorithm"""
        # Simplified implementation - would use Dijkstra's algorithm
        if start_id == end_id:
            return [start_id]
        
        path = []
        current = start_id
        
        while current != end_id and len(path) < 100:  # Prevent infinite loops
            path.append(current)
            
            # Simple progression
            if current < end_id:
                next_block = current + 1
            else:
                next_block = current - 1
            
            # Avoid blocked blocks
            if next_block in avoid_blocks:
                # Try alternative (simplified)
                if current < end_id:
                    next_block = current + 2
                else:
                    next_block = current - 2
                
                if next_block in avoid_blocks:
                    break  # No route possible
            
            current = next_block
        
        path.append(end_id)
        return path if current == end_id else []
    
    def _fastest_route_algorithm(self, start_id: int, end_id: int, avoid_blocks: Set[int]) -> List[int]:
        """Algorithm optimizing for travel time"""
        # Similar to shortest path but considers speed limits
        return self._shortest_path_algorithm(start_id, end_id, avoid_blocks)
    
    def _least_traffic_algorithm(self, start_id: int, end_id: int, avoid_blocks: Set[int]) -> List[int]:
        """Algorithm avoiding high-traffic areas"""
        # Would consider current train density
        return self._shortest_path_algorithm(start_id, end_id, avoid_blocks)
    
    def _build_track_graph(self):
        """Build track connectivity graph from track reader"""
        if not self.track_reader:
            return
        
        # This would build a proper graph representation
        # For now, simple adjacency representation
        self.track_graph = {}
    
    def _optimize_route(self, route: Route) -> Route:
        """Apply optimization algorithms to route"""
        # For now, return original route
        # Would implement optimization logic here
        return route
    
    def _route_still_valid(self, route: Route) -> bool:
        """Check if cached route is still valid"""
        # Check if blocks are still operational
        for block in route.blockSequence:
            if not block.block_operational():
                return False
        return True
    
    def _clone_route(self, original: Route, new_arrival_time: datetime) -> Route:
        """Create a copy of route with new timing"""
        new_route = Route()
        new_route.startBlock = original.startBlock
        new_route.endBlock = original.endBlock
        new_route.blockSequence = original.blockSequence.copy()
        new_route.scheduledArrival = new_arrival_time
        new_route.create_route(original.startBlock, original.endBlock, new_arrival_time)
        return new_route
    
    def _create_route_from_path(self, path: List[int], start: Block, end: Block) -> Optional[Route]:
        """Create Route object from block ID path"""
        # Would create proper Block objects from path
        route = Route()
        route.startBlock = start
        route.endBlock = end
        # Simplified - would populate blockSequence properly
        return route
    
    def _calculate_travel_time(self, blocks: List[Block], route: Route) -> float:
        """Calculate travel time for block sequence"""
        total_time = 0.0
        for block in blocks:
            # Simple calculation - would use actual speed profiles
            if block.speedLimit > 0:
                block_time = (block.length / 1000.0) / (block.speedLimit * 0.6) * 3600
                total_time += block_time
        return total_time
    
    def _calculate_minimum_travel_time(self, route: Route) -> float:
        """Calculate minimum possible travel time"""
        return self._calculate_travel_time(route.blockSequence, route)
    
    def _has_route_conflicts(self, route: Route) -> bool:
        """Check if route conflicts with existing routes"""
        # Check timing conflicts with other routes
        for active_route in self.activeRoutes:
            if self._routes_conflict(route, active_route):
                return True
        return False
    
    def _routes_conflict(self, route1: Route, route2: Route) -> bool:
        """Check if two routes conflict"""
        # Check if routes share blocks at overlapping times
        # Simplified implementation
        shared_blocks = set(b.blockID for b in route1.blockSequence) & set(b.blockID for b in route2.blockSequence)
        return len(shared_blocks) > 0
    
    def _is_block_available(self, block_id: int, time: datetime) -> bool:
        """Check if block is available for reservation at specific time"""
        if block_id not in self.block_reservations:
            return True
        
        # Check time conflicts with existing reservations
        # Simplified - would check actual timing overlaps
        return len(self.block_reservations[block_id]) < 1  # Only one train per block
    
    def _rollback_reservations(self, reserved_blocks: List[int], route: Route):
        """Rollback block reservations"""
        for block_id in reserved_blocks:
            if block_id in self.block_reservations and route in self.block_reservations[block_id]:
                self.block_reservations[block_id].remove(route)
    
    def _cleanup_expired_routes(self):
        """Remove expired routes from active list"""
        current_time = datetime.now()
        expired_routes = []
        
        for route in self.activeRoutes:
            if route.actualArrival or (route.scheduledArrival and route.scheduledArrival < current_time - timedelta(hours=1)):
                expired_routes.append(route)
        
        for route in expired_routes:
            self.release_route(route)
    
    def _detect_route_conflicts(self):
        """Detect conflicts between active routes"""
        self.route_conflicts = []
        
        for i, route1 in enumerate(self.activeRoutes):
            for route2 in self.activeRoutes[i+1:]:
                if self._routes_conflict(route1, route2):
                    self.route_conflicts.append((route1, route2))
    
    def _update_block_reservations(self):
        """Update block reservation status"""
        # Clean up expired reservations
        current_time = datetime.now()
        
        for block_id, routes in list(self.block_reservations.items()):
            active_routes = [r for r in routes if r.isActive or 
                           (r.scheduledArrival and r.scheduledArrival > current_time)]
            
            if active_routes:
                self.block_reservations[block_id] = active_routes
            else:
                del self.block_reservations[block_id]
    
    def _optimize_speed_profile(self, route: Route, target_time: datetime):
        """Optimize speed profile for target arrival time"""
        # Would implement speed optimization logic
        pass
    
    # Time-based routing methods (from time_based_routing)
    
    def create_schedule(self, train_id: str, schedule_points: List[SchedulePoint],
                       service_type: str = "regular", 
                       priority: SchedulePriority = SchedulePriority.NORMAL) -> TrainSchedule:
        """
        Create a new schedule for a train (from time_based_routing)
        
        Args:
            train_id: ID of train to schedule
            schedule_points: List of scheduled points with timing requirements
            service_type: Type of service (regular, express, local)
            priority: Schedule priority level
            
        Returns:
            TrainSchedule object
        """
        if not hasattr(self, 'ctc_system') or not self.ctc_system:
            raise ValueError("No CTC system reference")
            
        train = self.ctc_system.get_train(train_id)
        if not train:
            raise ValueError(f"Train {train_id} not found")
            
        # Set train_id for each schedule point
        for point in schedule_points:
            point.train_id = train_id
            
        schedule = TrainSchedule(
            train_id=train_id,
            line=train.line,
            schedule_points=sorted(schedule_points, key=lambda p: p.block_number),
            service_type=service_type,
            priority=priority
        )
        
        # Store schedule
        self.active_schedules[train_id] = schedule
        
        # Index schedule points by block for quick lookup
        for point in schedule_points:
            key = (train.line, point.block_number)
            if key not in self.schedule_points_by_block:
                self.schedule_points_by_block[key] = []
            self.schedule_points_by_block[key].append(point)
            
        self.schedules_created += 1
        logger.info(f"Created schedule for train {train_id} with {len(schedule_points)} points")
        return schedule
    
    def calculate_timed_route(self, train_id: str, destination_block: int,
                             target_arrival_time: Optional[datetime] = None,
                             route_type: RouteType = RouteType.SAFEST_PATH) -> Optional[TimedRoute]:
        """
        Calculate a route with detailed timing to meet schedule requirements (from time_based_routing)
        
        Args:
            train_id: ID of train to route
            destination_block: Target block number
            target_arrival_time: Desired arrival time (None for ASAP)
            route_type: Type of route optimization
            
        Returns:
            TimedRoute object with timing details
        """
        # Get base route
        base_route = self.calculate_route(train_id, destination_block, route_type, scheduled_arrival=target_arrival_time)
        if not base_route:
            return None
            
        # Get train schedule if available
        schedule = self.active_schedules.get(train_id)
        
        # Calculate timing for each segment
        timed_segments = self._calculate_segment_timing(base_route, schedule, target_arrival_time)
        
        # Calculate schedule adherence metrics
        adherence_score, delay, missed_points = self._calculate_schedule_adherence(timed_segments, schedule)
        
        timed_route = TimedRoute(
            base_route=base_route,
            schedule=schedule,
            timed_segments=timed_segments,
            schedule_adherence_score=adherence_score,
            total_delay_seconds=delay,
            critical_points_missed=missed_points
        )
        
        # Generate alternative routes if schedule adherence is poor
        if adherence_score < 0.7:
            alternatives = self._generate_alternative_timed_routes(train_id, destination_block, target_arrival_time)
            timed_route.alternative_routes = alternatives
            
        return timed_route
    
    def _calculate_segment_timing(self, route: CalculatedRoute, 
                                 schedule: Optional[TrainSchedule],
                                 target_arrival: Optional[datetime]) -> List[Tuple[RouteSegment, datetime, datetime]]:
        """Calculate arrival and departure times for each route segment"""
        timed_segments = []
        current_time = datetime.now()
        
        for i, segment in enumerate(route.segments):
            # Calculate arrival time at this segment
            if i == 0:
                arrival_time = current_time
            else:
                prev_departure = timed_segments[i-1][2]
                travel_time = timedelta(seconds=segment.estimated_time)
                arrival_time = prev_departure + travel_time
                
            # Calculate departure time
            departure_time = self._calculate_departure_time(segment, arrival_time, schedule)
            
            timed_segments.append((segment, arrival_time, departure_time))
            
        # Adjust timing if target arrival time is specified
        if target_arrival and timed_segments:
            final_arrival = timed_segments[-1][1]
            time_difference = target_arrival - final_arrival
            
            # Adjust all times to meet target
            adjusted_segments = []
            for segment, arrival, departure in timed_segments:
                adjusted_arrival = arrival + time_difference
                adjusted_departure = departure + time_difference
                adjusted_segments.append((segment, adjusted_arrival, adjusted_departure))
            timed_segments = adjusted_segments
            
        return timed_segments
    
    def _calculate_departure_time(self, segment: RouteSegment, 
                                 arrival_time: datetime,
                                 schedule: Optional[TrainSchedule]) -> datetime:
        """Calculate departure time from a segment considering dwell requirements"""
        
        # Check if this block has a scheduled stop
        if schedule:
            schedule_point = schedule.get_schedule_point_at_block(segment.block_number)
            if schedule_point:
                # This is a scheduled stop
                min_dwell = timedelta(seconds=schedule_point.minimum_dwell_seconds)
                max_dwell = timedelta(seconds=schedule_point.maximum_dwell_seconds)
                
                # Use scheduled departure if available
                if schedule_point.scheduled_departure:
                    scheduled_departure = schedule_point.scheduled_departure
                    # Ensure minimum dwell time
                    earliest_departure = arrival_time + min_dwell
                    return max(scheduled_departure, earliest_departure)
                else:
                    # Use minimum dwell time
                    return arrival_time + min_dwell
                    
        # Check if this block has a station (default dwell)
        if self._is_station_block("Blue", segment.block_number):  # Simplified line determination
            dwell_time = timedelta(seconds=self.station_dwell_default)
            return arrival_time + dwell_time
        else:
            # No stop required - immediate departure
            return arrival_time
    
    def _calculate_schedule_adherence(self, timed_segments: List[Tuple[RouteSegment, datetime, datetime]],
                                    schedule: Optional[TrainSchedule]) -> Tuple[float, float, int]:
        """Calculate schedule adherence metrics"""
        if not schedule:
            return 1.0, 0.0, 0
            
        total_delay = 0.0
        critical_missed = 0
        points_checked = 0
        
        for segment, arrival_time, departure_time in timed_segments:
            schedule_point = schedule.get_schedule_point_at_block(segment.block_number)
            if not schedule_point:
                continue
                
            points_checked += 1
            
            # Calculate delay for arrival
            if schedule_point.scheduled_arrival:
                delay_seconds = (arrival_time - schedule_point.scheduled_arrival).total_seconds()
                total_delay += max(0, delay_seconds)
                
                # Check if critical point was missed
                if (delay_seconds > 300 and 
                    schedule_point.priority in [SchedulePriority.CRITICAL, SchedulePriority.HIGH]):
                    critical_missed += 1
                    
        # Calculate adherence score
        if points_checked == 0:
            adherence_score = 1.0
        else:
            avg_delay = total_delay / points_checked
            delay_penalty = min(1.0, avg_delay / 600.0)
            critical_penalty = critical_missed * 0.3
            adherence_score = max(0.0, 1.0 - delay_penalty - critical_penalty)
            
        return adherence_score, total_delay, critical_missed
    
    def _generate_alternative_timed_routes(self, train_id: str, destination_block: int,
                                         target_arrival: Optional[datetime]) -> List[TimedRoute]:
        """Generate alternative routes when schedule adherence is poor"""
        alternatives = []
        
        # Try different route types
        for route_type in [RouteType.FASTEST_TIME, RouteType.SHORTEST_DISTANCE]:
            alt_route = self.calculate_timed_route(train_id, destination_block, target_arrival, route_type)
            if alt_route and alt_route.schedule_adherence_score > 0.7:
                alternatives.append(alt_route)
                
        return alternatives
    
    def optimize_schedule_for_transfers(self, hub_block: int, 
                                      connecting_trains: List[str],
                                      transfer_window: float = None) -> Dict[str, datetime]:
        """
        Optimize arrival times at a hub station to facilitate transfers (from time_based_routing)
        
        Args:
            hub_block: Block number of transfer hub
            connecting_trains: List of train IDs that connect at this hub
            transfer_window: Maximum time window for transfers (seconds)
            
        Returns:
            Dictionary of optimized arrival times for each train
        """
        if transfer_window is None:
            transfer_window = self.transfer_window_seconds
            
        optimized_times = {}
        
        # Get current scheduled arrival times
        scheduled_arrivals = {}
        for train_id in connecting_trains:
            schedule = self.active_schedules.get(train_id)
            if schedule:
                point = schedule.get_schedule_point_at_block(hub_block)
                if point and point.scheduled_arrival:
                    scheduled_arrivals[train_id] = point.scheduled_arrival
                    
        if len(scheduled_arrivals) < 2:
            return optimized_times
            
        # Find optimal time window that minimizes total delay
        earliest_arrival = min(scheduled_arrivals.values())
        latest_arrival = max(scheduled_arrivals.values())
        
        # If all trains arrive within transfer window, no optimization needed
        if (latest_arrival - earliest_arrival).total_seconds() <= transfer_window:
            return scheduled_arrivals
            
        # Calculate optimal arrival time
        optimal_time = earliest_arrival + (latest_arrival - earliest_arrival) / 2
        
        # Adjust each train's arrival to be within transfer window
        half_window = timedelta(seconds=transfer_window / 2)
        
        for train_id, original_time in scheduled_arrivals.items():
            if abs((original_time - optimal_time).total_seconds()) <= transfer_window / 2:
                optimized_times[train_id] = original_time
            else:
                if original_time < optimal_time:
                    optimized_times[train_id] = optimal_time - half_window
                else:
                    optimized_times[train_id] = optimal_time + half_window
                    
        return optimized_times
    
    def check_schedule_conflicts(self, train_id: str) -> List[Dict]:
        """Check for conflicts with scheduled maintenance or other trains"""
        conflicts = []
        schedule = self.active_schedules.get(train_id)
        
        if not schedule or not hasattr(self, 'ctc_system') or not self.ctc_system:
            return conflicts
            
        train = self.ctc_system.get_train(train_id)
        if not train:
            return conflicts
            
        # Check each schedule point for conflicts
        for point in schedule.schedule_points:
            # Check maintenance conflicts
            if self.ctc_system.is_block_closed(train.line, point.block_number):
                conflicts.append({
                    "type": "maintenance_conflict",
                    "block": point.block_number,
                    "scheduled_time": point.scheduled_arrival,
                    "severity": "HIGH",
                    "description": f"Scheduled arrival conflicts with maintenance closure"
                })
                
            # Check other train conflicts at same time/location
            block_key = (train.line, point.block_number)
            other_points = self.schedule_points_by_block.get(block_key, [])
            
            for other_point in other_points:
                if other_point.train_id == train_id:
                    continue
                    
                # Check if arrival times are too close
                time_diff = abs((point.scheduled_arrival - other_point.scheduled_arrival).total_seconds())
                if time_diff < 120:
                    conflicts.append({
                        "type": "schedule_conflict",
                        "block": point.block_number,
                        "scheduled_time": point.scheduled_arrival,
                        "conflicting_train": other_point.train_id,
                        "time_difference": time_diff,
                        "severity": "MEDIUM",
                        "description": f"Close scheduled arrival with Train {other_point.train_id}"
                    })
                    
        return conflicts
    
    def update_schedule_progress(self, train_id: str, current_block: int) -> Dict:
        """Update schedule progress and performance metrics"""
        schedule = self.active_schedules.get(train_id)
        if not schedule:
            return {}
            
        current_time = datetime.now()
        progress = {
            "train_id": train_id,
            "current_block": current_block,
            "current_time": current_time,
            "schedule_status": "unknown",
            "next_scheduled_stop": None,
            "estimated_delay": 0.0,
            "on_time_percentage": 0.0
        }
        
        # Find current position in schedule
        current_point = schedule.get_schedule_point_at_block(current_block)
        if current_point:
            # At a scheduled point
            if current_point.scheduled_arrival:
                delay = (current_time - current_point.scheduled_arrival).total_seconds()
                progress["estimated_delay"] = delay
                
                if delay <= 60:
                    progress["schedule_status"] = "on_time"
                    self.on_time_arrivals += 1
                elif delay <= 300:
                    progress["schedule_status"] = "slightly_delayed"
                    self.delayed_arrivals += 1
                else:
                    progress["schedule_status"] = "delayed"
                    self.delayed_arrivals += 1
        else:
            # Between scheduled points
            next_point = schedule.get_next_schedule_point(current_block)
            if next_point:
                progress["next_scheduled_stop"] = {
                    "block": next_point.block_number,
                    "scheduled_arrival": next_point.scheduled_arrival,
                    "constraint_type": next_point.constraint_type.value
                }
                
        # Calculate overall on-time percentage
        total_arrivals = self.on_time_arrivals + self.delayed_arrivals + self.early_arrivals
        if total_arrivals > 0:
            progress["on_time_percentage"] = (self.on_time_arrivals / total_arrivals) * 100
            
        return progress
    
    def get_schedule_statistics(self) -> Dict:
        """Get schedule performance statistics"""
        total_arrivals = self.on_time_arrivals + self.delayed_arrivals + self.early_arrivals
        
        stats = self.get_route_statistics()
        stats.update({
            "schedules_created": self.schedules_created,
            "active_schedules": len(self.active_schedules),
            "total_arrivals": total_arrivals,
            "on_time_arrivals": self.on_time_arrivals,
            "delayed_arrivals": self.delayed_arrivals,
            "early_arrivals": self.early_arrivals,
            "on_time_percentage": (self.on_time_arrivals / max(1, total_arrivals)) * 100
        })
        
        return stats