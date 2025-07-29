# CTC-Wayside Controller Integration API

## Overview

This document describes the communication interface between the Central Traffic Control (CTC) Office and the Wayside Controller system. The CTC Office controls train operations by sending speed suggestions and movement authorities, while receiving real-time updates about train positions, track conditions, and railway crossings.

## Communication Architecture

### Message Flow
```
CTC Office ←→ Wayside Controller
     ↑              ↓
   Control      Field Data
  Commands      & Status
```

### Transport Mechanism
- **Queue-based**: Uses thread-safe Python queues for message passing
- **JSON Format**: All messages are JSON-encoded for consistency
- **Asynchronous**: Non-blocking communication to prevent UI freezing
- **Bidirectional**: Both systems can send and receive messages

## Integration Functions

### Primary Integration API

```python
def send_to_ctc(ctc_interface, message):
    """
    Send message from Wayside Controller to CTC Interface.
    
    Args:
        ctc_interface: CTC Interface instance
        message: JSON string or dict containing message data
    """

def get_from_ctc(ctc_interface):
    """
    Get message from CTC Interface to send to Wayside Controller.
    
    Args:
        ctc_interface: CTC Interface instance
        
    Returns:
        str: JSON-encoded message or None if no messages pending
    """
```

### Usage Example

```python
from CTC import create_ctc_office, send_to_ctc, get_from_ctc

# Initialize CTC Office
ctc = create_ctc_office()

# Send train update to CTC
train_data = {
    "type": "train_update",
    "data": {
        "B123": {"line": "Blue", "block": 15, "speed": 45.5},
        "R456": {"line": "Red", "block": 8, "speed": 0.0}
    }
}
send_to_ctc(ctc, train_data)

# Get control commands from CTC
outgoing_message = get_from_ctc(ctc)
if outgoing_message:
    control_data = json.loads(outgoing_message)
    # Process CTC commands
```

## Message Formats

### 1. CTC → Wayside Controller (Control Commands)

#### CTC Update Message
```json
{
    "type": "ctc_update",
    "timestamp": 1234567890.123,
    "data": {
        "suggested_speeds": {
            "B123": 50.0,
            "R456": 30.0,
            "G789": 0.0
        },
        "authorities": {
            "B123": 3,
            "R456": 2,
            "G789": 0
        },
        "maintenance_closures": {
            "Blue": [15, 16, 17],
            "Red": [8],
            "Green": []
        }
    }
}
```

#### Field Descriptions

**suggested_speeds**: 
- **Type**: `Dict[str, float]`
- **Description**: Recommended speed for each train in km/h
- **Range**: 0.0 (stop) to maximum line speed
- **Safety**: 0.0 indicates mandatory stop

**authorities**:
- **Type**: `Dict[str, int]`
- **Description**: Number of blocks ahead each train is authorized to travel
- **Range**: 0 (must stop immediately) to 5+ blocks
- **Safety**: Prevents train-to-train collisions

**maintenance_closures**:
- **Type**: `Dict[str, List[int]]`
- **Description**: Blocks closed for maintenance on each line
- **Purpose**: Informs Wayside of areas to avoid

### 2. Wayside Controller → CTC (Field Data)

#### Train Update Message
```json
{
    "type": "train_update",
    "data": {
        "B123": {
            "line": "Blue",
            "block": 15,
            "speed": 45.5,
            "status": "moving"
        },
        "R456": {
            "line": "Red", 
            "block": 8,
            "speed": 0.0,
            "status": "stopped"
        }
    }
}
```

#### Track Status Message
```json
{
    "type": "track_status",
    "data": {
        "Blue": {
            "15": "normal",
            "16": "broken_rail",
            "17": "maintenance"
        },
        "Red": {
            "8": "normal",
            "9": "signal_failure"
        }
    }
}
```

