#File Location: train_controller_sw/controller/train_controller.py
# accept inputs: driver and train model
# emergency logic
# power control (auto mode): compare command speed and actual speed. apply proportional control to calculate power. Also make sure its less than speed limit and more than 0 for commanded. (manual): compare set_speed and actual_speed and apply proportional control 
# braking: when in manual allow for service_brake
# doors 
# cabin temp
# return output with get_output

"""
Contains the TrainController class responsible for processing
train and driver inputs to compute outputs using the PI controller.
"""
import datetime
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from train_controller_hw.controller.data_types import (TrainModelInput, DriverInput, EngineerInput, 
                                  TrainModelOutput, OutputToDriver, BlockInfo, TrainControllerInit)

# Import universal time function from Master Interface
try:
    from Master_Interface.master_control import get_time
except ImportError:
    raise ImportError("CRITICAL ERROR: Master Interface universal time function not available. Train controller requires universal time synchronization.")

# Import track data loader with proper error handling
# Try multiple paths to find the Track_Reader module
track_reader_paths = [
    os.path.join(os.path.dirname(__file__), '..', 'Track_Reader'),  # train_controller_hw/Track_Reader
    os.path.join(os.path.dirname(__file__), '..', '..', 'Track_Reader'),  # root/Track_Reader
]

for path in track_reader_paths:
    if os.path.exists(path):
        sys.path.append(path)
        print(f"Added Track_Reader path: {path}")
        break

class TrackDataError(Exception):
    """Exception raised when track data cannot be loaded or accessed."""
    pass

try:
    from track_reader import TrackLayoutReader
    TRACK_DATA_AVAILABLE = True
except ImportError as e:
    print(f"CRITICAL ERROR: Cannot import track data loader: {e}")
    TRACK_DATA_AVAILABLE = False
    TrackLayoutReader = None

MAX_POWER_KW = 120.0  # Update after verifying the actual maximum power of the train

