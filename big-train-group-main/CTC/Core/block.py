"""
Block Module
===========
Defines the Block class according to UML specifications.
Manages individual track blocks with occupation tracking and switch information.

This module handles:
- Block occupation status
- Switch position management
- Crossing status
- Scheduled occupations and closures
- Authority and speed calculations
"""

from typing import List, Optional
from datetime import datetime
import logging

# Set up logging
logger = logging.getLogger(__name__)


class Block:
    """
    Block class implementing UML interface
    Represents a single track block with all associated infrastructure
    """
    
    def __init__(self, track_block_data):
        """
        Initialize Block with data from Track Reader
        
        Args:
            track_block_data: TrackBlock object from Track_Reader
        """
        # Attributes from UML
        self.blockID = track_block_data.block_number
        self.block_number = track_block_data.block_number  # For UI compatibility
        self.length = track_block_data.length_m
        self.grade = track_block_data.grade_percent
        self.speedLimit = track_block_data.speed_limit_kmh
        self.stationaryStatus = True  # Operational status (True = operational)
        self.switchPosition = False   # Current switch position if applicable
        self.switchPresent = track_block_data.has_switch
        self.crossingPresent = track_block_data.has_crossing
        self.crossingStatus = False   # Crossing active status
        self.circuitPresent = True    # All blocks have track circuits
        self.scheduledOccupations = []  # List[datetime]
        self.scheduledClosures = []     # List[datetime]
        self.occupyingTrain = None      # Train object currently in block
        
        # Additional attributes needed for implementation
        self.authority = 0              # Current authority (0 or 1)
        self.suggestedSpeed = 0         # Current speed command (0-3)
        self.track_circuit_failed = False
        self.power_rail_status = True
        self.line = track_block_data.line
        self.section = track_block_data.section
        self.elevation = track_block_data.elevation_m
        self.direction = track_block_data.direction
        self.is_underground = track_block_data.is_underground
        
        # Infrastructure objects
        self.station = track_block_data.station if track_block_data.has_station else None
        self.switch = track_block_data.switch if track_block_data.has_switch else None
        
        # Occupancy tracking
        self.occupied = False
        self.last_occupancy_change = None
        self.occupancy_history = []
        
        # Maintenance and failure tracking
        self.maintenance_mode = False
        self.failure_mode = False
        self.last_maintenance = None
        
        logger.debug(f"Block {self.blockID} initialized on {self.line} line")
    
    # Methods from UML
    
    def update_occupation(self, occupied: bool) -> None:
        """
        Update block occupation status
        
        Args:
            occupied: True if block is occupied, False otherwise
        """
        if self.occupied != occupied:
            self.occupied = occupied
            self.last_occupancy_change = datetime.now()
            
            # Update occupancy history
            self.occupancy_history.append({
                'timestamp': self.last_occupancy_change,
                'occupied': occupied,
                'train': self.occupyingTrain
            })
            
            # Keep only last 100 occupancy changes
            if len(self.occupancy_history) > 100:
                self.occupancy_history = self.occupancy_history[-100:]
            
            logger.debug(f"Block {self.blockID} occupation updated: {occupied}")
    
    def get_switch_info(self) -> bool:
        """
        Get current switch position
        
        Returns:
            Current switch position (0=normal/lower block, 1=reverse/higher block)
            Returns False if no switch present
        """
        if self.switchPresent:
            return self.switchPosition
        return False
    
    def setCrossing_status(self, status: bool) -> None:
        """
        Set railway crossing status
        
        Args:
            status: True if crossing is active, False otherwise
        """
        if self.crossingPresent:
            old_status = self.crossingStatus
            self.crossingStatus = status
            
            if old_status != status:
                logger.info(f"Block {self.blockID} crossing status changed: {status}")
        else:
            logger.warning(f"Block {self.blockID} has no crossing - cannot set status")
    
    def setBlock_status(self, status: bool) -> None:
        """
        Set block operational status
        
        Args:
            status: True if block is operational, False if failed/closed
        """
        old_status = self.stationaryStatus
        self.stationaryStatus = status
        
        if old_status != status:
            if not status:
                self.failure_mode = True
                logger.warning(f"Block {self.blockID} set to non-operational")
            else:
                self.failure_mode = False
                logger.info(f"Block {self.blockID} restored to operational")
    
    def block_operational(self) -> bool:
        """
        Check if block is operational
        
        Returns:
            True if block is operational and safe for trains
        """
        return (self.stationaryStatus and 
                not self.failure_mode and 
                not self.track_circuit_failed and 
                self.power_rail_status)
    
    def update_scheduled_occupancy(self, times: List[datetime]) -> None:
        """
        Update scheduled occupations
        
        Args:
            times: List of datetime objects when block will be occupied
        """
        self.scheduledOccupations = times.copy()
        logger.debug(f"Block {self.blockID} scheduled occupations updated: {len(times)} times")
    
    def block_occupation(self) -> List[datetime]:
        """
        Get scheduled occupations
        
        Returns:
            List of datetime objects when block is scheduled to be occupied
        """
        return self.scheduledOccupations.copy()
    
    def add_train(self, train) -> None:
        """
        Add train to block
        
        Args:
            train: Train object entering the block
        """
        if self.occupyingTrain is not None and self.occupyingTrain != train:
            logger.error(f"Block {self.blockID} already occupied by different train!")
            return
        
        self.occupyingTrain = train
        self.update_occupation(True)
        
        # Update train's current block if possible
        if hasattr(train, 'currentBlock'):
            train.currentBlock = self.blockID
        
        logger.info(f"Train {self._get_train_id(train)} entered block {self.blockID}")
    
    def remove_train(self) -> None:
        """Remove train from block"""
        if self.occupyingTrain:
            train_id = self._get_train_id(self.occupyingTrain)
            self.occupyingTrain = None
            self.update_occupation(False)
            logger.info(f"Train {train_id} left block {self.blockID}")
        else:
            logger.warning(f"No train to remove from block {self.blockID}")
    
    def get_occupying_train(self):
        """
        Get current occupying train
        
        Returns:
            Train object currently in block, or None if empty
        """
        return self.occupyingTrain
    
    # Additional methods needed for implementation
    
    def calculate_safe_authority(self, next_blocks: List['Block']) -> int:
        """
        Calculate safe authority based on ahead conditions
        
        Args:
            next_blocks: List of blocks ahead in train's path
            
        Returns:
            Authority value (0=no authority, 1=full authority)
        """
        # Check if current block is operational
        if not self.block_operational():
            return 0
        
        # Check next blocks for obstacles
        for block in next_blocks:
            if not block.block_operational():
                return 0  # Stop before failed block
            if block.occupied:
                return 0  # Stop before occupied block
            if block.maintenance_mode:
                return 0  # Stop before maintenance
        
        # Check for switch conflicts
        if self.switchPresent and not self._switch_aligned_for_route(next_blocks):
            return 0
        
        return 1  # Safe to proceed
    
    def calculate_suggested_speed(self, train_state: dict, track_conditions: dict) -> int:
        """
        Calculate speed command based on conditions
        
        Args:
            train_state: Current train state information
            track_conditions: Current track conditions
            
        Returns:
            Speed command (0=stop, 1=1/3 speed, 2=2/3 speed, 3=full speed)
        """
        # Check for immediate stops
        if not self.block_operational():
            return 0
        
        if self.crossingPresent and self.crossingStatus:
            return 0  # Stop for active crossing
        
        # Check grade and speed limits
        if abs(self.grade) > 5.0:  # Steep grade
            return 1  # Reduced speed
        
        # Weather/environmental conditions
        weather = track_conditions.get('weather', 'clear')
        if weather in ['rain', 'snow', 'ice']:
            return 2  # Reduced speed for weather
        
        # Normal operations - respect speed limit
        current_speed = train_state.get('speed', 0)
        if current_speed > self.speedLimit * 0.8:
            return 2  # Approach speed limit
        
        return 3  # Full speed
    
    def set_switch_position(self, position: bool) -> None:
        """
        Set switch position
        
        Args:
            position: Switch position (0=normal/lower, 1=reverse/higher)
        """
        if self.switchPresent:
            old_position = self.switchPosition
            self.switchPosition = position
            
            if old_position != position:
                position_name = "reverse (higher)" if position else "normal (lower)"
                logger.info(f"Block {self.blockID} switch set to {position_name}")
        else:
            logger.warning(f"Block {self.blockID} has no switch")
    
    def schedule_closure(self, start_time: datetime, end_time: datetime) -> None:
        """
        Schedule block closure for maintenance
        
        Args:
            start_time: When closure begins
            end_time: When closure ends
        """
        self.scheduledClosures.append({
            'start': start_time,
            'end': end_time,
            'type': 'maintenance'
        })
        
        logger.info(f"Block {self.blockID} closure scheduled: {start_time} to {end_time}")
    
    def is_closed_at_time(self, check_time: datetime) -> bool:
        """
        Check if block is closed at specific time
        
        Args:
            check_time: Time to check
            
        Returns:
            True if block is closed at that time
        """
        for closure in self.scheduledClosures:
            if closure['start'] <= check_time <= closure['end']:
                return True
        return False
    
    def get_next_valid_blocks(self, direction: str = None) -> List[int]:
        """
        Get list of valid next blocks based on track layout
        
        Args:
            direction: Optional direction constraint
            
        Returns:
            List of block numbers that can be reached from this block
        """
        valid_blocks = []
        
        if self.switchPresent and self.switch:
            # Get switch connections
            for connection in self.switch.connections:
                if connection.from_block == self.blockID:
                    valid_blocks.append(connection.to_block)
        else:
            # Simple progression
            if direction == 'forward' or direction is None:
                valid_blocks.append(self.blockID + 1)
            if direction == 'backward' or direction is None:
                valid_blocks.append(self.blockID - 1)
        
        return valid_blocks
    
    def get_infrastructure_info(self) -> dict:
        """
        Get complete infrastructure information
        
        Returns:
            Dict containing all infrastructure details
        """
        return {
            'blockID': self.blockID,
            'line': self.line,
            'section': self.section,
            'length': self.length,
            'grade': self.grade,
            'speed_limit': self.speedLimit,
            'elevation': self.elevation,
            'underground': self.is_underground,
            'station': self.station.name if self.station else None,
            'switch_present': self.switchPresent,
            'switch_position': self.switchPosition if self.switchPresent else None,
            'crossing_present': self.crossingPresent,
            'crossing_active': self.crossingStatus if self.crossingPresent else None,
            'occupied': self.occupied,
            'operational': self.block_operational(),
            'maintenance_mode': self.maintenance_mode
        }
    
    # Private helper methods
    
    def _switch_aligned_for_route(self, next_blocks: List['Block']) -> bool:
        """Check if switch is properly aligned for route"""
        if not self.switchPresent or not next_blocks:
            return True
        
        # Get intended next block
        next_block = next_blocks[0]
        next_block_id = next_block.blockID
        
        # Check switch alignment
        if self.switch:
            for connection in self.switch.connections:
                if (connection.from_block == self.blockID and 
                    connection.to_block == next_block_id):
                    # Determine required switch position
                    required_position = next_block_id > self.blockID
                    return self.switchPosition == required_position
        
        return False
    
    def _get_train_id(self, train) -> str:
        """Extract train ID from train object"""
        if hasattr(train, 'trainID'):
            return str(train.trainID)
        elif hasattr(train, 'id'):
            return str(train.id)
        else:
            return f"train_{id(train)}"
    
    def __str__(self) -> str:
        """String representation of block"""
        status = "occupied" if self.occupied else "empty"
        return f"Block {self.blockID} ({self.line} Line, {status})"
    
    def __repr__(self) -> str:
        """Detailed representation of block"""
        return (f"Block(id={self.blockID}, line={self.line}, "
                f"occupied={self.occupied}, operational={self.block_operational()})")