#### Railway Crossing Message
```json
{
    "type": "railway_crossing",
    "data": {
        "Blue,12": "normal",
        "Red,25": "malfunction",
        "Green,8": "normal"
    }
}
```

## Message Processing

### CTC Message Processing Flow

1. **Receive Message**: Wayside Controller calls `send_to_ctc()`
2. **Queue Message**: Message placed in incoming queue
3. **Process in Main Loop**: CTC processes queue during update cycle
4. **Update State**: Internal state updated based on message
5. **Generate Warnings**: System generates appropriate warnings
6. **Update UI**: User interface reflects new information

### Wayside Message Processing Flow

1. **Calculate Commands**: CTC calculates safe speeds and authorities
2. **Generate Message**: Commands formatted as JSON message
3. **Queue Message**: Message placed in outgoing queue
4. **Retrieve Message**: Wayside Controller calls `get_from_ctc()`
5. **Execute Commands**: Wayside implements speed and authority controls

## Safety Protocols

### 1. Speed Control Safety

```python
# CTC Speed Calculation Logic
def calculate_suggested_speed(train, maintenance_closures):
    speed = block.speed_limit_kmh  # Start with track limit
    
    # Safety override: Stop for maintenance
    if train.currentBlock in maintenance_closures[train.line]:
        speed = 0.0
    
    # Safety override: Stop for broken rails
    if track_status[train.line][train.currentBlock] == 'broken_rail':
        speed = 0.0
        
    return speed
```

### 2. Authority Management Safety

```python
# CTC Authority Calculation Logic
def calculate_authority(train, maintenance_closures):
    authority = 3  # Default safe authority
    
    # Reduce authority for train conflicts
    for other_train in trains:
        if other_train.blocks_ahead_intersect(train):
            authority = min(authority, distance_to_conflict - 1)
    
    # Reduce authority for maintenance ahead
    for block in train.route_ahead:
        if block in maintenance_closures[train.line]:
            authority = min(authority, distance_to_maintenance)
            
    return max(0, authority)  # Never negative
```

### 3. Emergency Procedures

#### Emergency Stop Protocol
```json
{
    "type": "ctc_update",
    "data": {
        "suggested_speeds": {
            "ALL_TRAINS": 0.0
        },
        "authorities": {
            "ALL_TRAINS": 0
        }
    }
}
```

#### Individual Train Emergency
```json
{
    "type": "ctc_update", 
    "data": {
        "suggested_speeds": {
            "EMERGENCY_TRAIN_ID": 0.0
        },
        "authorities": {
            "EMERGENCY_TRAIN_ID": 0
        }
    }
}
```

## Data Validation

### Incoming Message Validation

```python
def validate_train_update(message):
    """Validate incoming train update message."""
    required_fields = ['type', 'data']
    train_required = ['line', 'block', 'speed']
    
    # Validate message structure
    for field in required_fields:
        if field not in message:
            raise ValidationError(f"Missing field: {field}")
    
    # Validate train data
    for train_id, train_data in message['data'].items():
        for field in train_required:
            if field not in train_data:
                raise ValidationError(f"Train {train_id} missing {field}")
        
        # Validate line names
        if train_data['line'] not in ['Blue', 'Red', 'Green']:
            raise ValidationError(f"Invalid line: {train_data['line']}")
        
        # Validate block numbers
        if not isinstance(train_data['block'], int) or train_data['block'] <= 0:
            raise ValidationError(f"Invalid block: {train_data['block']}")
        
        # Validate speed
        if train_data['speed'] < 0:
            raise ValidationError(f"Invalid speed: {train_data['speed']}")
```

### Outgoing Message Validation

```python
def validate_ctc_update(message):
    """Validate outgoing CTC control message."""
    # Ensure all speeds are non-negative
    for train_id, speed in message['data']['suggested_speeds'].items():
        if speed < 0:
            raise ValidationError(f"Negative speed for {train_id}: {speed}")
    
    # Ensure all authorities are non-negative
    for train_id, authority in message['data']['authorities'].items():
        if authority < 0:
            raise ValidationError(f"Negative authority for {train_id}: {authority}")
```

