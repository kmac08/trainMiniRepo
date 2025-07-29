"""
Track Layout Reader for Train Control System
============================================
This module reads track layout data from Excel files and provides
easy-to-use data structures for the CTC Office, Track Controller,
and Track Model components.

Designed with non-technical dispatchers in mind - provides clear,
intuitive access to track information.
"""

import pandas as pd
import json
import re
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum


# Debug flag - set to True to enable detailed debugging output
DEBUG_PARSING = False
DEBUG_SHOW_ALL_OBJECTS = False  # New flag for comprehensive object dump

# To turn off debug output:
# Set DEBUG_PARSING = False to disable parsing debug messages
# Set DEBUG_SHOW_ALL_OBJECTS = False to disable the comprehensive object dump


class InfrastructureType(Enum):
    """Types of infrastructure that can exist on a track block"""
    STATION = "STATION"
    SWITCH = "SWITCH"
    CROSSING = "CROSSING"
    NONE = "NONE"


class SwitchDirection(Enum):
    """Direction restrictions for switches"""
    BIDIRECTIONAL = "BIDIRECTIONAL"  # Traffic can flow both ways
    TO_ONLY = "TO_ONLY"              # Traffic can only go TO the destination
    FROM_ONLY = "FROM_ONLY"          # Traffic can only come FROM the destination


class BlockDirection(Enum):
    """Direction of allowed movement for a track block"""
    FORWARD = "FORWARD"           # Movement to higher block numbers
    BACKWARD = "BACKWARD"         # Movement to lower block numbers
    BIDIRECTIONAL = "BIDIRECTIONAL"  # Movement in either direction


@dataclass
class Station:
    """Represents a station on the track"""
    name: str
    side: str  # "Left", "Right", or "Both"
    station_id: int  # Unique numbered identifier for the station

    def __str__(self):
        return f"Station {self.station_id}: {self.name} (Platform: {self.side} side)"


@dataclass
class SwitchConnection:
    """Represents a single connection in a switch"""
    from_block: Union[int, str]  # Block number or "yard"
    to_block: Union[int, str]    # Block number or "yard"
    direction: SwitchDirection = SwitchDirection.BIDIRECTIONAL

    def __str__(self):
        from_str = f"Block {self.from_block}" if isinstance(self.from_block, int) else str(self.from_block).title()
        to_str = f"Block {self.to_block}" if isinstance(self.to_block, int) else str(self.to_block).title()

        if self.direction == SwitchDirection.BIDIRECTIONAL:
            return f"{from_str} ↔ {to_str}"
        elif self.direction == SwitchDirection.TO_ONLY:
            return f"{from_str} → {to_str}"
        else:  # FROM_ONLY
            return f"{from_str} ← {to_str}"


@dataclass
class Switch:
    """Represents a track switch with multiple possible connections"""
    connections: List[SwitchConnection]
    switch_type: str = "STANDARD"  # "STANDARD", "YARD_TO", "YARD_FROM", "YARD_TO_FROM"
    normal_state: int = 0  # 0 = normal (connected to lower block number), 1 = reverse (connected to higher block number)
    current_state: int = 0  # Current switch position (0 = normal, 1 = reverse)

    def __str__(self):
        if len(self.connections) == 1:
            return f"Switch: {self.connections[0]}"
        else:
            conn_strs = [str(conn) for conn in self.connections]
            return f"Switch: {'; '.join(conn_strs)}"

    def get_destinations_from_block(self, block: Union[int, str]) -> List[Union[int, str]]:
        """Get all possible destinations from a given block"""
        destinations = []
        for conn in self.connections:
            if conn.from_block == block and conn.direction != SwitchDirection.FROM_ONLY:
                destinations.append(conn.to_block)
            elif conn.to_block == block and conn.direction != SwitchDirection.TO_ONLY:
                destinations.append(conn.from_block)
        return destinations

    def can_travel_between(self, from_block: Union[int, str], to_block: Union[int, str]) -> bool:
        """Check if travel is allowed between two blocks through this switch"""
        for conn in self.connections:
            if ((conn.from_block == from_block and conn.to_block == to_block and
                 conn.direction != SwitchDirection.FROM_ONLY) or
                (conn.from_block == to_block and conn.to_block == from_block and
                 conn.direction != SwitchDirection.TO_ONLY)):
                return True
        return False

    def set_normal_state_from_blocks(self):
        """Set the normal state based on which connection has the lower block number"""
        if not self.connections:
            return
        
        # Find the connection with the lowest block number
        min_block = float('inf')
        for conn in self.connections:
            # Only consider numeric blocks (not yard connections)
            if isinstance(conn.from_block, int):
                min_block = min(min_block, conn.from_block)
            if isinstance(conn.to_block, int):
                min_block = min(min_block, conn.to_block)
        
        # Normal state (0) connects to lower block number
        self.normal_state = 0
        self.current_state = 0

    def get_state_description(self) -> str:
        """Get human-readable description of switch state"""
        state_str = "Normal" if self.current_state == 0 else "Reverse"
        return f"Switch state: {state_str} ({self.current_state})"


