# CTC System - Modular Architecture

## Overview
The Central Traffic Control (CTC) system for the PAAC Light Rail System has been reorganized into a modular architecture that separates UI components from business logic for better maintainability, testing, and scalability.

## New Folder Structure

```
CTC/
├── Core/                    # Business Logic
│   ├── train_management.py    # Train operations and routing
│   ├── maintenance_manager.py # Maintenance closures and warnings
│   └── __init__.py
├── UI/                      # User Interface
│   ├── ctc_interface.py       # Main PyQt5 GUI interface
│   ├── track_visualization.py # Track display components
│   ├── ctc_display.py         # Display helper (legacy)
│   ├── ctc.py                 # CTC UI utilities (legacy)
│   └── __init__.py
├── Utils/                   # Helper Utilities
│   ├── update_worker.py       # Threading for system updates
│   └── __init__.py
├── ctc_main.py              # Main application entry point
├── __init__.py
└── README.md
```

## Key Components

### Core Package
- **TrainManager**: Handles all train operations including routing, speed calculations, and Wayside Controller communication
- **MaintenanceManager**: Manages block closures, warnings, and track status
- **Train**: Data model for train objects

### UI Package
- **CTCInterface**: Main PyQt5 GUI application with tabbed interface
- **TrackVisualization**: Matplotlib-based track visualization components
- Legacy display files (preserved for compatibility)

### Utils Package
- **UpdateWorker**: Threaded worker for handling different update frequencies (high/medium/low frequency updates)

## Usage

### Running the Application
```python
from CTC import create_ctc_office

# Create and run CTC application
app = QApplication(sys.argv)
ctc = create_ctc_office()
ctc.show()
sys.exit(app.exec_())
```

### Integration with Wayside Controller
```python
from CTC import send_to_ctc, get_from_ctc

# Send message to CTC
send_to_ctc(ctc_instance, message)

# Get message from CTC
outgoing_message = get_from_ctc(ctc_instance)
```

## Features

### Current Functionality
- **Train Management**: Dispatch, routing, and monitoring
- **Track Visualization**: Real-time track layouts for Red & Green and Blue lines
- **Maintenance Control**: Individual block closures and reopening
- **Warning System**: Track status, broken rails, and crossing malfunctions
- **Performance Optimized**: Separated update frequencies for different components

### Modular Benefits
- **Separation of Concerns**: UI logic separated from business logic
- **Testability**: Core components can be unit tested independently
- **Maintainability**: Changes to UI don't affect business logic and vice versa
- **Scalability**: Easy to add new features or modify existing ones
- **Code Reuse**: Core components can be used in different interfaces

## Future Enhancements

The modular structure makes it easy to implement wireframe requirements:
- Add new UI components in the UI package
- Extend business logic in the Core package
- Add new utilities in the Utils package
- Maintain backward compatibility through the main interface

## Migration Notes

- The main application entry point remains `ctc_main.py`
- All existing integration APIs are preserved
- Legacy files are kept in the UI folder for compatibility
- The new modular structure is fully backward compatible

## Dependencies

- PyQt5 for GUI components
- Matplotlib for track visualization
- Track_Reader for track layout data
- Standard Python libraries for threading, queuing, and data management