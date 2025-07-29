# CTC System - Comprehensive Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [User Interface](#user-interface)
5. [Communication Protocol](#communication-protocol)
6. [Safety Systems](#safety-systems)
7. [Data Models](#data-models)
8. [Installation & Setup](#installation--setup)
9. [User Guide](#user-guide)
10. [Developer Guide](#developer-guide)
11. [Troubleshooting](#troubleshooting)

## System Overview

The Central Traffic Control (CTC) System is a comprehensive train control and management system designed for the PAAC Light Rail System. It provides centralized control and monitoring of train operations across the Blue, Red, and Green lines.

### Key Features
- **Real-time Train Tracking**: Monitor train positions, speeds, and statuses
- **Automated Route Management**: Calculate optimal routes and movement authorities
- **Safety Control**: Implement speed restrictions and collision prevention
- **Maintenance Management**: Close blocks for maintenance and manage track status
- **Warning System**: Alert dispatchers to safety and operational issues
- **Track Visualization**: Graphical display of track layouts and train positions

### Target Users
- **Primary**: Train dispatchers with philosophy backgrounds and 3/5 technical comfort level
- **Secondary**: Maintenance personnel, supervisors, and system administrators

## Architecture

The CTC system follows a modular architecture that separates concerns for better maintainability:

```
CTC/
├── Core/                    # Business Logic Layer
│   ├── train_management.py    # Train operations and routing
│   ├── maintenance_manager.py # Maintenance closures and warnings
│   └── __init__.py
├── UI/                      # User Interface Layer
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

### Design Principles
1. **Separation of Concerns**: UI logic separated from business logic
2. **Modularity**: Each component has a specific responsibility
3. **Safety First**: All operations prioritize safety over convenience
4. **Real-time Updates**: System maintains current state through regular updates
5. **User-Friendly**: Designed for non-technical dispatchers

## Core Components

### 1. TrainManager (`CTC/Core/train_management.py`)

The TrainManager is the heart of the CTC system, responsible for:

#### Responsibilities
- **Train Tracking**: Maintain current positions and status of all trains
- **Speed Control**: Calculate safe speeds based on track conditions
- **Authority Management**: Determine how far trains can safely travel
- **Route Planning**: Manage train routes and destinations
- **Communication**: Interface with Wayside Controller for real-time data

#### Key Methods
- `add_train()`: Register new trains in the system
- `calculate_suggested_speed()`: Determine safe operating speed
- `calculate_authority()`: Calculate movement authority
- `process_wayside_messages()`: Handle incoming data from field
- `send_wayside_updates()`: Send control commands to field

#### Safety Features
- Collision prevention through authority management
- Speed restrictions for maintenance areas
- Emergency stop capability
- Real-time track status monitoring

### 2. MaintenanceManager (`CTC/Core/maintenance_manager.py`)

Handles all maintenance-related operations:

#### Responsibilities
- **Block Closures**: Close individual blocks for maintenance work
- **Warning Generation**: Create alerts for various system conditions
- **Status Tracking**: Monitor closed blocks and affected areas
- **Impact Assessment**: Identify stations and routes affected by closures

#### Key Methods
- `close_block()`: Close a block for maintenance
- `open_block()`: Reopen a block after maintenance
- `generate_warnings()`: Create warning list for dispatcher
- `get_closure_display_list()`: Format closures for UI display

#### Safety Features
- Prevents trains from entering maintenance areas
- Alerts dispatchers to potential service impacts
- Tracks all active closures and warnings

### 3. Train Data Model

Each train is represented by a Train object with the following attributes:

```python
class Train:
    id: str                    # Unique train identifier (e.g., "B123")
    line: str                  # Operating line ("Blue", "Red", "Green")
    currentBlock: int          # Current block location
    destinationBlock: int      # Target destination
    route: List[int]           # Planned route as block numbers
    speedKmh: float           # Current speed in km/h
    authorityBlocks: int      # Movement authority in blocks
    passengers: int           # Current passenger count
    sectionLocation: str      # Current section (A, B, C, etc.)
```

## User Interface

### Main Interface (`CTC/UI/ctc_interface.py`)

The PyQt5-based GUI provides:

#### Train Management Tab
- **Train List**: Shows all active trains with current status
- **Dispatch Controls**: Add new trains to the system
- **Speed/Authority Display**: Shows suggested speeds and authorities
- **Route Management**: Set destinations and routes for trains

#### Track Status Tab
- **Track Visualization**: Graphical representation of track layouts
- **Real-time Updates**: Live display of train positions
- **Status Indicators**: Visual indication of block conditions

#### Maintenance Tab
- **Block Closure Controls**: Close/open individual blocks
- **Maintenance List**: View all current closures
- **Impact Assessment**: See affected stations and routes

#### Warnings Tab
- **Active Warnings**: List of all current system warnings
- **Warning Types**: Broken rails, maintenance closures, crossing issues
- **Status Tracking**: Monitor warning resolution

### Track Visualization (`CTC/UI/track_visualization.py`)

Provides graphical track displays:

#### Features
- **Multi-line Support**: Blue, Red, and Green line displays
- **Real-time Updates**: Live train position updates
- **Interactive Elements**: Click to select blocks or trains
- **Status Indicators**: Visual representation of track conditions

## Communication Protocol

### Wayside Controller Integration

The CTC system communicates with Wayside Controllers using a JSON message protocol:

#### Outgoing Messages (CTC → Wayside)
```json
{
    "type": "ctc_update",
    "timestamp": 1234567890.123,
    "data": {
        "suggested_speeds": {
            "train_id": speed_kmh
        },
        "authorities": {
            "train_id": authority_blocks
        },
        "maintenance_closures": {
            "line": [block_numbers]
        }
    }
}
```

#### Incoming Messages (Wayside → CTC)
```json
{
    "type": "train_update|track_status|railway_crossing",
    "data": {
        // Message-specific data
    }
}
```

### Integration API

```python
# Send message to CTC
send_to_ctc(ctc_instance, message)

# Get message from CTC
outgoing_message = get_from_ctc(ctc_instance)
```

## Safety Systems

### 1. Collision Prevention
- **Authority Management**: Limits how far trains can travel
- **Block Occupancy**: Prevents multiple trains in same block
- **Route Validation**: Ensures safe routing decisions

### 2. Speed Control
- **Dynamic Speed Limits**: Based on track conditions
- **Emergency Stops**: Immediate stopping for safety issues
- **Condition-based Restrictions**: Reduced speeds for maintenance

### 3. Maintenance Safety
- **Block Closures**: Prevents train access to work areas
- **Warning Systems**: Alerts for all safety conditions
- **Impact Assessment**: Identifies affected services

## Data Models

### Track Data Structure
Tracks are organized hierarchically:
- **Lines**: Blue, Red, Green
- **Sections**: A, B, C, D, etc.
- **Blocks**: Individual track segments with unique numbers

### Block Information
Each block contains:
- Length, grade, speed limit, elevation
- Infrastructure (stations, switches, crossings)
- Direction restrictions
- Current status and conditions

### Communication Queues
- **Incoming Queue**: Messages from Wayside Controller
- **Outgoing Queue**: Commands to Wayside Controller
- **Thread-safe**: Uses Python queue.Queue for safe concurrent access

## Installation & Setup

### Prerequisites
- Python 3.7+
- PyQt5
- Matplotlib
- Pandas
- Track layout Excel file

### Installation Steps
1. Clone repository
2. Install dependencies: `pip install PyQt5 matplotlib pandas`
3. Configure track layout file path
4. Run: `python -m CTC.run_ctc`

### Configuration
- Track layout file: `Track Layout & Vehicle Data vF2.xlsx`
- Update frequencies configured in `UpdateWorker`
- UI styling customizable in interface components

## User Guide

### Starting the System
1. Launch CTC application
2. Load track layout data
3. System automatically begins monitoring

### Adding Trains
1. Go to Train Management tab
2. Enter train ID, line, starting block
3. Optionally set destination and route
4. Click "Dispatch Train"

### Managing Maintenance
1. Go to Maintenance tab
2. Select line and block for closure
3. Confirm closure (system alerts about impacts)
4. Monitor closure list
5. Reopen blocks when maintenance complete

### Monitoring Operations
1. Train Status: View real-time train information
2. Track Visualization: See trains on track diagrams
3. Warnings: Monitor all system alerts
4. Take corrective actions as needed

## Developer Guide

### Code Structure
- **TBTG Coding Standards**: Follow naming conventions in documentation
- **Comments**: All methods have comprehensive documentation
- **Type Hints**: Use Python type hints for clarity
- **Error Handling**: Robust error handling throughout

### Adding New Features
1. Identify appropriate module (Core, UI, Utils)
2. Follow existing patterns and conventions
3. Add comprehensive comments and documentation
4. Test thoroughly with existing functionality

### Testing
- Unit tests for Core components
- Integration tests for Wayside communication
- UI testing for interface components
- Safety testing for critical functions

### Extending the System
- New track lines: Extend data structures and UI
- Additional warnings: Enhance warning generation
- Better algorithms: Improve routing and authority calculation
- Enhanced UI: Add new tabs or visualization features

## Troubleshooting

### Common Issues

#### Trains Not Appearing
- Check Wayside Controller connection
- Verify message format
- Check train data validity

#### Maintenance Closures Not Working
- Confirm block numbers are correct
- Check line selection
- Verify track reader data

#### UI Performance Issues
- Reduce update frequency
- Check for memory leaks
- Optimize visualization rendering

#### Communication Problems
- Verify message queue status
- Check JSON formatting
- Monitor error logs

### Debug Information
- Enable debug output in track_reader.py
- Monitor console output for errors
- Check log files for detailed information
- Use Qt debugging tools for UI issues

### Support
- Check code comments for detailed explanations
- Review error messages in console output
- Consult TBTG coding standards document
- Review commit history for recent changes

---

*This documentation is comprehensive but should be updated as the system evolves. Always refer to the actual code for the most current implementation details.*