@dataclass
class TrackBlock:
    """
    Represents a single block of track.
    All information a dispatcher needs about a track segment.
    """
    line: str  # "Blue", "Red", or "Green"
    section: str  # Section letter (A, B, C, etc.)
    block_number: int
    length_m: float  # Length in meters
    grade_percent: float  # Grade as percentage
    speed_limit_kmh: float  # Speed limit in km/hr
    elevation_m: float  # Elevation in meters
    direction: BlockDirection = BlockDirection.BIDIRECTIONAL  # Direction of allowed movement

    # Infrastructure on this block
    has_station: bool = False
    station: Optional[Station] = None
    has_switch: bool = False
    switch: Optional[Switch] = None
    has_crossing: bool = False
    is_underground: bool = False  # New attribute for underground sections

    # Calculated fields - minimum time to traverse at speed limit
    min_traversal_time_seconds: float = 0.0  # Minimum time to traverse this block

    def can_move_to_block(self, target_block_number: int) -> bool:
        """
        Check if movement is allowed from this block to the target block.

        Args:
            target_block_number: Block number to move to

        Returns:
            True if movement is allowed based on block direction
        """
        if self.direction == BlockDirection.BIDIRECTIONAL:
            return True
        elif self.direction == BlockDirection.FORWARD:
            return target_block_number > self.block_number
        elif self.direction == BlockDirection.BACKWARD:
            return target_block_number < self.block_number
        else:
            return True  # Default to allowing movement

    def get_direction_description(self) -> str:
        """Get human-readable description of block direction"""
        if self.direction == BlockDirection.FORWARD:
            return f"Forward only (→ higher block numbers)"
        elif self.direction == BlockDirection.BACKWARD:
            return f"Backward only (→ lower block numbers)"
        else:
            return "Bidirectional (↔)"

    def get_infrastructure_description(self) -> str:
        """Get human-readable description of infrastructure"""
        items = []
        if self.has_station and self.station:
            items.append(str(self.station))
        if self.has_switch and self.switch:
            items.append(str(self.switch))
        if self.has_crossing:
            items.append("Railway Crossing")
        if self.is_underground:
            items.append("Underground")

        return "; ".join(items) if items else "No special infrastructure"


