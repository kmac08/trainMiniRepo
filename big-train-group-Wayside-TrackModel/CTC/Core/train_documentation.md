# Train Class Documentation

## Overview
The Train class (`train.py`) represents a train entity in the CTC system with all its properties and state.

## Attributes

### Required Attributes
- `trainID` (int): Unique identifier for the train
- `currentBlock` (Block): Current block the train is on

### Optional Attributes with Defaults
- `nextBlock` (Optional[Block]): Next block in the train's path (default: None)
- `grade` (float): Current grade/slope (default: 0.0)
- `speedLimit` (float): Current speed limit (default: 0.0)
- `authority` (int): Number of blocks the train is authorized to travel (default: 0)
- `suggestedSpeed` (int): Suggested speed for the train (default: 0)
- `locationOnBlock` (float): Position on current block (0.0 to 1.0, default: 0.0)
- `commanded_speed` (float): Commanded speed (default: 0.0)
- `current_speed` (int): Current actual speed (default: 0)
- `route` (Optional[Route]): Route assignment (default: None)
- `is_active` (bool): Train active status (default: True)
- `line` (str): Line name (Red, Green, etc., default: "")

## Methods

### Location and Movement Methods
- `update_location(new_block: Block, location: float = 0.0)`: Update train's current location
- `get_location() -> Block`: Get the train's current block location

### Speed and Control Methods
- `set_commanded_speed(speed: float)`: Set the commanded speed for the train
- `get_current_speed() -> int`: Get the train's current speed
- `update_suggested_speed(speed: int)`: Update the suggested speed

### Route Management Methods
- `update_route(new_route: Route)`: Update the train's assigned route
- `get_route() -> Optional[Route]`: Get the train's current route
- `update_authority(new_authority: int)`: Update the train's authority

### Utility Methods
- `__str__() -> str`: String representation of the train
- `to_dict() -> dict`: Convert train to dictionary for serialization

## Integration Notes
- Train objects are designed to work with the Block and Route classes
- The dataclass decorator provides automatic initialization and comparison methods
- Route assignment automatically updates the nextBlock based on the route's block sequence
- Speed commands are automatically constrained to not exceed the speed limit