# UpdateWorker Class Documentation

## Overview
The UpdateWorker class (`update_worker.py`) is a threading utility for handling system updates at different frequencies. It has been updated to work with the migrated CTC System architecture.

## Attributes

### Instance Attributes
- `ctcOffice`: Reference to the CTC Office main application
- `running` (bool): Thread running flag
- `updateCounter` (int): Counter for tracking update cycles

## Qt Signals

### Update Signals
- `updateData`: High frequency signal for data-only updates (emitted every 100ms)
- `updateTables`: Medium frequency signal for table content updates (emitted every 500ms)
- `updateVisuals`: Low frequency signal for charts/plots updates (emitted every 2 seconds)

## Methods

### Core Methods
- `__init__(ctc_office)`: Initialize with reference to CTC Office application
- `run()`: Main update loop with different frequencies for different components
- `stop()`: Stop the update worker thread safely

## Update Frequencies

### High Frequency (100ms / 10Hz)
- **Purpose**: Real-time data updates that need immediate reflection
- **Signal**: `updateData`
- **Use Cases**:
  - Train position updates
  - Block occupation status
  - Speed and authority changes
  - Emergency alerts

### Medium Frequency (500ms / 2Hz)
- **Purpose**: Table content updates that change moderately
- **Signal**: `updateTables`
- **Use Cases**:
  - Train status tables
  - Block status tables
  - Emergency/failure tables
  - System metrics displays

### Low Frequency (2 seconds / 0.5Hz)
- **Purpose**: Resource-intensive visual updates
- **Signal**: `updateVisuals`
- **Use Cases**:
  - Track layout diagrams
  - Charts and graphs
  - Throughput visualizations
  - System overview displays

## System Integration

### CTC System Integration
The UpdateWorker integrates with the new CTC System architecture:

```python
# Get the CTC system instance
ctc_system = getattr(self.ctcOffice, 'ctc_system', None)

# System tick for CTC system (replaces individual manager updates)
ctc_system.system_tick(current_time)
```

### Time Management
- Attempts to use Master Interface time for synchronized operation
- Falls back to real-time if Master Interface isn't available
- Supports time acceleration through the time multiplier system

### Error Handling
- Comprehensive exception handling to prevent thread crashes
- Automatic recovery with delayed retry on errors
- Debug logging for troubleshooting update issues

## Threading Considerations

### Thread Safety
- Runs in separate QThread to avoid blocking UI
- Uses Qt signal/slot mechanism for thread-safe communication
- All UI updates must be performed in the main thread

### Performance Optimization
- Different update frequencies prevent unnecessary computation
- High frequency updates focus on critical real-time data
- Low frequency updates handle resource-intensive operations
- Update counter prevents simultaneous heavy operations

### Resource Management
- Automatic cleanup when stopping
- Graceful shutdown with thread joining
- Memory-efficient operation with minimal overhead

## Integration Notes

### With CTC Office Application
- Designed to work with the main CTC Office GUI application
- Expects `ctc_system` attribute on the CTC Office instance
- Supports applications with or without Master Interface integration

### With UI Frameworks
- Compatible with PyQt5/PyQt6 applications
- Can be adapted for other GUI frameworks by changing signal mechanism
- Signals can be replaced with callback functions for non-Qt applications

### With System Architecture
- Replaces individual manager update loops with unified system tick
- Supports the consolidated CTC System architecture
- Maintains backward compatibility with existing UI update patterns

## Best Practices

### UI Responsiveness
1. Keep high frequency update handlers lightweight
2. Batch database/file operations in medium frequency updates
3. Perform expensive rendering in low frequency updates
4. Use background processing for non-critical updates

### Error Recovery
1. Implement robust error handling in signal handlers
2. Log errors for debugging without crashing the update loop
3. Provide fallback behavior for missing system components
4. Test update frequency changes under various load conditions

### Performance Monitoring
1. Monitor update loop performance under various conditions
2. Adjust frequencies based on system capabilities
3. Profile individual update handlers to identify bottlenecks
4. Consider adaptive frequency adjustment based on system load