class TrackLayoutReader:
    """
    Main class for reading and managing track layout data.
    Provides easy access to track information for dispatchers.
    """

    def __init__(self, excel_file_path: str, selected_lines: List[str] = None):
        """
        Initialize the track layout reader with an Excel file.

        Args:
            excel_file_path: Path to the track layout Excel file
            selected_lines: List of lines to load (e.g., ['Blue', 'Red']). 
                          If None, loads all lines.
        """
        self.file_path = excel_file_path
        
        # Default to all lines if none specified
        if selected_lines is None:
            selected_lines = ["Blue", "Red", "Green"]
        
        self.selected_lines = selected_lines
        
        # Initialize data structures only for selected lines
        self.lines: Dict[str, List[TrackBlock]] = {}
        self.sections: Dict[str, Dict[str, List[int]]] = {}
        
        # Station counter for unique IDs
        self.station_counter = 0
        
        for line in selected_lines:
            self.lines[line] = []
            self.sections[line] = {}
        
        self._load_track_data()

        # Debug output all objects if enabled
        if DEBUG_SHOW_ALL_OBJECTS:
            self._debug_print_all_objects()

    def _debug_print(self, *args, **kwargs):
        """Print debug information only if DEBUG_PARSING is True"""
        if DEBUG_PARSING:
            print("[DEBUG]", *args, **kwargs)

    def _debug_print_all_objects(self):
        """Print comprehensive debug output of all parsed objects"""
        print("\n" + "="*80)
        print("=== COMPREHENSIVE DEBUG OUTPUT - ALL PARSED OBJECTS ===")
        print("="*80)

        for line_name in self.selected_lines:
            print(f"\n=== {line_name.upper()} LINE ===")
            blocks = self.lines.get(line_name, [])
            print(f"Total blocks: {len(blocks)}")

            # Print sections summary
            sections = self.sections.get(line_name, {})
            print(f"Sections: {list(sections.keys())}")

            # Print detailed block information
            print(f"\nDetailed Block Information for {line_name} Line:")
            print("-" * 70)

            for block in blocks:
                print(f"\nBlock #{block.block_number} (Section {block.section}):")
                print(f"  Length: {block.length_m}m")
                print(f"  Speed Limit: {block.speed_limit_kmh} km/hr")
                print(f"  Grade: {block.grade_percent}%")
                print(f"  Elevation: {block.elevation_m}m")
                print(f"  Direction: {block.get_direction_description()}")
                print(f"  Min Traversal Time: {block.min_traversal_time_seconds:.1f} seconds")

                # Infrastructure details
                if block.has_station or block.has_switch or block.has_crossing or block.is_underground:
                    print(f"  Infrastructure:")
                    if block.has_station and block.station:
                        print(f"    - Station: '{block.station.name}' (Platform: {block.station.side})")
                    if block.has_switch and block.switch:
                        print(f"    - Switch: {block.switch}")
                        print(f"      Type: {block.switch.switch_type}")
                        print(f"      Connections:")
                        for i, conn in enumerate(block.switch.connections):
                            print(f"        {i+1}. {conn}")
                    if block.has_crossing:
                        print(f"    - Railway Crossing")
                    if block.is_underground:
                        print(f"    - Underground")
                else:
                    print(f"  Infrastructure: None")

            # Summary statistics
            print(f"\n{line_name} Line Statistics:")
            print(f"  Total Blocks: {len(blocks)}")
            print(f"  Stations: {sum(1 for b in blocks if b.has_station)}")
            print(f"  Switches: {sum(1 for b in blocks if b.has_switch)}")
            print(f"  Crossings: {sum(1 for b in blocks if b.has_crossing)}")
            print(f"  Underground: {sum(1 for b in blocks if b.is_underground)}")

            # List all stations with details
            stations = [b for b in blocks if b.has_station and b.station]
            if stations:
                print(f"\n  All Stations on {line_name} Line:")
                for b in stations:
                    print(f"    - Block {b.block_number}: '{b.station.name}' ({b.station.side} platform)")

            # List all switches with details
            switches = [b for b in blocks if b.has_switch and b.switch]
            if switches:
                print(f"\n  All Switches on {line_name} Line:")
                for b in switches:
                    print(f"    - Block {b.block_number}: {b.switch}")

        print("\n" + "="*80)
        print("=== END OF DEBUG OUTPUT ===")
        print("="*80 + "\n")

    def _parse_switch_string(self, switch_str: str, block_num: int) -> Optional[Switch]:
        """
        Parse switch string into Switch object.

        Handles formats:
        - Switch (5-6): Simple bidirectional switch
        - Switch (5-6; 5-11): Multi-destination switch
        - SWITCH TO/FROM YARD (75-yard): Bidirectional yard connection
        - SWITCH TO YARD (57-yard): One-way to yard
        - SWITCH FROM YARD (Yard-63): One-way from yard
        """
        self._debug_print(f"    Parsing switch string: '{switch_str}'")

        switch_str_upper = switch_str.upper()
        connections = []
        switch_type = "STANDARD"

        # Extract content within parentheses
        paren_match = re.search(r'\((.*?)\)', switch_str)
        if not paren_match:
            self._debug_print(f"    No parentheses found in switch string")
            return None

        connections_str = paren_match.group(1).strip()
        self._debug_print(f"    Connections string: '{connections_str}'")

        # Determine switch type and direction from the prefix
        direction = SwitchDirection.BIDIRECTIONAL
        if "TO/FROM YARD" in switch_str_upper or "FROM/TO YARD" in switch_str_upper:
            switch_type = "YARD_TO_FROM"
            direction = SwitchDirection.BIDIRECTIONAL
        elif "TO YARD" in switch_str_upper:
            switch_type = "YARD_TO"
            direction = SwitchDirection.TO_ONLY
        elif "FROM YARD" in switch_str_upper:
            switch_type = "YARD_FROM"
            direction = SwitchDirection.FROM_ONLY

        # Split connections by semicolon
        connection_parts = [part.strip() for part in connections_str.split(';')]

        for part in connection_parts:
            if not part:
                continue

            self._debug_print(f"      Processing connection part: '{part}'")

            # Parse individual connection (e.g., "5-6", "75-yard", "yard-63")
            connection_match = re.match(r'(\w+)\s*-\s*(\w+)', part.lower())
            if connection_match:
                from_str = connection_match.group(1).strip()
                to_str = connection_match.group(2).strip()

                # Convert to appropriate types (int for block numbers, str for yard)
                from_block = int(from_str) if from_str.isdigit() else from_str
                to_block = int(to_str) if to_str.isdigit() else to_str

                # Create connection with appropriate direction
                conn = SwitchConnection(
                    from_block=from_block,
                    to_block=to_block,
                    direction=direction
                )

                connections.append(conn)
                self._debug_print(f"        Added connection: {conn}")
            else:
                self._debug_print(f"        Could not parse connection: '{part}'")

        if connections:
            switch = Switch(connections=connections, switch_type=switch_type)
            # Set normal state based on block numbers
            switch.set_normal_state_from_blocks()
            self._debug_print(f"    Created switch: {switch}")
            self._debug_print(f"    Switch state set to: {switch.get_state_description()}")
            return switch
        else:
            self._debug_print(f"    No valid connections found")
            return None

    def _smart_split_infrastructure(self, infra_str: str) -> List[str]:
        """
        Intelligently split infrastructure string, respecting parentheses.

        For example: "STATION; SWITCH (15-16; 1-16); UNDERGROUND"
        Should split into: ["STATION", "SWITCH (15-16; 1-16)", "UNDERGROUND"]
        Not: ["STATION", "SWITCH (15-16", "1-16)", "UNDERGROUND"]
        """
        items = []
        current_item = ""
        paren_depth = 0

        for char in infra_str:
            if char == '(':
                paren_depth += 1
                current_item += char
            elif char == ')':
                paren_depth -= 1
                current_item += char
            elif char == ';' and paren_depth == 0:
                # Only split on semicolon if we're not inside parentheses
                if current_item.strip():
                    items.append(current_item.strip())
                current_item = ""
            else:
                current_item += char

        # Add the last item
        if current_item.strip():
            items.append(current_item.strip())

        return items

    def _parse_block_direction(self, direction_str: str) -> BlockDirection:
        """
        Parse block direction string from Excel data.

        Args:
            direction_str: Direction string from Excel ("forward", "backward", "bidirectional", etc.)

        Returns:
            BlockDirection enum value
        """
        if pd.isna(direction_str) or not direction_str:
            self._debug_print(f"    No direction specified, defaulting to BIDIRECTIONAL")
            return BlockDirection.BIDIRECTIONAL

        direction_clean = str(direction_str).strip().upper()
        self._debug_print(f"    Parsing direction: '{direction_str}' -> '{direction_clean}'")

        # Handle various ways direction might be specified
        if direction_clean in ["FORWARD", "FWD", "F", "→", "FORWARDS"]:
            return BlockDirection.FORWARD
        elif direction_clean in ["BACKWARD", "BACKWARDS", "BWD", "B", "←", "REVERSE", "REV"]:
            return BlockDirection.BACKWARD
        elif direction_clean in ["BIDIRECTIONAL", "BOTH", "BI", "BIDIR", "↔", "BOTH WAYS", "EITHER"]:
            return BlockDirection.BIDIRECTIONAL
        else:
            # Log unknown direction and default to bidirectional
            self._debug_print(f"    Unknown direction '{direction_str}', defaulting to BIDIRECTIONAL")
            return BlockDirection.BIDIRECTIONAL

    def _normalize_platform_side(self, side_str: str) -> str:
        """
        Normalize platform side strings.
        Left, Right, or Both all mean the platform serves both sides.
        """
        if pd.isna(side_str) or not side_str:
            return "Both"

        side_upper = str(side_str).strip().upper()

        # All platform configurations mean trains can be served
        if side_upper in ["LEFT", "RIGHT", "BOTH", "L", "R", "B"]:
            return "Both"

        return "Both"  # Default to Both

    def _parse_infrastructure(self, infra_str: str, block_num: int, line: str) -> Tuple[
        bool, Optional[Station], bool, Optional[Switch], bool, bool]:
        """
        Parse infrastructure string to identify stations, switches, etc.

        Format:
        - STATION; STATION_NAME - station with given name
        - Switch (5-6) - simple switch
        - Switch (5-6; 5-11) - multi-destination switch
        - SWITCH TO/FROM YARD (75-yard) - bidirectional yard switch
        - SWITCH TO YARD (57-yard) - one-way to yard
        - SWITCH FROM YARD (Yard-63) - one-way from yard
        - UNDERGROUND - underground section
        - RAILWAY CROSSING - railway crossing
        - Multiple items separated by semicolons (respecting parentheses)

        Returns: (has_station, station, has_switch, switch, has_crossing, is_underground)
        """

        self._debug_print(f"Parsing infrastructure for {line} Line Block {block_num}: '{infra_str}'")

        if pd.isna(infra_str) or infra_str is None:
            self._debug_print(f"  -> No infrastructure data (NaN/None)")
            return False, None, False, None, False, False

        infra_str = str(infra_str).strip()

        has_station = False
        station = None
        has_switch = False
        switch = None
        has_crossing = False
        is_underground = False

        # Use smart splitting that respects parentheses
        items = self._smart_split_infrastructure(infra_str)
        self._debug_print(f"  Smart split result: {items}")

        for item in items:
            if not item:  # Skip empty items
                continue

            item_upper = item.upper()
            self._debug_print(f"  Processing item: '{item}'")

            # Check for SWITCH with various formats (check this FIRST before station)
            if 'SWITCH' in item_upper:
                has_switch = True
                switch = self._parse_switch_string(item, block_num)
                if switch:
                    self._debug_print(f"  -> Successfully parsed switch: {switch}")
                else:
                    # Create default switch if parsing failed
                    self._debug_print(f"  -> Switch parsing failed, creating default switch")
                    default_conn = SwitchConnection(
                        from_block=block_num,
                        to_block=block_num + 1,
                        direction=SwitchDirection.BIDIRECTIONAL
                    )
                    switch = Switch(connections=[default_conn], switch_type="STANDARD")
                    switch.set_normal_state_from_blocks()

            # Check for STATION
            elif item_upper.startswith('STATION'):
                has_station = True
                # Extract station name - it should be after "STATION" or after a semicolon/space
                if 'STATION' in item:
                    # Split by STATION and take what's after it
                    parts = item.split('STATION', 1)
                    if len(parts) > 1 and parts[1].strip():
                        station_name = parts[1].strip()
                        # Remove any leading punctuation
                        if station_name and station_name[0] in [';', ':', ' ']:
                            station_name = station_name[1:].strip()
                        if station_name:
                            self.station_counter += 1
                            station = Station(name=station_name, side="Both", station_id=self.station_counter)
                            self._debug_print(f"  -> Found station: '{station_name}' (ID: {self.station_counter})")
                        else:
                            # No name provided, use default
                            self.station_counter += 1
                            station = Station(name=f"Station {block_num}", side="Both", station_id=self.station_counter)
                            self._debug_print(f"  -> Station with no name, using default (ID: {self.station_counter})")
                    else:
                        # Check if there's another item that might be the station name
                        # Look at the next item in the list
                        try:
                            idx = items.index(item)
                            if idx + 1 < len(items) and items[idx + 1].strip():
                                # Next item might be the station name
                                next_item = items[idx + 1].strip()
                                if not any(keyword in next_item.upper() for keyword in ['SWITCH', 'UNDERGROUND', 'CROSSING']):
                                    self.station_counter += 1
                                    station = Station(name=next_item, side="Both", station_id=self.station_counter)
                                    self._debug_print(f"  -> Found station name in next item: '{next_item}' (ID: {self.station_counter})")
                                    # Mark this item as processed
                                    items[idx + 1] = ""
                                else:
                                    self.station_counter += 1
                                    station = Station(name=f"Station {block_num}", side="Both", station_id=self.station_counter)
                                    self._debug_print(f"  -> Station with no name, using default (ID: {self.station_counter})")
                            else:
                                self.station_counter += 1
                                station = Station(name=f"Station {block_num}", side="Both", station_id=self.station_counter)
                                self._debug_print(f"  -> Station with no name, using default (ID: {self.station_counter})")
                        except ValueError:
                            self.station_counter += 1
                            station = Station(name=f"Station {block_num}", side="Both", station_id=self.station_counter)
                            self._debug_print(f"  -> Station with no name, using default (ID: {self.station_counter})")

            # Check for UNDERGROUND
            elif 'UNDERGROUND' in item_upper:
                is_underground = True
                self._debug_print(f"  -> Found underground section")

            # Check for RAILWAY CROSSING
            elif any(crossing_term in item_upper for crossing_term in ['CROSSING', 'RAILWAY CROSSING', 'X-ING', 'XING']):
                has_crossing = True
                self._debug_print(f"  -> Found railway crossing")

            # If none of the above keywords, it might be a station name without STATION prefix
            elif item and not any(keyword in item_upper for keyword in ['SWITCH', 'UNDERGROUND', 'CROSSING']):
                # This could be a standalone station name
                # But be careful - don't treat fragments like "1-16)" as station names
                if not has_station and not re.search(r'\d+-\d+\)', item):  # Avoid switch fragments
                    has_station = True
                    self.station_counter += 1
                    station = Station(name=item, side="Both", station_id=self.station_counter)
                    self._debug_print(f"  -> Treating standalone text as station: '{item}' (ID: {self.station_counter})")
                else:
                    self._debug_print(f"  -> Ignoring potential switch fragment: '{item}'")

        self._debug_print(f"  -> Final result: station={has_station}, switch={has_switch}, crossing={has_crossing}, underground={is_underground}")
        return has_station, station, has_switch, switch, has_crossing, is_underground

    def _load_track_data(self):
        """Load track data from the Excel file"""
        try:
            # Read the Excel file
            self._debug_print(f"Loading track data from: {self.file_path}")
            excel_data = pd.ExcelFile(self.file_path)
            self._debug_print(f"Available sheets: {excel_data.sheet_names}")

            # Process each selected line
            for line_name in self.selected_lines:
                sheet_name = f"{line_name} Line"
                if sheet_name not in excel_data.sheet_names:
                    print(f"Warning: {sheet_name} not found in Excel file")
                    continue

                self._debug_print(f"\n=== Processing {sheet_name} ===")

                # Read the sheet
                df = pd.read_excel(excel_data, sheet_name)
                self._debug_print(f"Sheet columns: {list(df.columns)}")
                self._debug_print(f"Sheet shape: {df.shape}")

                # Show first few rows for debugging
                if DEBUG_PARSING and len(df) > 0:
                    self._debug_print("First few rows:")
                    for i in range(min(5, len(df))):
                        row = df.iloc[i]
                        self._debug_print(f"  Row {i}: Block={row.get('Block Number')}, Section={row.get('Section')}, Infrastructure='{row.get('Infrastructure')}'")

                block_count = 0
                station_count = 0
                switch_count = 0
                crossing_count = 0

                # Process each row
                for idx, row in df.iterrows():
                    # More robust validation for valid blocks
                    block_number_raw = row.get('Block Number')

                    # Skip rows with no block number or invalid block numbers
                    if pd.isna(block_number_raw):
                        self._debug_print(f"  Skipping row {idx}: Block Number is NaN")
                        continue

                    # Try to convert to integer
                    try:
                        block_num = int(float(block_number_raw))  # Handle potential float values
                    except (ValueError, TypeError):
                        self._debug_print(f"  Skipping row {idx}: Block Number '{block_number_raw}' cannot be converted to integer")
                        continue

                    # Skip invalid block numbers (0 or negative)
                    if block_num <= 0:
                        self._debug_print(f"  Skipping row {idx}: Block Number {block_num} is not valid (must be > 0)")
                        continue

                    # Additional validation - check if this looks like a real data row
                    section = row.get('Section', '')
                    length = row.get('Block Length (m)', 0)

                    # Skip rows that don't have basic required data
                    if pd.isna(section) and (pd.isna(length) or length == 0):
                        self._debug_print(f"  Skipping row {idx}: Block {block_num} missing essential data (section and length)")
                        continue

                    self._debug_print(f"  Processing valid block {block_num} at row {idx}")

                    # Parse infrastructure
                    has_station, station, has_switch, switch, has_crossing, is_underground = \
                        self._parse_infrastructure(row.get('Infrastructure'), block_num, line_name)

                    # Parse block direction
                    block_direction = self._parse_block_direction(row.get('Line Direction'))

                    # Handle station side if specified
                    if has_station and station and 'Station Side' in row and not pd.isna(row['Station Side']):
                        station.side = self._normalize_platform_side(row['Station Side'])
                        self._debug_print(f"  -> Updated station side to: {station.side}")

                    # Create track block with safer data extraction
                    try:
                        block = TrackBlock(
                            line=line_name,
                            section=str(row.get('Section', '')).strip(),
                            block_number=block_num,
                            length_m=float(row.get('Block Length (m)', 0)),
                            grade_percent=float(row.get('Block Grade (%)', 0)),
                            speed_limit_kmh=float(row.get('Speed Limit (Km/Hr)', 0)),
                            elevation_m=float(row.get('ELEVATION (M)', 0)),
                            direction=block_direction,
                            has_station=has_station,
                            station=station,
                            has_switch=has_switch,
                            switch=switch,
                            has_crossing=has_crossing,
                            is_underground=is_underground
                        )
                    except (ValueError, TypeError) as e:
                        self._debug_print(f"  Error creating block {block_num}: {e}")
                        continue

                    # Calculate minimum traversal time
                    if block.speed_limit_kmh > 0 and block.length_m > 0:
                        # Convert km/hr to m/s, then calculate time
                        speed_ms = block.speed_limit_kmh * 1000 / 3600
                        block.min_traversal_time_seconds = block.length_m / speed_ms
                        self._debug_print(f"  Block {block_num}: {block.length_m}m at {block.speed_limit_kmh} km/hr = {block.min_traversal_time_seconds:.1f}s")
                    else:
                        block.min_traversal_time_seconds = 0.0
                        self._debug_print(f"  Block {block_num}: No valid speed/length for traversal time calculation")

                    # Check for duplicate blocks
                    existing_blocks = [b.block_number for b in self.lines[line_name]]
                    if block_num in existing_blocks:
                        self._debug_print(f"  WARNING: Duplicate block number {block_num} found! Skipping.")
                        continue

                    # Add to line data
                    self.lines[line_name].append(block)
                    block_count += 1

                    if has_station:
                        station_count += 1
                    if has_switch:
                        switch_count += 1
                    if has_crossing:
                        crossing_count += 1

                    # Track sections
                    if block.section and block.section not in self.sections[line_name]:
                        self.sections[line_name][block.section] = []
                    if block.section:
                        self.sections[line_name][block.section].append(block.block_number)

                    # Debug output for significant blocks
                    if has_station or has_switch or has_crossing:
                        self._debug_print(f"  Block {block_num}: {block.get_infrastructure_description()}")

                self._debug_print(f"{line_name} Line Summary: {block_count} blocks, {station_count} stations, {switch_count} switches, {crossing_count} crossings")

            print(f"Successfully loaded track data:")
            for line, blocks in self.lines.items():
                stations = sum(1 for b in blocks if b.has_station)
                switches = sum(1 for b in blocks if b.has_switch)
                crossings = sum(1 for b in blocks if b.has_crossing)
                underground = sum(1 for b in blocks if b.is_underground)
                print(f"  {line} Line: {len(blocks)} blocks, {stations} stations, {switches} switches, {crossings} crossings, {underground} underground")

            # Debug: Show all stations found
            if DEBUG_PARSING:
                self._debug_print("\n=== ALL STATIONS FOUND ===")
                for line_name in self.selected_lines:
                    stations = self.get_all_stations(line_name)
                    self._debug_print(f"{line_name} Line stations ({len(stations)} total):")
                    for station in stations:
                        self._debug_print(f"  - Block {station['block_number']}: {station['station_name']} ({station['platform_side']})")

        except Exception as e:
            print(f"Error loading track data: {e}")
            import traceback
            traceback.print_exc()
            raise

    # === Methods for Dispatcher Interface ===

    def get_all_stations(self, line: Optional[str] = None) -> List[Dict]:
        """
        Get all stations for dispatcher display.
        Returns list of station info with block numbers for easy routing.
        """
        stations = []
        lines_to_check = [line] if line else self.selected_lines

        for line_name in lines_to_check:
            for block in self.lines.get(line_name, []):
                if block.has_station and block.station:
                    stations.append({
                        "line": line_name,
                        "block_number": block.block_number,
                        "station_id": block.station.station_id,
                        "station_name": block.station.name,
                        "platform_side": block.station.side,
                        "section": block.section
                    })

        return sorted(stations, key=lambda x: (x["line"], x["block_number"]))

    def get_all_switches(self, line: Optional[str] = None) -> List[Dict]:
        """
        Get all switches for dispatcher routing decisions.
        Returns switch info in easy-to-understand format.
        """
        switches = []
        lines_to_check = [line] if line else self.selected_lines

        for line_name in lines_to_check:
            for block in self.lines.get(line_name, []):
                if block.has_switch and block.switch:
                    # Get all possible destinations from this switch
                    all_destinations = set()
                    for conn in block.switch.connections:
                        all_destinations.add(conn.to_block)
                        if conn.direction == SwitchDirection.BIDIRECTIONAL:
                            all_destinations.add(conn.from_block)

                    switches.append({
                        "line": line_name,
                        "block_number": block.block_number,
                        "switch_type": block.switch.switch_type,
                        "normal_state": block.switch.normal_state,
                        "current_state": block.switch.current_state,
                        "state_description": block.switch.get_state_description(),
                        "connections": [
                            {
                                "from_block": conn.from_block,
                                "to_block": conn.to_block,
                                "direction": conn.direction.value,
                                "description": str(conn)
                            }
                            for conn in block.switch.connections
                        ],
                        "all_destinations": list(all_destinations),
                        "section": block.section,
                        "description": str(block.switch)
                    })

        return switches

    def get_route_options(self, line: str, from_block: int, to_block: int) -> List[List[int]]:
        """
        Get possible routes between two blocks.
        Useful for dispatcher routing interface.

        Returns:
            List of possible routes (each route is a list of block numbers)
        """
        # Simple implementation - can be enhanced with graph algorithms
        if from_block == to_block:
            return [[from_block]]

        # For now, return direct route if blocks are sequential
        # This should be enhanced with proper pathfinding for switches
        blocks = self.lines.get(line, [])
        block_nums = [b.block_number for b in blocks]

        if from_block in block_nums and to_block in block_nums:
            start_idx = block_nums.index(from_block)
            end_idx = block_nums.index(to_block)

            if start_idx < end_idx:
                route = block_nums[start_idx:end_idx + 1]
            else:
                route = block_nums[end_idx:start_idx + 1][::-1]

            return [route]

        return []

    def get_block_info(self, line: str, block_number: int) -> Optional[TrackBlock]:
        """Get detailed information about a specific block"""
        for block in self.lines.get(line, []):
            if block.block_number == block_number:
                return block
        return None

    def get_maintenance_zones(self, line: str) -> Dict[str, List[int]]:
        """
        Get blocks organized by section for maintenance planning.
        Sections can be closed for maintenance independently.
        """
        return self.sections.get(line, {})

    def calculate_journey_time(self, line: str, route: List[int]) -> float:
        """
        Calculate estimated journey time for a route at speed limits.
        Returns time in seconds.
        """
        total_time = 0
        for block_num in route:
            block = self.get_block_info(line, block_num)
            if block:
                total_time += block.min_traversal_time_seconds
        return total_time

    def export_for_display(self, line: str) -> List[Dict]:
        """
        Export track data in format suitable for graphical display.
        Includes all info needed for dispatcher interface.
        """
        display_data = []
        for block in self.lines.get(line, []):
            display_data.append({
                "block_number": block.block_number,
                "section": block.section,
                "length_m": block.length_m,
                "speed_limit_kmh": block.speed_limit_kmh,
                "grade_percent": block.grade_percent,
                "elevation_m": block.elevation_m,
                "direction": block.direction.value,
                "direction_description": block.get_direction_description(),
                "min_traversal_time_seconds": block.min_traversal_time_seconds,
                "infrastructure": block.get_infrastructure_description(),
                "has_station": block.has_station,
                "has_switch": block.has_switch,
                "has_crossing": block.has_crossing,
                "is_underground": block.is_underground
            })
        return display_data

    def get_block_traversal_time(self, line: str, block_number: int) -> float:
        """
        Get the minimum traversal time for a specific block.
        Useful for dispatcher timing calculations.

        Returns:
            Minimum traversal time in seconds, or 0.0 if block not found
        """
        block = self.get_block_info(line, block_number)
        return block.min_traversal_time_seconds if block else 0.0

    def validate_route_direction(self, line: str, route: List[int]) -> Tuple[bool, List[str]]:
        """
        Validate if a route is allowed based on block directions.

        Args:
            line: Line name ("Blue", "Red", "Green")
            route: List of block numbers in order

        Returns:
            Tuple of (is_valid, list_of_violations)
        """
        violations = []

        if len(route) < 2:
            return True, []  # Single block or empty route is always valid

        for i in range(len(route) - 1):
            current_block_num = route[i]
            next_block_num = route[i + 1]

            current_block = self.get_block_info(line, current_block_num)
            if not current_block:
                violations.append(f"Block {current_block_num} not found")
                continue

            if not current_block.can_move_to_block(next_block_num):
                violations.append(
                    f"Block {current_block_num} ({current_block.get_direction_description()}) "
                    f"cannot move to Block {next_block_num}"
                )

        return len(violations) == 0, violations

    def get_valid_next_blocks(self, line: str, current_block_number: int) -> List[int]:
        """
        Get list of valid next blocks from current block based on direction restrictions.

        Args:
            line: Line name
            current_block_number: Current block number

        Returns:
            List of valid next block numbers
        """
        current_block = self.get_block_info(line, current_block_number)
        if not current_block:
            return []

        valid_blocks = []
        all_blocks = [b.block_number for b in self.lines.get(line, [])]

        for block_num in all_blocks:
            if block_num != current_block_number and current_block.can_move_to_block(block_num):
                # Additional check: is this block actually adjacent or reachable?
                # For now, just check if it's numerically adjacent
                if abs(block_num - current_block_number) == 1:
                    valid_blocks.append(block_num)

        return sorted(valid_blocks)

    def get_directional_summary(self, line: Optional[str] = None) -> Dict[str, Dict[str, int]]:
        """
        Get summary of block directions for dispatcher overview.

        Returns:
            Dictionary with direction counts per line
        """
        summary = {}
        lines_to_check = [line] if line else self.selected_lines

        for line_name in lines_to_check:
            summary[line_name] = {
                "FORWARD": 0,
                "BACKWARD": 0,
                "BIDIRECTIONAL": 0,
                "TOTAL": 0
            }

            for block in self.lines.get(line_name, []):
                summary[line_name][block.direction.value] += 1
                summary[line_name]["TOTAL"] += 1

        return summary

    def get_yard_connections(self, line: Optional[str] = None) -> List[Dict]:
        """
        Get all yard connections for dispatcher interface.
        Returns information about switches connecting to/from yard.
        """
        yard_connections = []
        lines_to_check = [line] if line else self.selected_lines

        for line_name in lines_to_check:
            for block in self.lines.get(line_name, []):
                if block.has_switch and block.switch:
                    for conn in block.switch.connections:
                        if conn.from_block == "yard" or conn.to_block == "yard":
                            yard_connections.append({
                                "line": line_name,
                                "block_number": block.block_number,
                                "connection": str(conn),
                                "direction": conn.direction.value,
                                "switch_type": block.switch.switch_type,
                                "from_block": conn.from_block,
                                "to_block": conn.to_block
                            })

        return yard_connections

    # === Utility Functions for Module Integration ===

    def get_block_by_number(self, block_number: int, line: Optional[str] = None) -> Optional[TrackBlock]:
        """
        Get detailed information about a specific block by its number.
        
        Args:
            block_number: The block number to find
            line: Optional line to search in. If None, searches all lines.
            
        Returns:
            TrackBlock object if found, None otherwise
        """
        lines_to_check = [line] if line else self.selected_lines
        
        for line_name in lines_to_check:
            for block in self.lines.get(line_name, []):
                if block.block_number == block_number:
                    return block
        return None

    def get_station_by_id(self, station_id: int) -> Optional[Dict]:
        """
        Get station information by station ID.
        
        Args:
            station_id: The unique station ID
            
        Returns:
            Dictionary with station info or None if not found
        """
        for line_name in self.selected_lines:
            for block in self.lines.get(line_name, []):
                if block.has_station and block.station and block.station.station_id == station_id:
                    return {
                        "station_id": block.station.station_id,
                        "name": block.station.name,
                        "platform_side": block.station.side,
                        "line": line_name,
                        "block_number": block.block_number,
                        "section": block.section
                    }
        return None

    def get_line_for_station(self, station_id: int) -> Optional[str]:
        """
        Get the line name for a given station ID.
        
        Args:
            station_id: The unique station ID
            
        Returns:
            Line name ("Blue", "Red", "Green") or None if not found
        """
        station_info = self.get_station_by_id(station_id)
        return station_info["line"] if station_info else None

    def get_switch_by_block(self, block_number: int, line: Optional[str] = None) -> Optional[Dict]:
        """
        Get switch information for a specific block.
        
        Args:
            block_number: The block number to check
            line: Optional line to search in. If None, searches all lines.
            
        Returns:
            Dictionary with switch info or None if no switch found
        """
        block = self.get_block_by_number(block_number, line)
        if block and block.has_switch and block.switch:
            return {
                "block_number": block.block_number,
                "line": block.line,
                "switch_type": block.switch.switch_type,
                "normal_state": block.switch.normal_state,
                "current_state": block.switch.current_state,
                "state_description": block.switch.get_state_description(),
                "connections": [
                    {
                        "from_block": conn.from_block,
                        "to_block": conn.to_block,
                        "direction": conn.direction.value,
                        "description": str(conn)
                    }
                    for conn in block.switch.connections
                ],
                "description": str(block.switch)
            }
        return None

    def get_block_infrastructure_summary(self, block_number: int, line: Optional[str] = None) -> Dict:
        """
        Get a summary of infrastructure on a specific block.
        
        Args:
            block_number: The block number to check
            line: Optional line to search in. If None, searches all lines.
            
        Returns:
            Dictionary with infrastructure summary
        """
        block = self.get_block_by_number(block_number, line)
        if not block:
            return {
                "block_found": False,
                "block_number": block_number,
                "line": line,
                "error": "Block not found"
            }
        
        return {
            "block_found": True,
            "block_number": block.block_number,
            "line": block.line,
            "section": block.section,
            "has_station": block.has_station,
            "station_info": {
                "station_id": block.station.station_id,
                "name": block.station.name,
                "platform_side": block.station.side
            } if block.has_station and block.station else None,
            "has_switch": block.has_switch,
            "switch_info": {
                "switch_type": block.switch.switch_type,
                "normal_state": block.switch.normal_state,
                "current_state": block.switch.current_state,
                "state_description": block.switch.get_state_description()
            } if block.has_switch and block.switch else None,
            "has_crossing": block.has_crossing,
            "is_underground": block.is_underground,
            "speed_limit_kmh": block.speed_limit_kmh,
            "length_m": block.length_m,
            "grade_percent": block.grade_percent,
            "elevation_m": block.elevation_m,
            "direction": block.direction.value,
            "direction_description": block.get_direction_description(),
            "min_traversal_time_seconds": block.min_traversal_time_seconds,
            "infrastructure_description": block.get_infrastructure_description()
        }

    def is_block_station(self, block_number: int, line: Optional[str] = None) -> bool:
        """
        Check if a block has a station.
        
        Args:
            block_number: The block number to check
            line: Optional line to search in. If None, searches all lines.
            
        Returns:
            True if block has a station, False otherwise
        """
        block = self.get_block_by_number(block_number, line)
        return block.has_station if block else False

    def is_block_switch(self, block_number: int, line: Optional[str] = None) -> bool:
        """
        Check if a block has a switch.
        
        Args:
            block_number: The block number to check
            line: Optional line to search in. If None, searches all lines.
            
        Returns:
            True if block has a switch, False otherwise
        """
        block = self.get_block_by_number(block_number, line)
        return block.has_switch if block else False

    def get_block_speed_limit(self, block_number: int, line: Optional[str] = None) -> Optional[float]:
        """
        Get the speed limit for a specific block.
        
        Args:
            block_number: The block number to check
            line: Optional line to search in. If None, searches all lines.
            
        Returns:
            Speed limit in km/h or None if block not found
        """
        block = self.get_block_by_number(block_number, line)
        return block.speed_limit_kmh if block else None

    def get_block_length(self, block_number: int, line: Optional[str] = None) -> Optional[float]:
        """
        Get the length of a specific block.
        
        Args:
            block_number: The block number to check
            line: Optional line to search in. If None, searches all lines.
            
        Returns:
            Block length in meters or None if block not found
        """
        block = self.get_block_by_number(block_number, line)
        return block.length_m if block else None

    def get_adjacent_blocks(self, block_number: int, line: str) -> List[int]:
        """
        Get blocks adjacent to the given block (numerically adjacent).
        
        Args:
            block_number: The block number to check
            line: The line to search in
            
        Returns:
            List of adjacent block numbers
        """
        adjacent = []
        all_blocks = [b.block_number for b in self.lines.get(line, [])]
        
        # Check for numerically adjacent blocks
        if (block_number - 1) in all_blocks:
            adjacent.append(block_number - 1)
        if (block_number + 1) in all_blocks:
            adjacent.append(block_number + 1)
            
        return adjacent


    def get_stations_on_line(self, line: str) -> List[Dict]:
        """
        Get all stations on a specific line, sorted by block number.
        
        Args:
            line: The line name ("Blue", "Red", "Green")
            
        Returns:
            List of station dictionaries
        """
        stations = []
        for block in sorted(self.lines.get(line, []), key=lambda b: b.block_number):
            if block.has_station and block.station:
                stations.append({
                    "station_id": block.station.station_id,
                    "name": block.station.name,
                    "platform_side": block.station.side,
                    "block_number": block.block_number,
                    "line": line,
                    "section": block.section
                })
        return stations

    def get_switches_on_line(self, line: str) -> List[Dict]:
        """
        Get all switches on a specific line, sorted by block number.
        
        Args:
            line: The line name ("Blue", "Red", "Green")
            
        Returns:
            List of switch dictionaries
        """
        switches = []
        for block in sorted(self.lines.get(line, []), key=lambda b: b.block_number):
            if block.has_switch and block.switch:
                switches.append({
                    "block_number": block.block_number,
                    "line": line,
                    "switch_type": block.switch.switch_type,
                    "normal_state": block.switch.normal_state,
                    "current_state": block.switch.current_state,
                    "state_description": block.switch.get_state_description(),
                    "connections": [
                        {
                            "from_block": conn.from_block,
                            "to_block": conn.to_block,
                            "direction": conn.direction.value,
                            "description": str(conn)
                        }
                        for conn in block.switch.connections
                    ],
                    "description": str(block.switch)
                })
        return switches


    def get_line_summary(self, line: str) -> Dict:
        """
        Get a comprehensive summary of a line.
        
        Args:
            line: The line name ("Blue", "Red", "Green")
            
        Returns:
            Dictionary with line summary information
        """
        blocks = self.lines.get(line, [])
        
        if not blocks:
            return {"line": line, "error": "Line not found or has no blocks"}
        
        stations = [b for b in blocks if b.has_station]
        switches = [b for b in blocks if b.has_switch]
        crossings = [b for b in blocks if b.has_crossing]
        underground = [b for b in blocks if b.is_underground]
        
        return {
            "line": line,
            "total_blocks": len(blocks),
            "block_range": {
                "min": min(b.block_number for b in blocks),
                "max": max(b.block_number for b in blocks)
            },
            "total_length_m": sum(b.length_m for b in blocks),
            "stations": {
                "count": len(stations),
                "station_ids": [b.station.station_id for b in stations if b.station],
                "names": [b.station.name for b in stations if b.station]
            },
            "switches": {
                "count": len(switches),
                "blocks": [b.block_number for b in switches]
            },
            "crossings": {
                "count": len(crossings),
                "blocks": [b.block_number for b in crossings]
            },
            "underground": {
                "count": len(underground),
                "blocks": [b.block_number for b in underground]
            },
            "sections": list(self.sections.get(line, {}).keys())
        }