## Error Handling

### Connection Errors
```python
try:
    send_to_ctc(ctc, message)
except Exception as e:
    logger.error(f"Failed to send message to CTC: {e}")
    # Implement retry logic or fallback
```

### Message Format Errors
```python
try:
    message = json.loads(raw_message)
    validate_message(message)
except json.JSONDecodeError:
    logger.error("Invalid JSON in message")
except ValidationError as e:
    logger.error(f"Message validation failed: {e}")
```

### Queue Overflow Protection
```python
def safe_queue_put(queue, message, timeout=1.0):
    """Safely add message to queue with timeout."""
    try:
        queue.put(message, timeout=timeout)
    except queue.Full:
        logger.warning("Message queue full, dropping oldest message")
        try:
            queue.get_nowait()  # Remove oldest
            queue.put(message, timeout=timeout)
        except queue.Empty:
            pass
```

## Performance Considerations

### Update Frequencies
- **High Frequency** (100ms): Train positions, speeds
- **Medium Frequency** (500ms): Track status, authorities
- **Low Frequency** (2s): Maintenance closures, system status

### Message Optimization
- **Batch Updates**: Combine multiple train updates
- **Delta Updates**: Only send changed data
- **Compression**: Use compact JSON formatting
- **Priority Queues**: Safety messages get priority

### Memory Management
```python
# Limit queue sizes to prevent memory growth
MAX_QUEUE_SIZE = 1000
incoming_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
outgoing_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
```

## Testing and Debugging

### Message Logging
```python
def log_message(direction, message):
    """Log all messages for debugging."""
    timestamp = datetime.now().isoformat()
    logger.debug(f"{timestamp} {direction}: {json.dumps(message, indent=2)}")

# Usage
log_message("OUTGOING", ctc_update_message)
log_message("INCOMING", train_update_message)
```

### Test Message Generation
```python
def generate_test_train_update():
    """Generate test train update for testing."""
    return {
        "type": "train_update",
        "data": {
            "TEST_001": {
                "line": "Blue",
                "block": random.randint(1, 50),
                "speed": random.uniform(0, 60),
                "status": "moving"
            }
        }
    }
```

### Integration Testing
```python
def test_ctc_wayside_integration():
    """Test complete CTC-Wayside communication cycle."""
    ctc = create_ctc_office()
    
    # Send test train data
    test_update = generate_test_train_update()
    send_to_ctc(ctc, test_update)
    
    # Allow processing time
    time.sleep(0.1)
    
    # Get response
    response = get_from_ctc(ctc)
    assert response is not None
    
    # Validate response format
    response_data = json.loads(response)
    assert response_data['type'] == 'ctc_update'
    assert 'suggested_speeds' in response_data['data']
```

## Security Considerations

### Message Authentication
- Implement message signing for production systems
- Validate message sources
- Use secure communication channels

### Input Sanitization
- Validate all incoming data types and ranges
- Prevent injection attacks through malformed messages
- Limit message sizes to prevent DoS attacks

### Access Control
- Restrict CTC interface access to authorized personnel
- Log all control commands for audit trail
- Implement role-based permissions

## Deployment Notes

### Configuration
```python
# CTC Configuration
CTC_CONFIG = {
    'update_frequency_ms': 100,
    'max_queue_size': 1000,
    'message_timeout_s': 5.0,
    'enable_debug_logging': False
}
```

### Environment Requirements
- Python 3.7+
- Thread-safe queue implementation
- JSON library
- Logging framework
- Error handling and recovery systems

### Monitoring
- Track message processing rates
- Monitor queue depths
- Alert on communication failures
- Log safety-critical events

---

*This API documentation should be updated as the system evolves. Always test integration thoroughly before production deployment.*