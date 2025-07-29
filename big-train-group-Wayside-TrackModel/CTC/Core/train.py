"""
Train class for CTC system
Represents a train entity in the system with all its properties and state
"""

from dataclasses import dataclass, field
from typing import Optional, List
from CTC.Core.block import Block
from CTC.Core.route import Route


@dataclass
class Train:
    """
    Represents a train in the CTC system with comprehensive state tracking and route management.
    
    This class implements a train entity with all necessary properties for CTC control,
    including position tracking, route management, speed control, and emergency detection.
    
    Core Attributes:
        trainID (int): Unique identifier for the train
        currentBlock (Block): Current block the train is occupying
        nextBlock (Optional[Block]): Next block in the train's path
        route (Optional[Route]): Current route assignment
        
    Movement & Control:
        grade (float): Current grade/slope percentage (default: 0.0)
        authority (int): Train's movement authority - 0=stop, 1=proceed (default: 0)
        suggestedSpeed (int): Suggested speed command - 0=stop, 1=1/3 speed, 2=2/3 speed, 3=full speed (default: 0)
        
    Status & Configuration:
        is_active (bool): Whether train is currently active (default: True)
        line (str): Train line (Red, Green, Blue) (default: "")
        
    Emergency Detection:
        movement_history (dict): Tracks train movement for emergency detection
            - 'block': Current block ID being tracked
            - 'count': Consecutive updates in same block
            - 'last_update': Timestamp of last update
    
    Methods Overview:
        Movement Control:
            - update_location(new_block): Update train position
            - update_authority(authority): Update movement authority
            - update_suggested_speed(speed): Update suggested speed
            - get_speed_limit(): Get speed limit from current block
            - get_speed_mph(): Convert suggested speed to mph
            
        Route Management:
            - update_route(route): Assign new route to train
            - get_route(): Get current route assignment
            
        State Queries:
            - get_location(): Get current block location
            - get_speed_limit(): Get current block's speed limit
            - get_speed_mph(): Get speed in mph based on suggested speed
            
        Emergency Detection:
            - update_movement_history(block_id): Track movement for emergency detection
            - get_stationary_count(): Get consecutive stationary updates
            - is_stationary_too_long(threshold): Check for emergency conditions
            - reset_movement_history(): Reset emergency tracking
            
        Utilities:
            - to_dict(): Serialize train state for communication
            - __str__(): String representation for logging
    """
    
    # Required attributes
    trainID: int
    currentBlock: Block
    
    # Optional attributes with defaults
    nextBlock: Optional[Block] = None
    grade: float = 0.0
    authority: int = 0
    suggestedSpeed: int = 0
    
    # Route information
    route: Optional[Route] = None
    
    # Additional state tracking
    is_active: bool = True
    line: str = ""  # Red, Green, etc.
    
    # Movement history for emergency detection
    movement_history: dict = field(default_factory=lambda: {'block': None, 'count': 0, 'last_update': None, 'first_stationary_time': None})
    
    def update_location(self, new_block: Block) -> None:
        """Update train's current location"""
        self.currentBlock = new_block
        
    def get_speed_limit(self) -> float:
        """Get the speed limit from the current block in km/h"""
        return self.currentBlock.speedLimit
        
    def get_speed_mph(self) -> float:
        """Convert suggested speed to mph based on current block's speed limit"""
        if self.suggestedSpeed == 0:
            return 0.0
        
        # Get speed limit from current block and convert to mph
        speed_limit_kmh = self.get_speed_limit()
        speed_limit_mph = speed_limit_kmh * 0.621371
        
        # Apply suggested speed scale
        if self.suggestedSpeed == 1:
            return speed_limit_mph / 3.0
        elif self.suggestedSpeed == 2:
            return (speed_limit_mph * 2.0) / 3.0
        elif self.suggestedSpeed == 3:
            return speed_limit_mph
        else:
            return 0.0
        
    def update_route(self, new_route: Route) -> None:
        """Update the train's assigned route"""
        self.route = new_route
        if new_route and new_route.blockSequence:
            # Update next block based on route
            current_idx = None
            for i, block in enumerate(new_route.blockSequence):
                if block.blockID == self.currentBlock.blockID:
                    current_idx = i
                    break
                    
            if current_idx is not None and current_idx < len(new_route.blockSequence) - 1:
                self.nextBlock = new_route.blockSequence[current_idx + 1]
    
    def get_route(self) -> Optional[Route]:
        """Get the train's current route"""
        return self.route
    
    
    def get_location(self) -> Block:
        """Get the train's current block location"""
        return self.currentBlock
    
    def update_authority(self, new_authority: int) -> None:
        """Update the train's authority (0=stop, 1=proceed)"""
        self.authority = max(0, min(1, new_authority))
        
    def update_suggested_speed(self, speed: int) -> None:
        """Update the suggested speed (0=stop, 1=1/3 speed, 2=2/3 speed, 3=full speed)"""
        self.suggestedSpeed = max(0, min(3, speed))
    
    def update_movement_history(self, current_block_id: int) -> None:
        """
        Update movement history when block occupation updates are received
        
        Args:
            current_block_id: Current block the train is on
        """
        from datetime import datetime
        current_time = datetime.now()
        
        if self.movement_history['block'] == current_block_id:
            # Train is still on the same block - increment count
            self.movement_history['count'] += 1
            self.movement_history['last_update'] = current_time
            
            # Set first_stationary_time when count reaches 2 (indicating stationary)
            if self.movement_history['count'] == 2 and self.movement_history['first_stationary_time'] is None:
                self.movement_history['first_stationary_time'] = current_time
        else:
            # Train has moved to a new block - reset count and stationary time
            self.movement_history['block'] = current_block_id
            self.movement_history['count'] = 1
            self.movement_history['last_update'] = current_time
            self.movement_history['first_stationary_time'] = None
    
    def get_stationary_count(self) -> int:
        """
        Get the number of consecutive updates the train has been stationary
        
        Returns:
            Number of consecutive updates without movement
        """
        return self.movement_history['count']
    
    def is_stationary_too_long(self, threshold: int = 3, time_threshold: int = 60) -> bool:
        """
        Check if train has been stationary for too many consecutive updates AND too much time
        
        Args:
            threshold: Number of updates to consider as "too long"
            time_threshold: Number of seconds to consider as "too long" (default: 60)
            
        Returns:
            True if train has been stationary for >= threshold updates AND >= time_threshold seconds
        """
        # Check if we have enough update count
        if self.movement_history['count'] < threshold:
            return False
            
        # Check if we have time tracking data
        first_stationary_time = self.movement_history.get('first_stationary_time')
        if first_stationary_time is None:
            return False
            
        # Check if enough time has passed since becoming stationary
        from datetime import datetime
        current_time = datetime.now()
        time_elapsed = (current_time - first_stationary_time).total_seconds()
        
        return time_elapsed >= time_threshold
    
    def reset_movement_history(self) -> None:
        """Reset movement history (e.g., when train is rerouted or removed)"""
        self.movement_history = {'block': None, 'count': 0, 'last_update': None, 'first_stationary_time': None}
        
    def __str__(self) -> str:
        """String representation of the train"""
        return f"Train {self.trainID} on Block {self.currentBlock.blockID}"
    
    def to_dict(self) -> dict:
        """Convert train to dictionary for serialization"""
        return {
            'trainID': self.trainID,
            'currentBlock': self.currentBlock.blockID if self.currentBlock else None,
            'nextBlock': self.nextBlock.blockID if self.nextBlock else None,
            'grade': self.grade,
            'authority': self.authority,
            'suggestedSpeed': self.suggestedSpeed,
            'line': self.line,
            'is_active': self.is_active,
            'route': self.route.routeID if self.route else None
        }