# === Example Usage ===
    def generate_controller_json(self, line: str) -> Dict:
        """
        Generate JSON data structure with only the fields needed by the train controller.
        
        Args:
            line: Track color ("Blue", "Red", or "Green")
            
        Returns:
            Dictionary containing minimal track data for controller use
        """
        if line not in self.lines:
            raise ValueError(f"Line {line} not found in track data")
        
        blocks = self.lines[line]
        
        # Build minimal JSON structure for controller
        track_data = {
            "blocks": {}
        }
        
        # Process each block with only essential fields
        for block in blocks:
            block_data = {
                "block_number": block.block_number,
                "physical_properties": {
                    "length_m": block.length_m,
                    "speed_limit_kmh": block.speed_limit_kmh
                },
                "infrastructure": {
                    "has_station": block.has_station,
                    "is_underground": block.is_underground
                }
            }
            
            # Add station details if present (including station number)
            if block.has_station and block.station:
                block_data["station"] = {
                    "name": block.station.name,
                    "platform_side": block.station.side,
                    "station_number": block.station.station_id
                }
            
            track_data["blocks"][str(block.block_number)] = block_data
        
        return track_data


if __name__ == "__main__":
    # Initialize the track layout reader
    reader = TrackLayoutReader("Track Layout & Vehicle Data vF2.xlsx")