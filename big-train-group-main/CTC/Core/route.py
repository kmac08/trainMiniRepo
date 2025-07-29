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

# Set up logging
logger = logging.getLogger(__name__)


class Route:
    """
    Route class implementing UML interface
    Represents a train route with all associated control information
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
        self.createdTime = datetime.now()
        self.lastUpdate = datetime.now()
        
        # Safety and operational data
        self.totalDistance = 0.0       # Total route distance in meters
        self.maxSpeed = 0              # Maximum speed for route
        self.grade_profile = []        # Grade information for each block
        self.station_stops = []        # List of station stops
        
        logger.debug(f"New route initialized")
    
    # Methods from UML
    
    def create_route(self, start, end, arrivalTime: datetime) -> None:
        """
        Create route from start to end
        
        Args:
            start: Block object for route start
            end: Block object for route destination  
            arrivalTime: Desired arrival time
        """
        self.startBlock = start
        self.endBlock = end
        self.scheduledArrival = arrivalTime
        
        # Generate unique route ID
        self.routeID = f"route_{start.blockID}_{end.blockID}_{int(datetime.now().timestamp())}"
        
        # Calculate block sequence (will be enhanced with full routing logic)
        self.blockSequence = self._calculate_block_sequence(start, end)
        
        # Calculate travel time and other parameters
        self._calculate_route_parameters()
        
        # Initialize authority and speed sequences
        self.calculate_authority_speed()
        
        self.lastUpdate = datetime.now()
        logger.info(f"Route {self.routeID} created: Block {start.blockID} to Block {end.blockID}")
    
    def validate_route(self) -> bool:
        """
        Validate route is traversable
        
        Returns:
            True if route is valid and safe
        """
        if not self.blockSequence:
            logger.warning(f"Route {self.routeID} validation failed: empty block sequence")
            return False
        
        if not self.startBlock or not self.endBlock:
            logger.warning(f"Route {self.routeID} validation failed: missing start/end blocks")
            return False
        
        # Check block connectivity
        for i in range(len(self.blockSequence) - 1):
            current_block = self.blockSequence[i]
            next_block = self.blockSequence[i + 1]
            
            if not self._blocks_connected(current_block, next_block):
                logger.warning(f"Route {self.routeID} validation failed: blocks {current_block.blockID} and {next_block.blockID} not connected")
                return False
        
        # Check for operational blocks
        for block in self.blockSequence:
            if not block.block_operational():
                logger.warning(f"Route {self.routeID} validation failed: block {block.blockID} not operational")
                return False
        
        # Check timing feasibility
        if not self._validate_timing():
            logger.warning(f"Route {self.routeID} validation failed: timing not feasible")
            return False
        
        logger.info(f"Route {self.routeID} validated successfully")
        return True
    
    def get_next_block(self):
        """
        Get next block in sequence
        
        Returns:
            Next Block object in route, or None if at end
        """
        if self.currentBlockIndex < len(self.blockSequence) - 1:
            return self.blockSequence[self.currentBlockIndex + 1]
        return None
    
    def update_location(self, newBlock) -> None:
        """
        Update train position in route
        
        Args:
            newBlock: Block object where train is now located
        """
        # Find block in sequence
        new_block_id = newBlock.blockID if hasattr(newBlock, 'blockID') else newBlock
        
        for i, block in enumerate(self.blockSequence):
            if block.blockID == new_block_id:
                old_index = self.currentBlockIndex
                self.currentBlockIndex = i
                self.lastUpdate = datetime.now()
                
                # Update actual departure time if this is the first move
                if old_index == 0 and i > 0 and not self.actualDeparture:
                    self.actualDeparture = datetime.now()
                
                # Update actual arrival time if reached destination
                if i == len(self.blockSequence) - 1 and not self.actualArrival:
                    self.actualArrival = datetime.now()
                
                logger.debug(f"Route {self.routeID} position updated: block index {old_index} -> {i}")
                return
        
        logger.warning(f"Route {self.routeID}: block {new_block_id} not found in sequence")
    
    def get_block_sequence(self) -> List:
        """
        Get full block sequence
        
        Returns:
            List of Block objects in route order
        """
        return self.blockSequence.copy()
    
    # Additional methods needed for implementation
    
    def calculate_authority_speed(self) -> None:
        """
        Calculate authority and speed for each block in route
        Updates authoritySequence and speedSequence based on current conditions
        """
        self.authoritySequence = []
        self.speedSequence = []
        
        for i, block in enumerate(self.blockSequence):
            # Calculate authority (0 = no authority, 1 = full authority)
            authority = self._calculate_block_authority(block, i)
            self.authoritySequence.append(authority)
            
            # Calculate suggested speed (0=stop, 1=1/3, 2=2/3, 3=full)
            speed = self._calculate_block_speed(block, i)
            self.speedSequence.append(speed)
        
        logger.debug(f"Route {self.routeID} authority/speed sequences updated")
    
    def update_for_conditions(self, track_conditions: dict) -> None:
        """
        Update authority/speed based on current conditions
        
        Args:
            track_conditions: Dictionary of current track conditions
        """
        # Store track conditions
        self.track_conditions = track_conditions
        
        # Recalculate authority and speed
        self.calculate_authority_speed()
        
        # Update estimated travel time if needed
        self._recalculate_travel_time()
        
        self.lastUpdate = datetime.now()
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
        
        return datetime.now() + timedelta(seconds=remaining_time)
    
    def add_station_stop(self, block, stop_duration: float) -> None:
        """
        Add station stop to route
        
        Args:
            block: Block object with station
            stop_duration: Stop duration in seconds
        """
        if hasattr(block, 'station') and block.station:
            stop_info = {
                'block': block,
                'station_name': block.station.name,
                'duration': stop_duration,
                'scheduled_time': None,
                'actual_arrival': None,
                'actual_departure': None
            }
            self.station_stops.append(stop_info)
            logger.info(f"Station stop added to route {self.routeID}: {block.station.name}")
    
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
    
    def _calculate_block_sequence(self, start_block, end_block) -> List:
        """
        Calculate sequence of blocks from start to end
        This is a simplified implementation - full routing would use track topology
        """
        sequence = []
        
        # Simple linear progression for now
        start_id = start_block.blockID
        end_id = end_block.blockID
        
        if start_id < end_id:
            # Forward direction
            current_id = start_id
            while current_id <= end_id:
                # Create placeholder block (would use actual Block objects)
                block = type('Block', (), {'blockID': current_id, 'length': 100, 'speedLimit': 50})()
                sequence.append(block)
                current_id += 1
        else:
            # Backward direction
            current_id = start_id
            while current_id >= end_id:
                block = type('Block', (), {'blockID': current_id, 'length': 100, 'speedLimit': 50})()
                sequence.append(block)
                current_id -= 1
        
        return sequence
    
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
    
    def _calculate_block_authority(self, block, block_index: int) -> int:
        """Calculate authority for specific block"""
        # Check basic operability
        if not hasattr(block, 'block_operational') or not block.block_operational():
            return 0
        
        # Check if block is occupied
        if hasattr(block, 'occupied') and block.occupied:
            return 0
        
        # Check for maintenance
        if hasattr(block, 'maintenance_mode') and block.maintenance_mode:
            return 0
        
        # Default to full authority
        return 1
    
    def _calculate_block_speed(self, block, block_index: int) -> int:
        """Calculate speed command for specific block"""
        # No authority = stop
        if self.authoritySequence and block_index < len(self.authoritySequence):
            if self.authoritySequence[block_index] == 0:
                return 0
        
        # Check for station stops
        for stop in self.station_stops:
            if stop['block'].blockID == block.blockID:
                return 1  # Approach speed for station
        
        # Check grade
        if hasattr(block, 'grade') and abs(block.grade) > 5.0:
            return 2  # Reduced speed for steep grade
        
        # Check if approaching end of route
        if block_index >= len(self.blockSequence) - 2:
            return 2  # Reduced speed approaching destination
        
        # Default to full speed
        return 3
    
    def _blocks_connected(self, block1, block2) -> bool:
        """Check if two blocks are connected"""
        # Simplified - just check if block numbers are adjacent
        return abs(block1.blockID - block2.blockID) == 1
    
    def _validate_timing(self) -> bool:
        """Validate route timing is feasible"""
        if not self.scheduledArrival or not self.estimatedTravelTime:
            return True  # No timing constraints
        
        earliest_arrival = datetime.now() + timedelta(seconds=self.estimatedTravelTime)
        return self.scheduledArrival >= earliest_arrival
    
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