# Track Model Integration Guide

## Overview
This guide shows how to integrate the Track Model with Train Systems. The Track Model can create multiple train systems and communicate with them using two interface functions. Each train system simulates a complete train with physics, automated control, and real-time monitoring capabilities.

---

## 1. Initialization

The Track Model must create and initialize train systems before communication. Each train system requires track layout data and starting parameters to function properly.

### Import Required Components
These imports provide access to both software and hardware train systems, plus the data structures needed for initialization.

```python
from train_system_main_sw import TrainSystemSW
from train_system_main_hw import TrainSystemHW
from train_controller_sw.controller.data_types import TrainControllerInit, BlockInfo
```

### Create Train System
Train systems need initialization data that defines their starting location, track layout, and routing information. This data tells the train controller where the train is and what track sections are ahead.

```python
# Create initialization data - defines the next 4 blocks ahead of the train
next_blocks = [
    BlockInfo(
        block_number=69, 
        length_meters=50.0, 
        speed_limit_mph=25, 
        underground=False, 
        authorized_to_go=True, 
        commanded_speed=2
    ),
    BlockInfo(
        block_number=70, 
        length_meters=50.0, 
        speed_limit_mph=25, 
        underground=False, 
        authorized_to_go=True, 
        commanded_speed=2
    ),
    BlockInfo(
        block_number=71, 
        length_meters=50.0, 
        speed_limit_mph=25, 
        underground=False, 
        authorized_to_go=True, 
        commanded_speed=1  # Slower for station approach
    ),
    BlockInfo(
        block_number=72, 
        length_meters=50.0, 
        speed_limit_mph=25, 
        underground=False, 
        authorized_to_go=True, 
        commanded_speed=2
    )
]

# Main initialization object containing all train setup data
init_data = TrainControllerInit(
    track_color="red",                      # Track line color ("red" or "green")
    current_block=68,                       # Starting block number
    current_commanded_speed=2,              # Initial speed command (0-3)
    authorized_current_block=True,          # Authorization for current block
    next_four_blocks=next_blocks,           # Upcoming track sections
    train_id="1",                           # Train ID as string
    next_station_number=5                   # Next station this train will reach
)

# Create software train system with GUI controls
train_system = TrainSystemSW(init_data, next_station_number=5)

# OR create hardware train system with GPIO controls
train_system = TrainSystemHW(init_data, next_station_number=5, serial_port='COM4', baud_rate=9600)
```

---

## 2. Send Track Circuit Data

This function allows the Track Model to send control commands to train systems. Track circuit data contains block information, speed commands, and authority signals that control train behavior.

### Function: `send_track_circuit_data(data_packet)`
Sends 18-bit track circuit commands to control train speed, authorization, and block transitions. The train system automatically parses this data and feeds it to the train controller for processing.

### 18-bit Packet Format:
The data packet uses a specific bit layout that matches real railway track circuit protocols. Each field controls different aspects of train operation.

- **Bits 17-11**: Block Number (0-127) - Target block for the train
- **Bits 10-9**: Commanded Signal (0=Stop, 1=Slow, 2=Medium, 3=Fast) - Speed command
- **Bit 8**: Authority Bit (0=No Authority, 1=Authorized) - Permission to proceed
- **Bit 7**: New Block Flag (0=No, 1=Yes) - Indicates new block information
- **Bit 6**: Next Block Entered Flag (0=No, 1=Yes) - Train entered next block
- **Bit 5**: Update Block Queue (0=No, 1=Yes) - Update internal block queue
- **Bits 4-0**: Station Number (0-31) - Station ID if applicable

### Usage Example:
```python
# Create 18-bit packet: Block 25, Medium speed, Authorized, New block, Station 5
packet = (25 << 11) | (2 << 9) | (1 << 8) | (1 << 7) | (0 << 6) | (0 << 5) | 5

# Send command to train system - returns True if successful
success = train_system.send_track_circuit_data(packet)
if success:
    print("Track circuit command sent successfully")
else:
    print("Failed to send command - check train system status")
```

### Helper Function:
This utility function simplifies creating track circuit packets by handling the bit manipulation automatically.

