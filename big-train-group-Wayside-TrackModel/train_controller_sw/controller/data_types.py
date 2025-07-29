#File Location: train_controller_sw/controller/data_types.py
from dataclasses import dataclass

@dataclass
class TrainModelInput:
    """
    Represents inputs received from the Train Model.

    Attributes:
        fault_status (dict): A dictionary indicating fault states.
        Keys: "signal", "brake", "engine" — all with boolean values.
        actual_speed (float): Current speed of the train (in mph).
        passenger_emergency_brake (bool): True if the emergency brake is pulled by a passenger.
        cabin_temperature (float): Current temperature inside the cabin (in °F).
        next_station_number (int): Station number for the upcoming station (used to lookup name and side).
    """
    fault_status: dict                  # Dictionary with fault status (bool values): Signal, Brake, Engine
    actual_speed: float                 # in mph
    passenger_emergency_brake: bool     # True if passenger emergency brake is applied
    cabin_temperature: float            # in Fahrenheit
    next_station_number: int            # Station number for the upcoming station
    authority_threshold: float          # Distance threshold in yards to start braking
    add_new_block_info: bool            # True if new block info is to be added
    next_block_info: dict               # Dictionary with next block information. {block_number: int, commanded_speed: float, authorized_to_go_on_the_block: int (0 or 1)}
    next_block_entered: bool            # toggles between True and False when the next block is entered
    update_next_block_info: bool        # True if train model should update next block authorization
    
@dataclass
class TrainModelOutput:
    """
    Represents outputs to be sent back to the Train Model.

    Attributes:
        power_kw (float): Power supposed to be used (in kilowatts).
        emergency_brake_status (bool): True if emergency brake is being applied.
        interior_lights_status (bool): True if interior lights should be on.
        headlights_status (bool): True if headlights should be on.
        door_left_status (bool): True if left-side door should be open.
        door_right_status (bool): True if right-side door should be open.
        service_brake_status (bool): True if service brake is being applied.
        set_cabin_temperature (float): Target cabin temperature (in °F).
        train_id (str): ID of the currently selected train.
        station_stop_complete (bool): True when 60-second station stop is complete.
        next_station_name (str): Name of the next station based on next_station_number.
        next_station_side (str): Platform side for the next station ("left", "right", or "both").
        edge_of_current_block (bool): True when train is at the edge of current block (temporary for iteration 3 simulation).
    """
    power_kw: float                     # Power in kW
    emergency_brake_status: bool        # True if emergency brake is applied    
    interior_lights_status: bool        # True if interior lights are on
    headlights_status: bool             # True if headlights are on
    door_left_status: bool              # True if left door is open
    door_right_status: bool             # True if right door is open
    service_brake_status: bool          # True if service brake is applied
    set_cabin_temperature: float        # in Fahrenheit
    train_id: str                       # ID of the currently selected train
    station_stop_complete: bool         # True when 60-second station stop is complete
    next_station_name: str              # Name of the next station
    next_station_side: str              # Platform side for the next station
    edge_of_current_block: bool         # TODO: Remove after iteration 3 - using only for simulating track


@dataclass
class DriverInput:
    """
    Represents manual or automatic driver control inputs.

    Attributes:
        auto_mode (bool): True if auto mode is active.
        headlights_on (bool): True if driver has turned on headlights.
        interior_lights_on (bool): True if interior lights are requested.
        door_left_open (bool): True if the driver wants left door open.
        door_right_open (bool): True if the driver wants right door open.
        set_temperature (float): Desired cabin temperature (in °F).
        emergency_brake (bool): True if driver activates emergency brake.
        set_speed (float): Desired speed when in manual mode (in mph).
        service_brake (bool): True if driver activates service brake in manual mode.
        train_id (str): ID of the currently selected train.
    """
    auto_mode: bool                     # True if auto mode is enabled
    headlights_on: bool                 # True if headlights are on
    interior_lights_on: bool            # True if interior lights are on
    door_left_open: bool                # True if left door is open
    door_right_open: bool               # True if right door is open
    set_temperature: float              # Desired cabin temperature in Fahrenheit
    emergency_brake: bool               # True if emergency brake is applied
    set_speed: float                    # Desired speed in mph
    service_brake: bool                 # True if service brake is applied
    train_id: str                       # ID of the currently selected train
    
