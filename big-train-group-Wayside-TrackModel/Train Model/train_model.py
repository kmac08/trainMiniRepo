# =============================================================================
#  train_model.py
# =============================================================================

import random
from dataclasses import dataclass
from typing import List, Dict

# -----------------------------------------------------------------------------
#  Dataclasses exchanged with the Train Controller backend
# -----------------------------------------------------------------------------

@dataclass
class TrainModelInput:
    """Packet we send to the Train Controller each control tick."""
    fault_status: Dict[str, bool]            # {'signal','brake','engine'}
    actual_speed: float                      # mph
    passenger_emergency_brake: bool          # EB pulled (driver OR passenger)
    cabin_temperature: float                 # °F
    next_station_number: int
    authority_threshold: float               # yards – dynamic stopping distance

    # Block‑queue handshake
    add_new_block_info: bool
    next_block_info: Dict[str, int]          # {'block_number','commanded_speed','authorized_to_go_on_the_block'}
    next_block_entered: bool
    update_next_block_info: bool

@dataclass
class TrainModelOutput:
    """Packet returned from the Train Controller."""
    power_kw: float
    emergency_brake_status: bool
    interior_lights_status: bool
    headlights_status: bool
    door_left_status: bool
    door_right_status: bool
    service_brake_status: bool
    set_cabin_temperature: float            
    train_id: str
    station_stop_complete: bool
    next_station_name: str
    next_station_side: str
    edge_of_current_block: bool

# -----------------------------------------------------------------------------
#                                Train Model
# -----------------------------------------------------------------------------

