# Master Interface Integration Guide

This guide explains how to integrate your module with the Master Control Interface to receive time updates and line selection data.

## Overview

The Master Control Interface manages:
- System-wide time synchronization
- Train line selection (Blue, Red, Green)
- Module lifecycle (start/stop)

## Time Integration

### How Time Updates Work

The Master Control broadcasts time updates to all active modules at regular intervals. Your module needs to implement a method to receive these updates.

### Using the get_time() Function

The Master Control provides a `get_time()` function that returns a datetime object with the current simulation time. This function can be imported and used by any module.

#### Important Notes about get_time():
- **Call Frequency**: Since time can be accelerated up to 10x normal speed, modules should call `get_time()` at least every 0.1 seconds (100ms) to ensure they don't miss any second-level events
- **Returns**: A Python datetime object with today's date and the current simulation time
- **Thread Safe**: The function is safe to call from any thread
- **Error Handling**: Raises RuntimeError if the Master Control is not running

#### Basic Usage:

```python
from Master_Interface.master_control import get_time

# Get current simulation time
current_time = get_time()
print(f"Current simulation time: {current_time}")

# Access time components
hour = current_time.hour
minute = current_time.minute
second = current_time.second

# Use in time-based logic
if current_time.hour == 7 and current_time.minute == 0 and current_time.second == 0:
    print("7:00 AM - Start rush hour!")
```

#### Recommended Timer Pattern:

```python
import threading
from Master_Interface.master_control import get_time

class YourModule:
    def __init__(self):
        self.running = True
        self.time_thread = threading.Thread(target=self.time_monitor)
        self.time_thread.daemon = True
        self.time_thread.start()
    
    def time_monitor(self):
        """Monitor time changes every 0.1 seconds"""
        while self.running:
            try:
                current_time = get_time()
                self.handle_time_update(current_time)
                time.sleep(0.1)  # Check every 100ms
            except RuntimeError:
                # Master Control not running, stop monitoring
                break
    
    def handle_time_update(self, current_time):
        """Handle time-based events"""
        # Your time-dependent logic here
        pass
```

#### Working with Datetime Objects

The `get_time()` function returns a standard Python datetime object. Here are common operations:

```python
from Master_Interface.master_control import get_time
from datetime import datetime, timedelta

# Get current time
current_time = get_time()

# Format time as string
time_str = current_time.strftime("%H:%M:%S")  # "14:30:45"
readable_time = current_time.strftime("%I:%M %p")  # "02:30 PM"

# Compare times
if current_time.hour >= 9 and current_time.hour < 17:
    print("Business hours")

# Time arithmetic
one_hour_later = current_time + timedelta(hours=1)
thirty_minutes_ago = current_time - timedelta(minutes=30)

# Check if it's a specific time
if current_time.time() == datetime.strptime("08:00:00", "%H:%M:%S").time():
    print("It's exactly 8 AM!")

# Get time components
hour = current_time.hour      # 0-23
minute = current_time.minute  # 0-59
second = current_time.second  # 0-59

# Day of week (0=Monday, 6=Sunday)
day_of_week = current_time.weekday()

# Convert to timestamp (seconds since epoch)
timestamp = current_time.timestamp()
```

#### Performance Considerations

- The `get_time()` function is lightweight and can be called frequently
- Consider caching the result if you need it multiple times in quick succession
- For high-frequency operations, call once per cycle and reuse the result

```python
# Good: Cache time for multiple operations
current_time = get_time()
if current_time.hour == 8:
    morning_schedule()
if current_time.minute == 0:
    hourly_task()
if current_time.second == 0:
    every_minute_task()

# Less efficient: Multiple calls
if get_time().hour == 8:
    morning_schedule()
if get_time().minute == 0:
    hourly_task()
if get_time().second == 0:
    every_minute_task()
```

### Legacy Time Updates (update_time method)

For backward compatibility, modules can still implement the `update_time()` method to receive time updates from Master Control. However, using the `get_time()` function is recommended for new implementations.

### Implementation Steps

1. **Add an `update_time()` method to your main interface class:**

```python
class YourModuleInterface:
    def __init__(self):
        self.current_time = "00:00:00"
        # ... other initialization
    
    def update_time(self, time_str):
        """
        Called by Master Control to update the current time.
        
        Args:
            time_str (str): Current time in "HH:MM:SS" format
        """
        self.current_time = time_str
        
        # Update your UI if needed
        if hasattr(self, 'time_label'):
            self.time_label.setText(f"Time: {time_str}")
        
        # Trigger any time-dependent logic
        self.handle_time_update(time_str)
    
    def handle_time_update(self, time_str):
        """Override this to add time-dependent behavior"""
        pass
```

2. **The Master Control will automatically call your `update_time()` method when:**
   - Time advances (every 100ms of real time)
   - Time speed changes
   - System is paused/resumed

### Example: Time-Based Events

