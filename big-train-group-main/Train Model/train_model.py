# train_model.py
import random

class TrainModel:
    def __init__(self, train_id):
        self.train_id = train_id

        # Core state variables (metric units)
        self.mass_kg = 40900
        self.velocity_mps = 0.0
        self.acceleration_mps2 = 0.0
        self.previous_acceleration = 0.0
        self.command_speed_mps = 0.0
        self.speed_limit_mps = 0.0
        self.authority_m = 0

        self.power_watts = 0.0
        self.max_acceleration = 0.5

        self.service_brake_engaged = False
        self.emergency_brake_engaged = False
        self.brake_failure = False
        self.engine_failure = False
        self.signal_failure = False

        self.grade_percent = 0.0
        self.elevation_m = 0.0
        self.gravity = 9.81

        self.total_distance_m = 0.0
        self.next_stop = "Yard"

        self.left_doors_open = False
        self.right_doors_open = False
        self.interior_lights_on = False
        self.exterior_lights_on = False

        self.cabin_temperature = 72.0
        self.crew_count = random.randint(2, 8)
        self.passenger_count = 0
        self.person_mass = 70
        self.update_mass()

    def update_mass(self):
        # Update mass of the train with people
        self.mass_kg = self.mass_kg + ((self.passenger_count + self.crew_count)*self.person_mass)

    def update_speed(self, dt):
        # Handle engine failure = no power output
        power = 0.0 if self.engine_failure else self.power_watts

        # Avoid divide-by-zero by assuming small velocity if at rest
        safe_velocity = self.velocity_mps if self.velocity_mps > 0.1 else 0.1

        # Compute force from power: F = P / v
        applied_force = power / safe_velocity

        # Grade resistance (opposes motion uphill, assists downhill)
        grade_force = self.mass_kg * self.gravity * (self.grade_percent / 100.0)

        net_force = applied_force - grade_force

        # Acceleration = net force / mass
        new_acceleration = net_force / self.mass_kg

        # Brake overrides
        if self.emergency_brake_engaged and not self.brake_failure:
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

    def get_distance_traveled(self):
        return self.total_distance_m

    def set_power(self, power_watts: float):
        self.power_watts = power_watts

    def set_cabin_temperature(self, temp: float):
        self.cabin_temperature = temp

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

    def set_service_brake(self, engaged: bool):
        self.service_brake_engaged = engaged