@dataclass
class EngineerInput:
    """
    Parameters input by the train engineer before train starts.
    
    Attributes:
        kp (float): Proportional gain.
        ki (float): Integral gain.
    """
    kp: float
    ki: float

@dataclass
class BlockInfo:
    """
    Information about a single track block.
    
    Attributes:
        block_number (int): The block number.
        length_meters (float): Length of the block in meters.
        speed_limit_mph (float): Speed limit for this block in mph.
        underground (bool): True if block is underground.
        authorized_to_go (bool): True if train is authorized to enter this block.
        commanded_speed (int): Commanded speed for this block (0, 1, 2, or 3).
    """
    block_number: int
    length_meters: float
    speed_limit_mph: float
    underground: bool
    authorized_to_go: bool
    commanded_speed: int


@dataclass
class TrainControllerInit:
    """
    Initialization data for train controller with track information.
    
    Attributes:
        track_color (str): Track color ("red" or "green").
        current_block (int): Current block number.
        current_commanded_speed (int): Commanded speed for current block (0, 1, 2, or 3).
        authorized_current_block (bool): Authorization for current block.
        next_four_blocks (list): List of next 4 BlockInfo objects in track order.
        train_id (str): ID of the train (e.g., "1", "2", "3").
        next_station_number (int): Number of the next station.
    """
    track_color: str
    current_block: int
    current_commanded_speed: int
    authorized_current_block: bool
    next_four_blocks: list  # List of BlockInfo objects
    train_id: str
    next_station_number: int

@dataclass
class OutputToDriver:
    """
    Represents all information that needs to be displayed on the Driver UI.
    This consolidates data from TrainModelInput, TrainModelOutput, and controller state.

    Attributes:
        # Speed Information
        input_speed (float): Either commanded speed (auto) or set speed (manual) in mph.
        actual_speed (float): Current speed of the train (in mph).
        speed_limit (float): Maximum allowed speed on current track segment (in mph).
        
        # Power and Authority
        power_output (float): Current power output (in kW).
        authority (float): Distance the train is allowed to travel (in yards).
        
        # Temperature
        current_cabin_temp (float): Current cabin temperature (in °F).
        set_cabin_temp (float): Target cabin temperature (in °F).
        
        # Control States
        auto_mode (bool): True if in auto mode, False if manual.
        emergency_brake_active (bool): True if emergency brake is applied.
        service_brake_active (bool): True if service brake is applied.
        
        # Environmental Controls
        headlights_on (bool): True if headlights are on.
        interior_lights_on (bool): True if interior lights are on.
        left_door_open (bool): True if left door is open.
        right_door_open (bool): True if right door is open.
        
        # Station Information
        next_station (str): Name of the upcoming station.
        station_side (str): Which side the station is on — "left" or "right".
        
        # Failure States
        engine_failure (bool): True if engine failure is detected.
        signal_failure (bool): True if signal failure is detected.
        brake_failure (bool): True if brake failure is detected.
        
        # Controller Information
        kp (float): Current proportional gain.
        ki (float): Current integral gain.
        kp_ki_set (bool): True if engineer has applied Kp/Ki values.
    """
    # Speed Information
    input_speed: float                  # Commanded/set speed in mph
    actual_speed: float                 # Current speed in mph
    speed_limit: float                  # Speed limit in mph
    
    # Power and Authority
    power_output: float                 # Power in kW
    authority: float                    # Authority in yards
    
    # Temperature
    current_cabin_temp: float           # Current temperature in Fahrenheit
    set_cabin_temp: float              # Set temperature in Fahrenheit
    
    # Control States
    auto_mode: bool                     # True if auto mode
    emergency_brake_active: bool        # True if emergency brake applied
    service_brake_active: bool          # True if service brake applied
    
    # Environmental Controls
    headlights_on: bool                 # True if headlights on
    interior_lights_on: bool            # True if interior lights on
    left_door_open: bool               # True if left door open
    right_door_open: bool              # True if right door open
    
    # Station Information
    next_station: str                   # Next station name
    station_side: str                   # Platform side
    
    # Failure States
    engine_failure: bool                # True if engine failure
    signal_failure: bool                # True if signal failure
    brake_failure: bool                 # True if brake failure
    
    # Controller Information
    kp: float                          # Proportional gain
    ki: float                          # Integral gain
    kp_ki_set: bool                    # True if engineer has applied values
