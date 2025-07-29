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
from datetime import datetime, timedelta
import logging

# Import simulation time (lazy import to avoid circular dependencies)
# from Master_Interface.master_control import get_time


def _get_simulation_time():
    """Get simulation time with lazy import to avoid circular dependencies"""
    try:
        from Master_Interface.master_control import get_time
        return get_time()
    except ImportError:
        # Fallback to regular datetime if Master Interface not available
        from datetime import datetime
        return datetime.now()

# Set up logging
logger = logging.getLogger(__name__)


class Block:
    """
    Represents a single track block with comprehensive infrastructure and state management.
    
    This class implements a track block entity with all necessary properties for CTC control,
    including occupation tracking, infrastructure management, safety calculations, and connectivity.
    
    Core Infrastructure:
        blockID (int): Unique block identifier
        length (float): Block length in meters
        grade (float): Grade percentage
        speedLimit (float): Speed limit in km/h
        line (str): Track line (Red, Green, Blue)
        section (str): Track section identifier
        elevation (float): Elevation in meters
        direction (str): Traffic direction (BIDIRECTIONAL, etc.)
        is_underground (bool): Whether block is underground
        
    Railway Infrastructure:
        switchPresent (bool): Whether block has a switch
        switchPosition (bool): Current switch position (0=normal, 1=reverse)
        crossingPresent (bool): Whether block has a railway crossing
        crossingStatus (bool): Crossing activation status
        circuitPresent (bool): Track circuit availability
        station (object): Station object if block has station
        switch (object): Switch object if block has switch
        
    Operational State:
        is_open (bool): Block open/closed status (True = open, False = closed)
        failed (bool): Block failure status (True = failed, False = operational)
        occupied (bool): Current occupation state
        occupyingTrain (object): Train currently in block
        authority (int): Current authority (0 or 1)
        suggestedSpeed (int): Current speed command (0-3)
        
    Connectivity & Routing:
        connected_blocks (List[int]): Connected block numbers
        has_yard_connection (bool): Whether block connects to yard
        
    Failure & Maintenance:
        failed (bool): Block failure status (True = failed, False = operational)
        maintenance_mode (bool): Maintenance mode status
        last_maintenance (datetime): Last maintenance timestamp
        
    Scheduling:
        scheduledOccupations (List[datetime]): Scheduled occupation times
        scheduledClosure (Dict): Single scheduled maintenance closure
        scheduledOpening (Dict): Single scheduled reopening after closure
        
    Methods Overview:
        Occupation Management:
            - update_occupation(occupied): Update occupation status
            - add_train(train): Add train to block
            - remove_train(): Remove train from block
            - get_occupying_train(): Get current occupying train
            
        Infrastructure Control:
            - get_switch_info(): Get switch position
            - set_switch_position(position): Set switch position
            - setCrossing_status(status): Set crossing status
            
        Operational Status:
            - set_block_open(open): Set block open/closed status
            - set_block_failed(failed): Set block failure status
            - block_operational(): Check if block is operational
            
        Safety & Authority:
            - calculate_safe_authority(next_blocks): Calculate authority for route
            - calculate_suggested_speed(train_state, conditions): Calculate speed command
            
        Scheduling & Maintenance:
            - update_scheduled_occupancy(times): Update scheduled occupations
            - block_occupation(): Get scheduled occupations
            - schedule_closure(start): Schedule maintenance closure (indefinite)
            - schedule_opening(opening_time): Schedule reopening after closure
            - is_closed_at_time(time): Check if closed at specific time
            
        Connectivity:
            - get_next_valid_blocks(direction): Get reachable blocks
            - is_connected_to(block_number): Check direct connection
            - leads_to_yard(): Check yard connection
            - get_connected_blocks(): Get connected block numbers
            
        Information:
            - get_infrastructure_info(): Get complete infrastructure data
            - __str__(), __repr__(): String representations for logging
    """
    
    def __init__(self, track_block_data):
        """
        Initialize Block with data from Track Reader
        
        Args:
            track_block_data: TrackBlock object from Track_Reader
        """
        # Static infrastructure attributes (read-only after initialization)
        self._blockID = track_block_data.block_number
        self._block_number = track_block_data.block_number  # For UI compatibility
        self._length = track_block_data.length_m
        self._grade = track_block_data.grade_percent
        self._speedLimit = track_block_data.speed_limit_kmh
        self._line = track_block_data.line
        self._section = track_block_data.section
        self._elevation = track_block_data.elevation_m
        self._direction = track_block_data.direction
        self._is_underground = track_block_data.is_underground
        self._switchPresent = track_block_data.has_switch
        self._crossingPresent = track_block_data.has_crossing
        self._circuitPresent = True    # All blocks have track circuits
        self._station = track_block_data.station if track_block_data.has_station else None
        self._switch = track_block_data.switch if track_block_data.has_switch else None
        self._connected_blocks = track_block_data.connected_blocks.copy() if hasattr(track_block_data, 'connected_blocks') else []
        self._has_yard_connection = track_block_data.has_yard_connection if hasattr(track_block_data, 'has_yard_connection') else False
        
        # Dynamic operational attributes (can be modified during runtime)
        self.is_open = True          # Open/closed status (True = open, False = closed)
        self.failed = False          # Failure status (True = failed, False = operational)
        self.switchPosition = False   # Current switch position if applicable
        self.crossingStatus = False   # Crossing active status
        self.scheduledOccupations = []  # List[datetime]
        self.scheduledClosure = None    # Dict - single scheduled maintenance closure
        self.scheduledOpening = None    # Dict - single scheduled reopening after closure
        self.occupyingTrain = None      # Train object currently in block
        self.authority = 0              # Current authority (0 or 1)
        self.suggestedSpeed = 0         # Current speed command (0-3)
        self.occupied = False           # Occupancy tracking
        self.maintenance_mode = False   # Maintenance tracking
        self.last_maintenance = None
        
        logger.debug(f"Block {self._blockID} initialized on {self._line} line")
        
        # Debug output for block instantiation - show comprehensive block information
        block_info = self.get_infrastructure_info()
        logger.debug(f"Block {self._blockID} instantiation details:")
        logger.debug(f"  Line: {block_info['line']}, Section: {block_info['section']}")
        logger.debug(f"  Length: {block_info['length']}m, Grade: {block_info['grade']}%, Speed Limit: {block_info['speed_limit']} kph")
        logger.debug(f"  Infrastructure: Switch={block_info['switch_present']}, Crossing={block_info['crossing_present']}, Station={block_info['station']}")
        logger.debug(f"  Connected blocks: {block_info['connected_blocks']}")
    
    # Static infrastructure properties (read-only)
    
    @property
    def blockID(self) -> int:
        """Block unique identifier (read-only)"""
        return self._blockID
    
    @property
    def block_number(self) -> int:
        """Block number for UI compatibility (read-only)"""
        return self._block_number
    
    @property
    def length(self) -> float:
        """Block length in meters (read-only)"""
        return self._length
    
    @property
    def grade(self) -> float:
        """Grade percentage (read-only)"""
        return self._grade
    
    @property
    def speedLimit(self) -> float:
        """Speed limit in km/h (read-only)"""
        return self._speedLimit
    
    @property
    def line(self) -> str:
        """Track line (Red, Green, Blue) (read-only)"""
        return self._line
    
    @property
    def section(self) -> str:
        """Track section identifier (read-only)"""
        return self._section
    
    @property
    def elevation(self) -> float:
        """Elevation in meters (read-only)"""
        return self._elevation
    
    @property
    def direction(self) -> str:
        """Traffic direction (read-only)"""
        return self._direction
    
    @property
    def is_underground(self) -> bool:
        """Whether block is underground (read-only)"""
        return self._is_underground
    
    @property
    def switchPresent(self) -> bool:
        """Whether block has a switch (read-only)"""
        return self._switchPresent
    
    @property
    def crossingPresent(self) -> bool:
        """Whether block has a railway crossing (read-only)"""
        return self._crossingPresent
    
    @property
    def circuitPresent(self) -> bool:
        """Track circuit availability (read-only)"""
        return self._circuitPresent
    
    @property
    def station(self):
        """Station object if block has station (read-only)"""
        return self._station
    
    @property
    def switch(self):
        """Switch object if block has switch (read-only)"""
        return self._switch
    
    @property
    def connected_blocks(self) -> List[int]:
        """Connected block numbers (read-only)"""
        return self._connected_blocks.copy()  # Return copy to prevent modification
    
    @property
    def has_yard_connection(self) -> bool:
        """Whether block connects to yard (read-only)"""
        return self._has_yard_connection
    
    # Methods from UML
    
    def update_occupation(self, occupied: bool) -> None:
        """
        Update block occupation status
        
        Args:
            occupied: True if block is occupied, False otherwise
        """
        if self.occupied != occupied:
            self.occupied = occupied
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
            # Ensure crossing status is False when no crossing is present
            self.crossingStatus = False
            logger.warning(f"Block {self.blockID} has no crossing - cannot set status")
    
    def set_block_open(self, open: bool) -> None:
        """
        Set block open/closed status
        
        Args:
            open: True to open block, False to close block
        """
        if not open and self.occupied:
            logger.error(f"Cannot close Block {self.blockID} - currently occupied by train")
            return
        
        old_status = self.is_open
        self.is_open = open
        
        if old_status != open:
            status_text = "opened" if open else "closed"
            logger.info(f"Block {self.blockID} {status_text}")
    
    def set_block_failed(self, failed: bool, reason: str = None) -> None:
        """
        Set block failure status
        
        Args:
            failed: True if block has failed, False if operational
            reason: Optional reason for failure (for logging/debugging)
        """
        old_status = self.failed
        self.failed = failed
        
        if old_status != failed:
            if failed:
                reason_text = f" ({reason})" if reason else ""
                logger.error(f"Block {self.blockID} failed{reason_text}")
            else:
                logger.info(f"Block {self.blockID} restored to operational")
    
    
    def block_operational(self) -> bool:
        """
        Check if block is operational
        
        Returns:
            True if block is operational and safe for trains
        """
        return self.is_open and not self.failed
    
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
            train.currentBlock = self
        
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
    
    def calculate_safe_authority(self) -> int:
        """
        Calculate safe authority based only on current block conditions
        
        Returns:
            Authority value (0=no authority, 1=full authority)
        """
        # Check if current block is operational
        if not self.block_operational():
            return 0
        
        # Check if current block is occupied
        if self.occupied:
            return 0
        
        # Check if block is in maintenance mode
        if self.maintenance_mode:
            return 0
        
        return 1  # Safe to proceed
    
    def calculate_suggested_speed(self, next_block_1=None, next_block_2=None) -> int:
        """
        Calculate speed command based on current block authority and next block occupation
        
        Args:
            next_block_1: First block ahead (optional)
            next_block_2: Second block ahead (optional)
            
        Returns:
            Speed command (0=stop, 1=1/3 speed, 2=2/3 speed, 3=full speed)
        """
        # Return 0 if no authority for current block
        if self.calculate_safe_authority() == 0:
            return 0
        
        # Check occupation of next blocks for speed reduction
        if next_block_1 is None or next_block_1.occupied:
            return 1  # 1/3 speed if no next block or next block is occupied
        
        if next_block_2 is None or next_block_2.occupied:
            return 2  # 2/3 speed if second block ahead is occupied
        
        return 3  # Full speed otherwise
    
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
    
    def schedule_closure(self, start_time: datetime) -> dict:
        """
        Schedule block closure for maintenance (indefinite duration)
        Overwrites any existing scheduled closure
        
        Args:
            start_time: When closure begins (indefinite duration)
            
        Returns:
            Dict with success status and message
        """
        # Validate that block is not currently occupied
        if self.occupied:
            return {
                'success': False,
                'message': f'Block {self.blockID} cannot be scheduled for closure - currently occupied by train'
            }
        
        # Validate that closure time is after all scheduled occupations
        for scheduled_time in self.scheduledOccupations:
            if start_time <= scheduled_time:
                return {
                    'success': False,
                    'message': f'Block {self.blockID} cannot be scheduled for closure at {start_time} - scheduled occupation at {scheduled_time}'
                }
        
        # Create/overwrite scheduled closure (simplified - no status tracking)
        self.scheduledClosure = {
            'closure_time': start_time,
            'type': 'maintenance'
        }
        
        logger.info(f"Block {self.blockID} closure scheduled: {start_time} (indefinite)")
        return {
            'success': True,
            'message': f'Block {self.blockID} closure scheduled for {start_time}'
        }
    
    def schedule_opening(self, opening_time: datetime) -> dict:
        """
        Schedule block opening after maintenance closure
        Overwrites any existing scheduled opening
        
        Args:
            opening_time: When to reopen the block
            
        Returns:
            Dict with success status and message
        """
        # Check if opening can be scheduled (closure scheduled or block currently closed)
        can_schedule = False
        reference_time = None
        
        if self.scheduledClosure:
            # Closure is scheduled - opening can be scheduled after it
            can_schedule = True
            reference_time = self.scheduledClosure['closure_time']
        elif not self.is_open:
            # Block is currently closed - opening can be scheduled
            can_schedule = True
            reference_time = _get_simulation_time()  # Current time as reference
        
        if not can_schedule:
            return {
                'success': False,
                'message': f'Block {self.blockID} is not scheduled for closure and is not currently closed - cannot schedule opening'
            }
        
        # Check if opening time is after reference time
        if opening_time <= reference_time:
            return {
                'success': False,
                'message': f'Opening time {opening_time} must be after {"closure time" if self.scheduledClosure else "current time"} {reference_time}'
            }
        
        # Create/overwrite scheduled opening (simplified - no status tracking)
        self.scheduledOpening = {
            'opening_time': opening_time
        }
        
        logger.info(f"Block {self.blockID} opening scheduled: {opening_time}")
        return {
            'success': True,
            'message': f'Block {self.blockID} opening scheduled for {opening_time}'
        }
    
    def clear_scheduled_closure(self) -> dict:
        """
        Clear any scheduled closure
        
        Returns:
            Dict with success status and message
        """
        if self.scheduledClosure:
            logger.info(f"Block {self.blockID} scheduled closure cleared")
            self.scheduledClosure = None
            return {
                'success': True,
                'message': f'Block {self.blockID} scheduled closure cleared'
            }
        else:
            return {
                'success': False, 
                'message': f'Block {self.blockID} has no scheduled closure to clear'
            }
    
    def is_closed_at_time(self, check_time: datetime) -> bool:
        """
        Check if block is closed at specific time
        
        Args:
            check_time: Time to check
            
        Returns:
            True if block is closed at that time
        """
        current_time = _get_simulation_time()
        
        # For current time, just check the is_open status
        if check_time <= current_time:
            return not self.is_open
        
        # For future times, check scheduled closures and openings
        block_will_be_open = self.is_open  # Start with current state
        
        # If there's a scheduled closure in the future
        if self.scheduledClosure and self.scheduledClosure['closure_time'] <= check_time:
            block_will_be_open = False  # Block will be closed
            
            # But if there's also a scheduled opening after the closure
            if (self.scheduledOpening and
                    check_time >= self.scheduledOpening['opening_time'] > self.scheduledClosure['closure_time']):
                block_will_be_open = True  # Block will be reopened
        
        return not block_will_be_open
    
    def process_scheduled_closure(self, current_time: datetime) -> bool:
        """
        Process scheduled closure if it's time to execute it
        
        Args:
            current_time: Current simulation time
            
        Returns:
            True if closure was executed, False otherwise
        """
        if (self.scheduledClosure and 
            self.scheduledClosure['closure_time'] <= current_time and
            self.is_open):  # Only close if currently open
            
            logger.info(f"Executing scheduled closure for Block {self.blockID}")
            self.set_block_open(False)
            self.scheduledClosure = None  # Remove scheduled closure after execution
            return True
        
        return False
    
    def process_scheduled_opening(self, current_time: datetime) -> bool:
        """
        Process scheduled opening if it's time to execute it
        
        Args:
            current_time: Current simulation time
            
        Returns:
            True if opening was executed, False otherwise
        """
        if (self.scheduledOpening and 
            self.scheduledOpening['opening_time'] <= current_time and
            not self.is_open):  # Only open if currently closed
            
            logger.info(f"Executing scheduled opening for Block {self.blockID}")
            self.set_block_open(True)
            self.scheduledOpening = None  # Remove scheduled opening after execution
            return True
        
        return False
    
    def get_next_valid_blocks(self, direction: str = None) -> List[int]:
        """
        Get list of valid next blocks based on track layout using connected_blocks data
        
        Args:
            direction: Optional direction constraint
            
        Returns:
            List of block numbers that can be reached from this block
        """
        # Use connected_blocks data if available (NEW: from Track Reader)
        if self._connected_blocks:
            return [block_num for block_num in self._connected_blocks if block_num != 0]
        
        # Fallback to legacy switch/sequential logic
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
            'maintenance_mode': self.maintenance_mode,
            'connected_blocks': self.connected_blocks,
            'has_yard_connection': self.has_yard_connection
        }
    
    def is_connected_to(self, block_number: int) -> bool:
        """
        Check if this block is directly connected to the specified block number
        
        Args:
            block_number: Block number to check connection to
            
        Returns:
            True if this block connects directly to the specified block
        """
        return block_number in self.connected_blocks
    
    def leads_to_yard(self) -> bool:
        """
        Check if this block has a connection to the yard
        
        Returns:
            True if this block connects to the yard
        """
        return self.has_yard_connection
    
    def get_connected_blocks(self) -> List[int]:
        """
        Get list of block numbers this block connects to (excluding yard)
        
        Returns:
            List of block numbers this block connects to
        """
        return [block_num for block_num in self.connected_blocks if block_num != 0]
    
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
    
    def can_close_safely(self, check_time: datetime = None) -> dict:
        """
        Comprehensive safety check before closing block for maintenance
        
        Args:
            check_time: Time to check for conflicts (defaults to current time)
            
        Returns:
            Dict with success status, message, and safety information
        """
        if check_time is None:
            check_time = _get_simulation_time()
        
        # Check if block is currently occupied
        if self.occupied:
            return {
                'success': False,
                'message': f'Block {self.blockID} cannot be closed - currently occupied by train {self.occupyingTrain}',
                'conflict_type': 'current_occupation',
                'earliest_safe_time': None
            }
        
        # Check if block is already closed
        if not self.is_open:
            return {
                'success': False, 
                'message': f'Block {self.blockID} is already closed',
                'conflict_type': 'already_closed',
                'earliest_safe_time': None
            }
        
        # Check for scheduled occupations
        earliest_conflict = None
        for scheduled_time in self.scheduledOccupations:
            if scheduled_time >= check_time:
                if earliest_conflict is None or scheduled_time < earliest_conflict:
                    earliest_conflict = scheduled_time
        
        if earliest_conflict:
            # Find next safe time after all scheduled occupations
            safe_time = max(self.scheduledOccupations) + timedelta(minutes=5)  # 5 minute buffer
            return {
                'success': False,
                'message': f'Block {self.blockID} has scheduled occupation at {earliest_conflict}',
                'conflict_type': 'scheduled_occupation',
                'earliest_safe_time': safe_time
            }
        
        return {
            'success': True,
            'message': f'Block {self.blockID} can be safely closed',
            'conflict_type': None,
            'earliest_safe_time': check_time
        }

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