```python
def create_track_circuit_packet(block_number, speed_command, authorized=True, 
                               new_block=True, station_number=0):
    """
    Creates a properly formatted 18-bit track circuit packet.
    
    Args:
        block_number: Target block (0-127)
        speed_command: Speed level (0=Stop, 1=Slow, 2=Medium, 3=Fast)
        authorized: Whether train has authority to proceed
        new_block: Whether this contains new block information
        station_number: Station ID if train is approaching station (0-31)
    """
    return (
        (block_number & 0b1111111) << 11 |
        (speed_command & 0b11) << 9 |
        (1 if authorized else 0) << 8 |
        (1 if new_block else 0) << 7 |
        (0) << 6 |  # Next block entered (set by train)
        (0) << 5 |  # Update block queue (set by train)
        (station_number & 0b11111)
    )
```

---

## 3. Get Train Position

This function provides real-time access to train position data. The Track Model needs this information to make safety decisions, manage routing, and prevent collisions between multiple trains.

### Function: `get_train_distance_traveled()`
Returns the total distance the train has traveled since system initialization. This distance is calculated through physics integration of velocity over time, providing accurate position tracking.

### Usage Example:
The position data enables the Track Model to implement location-based logic and safety systems.

```python
# Get current train position in meters from starting point
distance_m = train_system.get_train_distance_traveled()
print(f"Train has traveled {distance_m:.2f} meters from origin")

# Convert to other units for different applications
distance_ft = distance_m * 3.28084  # Convert to feet for US systems
distance_km = distance_m / 1000.0   # Convert to kilometers for long distances

# Use position data for safety decisions
if distance_m > 1000.0:
    # Train has traveled far - might need to slow down
    packet = create_track_circuit_packet(75, speed_command=1, authorized=True)
    train_system.send_track_circuit_data(packet)
```

---

## Complete Example

This example demonstrates a complete Track Model integration with train creation, command sending, and position monitoring. It shows the typical workflow for managing trains.

```python
from train_system_main_sw import TrainSystemSW
from train_controller_sw.controller.data_types import TrainControllerInit, BlockInfo
import time

# Step 1: Initialize train system with track layout data
next_blocks = [
    BlockInfo(69, 50.0, 25, False, True, 2),  # Block 69: medium speed
    BlockInfo(70, 50.0, 25, False, True, 1),  # Block 70: slow for station
    BlockInfo(71, 50.0, 25, False, True, 0),  # Block 71: stop at station
    BlockInfo(72, 50.0, 25, False, True, 2)   # Block 72: resume speed
]

init_data = TrainControllerInit(
    track_color="red",
    current_block=68,
    current_commanded_speed=2,
    authorized_current_block=True,
    next_four_blocks=next_blocks,
    train_id="1",
    next_station_number=5
)

# Create software train system
train_system = TrainSystemSW(init_data, next_station_number=5)
time.sleep(1.0)  # Wait for complete initialization

# Step 2: Send initial command to start train at medium speed
packet = (69 << 11) | (2 << 9) | (1 << 8) | (1 << 7) | (0 << 6) | (0 << 5) | 0
success = train_system.send_track_circuit_data(packet)
print(f"Initial command sent: {success}")

# Step 3: Monitor train position and send commands based on location
while True:
    position = train_system.get_train_distance_traveled()
    print(f"Train position: {position:.2f}m")
    
    # Example logic: Stop train when it reaches 500m
    if position > 500.0:
        stop_packet = (70 << 11) | (0 << 9) | (1 << 8) | (1 << 7) | (0 << 6) | (0 << 5) | 5
        train_system.send_track_circuit_data(stop_packet)
        print("Sent stop command - train approaching station")
        break
        
    time.sleep(1.0)  # Update every second
```

---

## Summary

The Track Model interface provides complete control over train systems through two essential functions. These functions enable realistic railway simulation with multiple trains operating safely under central control.

**Two Interface Functions:**
1. `send_track_circuit_data(packet)` - Send 18-bit track circuit commands to control train behavior
2. `get_train_distance_traveled()` - Get real-time train position in meters for safety decisions

**Integration Pattern:**
1. Create `TrainControllerInit` with complete track layout data including BlockInfo objects
2. Initialize `TrainSystemSW` (software GUI) or `TrainSystemHW` (GPIO hardware)
3. Send track circuit commands to control train speed, authority, and routing
4. Monitor train position continuously for collision avoidance and scheduling
5. Implement safety logic based on train positions and track conditions

This interface enables the Track Model to manage multiple trains simultaneously while maintaining safety and operational efficiency.