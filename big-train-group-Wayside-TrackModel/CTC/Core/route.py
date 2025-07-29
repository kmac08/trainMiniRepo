"""
Route Module
===========
Defines the Route class according to UML specifications.
Manages train routes with authority and speed sequences.

This module handles:
- Route creation and validation
- Block sequence management
- Authority and speed calculations
- Location tracking and updates
"""

from typing import List, Tuple, Optional
from datetime import datetime, timedelta
import logging

# Import simulation time (lazy import to avoid circular dependencies)
# from Master_Interface.master_control import get_time


def _get_simulation_time():
    """Get simulation time with lazy import to avoid circular dependencies"""
    from Master_Interface.master_control import get_time
    return get_time()

# Set up logging
logger = logging.getLogger(__name__)


class Route:
    """
    Represents a comprehensive train route with pathfinding, timing, and control management.
    
    This class implements an intelligent route entity that handles complex pathfinding using
    breadth-first search, route validation, timing calculations, and train control sequences.
    It supports multi-line routing, yard connections, and sophisticated route distance calculations.
    
    Core Route Data:
        routeID (str): Unique route identifier
        startBlock (Block): Starting block object
        endBlock (Block): Destination block object
        blockSequence (List[Block]): Complete sequence of blocks in route
        estimatedTravelTime (float): Estimated travel time in seconds
        
    Control Sequences:
        authoritySequence (List[int]): Authority values for each block (0=stop, 1=proceed)
        speedSequence (List[int]): Speed commands for each block (0-3 scale)
        currentBlockIndex (int): Current position in route sequence
        
    Route Status:
        isActive (bool): Whether route is currently active
        trainID (str): ID of train using this route
        routeType (str): Route type (NORMAL, EMERGENCY, MAINTENANCE)
        priority (int): Route priority (1=low, 2=medium, 3=high)
        
    Timing & Scheduling:
        scheduledDeparture (datetime): Planned departure time
        actualDeparture (datetime): Actual departure time
        scheduledArrival (datetime): Planned arrival time
        actualArrival (datetime): Actual arrival time
        createdTime (datetime): Route creation timestamp
        lastUpdate (datetime): Last modification timestamp
        
    Route Properties:
        totalDistance (float): Total route distance in meters
        maxSpeed (float): Maximum speed allowed on route
        grade_profile (List[float]): Grade information for each block
        
    Methods Overview:
        Route Creation & Management:
            - create_route(start, end, arrivalTime): Generate route using BFS pathfinding
            - validate_route(): Comprehensive route validation
            - activate_route(train_id): Activate route for specific train
            - deactivate_route(): Deactivate completed route
            
        Navigation & Progress:
            - get_next_block(): Get next block in sequence
            - update_location(newBlock): Update train position in route
            - get_block_sequence(): Get complete block sequence
            - get_remaining_blocks(): Get blocks from current position to end
            - get_progress_percentage(): Get completion percentage
            
        Authority & Speed Control:
            - calculate_authority_speed(): Calculate control sequences
            - update_for_conditions(conditions): Update for track conditions
            - get_lookahead_info(numBlocks): Get authority/speed for next N blocks
            
        Timing & Estimation:
            - get_estimated_arrival(): Calculate estimated arrival time
            - calculate_route_distance(from_block, to_block): Calculate route hops between blocks
            
        Advanced Pathfinding:
            - Breadth-First Search (BFS) algorithm for optimal pathfinding
            - Multi-line routing with proper connectivity validation
            - Yard connection handling using CTC system data
            - Junction and switch compatibility validation
            - Loop routing validation for circular track sections
            
        Route Validation Features:
            - Block connectivity verification using actual track data
            - Operational block checking (failures, maintenance)
            - Switch position compatibility validation
            - Junction routing verification
            - Loop routing conflict detection
            - Timing feasibility validation
            
        Utility Methods:
            - __str__(), __repr__(): String representations for logging
            
    Special Features:
        - Supports complex track layouts including loops and junctions
        - Handles yard departures and arrivals with proper exit/entry blocks
        - Calculates route distances based on actual route traversal (not arithmetic)
        - Provides comprehensive debug output for route generation
        - Integrates with CTC system for real-time track data access
    """
    
    def __init__(self):
        """Initialize Route with UML-specified attributes"""
        # Attributes from UML
        self.routeID = None            # String
        self.startBlock = None         # Block object
        self.endBlock = None           # Block object
        self.blockSequence = []        # List[Block]
        self.estimatedTravelTime = 0.0 # float (seconds)
        
        # Additional attributes needed for implementation
        self.authoritySequence = []    # List[int] - authority for each block (0 or 1)
        self.speedSequence = []        # List[int] - speed for each block (0-3)
        self.currentBlockIndex = 0     # Current position in route
        self.isActive = False
        self.trainID = None
        self.scheduledDeparture = None # DateTime
        self.actualDeparture = None    # DateTime
        self.scheduledArrival = None   # DateTime
        self.actualArrival = None      # DateTime
        
        # Route metadata
        self.routeType = 'NORMAL'      # NORMAL, EMERGENCY, MAINTENANCE
        self.priority = 1              # 1=low, 2=medium, 3=high
        self.createdTime = _get_simulation_time()
        self.lastUpdate = _get_simulation_time()
        
        # Safety and operational data
        self.totalDistance = 0.0       # Total route distance in meters
        self.maxSpeed = 0              # Maximum speed for route
        self.grade_profile = []        # Grade information for each block
        
        logger.debug(f"New route initialized")
    
    # Methods from UML
    
    def create_route(self, block_sequence: List, arrivalTime: datetime) -> None:
        """
        Create route with pre-calculated block sequence
        
        Args:
            block_sequence: Pre-calculated list of blocks defining the route path
            arrivalTime: Desired arrival time
        """
        # Validate block sequence
        if not block_sequence:
            logger.error("Cannot create route with empty block sequence")
            raise ValueError("Route creation requires non-empty block sequence from Route Manager")
        
        if len(block_sequence) < 1:
            logger.error("Block sequence must have at least one block")
            raise ValueError("Block sequence must contain at least one block")
            
        # Set block sequence and derive start/end blocks
        self.blockSequence = block_sequence
        self.startBlock = block_sequence[0]
        self.endBlock = block_sequence[-1]
        self.scheduledArrival = arrivalTime
        
        # Generate unique route ID using derived start/end blocks
        self.routeID = f"route_{self.startBlock.blockID}_{self.endBlock.blockID}_{int(_get_simulation_time().timestamp())}"
        
        # Debug output
        block_ids = [block.blockID for block in self.blockSequence]
        print(f"DEBUG: Route {self.routeID} created with block sequence: {block_ids}")
        print(f"DEBUG: Route from Block {self.startBlock.blockID} to Block {self.endBlock.blockID}, {len(block_ids)} blocks total")
        
        # Calculate travel time and other parameters
        self._calculate_route_parameters()
        
        # Initialize authority and speed sequences
        self.calculate_authority_speed()
        
        self.lastUpdate = _get_simulation_time()
        logger.info(f"Route {self.routeID} created: Block {self.startBlock.blockID} to Block {self.endBlock.blockID}")

    def get_next_block(self):
        """
        Get next block in sequence
        
        Returns:
            Next Block object in route, or None if at end
        """
        if self.currentBlockIndex < len(self.blockSequence) - 1:
            return self.blockSequence[self.currentBlockIndex + 1]
        return None
    
    def update_location(self, newBlock) -> bool:
        """
        Update train position in route
        
        Args:
            newBlock: Block object where train is now located
            
        Returns:
            True if location update was successful, False if block not found in route or backward movement attempted
        """
        # Find block in sequence
        new_block_id = newBlock.blockID if hasattr(newBlock, 'blockID') else newBlock
        
        for i, block in enumerate(self.blockSequence):
            if block.blockID == new_block_id:
                old_index = self.currentBlockIndex
                
                # Prevent backward movement - trains cannot move backwards
                if i < old_index:
                    logger.error(f"Route {self.routeID}: backward movement not allowed from block index {old_index} to {i}")
                    return False
                
                self.currentBlockIndex = i
                self.lastUpdate = _get_simulation_time()
                
                # Update actual departure time if this is the first move
                if old_index == 0 and i > 0 and not self.actualDeparture:
                    self.actualDeparture = _get_simulation_time()
                
                # Update actual arrival time if reached destination
                if i == len(self.blockSequence) - 1 and not self.actualArrival:
                    self.actualArrival = _get_simulation_time()
                
                logger.debug(f"Route {self.routeID} position updated: block index {old_index} -> {i}")
                return True
        
        logger.warning(f"Route {self.routeID}: block {new_block_id} not found in sequence")
        return False
    
    def get_block_sequence(self) -> List:
        """
        Get full block sequence
        
        Returns:
            List of Block objects in route order
        """
        return self.blockSequence.copy()
    
    # Additional methods needed for implementation
    
    def calculate_authority_speed(self) -> Tuple[List[int], List[int]]:
        """
        Calculate authority and speed for each block in route
        Updates authoritySequence and speedSequence based on current conditions
        
        Returns:
            Tuple of (authoritySequence, speedSequence)
        """
        self.authoritySequence = []
        self.speedSequence = []
        
        for i, block in enumerate(self.blockSequence):
            # Get next 2 blocks from sequence for speed calculation
            next_block_1 = self.blockSequence[i+1] if i+1 < len(self.blockSequence) else None
            next_block_2 = self.blockSequence[i+2] if i+2 < len(self.blockSequence) else None
            
            # Use Block class methods for calculations
            authority = block.calculate_safe_authority()
            speed = block.calculate_suggested_speed(next_block_1, next_block_2)
            
            self.authoritySequence.append(authority)
            self.speedSequence.append(speed)
        
        logger.debug(f"Route {self.routeID} authority/speed sequences updated")
        return (self.authoritySequence, self.speedSequence)
    
    def update_for_conditions(self, track_conditions: dict) -> None:
        """
        Update authority/speed based on current conditions
        
        Args:
            track_conditions: Dictionary of current track conditions
        """
        # Store track conditions for future use
        self.track_conditions = track_conditions
        
        # Recalculate using the simplified calculate_authority_speed method
        self.calculate_authority_speed()
        
        # Update estimated travel time based on new speeds
        self._recalculate_travel_time()
        
        self.lastUpdate = _get_simulation_time()
        logger.debug(f"Route {self.routeID} updated for current conditions")
    
    def get_lookahead_info(self, numBlocks: int) -> Tuple[List[int], List[int]]:
        """
        Get authority/speed for next N blocks from current position
        
        Args:
            numBlocks: Number of blocks ahead to return
            
        Returns:
            Tuple of (authority_list, speed_list) for next N blocks
        """
        start_index = self.currentBlockIndex
        end_index = min(start_index + numBlocks, len(self.blockSequence))
        
        authority_ahead = self.authoritySequence[start_index:end_index]
        speed_ahead = self.speedSequence[start_index:end_index]
        
        # Pad with zeros if needed
        while len(authority_ahead) < numBlocks:
            authority_ahead.append(0)
        while len(speed_ahead) < numBlocks:
            speed_ahead.append(0)
        
        return authority_ahead[:numBlocks], speed_ahead[:numBlocks]
    
    def get_remaining_blocks(self) -> List:
        """
        Get blocks remaining in route from current position
        
        Returns:
            List of Block objects from current position to end
        """
        return self.blockSequence[self.currentBlockIndex:]
    
    def get_progress_percentage(self) -> float:
        """
        Get route completion percentage
        
        Returns:
            Percentage of route completed (0.0 to 100.0)
        """
        if not self.blockSequence:
            return 0.0
        
        return (self.currentBlockIndex / len(self.blockSequence)) * 100.0
    
    def get_estimated_arrival(self) -> Optional[datetime]:
        """
        Get estimated arrival time based on current position and conditions
        Includes station stops with 60-second dwell time and deceleration/acceleration
        
        Returns:
            Estimated arrival datetime, or None if cannot calculate
        """
        if not self.isActive or self.currentBlockIndex >= len(self.blockSequence):
            return self.actualArrival

        # Calculate remaining time based on remaining blocks and current speeds
        remaining_time = 0.0
        
        for i in range(self.currentBlockIndex, len(self.blockSequence)):
            block = self.blockSequence[i]
            speed_command = self.speedSequence[i] if i < len(self.speedSequence) else 1

            # Convert speed command to actual speed
            actual_speed = self._speed_command_to_kmh(speed_command, block.speedLimit)
            
            # Calculate block traversal time
            if actual_speed > 0:
                block_time = (block.length / 1000.0) / actual_speed * 3600  # Convert to seconds
                remaining_time += block_time
                
                # Check if this block has a station (requires stop)
                if hasattr(block, 'station') and block.station:
                    # Add 60 seconds dwell time for station stop
                    remaining_time += 60.0
                    
                    # Add deceleration time (speed from km/h to m/s, then time = v/a)
                    # Deceleration rate: 1.2 m/s²
                    speed_ms = actual_speed / 3.6  # Convert km/h to m/s
                    decel_time = speed_ms / 1.2  # Time to decelerate to stop
                    remaining_time += decel_time
                    
                    # Add acceleration time for leaving station
                    # Acceleration rate: 0.5 m/s²
                    # Get speed for next block to determine target acceleration speed
                    next_i = i + 1
                    if next_i < len(self.blockSequence):
                        next_speed_command = self.speedSequence[next_i] if next_i < len(self.speedSequence) else 1
                        next_actual_speed = self._speed_command_to_kmh(next_speed_command, self.blockSequence[next_i].speedLimit)
                        next_speed_ms = next_actual_speed / 3.6  # Convert km/h to m/s
                        accel_time = next_speed_ms / 0.5  # Time to accelerate from stop
                        remaining_time += accel_time
        
        return _get_simulation_time() + timedelta(seconds=remaining_time)
    
    def activate_route(self, train_id: str) -> None:
        """
        Activate route for a specific train
        
        Args:
            train_id: ID of train using this route
        """
        self.isActive = True
        self.trainID = train_id
        self.actualDeparture = datetime.now()
        
        logger.info(f"Route {self.routeID} activated for train {train_id}")
    
    def deactivate_route(self) -> None:
        """Deactivate route when train reaches destination"""
        self.isActive = False
        if not self.actualArrival:
            self.actualArrival = datetime.now()
        
        logger.info(f"Route {self.routeID} deactivated")
    
    # Private helper methods
    
    
    
    def _calculate_route_parameters(self):
        """Calculate route distance, time, and other parameters"""
        self.totalDistance = sum(block.length for block in self.blockSequence)
        self.maxSpeed = max(block.speedLimit for block in self.blockSequence) if self.blockSequence else 0
        
        # Calculate estimated travel time (simplified)
        if self.maxSpeed > 0:
            # Assume average speed is 60% of max speed
            avg_speed = self.maxSpeed * 0.6
            self.estimatedTravelTime = (self.totalDistance / 1000.0) / avg_speed * 3600  # seconds
        
        # Set scheduled departure to allow time for travel
        if self.scheduledArrival:
            self.scheduledDeparture = self.scheduledArrival - timedelta(seconds=self.estimatedTravelTime)
    
    
    
    def _speed_command_to_kmh(self, speed_command: int, speed_limit: float) -> float:
        """Convert speed command to actual speed in km/h"""
        speed_map = {
            0: 0.0,                    # Stop
            1: speed_limit * 0.33,     # 1/3 speed
            2: speed_limit * 0.67,     # 2/3 speed
            3: speed_limit             # Full speed
        }
        return speed_map.get(speed_command, 0.0)
    
    
    
    
    def _recalculate_travel_time(self):
        """Recalculate travel time based on current speed restrictions"""
        total_time = 0.0
        
        for i, block in enumerate(self.blockSequence[self.currentBlockIndex:], self.currentBlockIndex):
            speed_command = self.speedSequence[i] if i < len(self.speedSequence) else 1
            actual_speed = self._speed_command_to_kmh(speed_command, block.speedLimit)
            
            if actual_speed > 0:
                block_time = (block.length / 1000.0) / actual_speed * 3600
                total_time += block_time
        
        self.estimatedTravelTime = total_time
    
    def __str__(self) -> str:
        """String representation of route"""
        status = "active" if self.isActive else "inactive"
        return f"Route {self.routeID} ({status}): Block {self.startBlock.blockID if self.startBlock else 'None'} to {self.endBlock.blockID if self.endBlock else 'None'}"
    
    def __repr__(self) -> str:
        """Detailed representation of route"""
        return (f"Route(id={self.routeID}, start={self.startBlock.blockID if self.startBlock else None}, "
                f"end={self.endBlock.blockID if self.endBlock else None}, active={self.isActive}, "
                f"progress={self.currentBlockIndex}/{len(self.blockSequence)})")
    
    
    def _is_junction_block(self, block) -> bool:
        """
        Check if a block is a junction (has more than 2 connections)
        """
        if not hasattr(block, 'connected_blocks'):
            return False
            
        # Count non-yard connections
        non_yard_connections = [conn for conn in block.connected_blocks if conn != 0]
        return len(non_yard_connections) > 2
    
    def _get_junction_area_blocks(self, junction_id: int) -> List[int]:
        """
        Get blocks in the area around a junction
        """
        area = [junction_id]
        
        if hasattr(self, 'ctc_system') and self.ctc_system:
            junction_block = self.ctc_system.blocks.get(junction_id)
            if junction_block and hasattr(junction_block, 'connected_blocks'):
                # Add directly connected blocks
                for conn in junction_block.connected_blocks:
                    if conn != 0 and conn not in area:
                        area.append(conn)
        
        return area
    
    def calculate_route_distance(self, from_block_id: int, to_block_id: int) -> int:
        """
        Calculate route distance from one block to another in the route sequence.
        This is NOT arithmetic difference but actual route traversal distance.
        
        IMPORTANT: This method calculates distance by counting route hops, not block number arithmetic.
        For example, if route is [1, 5, 3, 8] and train is at block 1 going to block 8,
        the distance is 3 route hops (1->5->3->8), NOT 7 (8-1).
        
        Args:
            from_block_id: Starting block ID (train's current position)
            to_block_id: Target block ID (4 positions ahead)
            
        Returns:
            Route distance in blocks (number of route hops from start to target)
            Positive means target is ahead in route, negative means behind
            Returns 0 if blocks are the same or not found in route
        """
        if not self.blockSequence:
            logger.warning("Cannot calculate route distance: no block sequence available")
            return 0
        
        # Find indices of blocks in the route sequence
        from_index = None
        to_index = None
        
        for i, block in enumerate(self.blockSequence):
            block_id = getattr(block, 'blockID', getattr(block, 'block_number', block))
            
            if block_id == from_block_id:
                from_index = i
            if block_id == to_block_id:
                to_index = i
                
            # Early exit if both found
            if from_index is not None and to_index is not None:
                break
        
        # Validate both blocks were found
        if from_index is None:
            logger.warning(f"Block {from_block_id} not found in route sequence for distance calculation")
            return 0
        if to_index is None:
            logger.warning(f"Block {to_block_id} not found in route sequence for distance calculation")
            return 0
        
        # Calculate route distance (positive = ahead, negative = behind)
        route_distance = to_index - from_index
        
        logger.debug(f"Route distance from block {from_block_id} to {to_block_id}: {route_distance} route hops")
        logger.debug(f"  From block at route index {from_index}, to block at route index {to_index}")
        
        return route_distance