class TrainModel:
    """Point‑mass physics + minimal protocol adapter for the PI controller."""

    # ------------------------------------------------------------------
    #  INITIALIZATION
    # ------------------------------------------------------------------

    def __init__(self, train_id: str):
        self.train_id = train_id

        # ---- Physical state ----
        self.mass_kg = 40900
        self.velocity_mps = 0.0
        self.acceleration_mps2 = 0.0
        self.previous_acceleration = 0.0

        # Power / commanded speed (traffic signal 0‑3)
        self.power_watts = 0.0
        self.command_speed_signal = 0  # 00,01,10,11
        self.max_acceleration = 0.5
        self.authority_m = 0

        # Terrain & limits
        self.speed_limit_mps = 0.0
        self.grade_percent = 0.0
        self.elevation_m = 0.0
        self.gravity = 9.81

        # Braking / faults
        self.service_brake_engaged = False
        self.emergency_brake_engaged = False  # Controller's emergency brake command
        self.passenger_emergency_brake = False  # Passenger-initiated emergency brake (independent)
        self.brake_failure = False
        self.engine_failure = False
        self.signal_failure = False

        # Travel stats
        self.total_distance_m = 0.0
        self.authority_threshold = 0.0

        # Cabin / environment
        self.cabin_temperature = 72.0  # Current actual temperature (°F)
        self.target_cabin_temperature = 72.0  # Setpoint from controller (°F)
        self.temperature_time_constant = 30.0  # Time constant for first-order response (seconds)
        self.left_doors_open = False
        self.right_doors_open = False
        self.interior_lights_on = False
        self.exterior_lights_on = False

        # People
        self.crew_count = random.randint(2, 8)
        self.passenger_count = 0
        self.person_mass = 70
        self.update_mass()

        # # Track‑circuit handshake
        self.next_station_code = 0
        self.next_block_info = {
            "block_number": -1,
            "commanded_speed": 0,
            "authorized_to_go_on_the_block": 0,
        }
        self.add_new_block_info = False
        self.update_next_block_info = False
        self.next_block_entered = False

        # Track circuit info (updated via parser)
        self.tc_block_number = 0
        self.tc_commanded_signal = 0
        self.tc_authority_bit = 0
        self.tc_new_block_flag = 0
        self.tc_next_block_entered_flag = 0
        self.tc_update_block_in_queue = 0
        self.tc_station_number = 0

        # Dashboard helper
        self.next_stop = "Yard"
        self.next_stop_side = ""
        
        # TODO: Remove after iteration 3 - using only for simulating track
        self.edge_of_current_block = False

    # ------------------------------------------------------------------
    #  PHYSICS CORE
    # ------------------------------------------------------------------

    def update_mass(self) -> None:
        """Re‑compute total train mass based on crew + passengers."""
        self.mass_kg = 40900 + (self.passenger_count + self.crew_count) * self.person_mass

    def update_speed(self, dt: float) -> None:
        """Physics by *dt* seconds using trapezoidal integration."""

        # Handle engine failure = no power output
        power = 0.0 if self.engine_failure else self.power_watts
        self.set_power(power)

        # Avoid divide-by-zero by assuming small velocity if at rest
        safe_velocity = self.velocity_mps if self.velocity_mps > 0.1 else 0.1

        # Compute force from power: F = P / v
        applied_force = power / safe_velocity

        # Grade resistance (opposes motion uphill, assists downhill)
        grade_force = self.mass_kg * self.gravity * (self.grade_percent / 100.0)

        net_force = applied_force - grade_force

        # Acceleration = net force / mass
        new_acceleration = net_force / self.mass_kg

        # Brake overrides (emergency brake from either controller command OR passenger)
        if self.emergency_brake_engaged or self.passenger_emergency_brake:
            new_acceleration = -2.73
        elif self.service_brake_engaged and not self.brake_failure:
            new_acceleration = -1.2
        else:
            if new_acceleration > self.max_acceleration:
                new_acceleration = self.max_acceleration

        # Trapezoidal integration of velocity
        self.velocity_mps += 0.5 * dt * (new_acceleration + self.previous_acceleration)
        self.velocity_mps = max(self.velocity_mps, 0.0)

        # Distance integration (backward Euler)
        self.total_distance_m += self.velocity_mps * dt

        # Save current acceleration for next round
        self.previous_acceleration = new_acceleration
        self.acceleration_mps2 = new_acceleration
        
        # Update cabin temperature using first-order system dynamics
        self.update_cabin_temperature(dt)

    # ------------------------------------------------------------------
    #  STOPPING DISTANCE UTILITY
    # ------------------------------------------------------------------

    def get_stopping_distance_yards(self) -> float:
        """Estimate yards required to come to a complete stop from current speed.

        Uses the available braking deceleration (service or emergency) and
        factors in track grade (gravity component). Mass is already captured
        by the specified deceleration limits.
        """
        v = self.velocity_mps  # current speed (m/s)

        # Choose deceleration profile
        if (self.emergency_brake_engaged or self.passenger_emergency_brake) and not self.brake_failure:
            decel = 2.73  # m/s² emergency
        else:
            # Use service brake spec for planning stop distance when e‑brake not engaged
            decel = 1.2   # m/s² service

        # Adjust deceleration for grade (assist/hinder)
        grade_acc = self.gravity * (self.grade_percent / 100.0)
        net_decel = decel + grade_acc  # downhill grade_percent negative ⇒ reduces net_decel

        # Prevent division by zero / negative decel values
        net_decel = max(net_decel, 0.01)

        stopping_distance_m = (v ** 2) / (2 * net_decel)
        return stopping_distance_m * 1.09361  # meters → yards

    # ------------------------------------------------------------------
    #  TRACK‑CIRCUIT HELPERS
    # ------------------------------------------------------------------

    def parse_track_circuit(self, data_packet: int):
        if self.signal_failure:
            print("Signal Failure: Failed to Parse Data Packet")
        else:
            self.tc_block_number = (data_packet >> 11) & 0b1111111
            self.tc_commanded_signal = (data_packet >> 9) & 0b11
            self.tc_authority_bit = (data_packet >> 8) & 0b1
            self.tc_new_block_flag = (data_packet >> 7) & 0b1
            self.tc_next_block_entered_flag = (data_packet >> 6) & 0b1
            self.tc_update_block_in_queue = (data_packet >> 5) & 0b1
            self.tc_station_number = data_packet & 0b11111

    def receive_track_circuit_data(self, block_num: int, cmd_speed: int, auth_bit: int, is_new: bool) -> None:
        """Called every 2 s with decoded payload from rails."""
        self.next_block_info.update({
            "block_number": block_num,
            "commanded_speed": cmd_speed,
            "authorized_to_go_on_the_block": auth_bit,
        })
        self.add_new_block_info = is_new
        self.update_next_block_info = not is_new

    def mark_next_block_entered(self) -> None:
        """Toggle flag – controller detects transition on change."""
        self.next_block_entered = not self.next_block_entered

    # ------------------------------------------------------------------
    #  CONTROLLER SERIALISATION
    # ------------------------------------------------------------------

    def build_train_input(self) -> TrainModelInput:
        """Package current state into dataclass for controller."""
        self.authority_threshold = self.get_stopping_distance_yards()
        
         # Use initialized next_station_code if no track circuit data received yet
        station_number = self.tc_station_number if self.tc_station_number > 0 else self.next_station_code
        
        # Debug logging for station number logic
        if station_number != self.tc_station_number:
            print(f"DEBUG TrainModel: Using next_station_code {self.next_station_code} (tc_station_number is {self.tc_station_number})")
        else:
            print(f"DEBUG TrainModel: Using tc_station_number {self.tc_station_number}")
            
        return TrainModelInput(
            fault_status={
                "signal": self.signal_failure,
                "brake": self.brake_failure,
                "engine": self.engine_failure,
            },
            actual_speed=self.velocity_mps * 2.237,
            passenger_emergency_brake=self.passenger_emergency_brake,
            cabin_temperature=self.cabin_temperature,
            next_station_number=station_number,
            authority_threshold=self.authority_threshold,
            add_new_block_info=self.tc_new_block_flag,
            next_block_info={
            "block_number": self.tc_block_number,
            "commanded_speed": self.tc_commanded_signal,
            "authorized_to_go_on_the_block": self.tc_authority_bit
            },
            next_block_entered=self.tc_next_block_entered_flag,
            update_next_block_info=self.tc_update_block_in_queue
        )
    
    def apply_controller_output(self, output: TrainModelOutput) -> None:
        """Apply controller commands to physical model."""
        self.set_power(output.power_kw * 1000)  # kW → W
        self.emergency_brake_engaged = output.emergency_brake_status
        self.service_brake_engaged = output.service_brake_status
        self.set_left_doors(output.door_left_status)
        self.set_right_doors(output.door_right_status)
        self.set_exterior_lights(output.headlights_status)
        self.set_interior_lights(output.interior_lights_status)
        self.set_cabin_temperature(output.set_cabin_temperature)
        self.next_stop = output.next_station_name
        self.next_stop_side = output.next_station_side
        # TODO: Remove after iteration 3 - using only for simulating track
        self.edge_of_current_block = output.edge_of_current_block

    # ------------------------------------------------------------------
    #  SETTERS / GETTERS
    # ------------------------------------------------------------------

    def get_distance_traveled(self):
        return self.total_distance_m

    def set_power(self, power_watts: float):
        self.power_watts = power_watts

    def set_cabin_temperature(self, temp: float):
        """Set the target cabin temperature (from controller)"""
        self.target_cabin_temperature = temp

    def update_cabin_temperature(self, dt: float):
        """Update cabin temperature using first-order system dynamics"""
        # First-order system: τ * dy/dt + y = u
        # Where: τ = time constant, y = cabin_temperature, u = target_cabin_temperature
        # Solution: y(t+dt) = y(t) + (dt/τ) * (u - y(t))
        
        temperature_error = self.target_cabin_temperature - self.cabin_temperature
        temperature_change = (dt / self.temperature_time_constant) * temperature_error
        self.cabin_temperature += temperature_change

    def set_elevation(self, elevation_m: float):
        self.elevation_m = elevation_m

    def set_total_weight(self, weight_kg: float):
        self.mass_kg = weight_kg

    def set_speed_limit(self, speed_limit_mps: float):
        self.speed_limit_mps = speed_limit_mps

    def set_command_speed(self, speed_mps: float):
        self.command_speed_mps = speed_mps

    def set_crew_count(self, count: int):
        self.crew_count = count

    def set_passenger_count(self, count: int):
        self.passenger_count = count

    def set_left_doors(self, open: bool):
        self.left_doors_open = open

    def set_right_doors(self, open: bool):
        self.right_doors_open = open

    def set_interior_lights(self, on: bool):
        self.interior_lights_on = on

    def set_exterior_lights(self, on: bool):
        self.exterior_lights_on = on

    def engage_emergency_brake(self, engaged: bool):
        self.emergency_brake_engaged = engaged

    def set_passenger_emergency_brake(self, engaged: bool):
        """Set passenger emergency brake state - passengers can only engage, not reset"""
        if engaged:
            self.passenger_emergency_brake = True
            print(f"Passenger emergency brake ENGAGED by passenger")
        # Note: Passengers cannot reset the emergency brake - only driver can do that via controller

    def reset_passenger_emergency_brake(self):
        """Reset passenger emergency brake - only called by controller when driver resets"""
        self.passenger_emergency_brake = False
        print(f"Passenger emergency brake RESET by driver/controller")

    def set_service_brake(self, engaged: bool):
        self.service_brake_engaged = engaged
