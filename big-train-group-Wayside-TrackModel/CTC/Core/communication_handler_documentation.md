# CommunicationHandler Class Documentation

## Overview
The CommunicationHandler class (`communication_handler.py`) manages all external communications between CTC and other subsystems according to UML specifications. **Updated with dynamic command state management and multi-train coordination.**

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

### **NEW: Dynamic Command State Management**
- `controller_command_states` (Dict[controller, Dict]): Complete command arrays per controller
  - Each controller maintains full-sized arrays for all blocks it covers
  - Keys: `suggested_speeds`, `authorities`, `block_nums`, `update_flags`, `next_stations`, `blocks_away`
- `controller_train_tracking` (Dict[controller, Dict[int, str]]): Maps block numbers to train IDs per controller
- `controller_block_coverage` (Dict[controller, List[int]]): Cached block coverage for each controller

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
- `tickets_purchased(line: str, numTickets: int)`: Handle throughput update from ticket system
- `stop_train(train)`: Emergency stop a specific train

### Wayside Communication Methods
- `provide_wayside_controller(waysideController, blocksCovered: List[int])`: Register controller and its blocks
  - **NEW**: Automatically initializes complete command state arrays sized to match controller's block coverage
- `send_train_commands(suggestedSpeed: List[int], authority: List[int], blockNum: List[int], updatePreviousFlag: List[int], nextStation: List[int], blocksAway: List[int])`: **UPDATED** - Now updates command state and sends complete arrays to affected controllers
  - **CRITICAL COMMAND STRUCTURE**: Array index = train's current block, Array values = commands for target block (4 positions ahead in route)
  - `blockNum[current_block]` = target block ID (NOT current block ID)
  - `blocksAway[current_block]` = route distance from current to target (NOT arithmetic difference)
  - Commands sent TO current block controller FOR target block
- `send_updated_train_commands(line_name: str = None)`: **NEW** - Send batched commands for all trains when block occupations change
- `command_switch(controller, switchPositions: List[bool])`: Send switch commands to specific controller
- `set_occupied(controller, blockList: List[bool])`: Set block occupation for manual closures

### **NEW: Multi-Train State Management**
- `update_train_location(train_id: str, old_block: int, new_block: int)`: Update train tracking when trains move between blocks
- `remove_train_from_system(train_id: str)`: Remove all traces of a train from the command system
- `_recalculate_controller_commands(controller)`: Recalculate complete command state for all active trains in controller territory

### **NEW: Dynamic Command State Methods**
- `_initialize_controller_command_state(controller, blocksCovered: List[int])`: Initialize command arrays for newly registered controller
- `_update_block_command_state(controller, block_num: int, speed: int, authority: int, update_flag: int, next_station: int, blocks_away: int)`: Update command state for specific block using dynamic indexing
- `_send_complete_command_array(controller)`: Send complete command array to wayside controller

### Maintenance Communication Methods
- `send_maintenance_closure(line: str, block_number: int, action: str)`: Send maintenance closure notification to wayside controller

### Event-Driven Command Methods
- `send_train_commands_for_route(train_id: str, route)`: Send commands when a train is newly routed or rerouted
- `send_departure_commands(train_id: str, route)`: **UPDATED** - Now uses dynamic yard detection and sends commands via yard controller

### Private Methods
- `_process_messages()`: Background thread to process incoming messages
- `_handle_message(message)`: Process a single message
- `_update_occupied_blocks_internal(occupied_blocks)`: Internal method to process occupied blocks update
- `_update_switch_positions_internal(switch_positions)`: Internal method to process switch positions update
- `_update_railway_crossings_internal(railway_crossings)`: Internal method to process railway crossings update
- `_calculate_train_commands(train, route)`: Calculate suggested speed and authority for a train

### Removed Methods
The following methods have been removed as they were unimplemented placeholders:
- `send_train_info()`: Legacy method replaced by event-driven commands
- `_check_obstacles_ahead()`: Placeholder for obstacle detection
- `_send_route_to_controller()`: Placeholder for route communication protocol
- `_send_closure_to_controller()`: Placeholder for closure communication protocol  
- `_send_opening_to_controller()`: Placeholder for opening communication protocol

### **NEW: Enhanced Calculation Methods**
- `_calculate_blocks_away(current_position: int, target_block_id: int, route)`: Original method for route-based distance calculation
- `_calculate_blocks_away_for_train(train_id: str, target_block_id: int, route)`: **NEW** - Calculate distance from specific train's actual current position

### Utility Methods
- `shutdown()`: Shutdown the communication handler

## **NEW: Key Architectural Improvements**

### **Complete Array Management**
- All `command_train()` calls now send complete arrays sized to match each controller's block coverage
- Green_A controller: 29-element arrays (blocks 1-29)
- Red_A controller: 25-element arrays (blocks 0,1-24) 
- Arrays are properly indexed: command for block N goes to position `blocks_covered.index(N)`

### **Dynamic Yard Detection**
- No hardcoded controller names - yard commands automatically route to controller managing block 0
- Supports configuration changes without code modification
- Uses `0 in controller.blocks_covered` for detection

### **Multi-Train Coordination**
- Prevents command conflicts when multiple trains operate in same controller territory
- Maintains separate commands for each train, consolidated into single arrays per controller
- Automatic recalculation when trains move, are added, or removed

### **Proper Command Timing**
- Route activation separated from departure command sending
- Yard departure commands only sent when `dispatch_train_from_yard()` is called
- Prevents premature command transmission during route planning

### **Dynamic Block Indexing**
- All indexing based on actual `controller.blocks_covered` arrays
- No assumptions about block numbering or controller coverage
- Supports arbitrary block arrangements and controller configurations

### **Command Array Structure Examples**

#### Example 1: Train in Block 5, Target Block 12
- Train's current location: Block 5
- Target block (4 positions ahead): Block 12
- Route distance: 4 hops through route sequence
- **Array structure**:
  - `suggested_speeds[5] = 3` (full speed for when train reaches block 12)
  - `authorities[5] = 1` (authority for when train reaches block 12)
  - `block_nums[5] = 12` (target block ID, NOT current block 5)
  - `blocks_away[5] = 4` (route distance, NOT arithmetic difference 12-5=7)

#### Example 2: Non-Sequential Route
- Route sequence: [1, 5, 3, 8, 15, 12]
- Train current: Block 1
- Target (4 ahead): Block 15 (1→5→3→8→15)
- Route distance: 4 hops
- **Array structure**:
  - `block_nums[1] = 15` (target is block 15, not block 5)
  - `blocks_away[1] = 4` (4 route hops, not 14 arithmetic difference)

#### Key Principle
- **Array Index** = WHERE the train IS (current block)
- **Array Values** = Commands for WHERE the train WILL BE (target block)

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

### **NEW Integration Features**
- **Dynamic Controller Registration**: Automatically adapts to any wayside controller configuration
- **Complete State Synchronization**: Wayside controllers always receive consistent, complete view of their territory
- **Event-Driven Updates**: Commands sent only when system state changes (routing, movement, departures)
- **Multi-Train Safety**: Prevents command conflicts between multiple active trains
- **Configuration Agnostic**: Works with any track layout or controller arrangement without code changes

### **Integration with CTC System**
- `CTCSystem.add_train()` automatically registers trains with communication handler
- `CTCSystem.remove_train()` properly cleans up all command state
- `CTCSystem.activate_route()` only sends commands for trains already on track
- `CTCSystem.dispatch_train_from_yard()` triggers proper departure command sequence