class TrainController:
    """
    A controller class that computes train outputs using a Proportional-Integral controller.

    Attributes:
        kp (float): Proportional gain. (kW/ (m/s))
        ki (float): Integral gain. kW (m)
        integral_error (float): Accumulated speed error.
        current_output (TrainModelOutput): The latest computed control output.
    """

    def __init__(self, init_data: TrainControllerInit, kp: float = 12, ki: float = 1.2):
        """
        Initializes the TrainController with track information and control gains.

        Args:
            init_data (TrainControllerInit): Required track and block initialization data.
            kp (float): Proportional gain for speed error.
            ki (float): Integral gain for accumulated speed error.
        
        Raises:
            ValueError: If init_data is None or missing required fields.
            TrackDataError: If track data cannot be loaded or accessed.
        """
        # CRITICAL SAFETY CHECK: Ensure track data is available
        if not TRACK_DATA_AVAILABLE:
            raise TrackDataError(
                "SAFETY CRITICAL ERROR: Track data loader is not available. "
                "Cannot initialize train controller without access to track layout information. "
                "This prevents the controller from knowing speed limits, block lengths, "
                "underground sections, and other critical safety information. "
                "Please ensure Track_Reader module and dependencies are properly installed."
            )
        
        if init_data is None:
            raise ValueError("TrainControllerInit data is required. Cannot create TrainController without track information.")
        
        # Validate required fields
        required_fields = ['track_color', 'current_block', 'current_commanded_speed', 'authorized_current_block', 'next_four_blocks', 'train_id', 'next_station_number']
        missing_fields = []
        for field in required_fields:
            if not hasattr(init_data, field) or getattr(init_data, field) is None:
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"TrainControllerInit is missing required fields: {missing_fields}")
        
        if len(init_data.next_four_blocks) != 4:
            raise ValueError(f"Expected exactly 4 blocks in next_four_blocks, got {len(init_data.next_four_blocks)}")
        
        # Validate track color
        valid_colors = ['red', 'green', 'Red', 'Green']  # Accept both cases for now
        if init_data.track_color not in valid_colors:
            raise ValueError(f"Invalid track color '{init_data.track_color}'. Must be one of: {valid_colors}")
        
        # Normalize to title case for JSON generator
        normalized_color = init_data.track_color.title()  # red -> Red, green -> Green
        
        # Dynamically generate track data from Excel file
        try:
            # Try multiple paths to find the Excel file
            excel_paths = [
                os.path.join(os.path.dirname(__file__), '..', 'Track_Reader', "Track Layout & Vehicle Data vF2.xlsx"),
                os.path.join(os.path.dirname(__file__), '..', '..', 'Track_Reader', "Track Layout & Vehicle Data vF2.xlsx"),
            ]
            
            excel_path = None
            for path in excel_paths:
                if os.path.exists(path):
                    excel_path = path
                    print(f"Found Excel file at: {excel_path}")
                    break
            
            if excel_path is None:
                raise FileNotFoundError(f"Excel file not found in any of the expected locations: {excel_paths}")
            
            self.track_reader = TrackLayoutReader(excel_path)
            self.track_data = self.track_reader.generate_controller_json(normalized_color)
            print(f"Successfully generated track data for {normalized_color} Line")
            print(f"Track data contains {len(self.track_data['blocks'])} blocks")
        except Exception as e:
            raise TrackDataError(
                f"SAFETY CRITICAL ERROR: Cannot load track data for {normalized_color} Line. "
                f"Error: {e}. "
                f"The train controller cannot operate safely without access to track layout "
                f"information including speed limits, block lengths, and infrastructure details."
            )
        
        self.kp = kp
        self.ki = ki
        self.kp_ki_set = False  # Flag to track if engineer has applied Kp/Ki values
        self.auto_mode = True  # default to auto mode
        self.integral_error = 0.0
        self.last_time = get_time().timestamp()
        self.debug_update_count = 0  # Initialize debug counter
        
        # Initialize track information from init_data
        self.track_color = init_data.track_color
        self.current_block = init_data.current_block
        self.current_block_commanded_speed = init_data.current_commanded_speed
        self.authorized_current_block = init_data.authorized_current_block
        self.next_four_blocks = init_data.next_four_blocks.copy()
        self.train_id = init_data.train_id
        self.next_station_number = init_data.next_station_number
        
        # Load current block data from the already-loaded track data
        current_block_data = self.get_block_essentials(self.current_block)
        if current_block_data is None:
            raise TrackDataError(
                f"SAFETY CRITICAL ERROR: Block {self.current_block} not found in {self.track_color} Line track data. "
                f"Cannot operate train controller without valid block information."
            )
        
        self.current_block_speed_limit = current_block_data['speed_limit_mph']
        self.current_block_underground_status = current_block_data['underground']
        print(f"Loaded block {self.current_block} data: Speed limit {self.current_block_speed_limit} mph, Underground: {self.current_block_underground_status}")
        
        # Fill in track data for initial blocks (they come from train model side with incomplete data)
        self.known_blocks = []
        for block in init_data.next_four_blocks:
            # Get track data for this block
            block_data = self.get_block_essentials(block.block_number)
            if block_data:
                # Create a new BlockInfo with complete data
                complete_block = BlockInfo(
                    block_number=block.block_number,
                    length_meters=block_data['length_meters'],
                    speed_limit_mph=block_data['speed_limit_mph'],
                    underground=block_data['underground'],
                    authorized_to_go=block.authorized_to_go,
                    commanded_speed=block.commanded_speed
                )
                self.known_blocks.append(complete_block)
                print(f"Filled block {block.block_number} with track data: {block_data['length_meters']}m, {block_data['speed_limit_mph']}mph, underground={block_data['underground']}")
            else:
                # Keep the original block if we can't find track data
                self.known_blocks.append(block)
                print(f"Warning: No track data found for block {block.block_number}, using provided data")
        
        self.calculated_authority = 0.0  # Authority calculated from next blocks
        self.last_next_block_entered = None  # Track block transition toggle (None means first reading)
        
        # Position tracking for real-time authority updates
        self.train_has_moved = False  # Flag to track if train has moved from initial position
        self.distance_traveled_in_current_block = 0.0  # Distance traveled in current block (meters)
        self.last_position_update_time = get_time().timestamp()  # For calculating distance traveled
        
        # Store latest inputs for OutputToDriver generation
        self.last_train_input = None
        self.last_driver_input = None

        self.setpoint_speed = 0
        self.start_breaking = False
        
        # Underground state tracking
        self.was_underground = False
        self.pre_underground_headlights = False
        self.pre_underground_interior = False
        
        # Fault-based emergency brake tracking
        self.fault_emergency_brake_active = False
        self.last_fault_state = {'signal': False, 'brake': False, 'engine': False}
        
        # Station stopping logic
        self.station_stop_timer = 0.0
        self.station_stop_active = False
        self.station_stop_complete_waiting = False  # Waiting for train model to update next block
        self.last_station_stop_time = get_time().timestamp()
        self.station_authority_extended = False  # Track if 60-second extension has been applied
        
        # Initialize station information based on next_station_number
        initial_station_name = "No Information"
        initial_station_side = "No Information"
        
        if self.next_station_number > 0:
            station_info = self.get_station_info_by_number(self.next_station_number)
            if station_info:
                initial_station_name = station_info['name']
                initial_station_side = station_info['platform_side']
                print(f"TrainController __init__: Found station info for station {self.next_station_number}: {initial_station_name} ({initial_station_side})")
            else:
                print(f"TrainController __init__: No station info found for station {self.next_station_number}")
        else:
            print(f"TrainController __init__: No next station number provided ({self.next_station_number})")
        
        self.current_output = TrainModelOutput(
            power_kw=0.0,
            emergency_brake_status=False,
            interior_lights_status=False,
            headlights_status=False,
            door_left_status=False,
            door_right_status=False,
            service_brake_status=False,
            set_cabin_temperature=72.0,
            train_id=self.train_id,
            station_stop_complete=False,
            next_station_name=initial_station_name,
            next_station_side=initial_station_side,
            edge_of_current_block=False
        )
        
    def update(self, train_input: TrainModelInput, driver_input: DriverInput) -> None:
        """
        Update controller output using simulation time PI control and driver inputs.

        Allows driver to always toggle auto/manual mode. Other driver inputs are only
        applied in manual mode. Emergency brake is always processed.
        """
        now_datetime = get_time()  # Get full datetime object
        now = now_datetime.timestamp()
        dt = now - self.last_time
        self.last_time = now
        
        # Debug: Print simulation time with milliseconds every 50 updates (every 5 seconds)
        if not hasattr(self, 'debug_update_count'):
            self.debug_update_count = 0
        self.debug_update_count += 1
        
        if self.debug_update_count % 50 == 0:
            ms = now_datetime.microsecond // 1000  # Convert microseconds to milliseconds
            time_str = f"{now_datetime.hour:02d}:{now_datetime.minute:02d}:{now_datetime.second:02d}.{ms:03d}"
            print(f"🕐 Controller Update #{self.debug_update_count} - Simulation Time: {time_str} (dt={dt:.4f}s)")
        
        # Store inputs for OutputToDriver
        self.last_train_input = train_input
        self.last_driver_input = driver_input
        
        # Train ID is set from initialization data and remains constant
        
        # Update station information using next_station_number from train model
        station_info = self.get_station_info_by_number(train_input.next_station_number)
        if station_info:
            self.current_output.next_station_name = station_info['name']
            self.current_output.next_station_side = station_info['platform_side']
        else:
            self.current_output.next_station_name = "No Information"
            self.current_output.next_station_side = "No Information"
        
        # Update position tracking
        self._update_position_tracking(train_input, dt)
        
        # Handle block progression and authority calculation
        self._handle_block_progression(train_input)
        
        # TODO: Remove after iteration 3 - using only for simulating track
        # Check if train is at the edge of current block (for automatic testing)
        self._update_edge_of_current_block_detection(train_input)
        
        self.auto_mode = driver_input.auto_mode

        # Handle station stopping logic when train speed reaches zero
        self._handle_station_stop(train_input, dt)

        # Check if we're stopped (authority = 0) and open doors on correct side
        if self.auto_mode and self.calculated_authority == 0 and train_input.actual_speed < 0.1:
            self.current_output.interior_lights_status = True # Always turn on interior lights when stopped
            
            # Get station information from track data using next_station_number
            station_info = self.get_station_info_by_number(train_input.next_station_number)
            if station_info:
                platform_side = station_info['platform_side'].lower()
                # Open doors on the platform side
                if platform_side == "left":
                    self.current_output.door_left_status = True
                    self.current_output.door_right_status = False
                elif platform_side == "right":
                    self.current_output.door_left_status = False
                    self.current_output.door_right_status = True
                elif platform_side == "both" or platform_side == "BOTH":
                    # Open both doors for stations that serve both sides
                    self.current_output.door_left_status = True
                    self.current_output.door_right_status = True
        
        #In both modes we should never be able to open/close door when moving
        if train_input.actual_speed > 0.1:
            self.current_output.door_left_status = False
            self.current_output.door_right_status = False
            if self.auto_mode:
                self.current_output.interior_lights_status = False  # Turn off interior lights when moving in auto mode
        
        # Critical safety: Handle fault-based emergency brake FIRST (regardless of mode)
        self._handle_fault_emergency_brake(train_input)
        
        # Process based on mode
        if self.auto_mode:
            # Safety: No power output until engineer sets Kp/Ki
            if not self.kp_ki_set:
                self.current_output.power_kw = 0.0
                print("Power disabled: Waiting for engineer to set Kp/Ki values")
            else:
                self.current_output.power_kw = self.calculate_power(train_input, dt)
        else:
            # Manual mode - use driver's set_speed for power calculation
            # We don't need to modify train_input - just use driver's set_speed directly
            
            # Safety: No power output until engineer sets Kp/Ki
            if not self.kp_ki_set:
                self.current_output.power_kw = 0.0
                print("Power disabled: Waiting for engineer to set Kp/Ki values")
            else:
                # Store the driver's set speed temporarily for power calculation
                old_commanded_speed = self.current_block_commanded_speed
                self.current_block_commanded_speed = driver_input.set_speed
                self.current_output.power_kw = self.calculate_power(train_input, dt)
                # Restore the original commanded speed
                self.current_block_commanded_speed = old_commanded_speed
            self.current_output.service_brake_status = driver_input.service_brake

            
            self.current_output.interior_lights_status = driver_input.interior_lights_on
            self.current_output.headlights_status = driver_input.headlights_on
            
            # Safety: Don't allow doors to open if speed > 0
            if train_input.actual_speed > 0.1:
                self.current_output.door_left_status = False
                self.current_output.door_right_status = False
            else:
                self.current_output.door_left_status = driver_input.door_left_open
                self.current_output.door_right_status = driver_input.door_right_open
            
            self.current_output.set_cabin_temperature = driver_input.set_temperature
            
        
        # Service Brake to OFF
        # Will turn on at the end of Update() if needed to still brake
        # This is being done because service brake in the driver's UI was previously automatically ON.
        if self.start_breaking:
            self.current_output.service_brake_status = False
    
        # Engine failure overrides power - power goes to 0 instantly when engine fails (both auto and manual mode)
        engine_failure = train_input.fault_status.get('engine', False)
        if engine_failure:
            self.current_output.power_kw = 0.0
            self.integral_error = 0.0
            print("Engine failure detected - power cut to 0")
        
        # Service brake overrides power - power goes to 0 instantly when service brake is active. Also activate when authority is below threshold
        if self.current_output.service_brake_status or self.calculated_authority <= train_input.authority_threshold or train_input.actual_speed > self.setpoint_speed:
            self.current_output.power_kw = 0.0
            self.integral_error = 0.0
            self.current_output.service_brake_status = True
            if(self.calculated_authority <= train_input.authority_threshold or train_input.actual_speed > self.setpoint_speed):
                self.start_breaking = True
        else:
            self.start_breaking = False

        if train_input.actual_speed > self.setpoint_speed:
            print("true")

        # Emergency brake logic - handle all cases
        # Emergency brake should be ON if:
        # 1. Driver emergency brake is pressed OR
        # 2. Passenger emergency brake is pressed OR
        # 3. Fault-based emergency brake is active (handled in _handle_fault_emergency_brake)
        if driver_input.emergency_brake or train_input.passenger_emergency_brake or self.fault_emergency_brake_active:
            self.current_output.emergency_brake_status = True
            self.current_output.power_kw = 0.0
            self.integral_error = 0.0
        else:
            # Emergency brake can be released if none of the above conditions are true
            self.current_output.emergency_brake_status = False

        # Check time and update headlights (ON from 7PM to 7AM)
        current_hour = get_time().hour
        if self.auto_mode:
            # Headlights ON between 7PM (19:00) and 7AM (07:00)
            if current_hour >= 19 or current_hour < 7:
                self.current_output.headlights_status = True
            else:
                self.current_output.headlights_status = False
                
            # Underground lighting logic - MOST IMPORTANT - Always applied at the end
            if self.current_block_underground_status:
                # If we're going underground for the first time, save current light states
                if not self.was_underground:
                    self.pre_underground_headlights = self.current_output.headlights_status
                    self.pre_underground_interior = self.current_output.interior_lights_status
                    self.was_underground = True
                
                # Force both lights ON when underground
                self.current_output.headlights_status = True
                self.current_output.interior_lights_status = True
            else:
                # If we were underground and now we're above ground, restore previous states
                if self.was_underground:
                    self.current_output.headlights_status = self.pre_underground_headlights
                    self.current_output.interior_lights_status = self.pre_underground_interior
                    self.was_underground = False

    def calculate_power(self, train_input: TrainModelInput, dt: float) -> float:
        """
        Real-time PI controller for motor power calculation with redundant voting.

        Args:
            train_input (TrainModelInput): Input values with speed info.
            dt (float): Time since last update, in seconds.

        Returns:
            float: Power output in kW (clamped to [0, 120]) or 0 if voting fails
        """
        # Calculate power 3 times with redundancy
        power_calculations = []
        
        for i in range(3):
            power_result = self._calculate_power_single(train_input, dt)
            power_calculations.append(power_result)
        
        # Implement voting method
        voted_power = self._vote_power_calculation(power_calculations)
        return voted_power
    
    def _calculate_power_single(self, train_input: TrainModelInput, dt: float) -> float:
        """
        Single power calculation using PI controller.

        Args:
            train_input (TrainModelInput): Input values with speed info.
            dt (float): Time since last update, in seconds.

        Returns:
            float: Power output in kW (clamped to [0, 120])
        """
        # Use current block speed limit from JSON track data (not from train_input)
        current_speed_limit = self.current_block_speed_limit
        
        # In auto mode, command speed values 0,1,2,3 map to fractions of speed limit
        if self.auto_mode:
            command_speed_value = self.current_block_commanded_speed
            if command_speed_value == 0:
                commanded_speed = (0) * current_speed_limit
            elif command_speed_value == 1:
                commanded_speed = (1/3) * current_speed_limit
            elif command_speed_value == 2:
                commanded_speed = (2/3) * current_speed_limit
            elif command_speed_value == 3:
                commanded_speed = current_speed_limit
            else:
                # Fallback for any other values
                commanded_speed = min(max(self.current_block_commanded_speed, 0.0), 0.8 * current_speed_limit)
        else:
            # Manual mode - use commanded speed directly with safety limit
            commanded_speed = min(max(self.current_block_commanded_speed, 0.0), 0.8 * current_speed_limit)
        
        self.setpoint_speed = commanded_speed
        
        # multiplied by 0.44704 to convert mph to mps
        speed_error = (commanded_speed - train_input.actual_speed) * 0.44704
        self.integral_error += speed_error * dt
        power_output = self.kp * speed_error + self.ki * self.integral_error
        #print(f"pwr Out: {power_output:.2f} kW, cmd speed: {commanded_speed * .44704:.2f} m/s, actual speed: {train_input.actual_speed * 0.44704:.2f} m/s, speed error: {speed_error:.2f} m/s, integral error: {self.integral_error:.2f} m/s")
        return max(0.0, min(MAX_POWER_KW, power_output))
    
    def _vote_power_calculation(self, power_calculations: list) -> float:
        """
        Voting method for power calculations.
        
        Args:
            power_calculations (list): List of 3 power calculation results
            
        Returns:
            float: Voted power value or 0 if unsure
        """
        # Check if all three calculations are identical
        if power_calculations[0] == power_calculations[1] == power_calculations[2]:
            return power_calculations[0]
        
        # Check if any two calculations match
        if power_calculations[0] == power_calculations[1]:
            return power_calculations[0]
        elif power_calculations[0] == power_calculations[2]:
            return power_calculations[0]
        elif power_calculations[1] == power_calculations[2]:
            return power_calculations[1]
        
        # If no two calculations match, check if they are within a small tolerance (1 kW)
        tolerance = 1.0
        if (abs(power_calculations[0] - power_calculations[1]) <= tolerance and
            abs(power_calculations[1] - power_calculations[2]) <= tolerance and
            abs(power_calculations[0] - power_calculations[2]) <= tolerance):
            # All values are close, return the average
            return sum(power_calculations) / 3
        
        # If unsure, return 0 for safety
        print(f"Power calculation voting failed: {power_calculations}. Returning 0 for safety.")
        return 0.0
    
    def get_output(self) -> TrainModelOutput:
        """Get the current TrainModelOutput for the Train Model."""
        return self.current_output
    
    def get_output_to_driver(self) -> OutputToDriver:
        """
        Get all information needed for the Driver UI display.
        
        Returns:
            OutputToDriver: Consolidated data for driver display.
        """
        # Use last known inputs or defaults
        train_input = self.last_train_input or TrainModelInput(
            fault_status={'signal': False, 'brake': False, 'engine': False},
            actual_speed=0.0,
            passenger_emergency_brake=False,
            cabin_temperature=72.0,
            next_station_number=0,
            authority_threshold=50.0,
            add_new_block_info=False,
            next_block_info={},
            next_block_entered=False,
            update_next_block_info=False
        )
        
        driver_input = self.last_driver_input or DriverInput(
            auto_mode=True,
            headlights_on=False,
            interior_lights_on=False,
            door_left_open=False,
            door_right_open=False,
            set_temperature=72.0,
            emergency_brake=False,
            set_speed=0.0,
            service_brake=False,
            train_id=1
        )
        
        # Determine input speed based on mode
        # Determine input speed based on mode
        #if self.auto_mode:
        #    input_speed = train_input.commanded_speed
        #else:
        #    input_speed = driver_input.set_speed
        input_speed = self.setpoint_speed

        # Lookup station information from track data
        station_info = self.get_station_info_by_number(train_input.next_station_number)
        next_station = station_info['name'] if station_info else "No Information"
        station_side = station_info['platform_side'] if station_info else "No Information"

        return OutputToDriver(
            # Speed Information
            input_speed=input_speed,
            actual_speed=train_input.actual_speed,
            speed_limit=self.current_block_speed_limit,  # Use JSON track data speed limit
            
            # Power and Authority
            power_output=self.current_output.power_kw,
            authority=self.calculated_authority,
            
            # Temperature
            current_cabin_temp=train_input.cabin_temperature,
            set_cabin_temp=self.current_output.set_cabin_temperature,
            
            # Control States
            auto_mode=self.auto_mode,
            emergency_brake_active=self.current_output.emergency_brake_status,
            service_brake_active=self.current_output.service_brake_status,
            
            # Environmental Controls
            headlights_on=self.current_output.headlights_status,
            interior_lights_on=self.current_output.interior_lights_status,
            left_door_open=self.current_output.door_left_status,
            right_door_open=self.current_output.door_right_status,
            
            # Station Information
            next_station=next_station,
            station_side=station_side,
            
            # Failure States
            engine_failure=train_input.fault_status.get('engine', False),
            signal_failure=train_input.fault_status.get('signal', False),
            brake_failure=train_input.fault_status.get('brake', False),
            
            # Controller Information
            kp=self.kp,
            ki=self.ki,
            kp_ki_set=self.kp_ki_set
        )
    
    def get_gains(self) -> tuple[float, float]:
        """Get current controller gains."""
        return self.kp, self.ki
    
    def set_gains(self, kp: float, ki: float):
        """Update controller gains and mark as set by engineer."""
        self.kp = kp
        self.ki = ki
        self.kp_ki_set = True
        
    def update_from_engineer_input(self, engineer_input: EngineerInput):
        """Update controller gains from engineer input."""
        self.set_gains(engineer_input.kp, engineer_input.ki)
    
    def reset(self):
        """
        Resets controller internal state.
        """
        self.integral_error = 0.0
        self.last_time = get_time().timestamp()
        self.debug_update_count = 0  # Reset debug counter
        self.last_train_input = None
        self.last_driver_input = None
        # Reset station stop state
        self.station_stop_timer = 0.0
        self.station_stop_active = False
        self.station_stop_complete_waiting = False
        self.last_station_stop_time = get_time().timestamp()
        self.station_authority_extended = False
        # Reset position tracking
        self.train_has_moved = False
        self.distance_traveled_in_current_block = 0.0
        self.last_position_update_time = get_time().timestamp()
        # Reset fault-based emergency brake state
        self.fault_emergency_brake_active = False
        self.last_fault_state = {'signal': False, 'brake': False, 'engine': False}
        # Note: Not resetting kp_ki_set here - engineer settings should persist
        self.current_output = TrainModelOutput(
            power_kw=0.0,
            emergency_brake_status=False,
            interior_lights_status=False,
            headlights_status=False,
            door_left_status=False,
            door_right_status=False,
            service_brake_status=False,
            set_cabin_temperature=72.0,
            train_id=self.train_id,
            station_stop_complete=False,
            next_station_name="No Information",
            next_station_side="No Information",
            edge_of_current_block=False,
        )
        
    def toggle_headlights(self, headlights_on: bool):
        """Toggle headlights on/off from driver UI."""
        if not self.auto_mode:  # Only allow manual control in manual mode
            self.current_output.headlights_status = headlights_on
    
    def toggle_interior_lights(self, interior_on: bool):
        """Toggle interior lights on/off from driver UI."""
        if not self.auto_mode:  # Only allow manual control in manual mode
            self.current_output.interior_lights_status = interior_on
    
    def get_block_essentials(self, block_number: int) -> dict:
        """
        Get essential block information from the already-loaded track data.
        Only returns what the train controller actually needs.
        
        Args:
            block_number: Block number to get information for
            
        Returns:
            Dictionary with essential block info: {block_number, length_meters, speed_limit_mph, underground}
            Returns None if block not found
        """
        try:
            block_key = str(block_number)
            if block_key not in self.track_data["blocks"]:
                return None
            
            block_info = self.track_data["blocks"][block_key]
            
            # Return only the essentials for train controller
            return {
                "block_number": block_info["block_number"],
                "length_meters": block_info["physical_properties"]["length_m"],
                "speed_limit_mph": round(block_info["physical_properties"]["speed_limit_kmh"] * 0.621371),  # Convert to mph and round
                "underground": block_info["infrastructure"]["is_underground"],
                "is_station": block_info["infrastructure"]["has_station"],
                "station_name": block_info.get("station", {}).get("name", None),
                "platform_side": block_info.get("station", {}).get("platform_side", None)
            }
        except Exception as e:
            print(f"Error getting essentials for block {block_number}: {e}")
            return None
    
    def get_station_info_by_number(self, station_number: int) -> dict:
        """
        Get station information by station number from track data.
        
        Args:
            station_number: Station number to lookup
            
        Returns:
            Dictionary with station info: {name, platform_side, block_number} or None if not found
        """
        try:
            # Search through all blocks to find the station by station number
            for block_key, block_info in self.track_data["blocks"].items():
                if (block_info["infrastructure"]["has_station"] and 
                    "station" in block_info and 
                    block_info["station"].get("station_number") == station_number):
                    
                    return {
                        "name": block_info["station"]["name"],
                        "platform_side": block_info["station"]["platform_side"],
                        "block_number": block_info["block_number"]
                    }
            
            # Station not found
            return None
            
        except Exception as e:
            print(f"Error looking up station {station_number}: {e}")
            return None
    
    def update_track_position(self, new_block: int):
        """
        Safely update the train's current block position using already-loaded track data.
        
        Args:
            new_block: New block number the train has entered
        """
        new_block_data = self.get_block_essentials(new_block)
        if new_block_data is None:
            print(f"Warning: Block {new_block} not found in {self.track_color} Line track data")
            return
        
        # Update current block information
        self.current_block = new_block
        self.current_block_speed_limit = new_block_data['speed_limit_mph']
        self.current_block_underground_status = new_block_data['underground']
        
        print(f"Updated to block {new_block}: Speed limit {self.current_block_speed_limit} mph, Underground: {self.current_block_underground_status}")
    
    @classmethod
    def from_engineer_input(cls, engineer_input: EngineerInput):
        """
        Create a TrainController from EngineerInput.
        
        Note: This method is deprecated as it doesn't provide track information.
        Use the main constructor with TrainControllerInit instead.
        """
        raise DeprecationWarning(
            "Creating TrainController from EngineerInput alone is no longer supported. "
            "Track information is required for safe operation. "
            "Please use TrainController(init_data, kp, ki) with proper TrainControllerInit data."
        )
    
    def _update_position_tracking(self, train_input: TrainModelInput, dt: float) -> None:
        """
        Update train position tracking for real-time authority calculation.
        
        Args:
            train_input: Current train model input data
            dt: Time since last update in seconds
        """
        # Check if train has started moving
        if train_input.actual_speed > 0.1 and not self.train_has_moved:
            self.train_has_moved = True
            print("Train has started moving - switching to post-movement authority calculation")
        
        # Calculate distance traveled since last update using kinematics
        # actual_speed is in mph, convert to m/s for calculation
        speed_ms = train_input.actual_speed * 0.44704  # Convert mph to m/s
        distance_this_update = speed_ms * dt  # Distance = speed × time
        
        # Add to total distance traveled in current block
        self.distance_traveled_in_current_block += distance_this_update
        
        # Get current block data to check length
        current_block_data = self.get_block_essentials(self.current_block)
        if current_block_data:
            current_block_length = current_block_data['length_meters']
            
            # Ensure we don't exceed the block length (train model should handle transitions)
            if self.distance_traveled_in_current_block > current_block_length:
                self.distance_traveled_in_current_block = current_block_length
                print(f"Clamped distance traveled to block length: {current_block_length:.1f}m")
        
        if distance_this_update > 0:
            print(f"Position update: traveled {distance_this_update:.2f}m this update, total in block: {self.distance_traveled_in_current_block:.1f}m")

    def _handle_block_progression(self, train_input: TrainModelInput) -> None:
        """
        Handle block progression logic and authority calculation.
        
        Args:
            train_input: Current train model input data
        """
        # Check for block transition using next_block_entered toggle
        if self.last_next_block_entered is None:
            # First reading - just store the value
            self.last_next_block_entered = train_input.next_block_entered
            print(f"Initial next_block_entered state: {train_input.next_block_entered}")
        else:
            # Check if next_block_entered has toggled
            if train_input.next_block_entered != self.last_next_block_entered:
                print(f"Block transition detected! next_block_entered toggled from {self.last_next_block_entered} to {train_input.next_block_entered}")
                self._handle_block_transition()
                self.last_next_block_entered = train_input.next_block_entered
        
        # Check for new block information - only if there's space in the queue
        if train_input.add_new_block_info and train_input.next_block_info:
            if len(self.known_blocks) < 4:
                print(f"New block info received: {train_input.next_block_info}")
                print(f"Current queue size: {len(self.known_blocks)}/4 - Adding new block")
                self._handle_new_block_info(train_input.next_block_info)
            else:
                print(f"Block queue full ({len(self.known_blocks)}/4) - Cannot add new block {train_input.next_block_info.get('block_number', 'Unknown')}")
                print("New block will be accepted after train moves to next block")
        
        # Check for block information updates (can happen anytime)
        if train_input.update_next_block_info and train_input.next_block_info:
            print(f"Block update request received: {train_input.next_block_info}")
            self._handle_block_update(train_input.next_block_info)
        
        # Calculate current authority based on known blocks
        self._calculate_authority()

    def _handle_block_transition(self) -> None:
        """
        Handle when train enters a new block.
        Move the first block from next_four_blocks to current block.
        This creates space in the queue for a new 4th block.
        """
        if not self.known_blocks:
            print("Warning: No blocks in queue during transition")
            return
        
        # Move to next block
        next_block = self.known_blocks.pop(0)  # Remove first block from queue
        old_block = self.current_block
        
        # Update current block information
        self.current_block = next_block.block_number
        self.current_block_commanded_speed = next_block.commanded_speed
        self.authorized_current_block = next_block.authorized_to_go
        
        # Update block properties from track data
        block_data = self.get_block_essentials(self.current_block)
        if block_data:
            self.current_block_speed_limit = block_data['speed_limit_mph']
            self.current_block_underground_status = block_data['underground']
        
        # Reset distance tracking for new block
        self.distance_traveled_in_current_block = 0.0
        
        # Reset station stop waiting if we were waiting (both conditions met: authorized + moved)
        if self.station_stop_complete_waiting:
            self.station_stop_complete_waiting = False
            print(f"Station stop complete waiting reset - train successfully moved to block {self.current_block}")
        
        print(f"Transitioned from block {old_block} to block {self.current_block}")
        print(f"New block - Speed limit: {self.current_block_speed_limit} mph, Underground: {self.current_block_underground_status}")
        print(f"Queue status: {len(self.known_blocks)}/4 blocks (space available for new block)")
        print("Reset distance tracking for new block")
        
        # Show the current block progression
        if self.known_blocks:
            block_numbers = [block.block_number for block in self.known_blocks]
            print(f"Next blocks in queue: {block_numbers}")
        else:
            print("Block queue is empty - train model should provide new blocks")

    def _handle_new_block_info(self, next_block_info: dict) -> None:
        """
        Handle new block information received from train model.
        Only called when there's space in the 4-block queue.
        
        Args:
            next_block_info: Dictionary with block info
                {block_number: int, commanded_speed: float, authorized_to_go_on_the_block: int (0 or 1)}
        """
        try:
            # Validate that we have space (should always be true when this is called)
            if len(self.known_blocks) >= 4:
                print(f"ERROR: Attempting to add block when queue is full ({len(self.known_blocks)}/4)")
                return
            
            # Extract commanded_speed from next_block_info dict
            commanded_speed = int(next_block_info['commanded_speed'])
            
            # Create new BlockInfo from received data
            new_block = BlockInfo(
                block_number=int(next_block_info['block_number']),
                length_meters=0.0,  # Will be filled from track data
                speed_limit_mph=0.0,  # Will be filled from track data
                underground=False,  # Will be filled from track data
                authorized_to_go=bool(next_block_info['authorized_to_go_on_the_block']),
                commanded_speed=commanded_speed
            )
            
            # Get block details from track data
            block_data = self.get_block_essentials(new_block.block_number)
            if block_data:
                new_block.length_meters = block_data['length_meters']
                new_block.speed_limit_mph = block_data['speed_limit_mph']
                new_block.underground = block_data['underground']
            else:
                print(f"Warning: Could not find track data for block {new_block.block_number}")
            
            # Add to end of known blocks queue (position 4)
            self.known_blocks.append(new_block)
            queue_position = len(self.known_blocks)
            print(f"Added block {new_block.block_number} to queue position {queue_position}/4")
            print(f"Block {new_block.block_number} - Speed: {commanded_speed}, Auth: {new_block.authorized_to_go}")
            
            # Show current queue status
            if len(self.known_blocks) == 4:
                print("Block queue is now FULL (4/4) - no more blocks can be added until train moves")
            else:
                print(f"Block queue: {len(self.known_blocks)}/4 - space available for {4 - len(self.known_blocks)} more blocks")
            
        except Exception as e:
            print(f"Error handling new block info: {e}")

    def _handle_block_update(self, next_block_info: dict) -> None:
        """
        Handle block information updates - can be used to update any existing block in the queue OR current block.
        This does NOT add new blocks, only updates existing ones.
        
        Args:
            next_block_info: Dictionary with block info
                {block_number: int, commanded_speed: float, authorized_to_go_on_the_block: int (0 or 1)}
        """
        try:
            block_number_to_update = int(next_block_info['block_number'])
            commanded_speed = int(next_block_info['commanded_speed'])
            authorized_to_go = bool(next_block_info['authorized_to_go_on_the_block'])
            
            block_found = False
            
            # First check if it's the current block
            if block_number_to_update == self.current_block:
                old_auth = self.authorized_current_block
                old_speed = self.current_block_commanded_speed
                
                # Update current block information
                self.authorized_current_block = authorized_to_go
                self.current_block_commanded_speed = commanded_speed
                
                print(f"Updated CURRENT block {block_number_to_update}:")
                print(f"  Authorization: {old_auth} → {authorized_to_go}")
                print(f"  Commanded Speed: {old_speed} → {commanded_speed}")
                
                block_found = True
                
                # If we were waiting for a station stop update and this block is now authorized
                # Note: Don't reset station_stop_complete_waiting here - only reset it when train actually moves to next block
                if self.station_stop_complete_waiting and authorized_to_go:
                    print(f"Next block {block_number_to_update} now authorized - train can proceed when ready!")
                    print("Station stop waiting will reset when train moves to next block")
            
            # If not current block, check the queue (next 4 blocks)
            if not block_found:
                for i, block in enumerate(self.known_blocks):
                    if block.block_number == block_number_to_update:
                        old_auth = block.authorized_to_go
                        old_speed = block.commanded_speed
                        
                        # Update the block information
                        block.authorized_to_go = authorized_to_go
                        block.commanded_speed = commanded_speed
                        
                        print(f"Updated block {block_number_to_update} in queue position {i+1}/4:")
                        print(f"  Authorization: {old_auth} → {authorized_to_go}")
                        print(f"  Commanded Speed: {old_speed} → {commanded_speed}")
                        
                        block_found = True
                        
                        # If we were waiting for a station stop update and this block is now authorized
                        # Note: Don't reset station_stop_complete_waiting here - only reset it when train actually moves to next block
                        if self.station_stop_complete_waiting and authorized_to_go:
                            print(f"Next block {block_number_to_update} now authorized - train can proceed when ready!")
                            print("Station stop waiting will reset when train moves to next block")
                        
                        break
            
            if not block_found:
                print(f"Warning: Block {block_number_to_update} not found in current block or queue for update")
                print(f"Current block: {self.current_block}")
                if self.known_blocks:
                    block_numbers = [block.block_number for block in self.known_blocks]
                    print(f"Queue contains blocks: {block_numbers}")
                else:
                    print("Queue is currently empty")
            
        except Exception as e:
            print(f"Error handling block update: {e}")

    def _calculate_authority(self) -> None:
        """
        Calculate total authority based on train position and block authorization status.
        
        NEW Logic:
        1. Initial placement: Only count next blocks (train starts at edge)
        2. After movement: Count remaining current block + next blocks
        3. Station handling: Authority always stops at middle of station blocks
        4. Real-time updates: Subtract distance traveled from current block
        5. Authority calculation stops at either unauthorized block OR station block middle, whichever comes first
        """
        total_authority = 0.0
        
        # Only calculate authority if current block is authorized
        if not self.authorized_current_block:
            self.calculated_authority = 0.0
            print("Current block not authorized - Authority = 0")
            return
        
        # Get current block information
        current_block_data = self.get_block_essentials(self.current_block)
        if not current_block_data:
            self.calculated_authority = 0.0
            print("Could not get current block data - Authority = 0")
            return
        
        current_block_length = current_block_data.get('length_meters', 0)
        current_is_station = current_block_data.get('is_station', False)
        
        # === CURRENT BLOCK AUTHORITY CALCULATION ===
        if not self.train_has_moved:
            # Initial placement - train is at edge of current block, don't include current block
            print(f"Initial placement - not including current block {self.current_block} in authority")
        else:
            # Train has moved - include remaining length of current block
            remaining_current_block = current_block_length - self.distance_traveled_in_current_block
            
            # Ensure remaining distance is not negative
            remaining_current_block = max(0.0, remaining_current_block)
            
            if current_is_station:
                # Station block - always stop at middle regardless of next block authorization
                if self.station_stop_complete_waiting:
                    # Station stop complete, add the other half (where train hasn't been)
                    half_block = current_block_length / 2.0
                    other_half_remaining = max(0.0, half_block - self.distance_traveled_in_current_block)
                    total_authority += other_half_remaining
                    print(f"Station stop complete - Current station block {self.current_block}: +{other_half_remaining:.1f}m (other half remaining)")
                else:
                    # Station but not stopped yet - only count up to half block, distance_traveled_in_current_block is set to 0 after 60 seconds stop at the station
                    half_block = current_block_length / 2.0
                    remaining_to_half = max(0.0, half_block - self.distance_traveled_in_current_block)
                    total_authority += remaining_to_half
                    print(f"Current station block {self.current_block}: +{remaining_to_half:.1f}m (remaining to station stop point)")
                    # Convert to yards for compatibility (1 meter = 1.09361 yards)
                    total_authority_yards = total_authority * 1.09361
                    
                    self.calculated_authority = total_authority_yards
                    print(f"Total calculated authority: {total_authority_yards:.1f} yards ({total_authority:.1f} meters)")
                    return
            else:
                # Normal block - add full remaining length
                total_authority += remaining_current_block
                print(f"Current block {self.current_block}: +{remaining_current_block:.1f}m (remaining after {self.distance_traveled_in_current_block:.1f}m traveled)")
        
        # === NEXT BLOCKS AUTHORITY CALCULATION ===
        for i, block in enumerate(self.known_blocks):
            if not block.authorized_to_go:
                print(f"Authority calculation stopped at block {block.block_number} (unauthorized)")
                print(f"Ignoring ALL blocks after unauthorized block {block.block_number}")
                break
            
            # Check if this is a station block
            block_data = self.get_block_essentials(block.block_number)
            is_station = block_data and block_data.get('is_station', False)
            
            if is_station:
                # Station block - always add only half length and stop authority calculation
                half_station_length = block.length_meters / 2.0
                total_authority += half_station_length
                print(f"Next station block {block.block_number}: +{half_station_length:.1f}m (half length - authority stops at station)")
                print(f"Authority calculation stopped at station block {block.block_number}")
                break
            else:
                # Normal block - add full length and continue
                total_authority += block.length_meters
                print(f"Next block {block.block_number}: +{block.length_meters}m (authorized)")
        
        # Convert to yards for compatibility (1 meter = 1.09361 yards)
        total_authority_yards = total_authority * 1.09361
        
        self.calculated_authority = total_authority_yards
        print(f"Total calculated authority: {total_authority_yards:.1f} yards ({total_authority:.1f} meters)")

    def get_calculated_authority(self) -> float:
        """
        Get the current calculated authority in yards.
        
        Returns:
            Current authority in yards
        """
        return self.calculated_authority

    def _handle_station_stop(self, train_input: TrainModelInput, dt: float) -> None:
        """
        Handle 60-second station stop logic when train speed reaches zero.
        After 60 seconds, wait for train model to update next block authorization.
        
        Args:
            train_input: Current train model input data
            dt: Time since last update in seconds
        """
        # Only reset station stop complete flag when train is moving
        if train_input.actual_speed >= 0.1:
            self.current_output.station_stop_complete = False
        
        # Check if train has stopped (speed is essentially zero)
        if train_input.actual_speed < 0.1:
            # Get current block information to check if it's a station
            current_block_data = self.get_block_essentials(self.current_block)
            
            if current_block_data and current_block_data.get('is_station', False):
                # We're at a station and stopped
                if not self.station_stop_active and not self.station_stop_complete_waiting:
                    # Start the 60-second timer
                    self.station_stop_active = True
                    self.station_stop_timer = 0.0
                    self.last_station_stop_time = get_time().timestamp()
                    print(f"Station stop started at block {self.current_block} - {current_block_data.get('station_name', 'Unknown Station')}")
                
                # Continue timing if station stop is active
                if self.station_stop_active:
                    self.station_stop_timer += dt
                    
                    if self.station_stop_timer < 60.0:
                        # Still within 60 seconds - keep service brake on
                        print(f"Station stop in progress: {self.station_stop_timer:.1f}/60.0 seconds")
                    else:
                        # 60 seconds completed - stop timing and wait for train model update
                        self.station_stop_active = False
                        self.station_stop_complete_waiting = True
                        # Reset distance tracking so the "other half" calculation works correctly
                        self.distance_traveled_in_current_block = 0.0
                        print(f"Station stop 60 seconds completed at block {self.current_block}")
                        print("Reset distance tracking for station authority calculation")
                        print("Waiting for train model to update next block authorization...")
                
                # If waiting for update and still stopped, keep service brake on
                if self.station_stop_complete_waiting:
                    #self.current_output.service_brake_status = False
                    self.current_output.station_stop_complete = True
                    print(f"Station stop complete - waiting for update_next_block_info from train model")
        else:
            # Train is moving - reset all station stop states
            if self.station_stop_active or self.station_stop_complete_waiting:
                self.station_stop_active = False
                self.station_stop_timer = 0.0
                print("Station stop cancelled - train is moving")

    def _handle_fault_emergency_brake(self, train_input: TrainModelInput) -> None:
        """
        Handle fault-based emergency brake activation/deactivation.
        
        Critical safety logic:
        - Automatically activates emergency brake when ANY fault occurs (signal, brake, or engine)
        - Only automatically deactivates when all faults are resolved AND it was activated by faults
        - Does not interfere with driver/passenger emergency brake activation
        
        Args:
            train_input: Current train model input data
        """
        current_fault_state = {
            'signal': train_input.fault_status.get('signal', False),
            'brake': train_input.fault_status.get('brake', False),
            'engine': train_input.fault_status.get('engine', False)
        }
        
        # Check if any fault is currently active
        any_fault_active = any(current_fault_state.values())
        
        # Check if fault state has changed
        fault_state_changed = current_fault_state != self.last_fault_state
        
        if fault_state_changed:
            # Report fault state changes
            for fault_type, is_active in current_fault_state.items():
                if is_active != self.last_fault_state[fault_type]:
                    state_str = "ACTIVATED" if is_active else "RESOLVED"
                    print(f"CRITICAL SAFETY: {fault_type.upper()} fault {state_str}")
        
        # Activate fault-based emergency brake if any fault is detected
        if any_fault_active and not self.fault_emergency_brake_active:
            self.fault_emergency_brake_active = True
            print("CRITICAL SAFETY: Fault-based emergency brake ACTIVATED due to system fault")
            print(f"Active faults: {[k for k, v in current_fault_state.items() if v]}")
        
        # Deactivate fault-based emergency brake only if:
        # 1. All faults are resolved AND
        # 2. Fault-based emergency brake was previously active
        elif not any_fault_active and self.fault_emergency_brake_active:
            self.fault_emergency_brake_active = False
            print("CRITICAL SAFETY: Fault-based emergency brake DEACTIVATED - all faults resolved")
        
        # Update last known fault state
        self.last_fault_state = current_fault_state.copy()
    
    def _update_edge_of_current_block_detection(self, train_input: TrainModelInput) -> None:
        """
        TODO: Remove after iteration 3 - using only for simulating track
        Detect when train is at the edge of current block for automatic testing.
        
        Args:
            train_input: Current train model input data
        """
        # Get current block information
        current_block_data = self.get_block_essentials(self.current_block)
        if not current_block_data:
            self.current_output.edge_of_current_block = False
            return
        
        current_block_length = current_block_data.get('length_meters', 0)
        
        # Consider train at edge if it has traveled more than 90% of the current block length
        # This gives some buffer before the actual block transition
        edge_threshold = 0.9 * current_block_length
        
        # Only check if train has moved and we have valid distance data
        if self.train_has_moved and current_block_length > 0:
            at_edge = self.distance_traveled_in_current_block >= edge_threshold
            
            # Only update if state changed (to avoid spam)
            if at_edge != self.current_output.edge_of_current_block:
                self.current_output.edge_of_current_block = at_edge
                if at_edge:
                    print(f"EDGE DETECTION: Train at edge of block {self.current_block} - {self.distance_traveled_in_current_block:.1f}m/{current_block_length:.1f}m")
                else:
                    print(f"EDGE DETECTION: Train no longer at edge of block {self.current_block}")
        else:
            # Train hasn't moved yet or no valid block data - not at edge
            self.current_output.edge_of_current_block = False