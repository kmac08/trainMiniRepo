# CommunicationHandler Class Documentation

## Overview
The CommunicationHandler class (`communication_handler.py`) manages all external communications between CTC and other subsystems according to UML specifications.

## Attributes

### Core UML Attributes
- `scheduledClosures` (List[Tuple[Block, DateTime]]): List of scheduled block closures
- `scheduledOpenings` (List[Tuple[Block, DateTime]]): List of scheduled block openings
- `scheduledTrains` (List[Route]): List of scheduled train routes

### Implementation Attributes
- `wayside_controllers` (List): List of wayside controller references
- `block_to_controller` (Dict[int, WaysideController]): Block number to controller mapping
- `message_queue` (Queue): Thread-safe message queue
- `ctc_system`: Reference to CTC System
- `current_occupied_blocks` (Dict[int, bool]): Current block occupation states
- `current_switch_positions` (Dict[int, bool]): Current switch positions
- `current_railway_crossings` (Dict[int, bool]): Current railway crossing states

### Throughput Tracking
- `throughput_by_line` (Dict[str, int]): Throughput tracking by line (Blue, Red, Green)

### Threading
- `_running` (bool): Thread running flag
- `_message_thread` (Thread): Background message processing thread

## Methods

### Core UML Methods
- `update_occupied_blocks(occupiedBlocks: List[bool])`: Receive occupation status from wayside controller
- `update_switch_positions(switchPositions: List[bool])`: Receive switch positions from wayside controller
- `update_railway_crossings(railwayCrossings: List[bool])`: Receive crossing status from wayside controller
- `schedule_route(route)`: Schedule a train route with wayside
- `schedule_closure(block, time: datetime)`: Schedule block closure
- `schedule_opening(block, time: datetime)`: Schedule block opening
- `send_train_info()`: Send train commands to wayside controllers
- `tickets_purchased(line: str, numTickets: int)`: Handle throughput update from ticket system
- `stop_train(train)`: Emergency stop a specific train

### Wayside Communication Methods
- `provide_wayside_controller(waysideController, blocksCovered: List[int])`: Register controller and its blocks
- `command_train(controller, suggestedSpeed: List[int], authority: List[int], numBlocksAhead: List[int])`: Send train commands to specific controller
- `command_switch(controller, switchPositions: List[bool])`: Send switch commands to specific controller
- `set_occupied(controller, blockList: List[bool])`: Set block occupation for manual closures

### Maintenance Communication Methods
- `send_maintenance_closure(line: str, block_number: int, action: str)`: Send maintenance closure notification to wayside controller

### Private Methods
- `_process_messages()`: Background thread to process incoming messages
- `_handle_message(message)`: Process a single message
- `_update_occupied_blocks_internal(occupied_blocks)`: Internal method to process occupied blocks update
- `_update_switch_positions_internal(switch_positions)`: Internal method to process switch positions update
- `_update_railway_crossings_internal(railway_crossings)`: Internal method to process railway crossings update
- `_calculate_train_commands(train, route)`: Calculate suggested speed and authority for a train
- `_check_obstacles_ahead(train, route)`: Check for obstacles in train's path
- `_send_route_to_controller(controller, route)`: Send route information to a specific controller
- `_send_closure_to_controller(controller, block, time)`: Send closure information to a specific controller
- `_send_opening_to_controller(controller, block, time)`: Send opening information to a specific controller

### Utility Methods
- `shutdown()`: Shutdown the communication handler

## Message Queue Processing
The class uses a threaded message queue system to handle incoming updates:

### Message Types
- `occupied_blocks_update`: Block occupation status updates
- `switch_positions_update`: Switch position updates
- `railway_crossings_update`: Railway crossing status updates

### Message Format
```python
{
    'type': 'message_type',
    'data': payload_data,
    'timestamp': datetime.now()
}
```

## Integration Notes
- Designed to handle multiple wayside controllers simultaneously
- Uses threaded message processing for responsive real-time updates
- Integrates with CTC System for train information and route management
- Supports both automated and manual train control operations
- Handles maintenance coordination between CTC and wayside systems
- Provides throughput integration with ticket system for demand management