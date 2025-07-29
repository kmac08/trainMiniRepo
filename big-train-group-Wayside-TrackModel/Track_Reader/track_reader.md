# Track Layout Reader Documentation
## Module Integration Guide

### Table of Contents
1. [Overview](#overview)
2. [Class Definitions](#class-definitions)
3. [Function Reference Tables](#function-reference-tables)
4. [Complete Function Documentation](#complete-function-documentation)
5. [Claude Usage Instructions](#claude-usage-instructions)

---

## Overview

The `TrackLayoutReader` provides easy-to-use functions for all system modules to access track layout information. Instead of dealing with complex data structures, each module can call simple functions to get exactly what they need.

### What It Provides
- **Numbered stations** with unique IDs for easy reference
- **Switch states** (normal=0, reverse=1) based on block numbers
- **Simple functions** for each module's specific needs
- **Comprehensive track information** in easy-to-use formats

### Installation & Import

```python
from Track_Reader.track_reader import TrackLayoutReader

# Initialize once in your module
reader = TrackLayoutReader("Track Layout & Vehicle Data vF2.xlsx")
```

---

## Class Definitions

### TrackBlock Class
```python
@dataclass
class TrackBlock:
    # Basic properties from Excel
    line: str                    # "Blue", "Red", or "Green"
    section: str                 # Section letter: "A", "B", "C", etc.
    block_number: int            # Unique block ID: 1, 2, 3...
    length_m: float              # Length in meters
    grade_percent: float         # Grade as percentage (+ uphill, - downhill)
    speed_limit_kmh: float       # Speed limit in km/hr
    elevation_m: float           # Elevation change for this block
    direction: BlockDirection    # Direction restriction
    
    # Infrastructure flags
    has_station: bool = False           # True if station exists here
    station: Optional[Station] = None   # Station object if exists
    has_switch: bool = False            # True if switch exists here
    switch: Optional[Switch] = None     # Switch object if exists
    has_crossing: bool = False          # True if railway crossing exists
    is_underground: bool = False        # True if section is underground
    
    # Calculated fields
    min_traversal_time_seconds: float = 0.0  # Minimum time to traverse at speed limit
    
    # Methods
    def can_move_to_block(self, target_block_number: int) -> bool:
        pass  # Check if movement is allowed to target block
        
    def get_direction_description(self) -> str:
        pass  # Human-readable direction description
        
    def get_infrastructure_description(self) -> str:
        pass  # Human-readable infrastructure description
```

### Station Class
```python
@dataclass
class Station:
    name: str          # Station name (e.g., "PIONEER", "EDGEBROOK")
    side: str          # Platform side: "Left", "Right", or "Both"
    station_id: int    # Unique numbered identifier for the station
    
    def __str__(self) -> str:
        return f"Station {self.station_id}: {self.name} (Platform: {self.side} side)"
```

### Switch Class
```python
@dataclass
class Switch:
    connections: List[SwitchConnection]  # All possible switch connections
    switch_type: str = "STANDARD"       # "STANDARD", "YARD_TO", "YARD_FROM", "YARD_TO_FROM"
    normal_state: int = 0                # 0 = normal (connected to lower block number)
    current_state: int = 0               # Current switch position (0 = normal, 1 = reverse)
    
    def get_destinations_from_block(self, block: Union[int, str]) -> List[Union[int, str]]:
        pass  # Get possible destinations from a block
        
    def can_travel_between(self, from_block: Union[int, str], to_block: Union[int, str]) -> bool:
        pass  # Check if travel is allowed between blocks
        
    def set_normal_state_from_blocks(self):
        pass  # Set normal state based on block numbers
        
    def get_state_description(self) -> str:
        pass  # Human-readable state description
```

### SwitchConnection Class
```python
@dataclass
class SwitchConnection:
    from_block: Union[int, str]     # Source block number or "yard"
    to_block: Union[int, str]       # Destination block number or "yard"
    direction: SwitchDirection = SwitchDirection.BIDIRECTIONAL
    
    def __str__(self) -> str:
        pass  # Human-readable connection description with direction arrows
```

### TrackLayoutReader Class
```python
class TrackLayoutReader:
    def __init__(self, excel_file_path: str, selected_lines: List[str] = None):
        self.file_path = excel_file_path
        self.selected_lines = selected_lines or ["Blue", "Red", "Green"]
        self.lines: Dict[str, List[TrackBlock]] = {}
        self.sections: Dict[str, Dict[str, List[int]]] = {}
        self.station_counter = 0
        
    # See Function Reference Tables below for all available methods
```

---

## Function Reference Tables

### Core Block Functions

| Function | Purpose | Parameters | Returns |
|----------|---------|------------|---------|
| `get_block_by_number(block_number, line=None)` | Get complete block object | `block_number: int`, `line: str (optional)` | `TrackBlock` or `None` |
| `get_block_infrastructure_summary(block_number, line=None)` | Get comprehensive block info | `block_number: int`, `line: str (optional)` | `Dict` with all block details |
| `is_block_station(block_number, line=None)` | Check if block has station | `block_number: int`, `line: str (optional)` | `bool` |
| `is_block_switch(block_number, line=None)` | Check if block has switch | `block_number: int`, `line: str (optional)` | `bool` |
| `get_block_speed_limit(block_number, line=None)` | Get block speed limit | `block_number: int`, `line: str (optional)` | `float` (km/h) or `None` |
| `get_block_length(block_number, line=None)` | Get block length | `block_number: int`, `line: str (optional)` | `float` (meters) or `None` |
| `get_adjacent_blocks(block_number, line)` | Get neighboring blocks | `block_number: int`, `line: str` | `List[int]` |

### Station Functions

| Function | Purpose | Parameters | Returns |
|----------|---------|------------|---------|
| `get_station_by_id(station_id)` | Get station info by ID | `station_id: int` | `Dict` or `None` |
| `get_line_for_station(station_id)` | Get line for station | `station_id: int` | `str` or `None` |
| `get_stations_on_line(line)` | Get all stations on line | `line: str` | `List[Dict]` |

### Switch Functions

| Function | Purpose | Parameters | Returns |
|----------|---------|------------|---------|
| `get_switch_by_block(block_number, line=None)` | Get switch info | `block_number: int`, `line: str (optional)` | `Dict` or `None` |
| `get_switches_on_line(line)` | Get all switches on line | `line: str` | `List[Dict]` |

### Summary Functions

| Function | Purpose | Parameters | Returns |
|----------|---------|------------|---------|
| `get_line_summary(line)` | Get line overview | `line: str` | `Dict` with comprehensive stats |

### Quick Reference Examples

```python
# Train Controller - Check what's at current block
block_info = reader.get_block_infrastructure_summary(current_block, "Blue")
has_station = block_info['has_station']
speed_limit = block_info['speed_limit_kmh']

# Train Controller - Get switch information
switch_info = reader.get_switch_by_block(23, "Red")
if switch_info:
    normal_state = switch_info['normal_state']  # 0 = connects to lower block
    current_state = switch_info['current_state']  # 0=normal, 1=reverse

# CTC Office - Get station by ID
station = reader.get_station_by_id(5)
if station:
    station_name = station['name']
    station_line = station['line']

# Track Model - Get all stations on a line
stations = reader.get_stations_on_line("Blue")

# All modules - Get line overview
summary = reader.get_line_summary("Blue")
total_blocks = summary['total_blocks']
station_count = summary['stations']['count']
```

---

## Complete Function Documentation

### Core Block Functions

#### `get_block_by_number(block_number, line=None)`
**Purpose:** Get complete TrackBlock object for detailed access

**Input Parameters:**
- `block_number` (int): Block number to find
- `line` (str, optional): Line to search ("Blue", "Red", "Green"). If None, searches all lines

**Output:** 
- `TrackBlock` object if found, `None` if not found
- TrackBlock contains all block properties (length, speed_limit, grade, etc.) and infrastructure

**Example:**
```python
block = reader.get_block_by_number(15, "Blue")
if block:
    print(f"Block {block.block_number}: {block.length_m}m, {block.speed_limit_kmh} km/h")
```

---

#### `get_block_infrastructure_summary(block_number, line=None)`
**Purpose:** Get comprehensive dictionary with all block information

**Input Parameters:**
- `block_number` (int): Block number to analyze
- `line` (str, optional): Line to search. If None, searches all lines

**Output Dictionary:**
```python
{
    "block_found": bool,           # True if block exists
    "block_number": int,           # The requested block number
    "line": str,                   # Line name ("Blue", "Red", "Green")
    "section": str,                # Section letter (A, B, C, etc.)
    "has_station": bool,           # True if block has a station
    "station_info": {              # None if no station
        "station_id": int,         # Unique station ID number
        "name": str,               # Station name
        "platform_side": str       # "Left", "Right", or "Both"
    },
    "has_switch": bool,            # True if block has a switch
    "switch_info": {               # None if no switch
        "switch_type": str,        # "STANDARD", "YARD_TO", etc.
        "normal_state": int,       # 0 (connects to lower block)
        "current_state": int,      # 0=normal, 1=reverse
        "state_description": str   # Human-readable state
    },
    "has_crossing": bool,          # True if railway crossing
    "is_underground": bool,        # True if underground
    "speed_limit_kmh": float,      # Speed limit in km/h
    "length_m": float,             # Block length in meters
    "grade_percent": float,        # Grade percentage
    "elevation_m": float,          # Elevation change in meters
    "direction": str,              # "FORWARD", "BACKWARD", "BIDIRECTIONAL"
    "min_traversal_time_seconds": float  # Minimum time to traverse
}
```

---

#### `is_block_station(block_number, line=None)`
**Purpose:** Quick check if a block contains a station

**Input Parameters:**
- `block_number` (int): Block number to check
- `line` (str, optional): Line to search. If None, searches all lines

**Output:** 
- `bool`: `True` if block has a station, `False` otherwise

---

#### `is_block_switch(block_number, line=None)`
**Purpose:** Quick check if a block contains a switch

**Input Parameters:**
- `block_number` (int): Block number to check
- `line` (str, optional): Line to search. If None, searches all lines

**Output:** 
- `bool`: `True` if block has a switch, `False` otherwise

---

#### `get_block_speed_limit(block_number, line=None)`
**Purpose:** Get the speed limit for a specific block

**Input Parameters:**
- `block_number` (int): Block number to check
- `line` (str, optional): Line to search. If None, searches all lines

**Output:** 
- `float`: Speed limit in km/h, or `None` if block not found

---

#### `get_block_length(block_number, line=None)`
**Purpose:** Get the length of a specific block

**Input Parameters:**
- `block_number` (int): Block number to check
- `line` (str, optional): Line to search. If None, searches all lines

**Output:** 
- `float`: Block length in meters, or `None` if block not found

---

#### `get_adjacent_blocks(block_number, line)`
**Purpose:** Get blocks that are numerically adjacent (±1 block number)

**Input Parameters:**
- `block_number` (int): Block number to find neighbors for
- `line` (str): Line to search ("Blue", "Red", "Green")

**Output:** 
- `List[int]`: List of adjacent block numbers (e.g., [9, 11] for block 10)

---

### Station Functions

#### `get_station_by_id(station_id)`
**Purpose:** Get complete station information by unique station ID

**Input Parameters:**
- `station_id` (int): Unique station ID number

**Output Dictionary:**
```python
{
    "station_id": int,        # Unique station ID
    "name": str,              # Station name (e.g., "PIONEER")
    "platform_side": str,     # "Left", "Right", or "Both"
    "line": str,              # Line name ("Blue", "Red", "Green")
    "block_number": int,      # Block number where station is located
    "section": str            # Section letter (A, B, C, etc.)
}
```
Returns `None` if station ID not found.

---

#### `get_line_for_station(station_id)`
**Purpose:** Get which line a station is on

**Input Parameters:**
- `station_id` (int): Unique station ID number

**Output:** 
- `str`: Line name ("Blue", "Red", "Green"), or `None` if station not found

---

#### `get_stations_on_line(line)`
**Purpose:** Get all stations on a specific line, sorted by block number

**Input Parameters:**
- `line` (str): Line name ("Blue", "Red", "Green")

**Output:** 
- `List[Dict]`: List of station dictionaries (same format as `get_station_by_id`)

---

### Switch Functions

#### `get_switch_by_block(block_number, line=None)`
**Purpose:** Get complete switch information for a block

**Input Parameters:**
- `block_number` (int): Block number to check
- `line` (str, optional): Line to search. If None, searches all lines

**Output Dictionary:**
```python
{
    "block_number": int,           # Block number with switch
    "line": str,                   # Line name
    "switch_type": str,            # "STANDARD", "YARD_TO", "YARD_FROM", "YARD_TO_FROM"
    "normal_state": int,           # 0 (connects to lower block number)
    "current_state": int,          # 0=normal, 1=reverse
    "state_description": str,      # "Switch state: Normal (0)" or "Switch state: Reverse (1)"
    "connections": [               # List of all switch connections
        {
            "from_block": int/str, # Source block number or "yard"
            "to_block": int/str,   # Destination block number or "yard"
            "direction": str,      # "BIDIRECTIONAL", "TO_ONLY", "FROM_ONLY"
            "description": str     # Human-readable connection description
        }
    ],
    "description": str             # Overall switch description
}
```
Returns `None` if no switch found at the block.

---

#### `get_switches_on_line(line)`
**Purpose:** Get all switches on a specific line, sorted by block number

**Input Parameters:**
- `line` (str): Line name ("Blue", "Red", "Green")

**Output:** 
- `List[Dict]`: List of switch dictionaries (same format as `get_switch_by_block`)

---

### Summary Functions

#### `get_line_summary(line)`
**Purpose:** Get comprehensive overview of an entire line

**Input Parameters:**
- `line` (str): Line name ("Blue", "Red", "Green")

**Output Dictionary:**
```python
{
    "line": str,                   # Line name
    "total_blocks": int,           # Total number of blocks
    "block_range": {               # Block number range
        "min": int,                # Lowest block number
        "max": int                 # Highest block number
    },
    "total_length_m": float,       # Total line length in meters
    "stations": {
        "count": int,              # Number of stations
        "station_ids": [int],      # List of station IDs
        "names": [str]             # List of station names
    },
    "switches": {
        "count": int,              # Number of switches
        "blocks": [int]            # Block numbers with switches
    },
    "crossings": {
        "count": int,              # Number of railway crossings
        "blocks": [int]            # Block numbers with crossings
    },
    "underground": {
        "count": int,              # Number of underground blocks
        "blocks": [int]            # Underground block numbers
    },
    "sections": [str]              # List of section letters
}
```

---

## Claude Usage Instructions

When Claude needs to help users with track layout information and this documentation is not sufficient, follow these steps:

### 1. Reading the Track Reader File
If you need to understand the implementation details:

```python
# First, read the track_reader.py file to understand the code structure
# Look for class definitions, method implementations, and data structures
```

### 2. Understanding Function Behavior
If a function's behavior is unclear from the documentation:

1. **Read the function implementation** in track_reader.py
2. **Look at the return statements** to understand exact output format
3. **Check error handling** to understand edge cases
4. **Examine the parsing logic** to understand how data is processed from Excel

### 3. Troubleshooting Issues
When users report problems:

1. **Check the Excel file format** - Look at the `_load_track_data()` method
2. **Verify function parameters** - Check if the user is passing correct data types
3. **Review error messages** - The code includes debug output and error handling
4. **Test with sample data** - Use the examples in this documentation

### 4. Understanding Data Flow
To help users understand how data flows through the system:

1. **Excel parsing** happens in `_load_track_data()`
2. **Station numbering** is handled by `station_counter`
3. **Switch state setting** occurs in `set_normal_state_from_blocks()`
4. **Infrastructure parsing** is in `_parse_infrastructure()`

### 5. Common User Questions
For typical questions about track layout:

- **"How do I get block information?"** → Use `get_block_infrastructure_summary()`
- **"How do I find stations?"** → Use `get_station_by_id()` or `get_stations_on_line()`
- **"How do switch states work?"** → Normal state (0) = lower block, Reverse state (1) = higher block
- **"What's in the Excel file?"** → Check the file reading and parsing methods

### 6. Advanced Usage
For complex scenarios, read the track_reader.py file to understand:

- How the `TrackBlock` class stores all block information
- How switches and connections are modeled
- How the station numbering system works
- How different infrastructure types are detected and parsed

### 7. Integration Help
When helping users integrate with other modules:

1. **Understand the user's module** (Train Controller, Track Model, CTC Office)
2. **Identify what information they need** from the track layout
3. **Recommend appropriate functions** from the reference tables above
4. **Provide code examples** using the patterns in this documentation

Remember: The track_reader.py file contains the definitive implementation. This documentation provides the interface, but the source code shows exactly how everything works internally.