```python
def handle_time_update(self, time_str):
    """Example: Schedule events based on time"""
    hour, minute, second = map(int, time_str.split(':'))
    
    # Rush hour logic
    if hour == 7 and minute == 0 and second == 0:
        self.start_rush_hour_schedule()
    elif hour == 9 and minute == 0 and second == 0:
        self.end_rush_hour_schedule()
```

## Line Selection Integration

### Getting Selected Lines

When your module is initialized by Master Control, it receives the selected train lines.

### Implementation Steps

1. **Accept selected lines in your constructor:**

```python
class YourModuleInterface:
    def __init__(self, track_file="Track_Layout.xlsx", selected_lines=None):
        """
        Args:
            track_file (str): Path to track layout file
            selected_lines (list): List of selected lines ['Blue', 'Red', 'Green']
        """
        self.selected_lines = selected_lines or []
        
        # Load track data only for selected lines
        if self.selected_lines:
            self.load_track_data(track_file, self.selected_lines)
```

2. **Use TrackLayoutReader to load line-specific data:**

```python
from Track_Reader.TrackLayoutReader import TrackLayoutReader

def load_track_data(self, track_file, selected_lines):
    """Load track data for selected lines only"""
    try:
        self.track_reader = TrackLayoutReader(track_file, selected_lines=selected_lines)
        
        # Access track data
        for line in selected_lines:
            blocks = self.track_reader.get_blocks_by_line(line)
            print(f"Loaded {len(blocks)} blocks for {line} line")
            
            # Get specific infrastructure
            stations = self.track_reader.get_stations_by_line(line)
            switches = self.track_reader.get_switches_by_line(line)
            
    except Exception as e:
        print(f"Error loading track data: {e}")
```

## Complete Integration Example

Here's a minimal example of a module that integrates with Master Control:

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from Track_Reader.TrackLayoutReader import TrackLayoutReader

class MyModule(QWidget):
    def __init__(self, track_file="Track_Layout.xlsx", selected_lines=None):
        super().__init__()
        
        # Store configuration
        self.current_time = "00:00:00"
        self.selected_lines = selected_lines or []
        
        # Initialize UI
        self.setup_ui()
        
        # Load track data
        if self.selected_lines:
            self.track_reader = TrackLayoutReader(track_file, selected_lines=selected_lines)
            self.display_track_info()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Time display
        self.time_label = QLabel(f"Time: {self.current_time}")
        layout.addWidget(self.time_label)
        
        # Line info
        self.info_display = QTextEdit()
        self.info_display.setReadOnly(True)
        layout.addWidget(self.info_display)
        
        self.setLayout(layout)
    
    def update_time(self, time_str):
        """Called by Master Control to update time"""
        self.current_time = time_str
        self.time_label.setText(f"Time: {time_str}")
        
        # Add any time-based logic here
        self.check_scheduled_events(time_str)
    
    def display_track_info(self):
        """Display information about loaded track data"""
        info = f"Loaded lines: {', '.join(self.selected_lines)}\n\n"
        
        for line in self.selected_lines:
            blocks = self.track_reader.get_blocks_by_line(line)
            stations = self.track_reader.get_stations_by_line(line)
            
            info += f"{line} Line:\n"
            info += f"  - Blocks: {len(blocks)}\n"
            info += f"  - Stations: {len(stations)}\n\n"
        
        self.info_display.setText(info)
    
    def check_scheduled_events(self, time_str):
        """Example of time-based logic"""
        # Parse time
        hour, minute, second = map(int, time_str.split(':'))
        
        # Example: Log every hour
        if minute == 0 and second == 0:
            print(f"[{self.__class__.__name__}] Hour {hour:02d}:00 reached")
```

## Important Notes

1. **Time Format**: Time is always provided as "HH:MM:SS" (24-hour format)

2. **Time Speed**: The Master Control supports time acceleration (1x-10x). Your module receives updates at the accelerated rate automatically.

3. **Selected Lines**: Only load and process data for the lines provided in `selected_lines`. This ensures consistency across the system.

4. **Module Lifecycle**: 
   - Your module is created when the user clicks "Run" in Master Control
   - Time updates begin immediately after creation
   - Your module should handle being stopped/restarted

5. **Thread Safety**: If your module uses threading, ensure `update_time()` is thread-safe as it's called from the Master Control's time thread.

## Testing Your Integration

To test without the full Master Control:

```python
# Test script
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Simulate Master Control initialization
    selected_lines = ['Blue', 'Red']  # Example selection
    module = MyModule(selected_lines=selected_lines)
    
    # Simulate time updates
    test_times = ["07:00:00", "07:00:01", "07:00:02"]
    for time_str in test_times:
        module.update_time(time_str)
    
    module.show()
    sys.exit(app.exec())
```

## Questions?

If you need help with integration or have questions about the Master Control Interface, please reach out to the integration team.