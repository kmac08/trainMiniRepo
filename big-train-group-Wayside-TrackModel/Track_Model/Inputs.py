import csv

class TrackModelInputs:
    """
    Interface for Track Model inputs and Murphy failures.
    Provides getters and setters for all inputs defined in the integration CSV.
    """

    def __init__(self):
        # Track Builder Inputs
        self._train_layout = None  # CSV file path or parsed data
        self._temperature = 70.0   # float, degrees Fahrenheit

        # Murphy Inputs (failures, per block)
        self._broken_rail_failure = {}      # {block_id: bool}
        self._track_circuit_failure = {}    # {block_id: bool}
        self._power_failure = {}            # {block_id: bool}

        # Wayside Controller Inputs (Green Line G0-G150)
        # Each block has wayside data as bit strings
        self._next_block_numbers = {}       # {block_id: str} - 7-bit strings
        self._next_station_numbers = {}     # {block_id: str} - 5-bit strings
        self._update_block_in_queue = {}    # {block_id: str} - 1-bit strings
        self._wayside_authority = {}        # {block_id: str} - 1-bit strings
        self._wayside_commanded_speed = {}  # {block_id: str} - 2-bit strings
        self._switch_states = {}            # {block_id: str} - 1-bit strings
        self._traffic_light_states = {}     # {block_id: str} - 1-bit strings
        self._crossing_states = {}          # {block_id: str} - 1-bit strings
        self._wayside_blocks_covered = {}   # {block_id: str} - 1-bit strings
        
        # Initialize dummy data for Green Line blocks G0-G150
        self._initialize_wayside_dummy_data()    
        

    # --- Track Builder Inputs ---

    def get_train_layout(self):
        return self._train_layout

    def set_train_layout(self, csv_path):
        """Load and store the train layout from a CSV file."""
        with open(csv_path, newline='') as csvfile:
            reader = csv.reader(csvfile)
            self._train_layout = [row for row in reader]

    def get_temperature(self):
        return self._temperature

    def set_temperature(self, temp_f):
        self._temperature = float(temp_f)

    # --- Murphy Inputs (per block) ---

    def get_broken_rail_failure(self, block_id):
        return self._broken_rail_failure.get(block_id, False)

    def set_broken_rail_failure(self, block_id, value: bool):
        self._broken_rail_failure[block_id] = bool(value)

    def get_track_circuit_failure(self, block_id):
        return self._track_circuit_failure.get(block_id, False)

    def set_track_circuit_failure(self, block_id, value: bool):
        self._track_circuit_failure[block_id] = bool(value)

    def get_power_failure(self, block_id):
        return self._power_failure.get(block_id, False)

    def set_power_failure(self, block_id, value: bool):
        self._power_failure[block_id] = bool(value)


    # --- Wayside Controller Inputs (per block bit strings) ---
    
    def _initialize_wayside_dummy_data(self):
        """Initialize dummy data for Green Line blocks G0-G150"""
        # Create sample datasets with different patterns for testing
        for block_num in range(151):  # G0 to G150
            block_id = f"G{block_num}"
            
            # Sample patterns based on block number for variety
            if block_num == 0:  # Yard block
                self._next_block_numbers[block_id] = "0000001"    # 7-bit: next block 1
                self._next_station_numbers[block_id] = "10011"    # 5-bit: station 19
                self._update_block_in_queue[block_id] = "0"       # 1-bit: no update
                self._wayside_authority[block_id] = "1"           # 1-bit: authorized
                self._wayside_commanded_speed[block_id] = "00"    # 2-bit: stop
                self._switch_states[block_id] = "0"               # 1-bit: lower block
                self._traffic_light_states[block_id] = "0"        # 1-bit: green
                self._crossing_states[block_id] = "0"             # 1-bit: inactive
                self._wayside_blocks_covered[block_id] = "1"      # 1-bit: covered
            elif block_num % 20 == 0:  # Station blocks (every 20th block)
                next_block = min(block_num + 1, 150)
                station_num = (block_num // 20) % 32  # Cycle through station numbers
                self._next_block_numbers[block_id] = f"{next_block:07b}"
                self._next_station_numbers[block_id] = f"{station_num:05b}"
                self._update_block_in_queue[block_id] = "0"
                self._wayside_authority[block_id] = "1"
                self._wayside_commanded_speed[block_id] = "01"    # Slow speed at stations
                self._switch_states[block_id] = "0"
                self._traffic_light_states[block_id] = "0"        # Green at stations
                self._crossing_states[block_id] = "0"
                self._wayside_blocks_covered[block_id] = "1"
            elif block_num % 15 == 0:  # Switch blocks (every 15th block)
                next_block = min(block_num + 1, 150)
                self._next_block_numbers[block_id] = f"{next_block:07b}"
                self._next_station_numbers[block_id] = "11111"    # No immediate station
                self._update_block_in_queue[block_id] = "0"
                self._wayside_authority[block_id] = "1"
                self._wayside_commanded_speed[block_id] = "10"    # Medium speed
                self._switch_states[block_id] = "1"               # Higher block direction
                self._traffic_light_states[block_id] = "0"
                self._crossing_states[block_id] = "0"
                self._wayside_blocks_covered[block_id] = "1"
            elif block_num % 25 == 0:  # Crossing blocks (every 25th block)
                next_block = min(block_num + 1, 150)
                self._next_block_numbers[block_id] = f"{next_block:07b}"
                self._next_station_numbers[block_id] = "11111"
                self._update_block_in_queue[block_id] = "0"
                self._wayside_authority[block_id] = "1"
                self._wayside_commanded_speed[block_id] = "01"    # Slow at crossings
                self._switch_states[block_id] = "0"
                self._traffic_light_states[block_id] = "1"        # Red at crossings
                self._crossing_states[block_id] = "1"             # Active crossing
                self._wayside_blocks_covered[block_id] = "1"
            else:  # Regular blocks
                next_block = min(block_num + 1, 150)
                self._next_block_numbers[block_id] = f"{next_block:07b}"
                self._next_station_numbers[block_id] = "11111"    # No immediate station
                self._update_block_in_queue[block_id] = "0"
                self._wayside_authority[block_id] = "1"
                self._wayside_commanded_speed[block_id] = "11"    # Full speed
                self._switch_states[block_id] = "0"
                self._traffic_light_states[block_id] = "0"        # Green
                self._crossing_states[block_id] = "0"
                self._wayside_blocks_covered[block_id] = "1"

    # Getter methods for wayside data
    def get_next_block_number(self, block_id):
        return self._next_block_numbers.get(block_id, "0000000")
    
    def get_next_station_number(self, block_id):
        return self._next_station_numbers.get(block_id, "10011")
    
    def get_update_block_in_queue(self, block_id):
        return self._update_block_in_queue.get(block_id, "0")
    
    def get_wayside_authority(self, block_id):
        return self._wayside_authority.get(block_id, "0")
    
    def get_wayside_commanded_speed(self, block_id):
        return self._wayside_commanded_speed.get(block_id, "00")
    
    def get_switch_state(self, block_id):
        return self._switch_states.get(block_id, "0")
    
    def get_traffic_light_state(self, block_id):
        return self._traffic_light_states.get(block_id, "0")
    
    def get_crossing_state(self, block_id):
        return self._crossing_states.get(block_id, "0")
    
    def get_wayside_blocks_covered(self, block_id):
        return self._wayside_blocks_covered.get(block_id, "0")

    # Setter methods for wayside data
    def set_next_block_number(self, block_id, value: str):
        if len(value) == 7 and all(c in '01' for c in value):
            self._next_block_numbers[block_id] = value
    
    def set_next_station_number(self, block_id, value: str):
        if len(value) == 5 and all(c in '01' for c in value):
            self._next_station_numbers[block_id] = value
    
    def set_update_block_in_queue(self, block_id, value: str):
        if len(value) == 1 and value in '01':
            self._update_block_in_queue[block_id] = value
    
    def set_wayside_authority(self, block_id, value: str):
        if len(value) == 1 and value in '01':
            self._wayside_authority[block_id] = value
    
    def set_wayside_commanded_speed(self, block_id, value: str):
        if len(value) == 2 and all(c in '01' for c in value):
            self._wayside_commanded_speed[block_id] = value
    
    def set_switch_state(self, block_id, value: str):
        if len(value) == 1 and value in '01':
            self._switch_states[block_id] = value
    
    def set_traffic_light_state(self, block_id, value: str):
        if len(value) == 1 and value in '01':
            self._traffic_light_states[block_id] = value
    
    def set_crossing_state(self, block_id, value: str):
        if len(value) == 1 and value in '01':
            self._crossing_states[block_id] = value
    
    def set_wayside_blocks_covered(self, block_id, value: str):
        if len(value) == 1 and value in '01':
            self._wayside_blocks_covered[block_id] = value

    def set_train_manager(self, train_manager):
        """Set reference to train manager for yard buffer processing"""
        self.train_manager = train_manager
    
    def process_next_block_for_yard(self, block_number: int):
        """Process next block number for yard buffer (called when wayside data changes)"""
        print(f"[WAYSIDE FLOW] Inputs.py received block {block_number} for yard processing")
        
        if hasattr(self, 'train_manager') and self.train_manager:
            print(f"[WAYSIDE FLOW] Forwarding block {block_number} to train manager")
            self.train_manager.process_yard_buffer_data(block_number)
        else:
            print(f"[WAYSIDE FLOW] ERROR: No train manager connected to process block {block_number}")

    # Utility method to get all wayside data for a block
    def get_wayside_data_summary(self, block_id):
        """Get a summary of all wayside data for a given block"""
        return {
            'next_block': self.get_next_block_number(block_id),
            'next_station': self.get_next_station_number(block_id),
            'update_queue': self.get_update_block_in_queue(block_id),
            'authority': self.get_wayside_authority(block_id),
            'commanded_speed': self.get_wayside_commanded_speed(block_id),
            'switch_state': self.get_switch_state(block_id),
            'traffic_light': self.get_traffic_light_state(block_id),
            'crossing': self.get_crossing_state(block_id),
            'covered': self.get_wayside_blocks_covered(block_id)
        }
    
    