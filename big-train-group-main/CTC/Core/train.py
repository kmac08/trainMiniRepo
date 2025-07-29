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
    Represents a train in the CTC system
    
    Attributes from UML diagram:
    - trainID: Unique identifier for the train
    - currentBlock: Current block the train is on
    - nextBlock: Next block in the train's path
    - grade: Current grade/slope (double)
    - speedLimit: Current speed limit (double)
    - authority: Number of blocks the train is authorized to travel (int)
    - suggestedSpeed: Suggested speed for the train (int)
    - locationOnBlock: Position on current block
    - setCommandedSpeed: Commanded speed (double)
    - updateRoute: Route assignment
    - getRoute: Current route
    - getCurrentSpeed: Current actual speed (int)
    - getLocation: Current location (Block)
    """
    
    # Required attributes
    trainID: int
    currentBlock: Block
    
    # Optional attributes with defaults
    nextBlock: Optional[Block] = None
    grade: float = 0.0
    speedLimit: float = 0.0
    authority: int = 0
    suggestedSpeed: int = 0
    locationOnBlock: float = 0.0  # Position on block (0.0 to 1.0)
    commanded_speed: float = 0.0
    current_speed: int = 0
    
    # Route information
    route: Optional[Route] = None
    
    # Additional state tracking
    is_active: bool = True
    line: str = ""  # Red, Green, etc.
    
    def update_location(self, new_block: Block, location: float = 0.0) -> None:
        """Update train's current location"""
        self.currentBlock = new_block
        self.locationOnBlock = location
        
    def set_commanded_speed(self, speed: float) -> None:
        """Set the commanded speed for the train"""
        self.commanded_speed = max(0.0, min(speed, self.speedLimit))
        
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
    
    def get_current_speed(self) -> int:
        """Get the train's current speed"""
        return self.current_speed
    
    def get_location(self) -> Block:
        """Get the train's current block location"""
        return self.currentBlock
    
    def update_authority(self, new_authority: int) -> None:
        """Update the train's authority"""
        self.authority = max(0, new_authority)
        
    def update_suggested_speed(self, speed: int) -> None:
        """Update the suggested speed"""
        self.suggestedSpeed = max(0, speed)
        
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
            'speedLimit': self.speedLimit,
            'authority': self.authority,
            'suggestedSpeed': self.suggestedSpeed,
            'locationOnBlock': self.locationOnBlock,
            'commanded_speed': self.commanded_speed,
            'current_speed': self.current_speed,
            'line': self.line,
            'is_active': self.is_active,
            'route': self.route.routeID if self.route else None
        }