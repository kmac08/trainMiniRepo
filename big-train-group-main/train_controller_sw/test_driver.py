import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QSpinBox, 
                             QDoubleSpinBox, QCheckBox, QGroupBox, QComboBox)
from PyQt5.QtCore import QTimer

# Add paths for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gui.train_controller_driver import DriverUI
from gui.train_controller_engineer import EngineerWindow
from controller.train_controller import TrainController
from controller.data_types import TrainModelInput, DriverInput, EngineerInput


class TestbenchWindow(QMainWindow):
    """Testbench for simulating train controller system"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Train Controller Testbench")
        
        # Create the shared TrainController instance
        self.train_controller = TrainController(kp=10.0, ki=1.0)
        
        # Create UI instances
        self.engineer_window = EngineerWindow()
        self.driver_ui = DriverUI()
        
        # Connect engineer window signal
        self.engineer_window.kp_ki_submitted.connect(self.update_controller_gains)
        
        # Set the train controller in both UIs
        self.driver_ui.set_train_controller(self.train_controller)
        self.engineer_window.set_train_controller(self.train_controller)
        
        # Initialize train model state
        self.train_state = {
            'actual_speed': 0.0,
            'commanded_speed': 0.0,
            'speed_limit': 40.0,
            'authority': 1000.0,
            'passenger_emergency_brake': False,
            'cabin_temperature': 72.0,
            'engine_fault': False,
            'signal_fault': False,
            'brake_fault': False,
            'next_station': "Central Station",
            'station_side': "right"
        }
        
        # Physics simulation parameters
        self.physics_enabled = True
        self.train_mass = 40900  # kg (approximate mass of a train car)
        self.max_acceleration = 0.5  # m/s^2
        self.max_deceleration = 1.2  # m/s^2
        self.emergency_deceleration = 2.73  # m/s^2
        
        # Setup UI
        self.setup_ui()
        
        # Setup timers
        self.setup_timers()
        
        # Initial update
        self.update_system()
        
    def setup_ui(self):
        """Setup the testbench UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # Left side - Control Panel
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        control_panel.setMaximumWidth(400)
        
        # Title
        title = QLabel("Simulation Controls")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        control_layout.addWidget(title)
        
        # Speed controls
        speed_group = QGroupBox("Speed Control")
        speed_layout = QVBoxLayout(speed_group)
        
        # Commanded speed
        cmd_speed_layout = QHBoxLayout()
        cmd_speed_layout.addWidget(QLabel("Commanded Speed (mph):"))
        self.cmd_speed_spin = QDoubleSpinBox()
        self.cmd_speed_spin.setRange(0, 100)
        self.cmd_speed_spin.setValue(0)
        self.cmd_speed_spin.setSingleStep(5)
        cmd_speed_layout.addWidget(self.cmd_speed_spin)
        speed_layout.addLayout(cmd_speed_layout)
        
        # Speed limit
        limit_layout = QHBoxLayout()
        limit_layout.addWidget(QLabel("Speed Limit (mph):"))
        self.speed_limit_spin = QDoubleSpinBox()
        self.speed_limit_spin.setRange(0, 100)
        self.speed_limit_spin.setValue(40)
        self.speed_limit_spin.setSingleStep(5)
        limit_layout.addWidget(self.speed_limit_spin)
        speed_layout.addLayout(limit_layout)
        
        # Authority
        authority_layout = QHBoxLayout()
        authority_layout.addWidget(QLabel("Authority (yards):"))
        self.authority_spin = QDoubleSpinBox()
        self.authority_spin.setRange(0, 10000)
        self.authority_spin.setValue(1000)
        self.authority_spin.setSingleStep(100)
        authority_layout.addWidget(self.authority_spin)
        speed_layout.addLayout(authority_layout)
        
        control_layout.addWidget(speed_group)
        
        # Failure injection
        failure_group = QGroupBox("Failure Injection")
        failure_layout = QVBoxLayout(failure_group)
        
        self.engine_fault_check = QCheckBox("Engine Failure")
        self.signal_fault_check = QCheckBox("Signal Failure")
        self.brake_fault_check = QCheckBox("Brake Failure")
        self.passenger_ebrake_check = QCheckBox("Passenger Emergency Brake")
        
        failure_layout.addWidget(self.engine_fault_check)
        failure_layout.addWidget(self.signal_fault_check)
        failure_layout.addWidget(self.brake_fault_check)
        failure_layout.addWidget(self.passenger_ebrake_check)
        
        control_layout.addWidget(failure_group)
        
        # Station controls
        station_group = QGroupBox("Station Control")
        station_layout = QVBoxLayout(station_group)
        
        # Next station
        station_name_layout = QHBoxLayout()
        station_name_layout.addWidget(QLabel("Next Station:"))
        self.station_combo = QComboBox()
        self.station_combo.addItems([
            "Central Station",
            "North Station",
            "South Station",
            "East Station",
            "West Station",
            "Airport Terminal",
            "University Station"
        ])
        station_name_layout.addWidget(self.station_combo)
        station_layout.addLayout(station_name_layout)
        
        # Station side
        side_layout = QHBoxLayout()
        side_layout.addWidget(QLabel("Platform Side:"))
        self.side_combo = QComboBox()
        self.side_combo.addItems(["left", "right"])
        self.side_combo.setCurrentText("right")
        side_layout.addWidget(self.side_combo)
        station_layout.addLayout(side_layout)
        
        control_layout.addWidget(station_group)
        
        # Simulation controls
        sim_group = QGroupBox("Simulation")
        sim_layout = QVBoxLayout(sim_group)
        
        self.physics_check = QCheckBox("Enable Physics Simulation")
        self.physics_check.setChecked(True)
        self.physics_check.toggled.connect(self.toggle_physics)
        sim_layout.addWidget(self.physics_check)
        
        self.logging_check = QCheckBox("Enable Logging")
        self.logging_check.setChecked(False)
        sim_layout.addWidget(self.logging_check)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        engineer_btn = QPushButton("Engineer Panel")
        engineer_btn.clicked.connect(self.show_engineer_window)
        button_layout.addWidget(engineer_btn)
        
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self.reset_simulation)
        button_layout.addWidget(reset_btn)
        
        sim_layout.addLayout(button_layout)
        control_layout.addWidget(sim_group)
        
        # Current state display
        state_group = QGroupBox("Current State")
        state_layout = QVBoxLayout(state_group)
        
        self.actual_speed_label = QLabel("Actual Speed: 0.0 mph")
        self.power_label = QLabel("Power: 0.0 kW")
        self.mode_label = QLabel("Mode: AUTO")
        self.ebrake_label = QLabel("Emergency Brake: OFF")
        
        state_layout.addWidget(self.actual_speed_label)
        state_layout.addWidget(self.power_label)
        state_layout.addWidget(self.mode_label)
        state_layout.addWidget(self.ebrake_label)
        
        control_layout.addWidget(state_group)
        
        control_layout.addStretch()
        
        # Right side - Driver UI
        main_layout.addWidget(control_panel)
        main_layout.addWidget(self.driver_ui)
        
        self.setGeometry(50, 50, 1600, 700)
        
    def setup_timers(self):
        """Setup update timers"""
        # System update timer (10 Hz for smooth simulation)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_system)
        self.update_timer.start(100)  # 100ms = 10Hz
        
        # Physics simulation timer (50 Hz for accurate physics)
        self.physics_timer = QTimer()
        self.physics_timer.timeout.connect(self.update_physics)
        self.physics_timer.start(20)  # 20ms = 50Hz
        
    def update_system(self):
        """Main system update - called at 10Hz"""
        # Update train state from UI controls
        self.train_state['commanded_speed'] = self.cmd_speed_spin.value()
        self.train_state['speed_limit'] = self.speed_limit_spin.value()
        self.train_state['authority'] = self.authority_spin.value()
        self.train_state['engine_fault'] = self.engine_fault_check.isChecked()
        self.train_state['signal_fault'] = self.signal_fault_check.isChecked()
        self.train_state['brake_fault'] = self.brake_fault_check.isChecked()
        self.train_state['passenger_emergency_brake'] = self.passenger_ebrake_check.isChecked()
        self.train_state['next_station'] = self.station_combo.currentText()
        self.train_state['station_side'] = self.side_combo.currentText()
        
        # Create TrainModelInput
        train_input = TrainModelInput(
            fault_status={
                'engine': self.train_state['engine_fault'],
                'signal': self.train_state['signal_fault'],
                'brake': self.train_state['brake_fault']
            },
            authority=self.train_state['authority'],
            actual_speed=self.train_state['actual_speed'],
            commanded_speed=self.train_state['commanded_speed'],
            speed_limit=self.train_state['speed_limit'],
            passenger_emergency_brake=self.train_state['passenger_emergency_brake'],
            cabin_temperature=self.train_state['cabin_temperature'],
            next_station=self.train_state['next_station'],
            station_side=self.train_state['station_side']
        )
        
        # Set train input in driver UI
        self.driver_ui.set_train_input(train_input)
        
        # Get driver input
        driver_input = self.driver_ui.get_driver_input()
        
        # Update controller
        self.train_controller.update(train_input, driver_input)
        
        # Get output
        output = self.train_controller.get_output()
        
        # Update driver UI
        self.driver_ui.update_from_train_controller()
        
        # Update state display
        self.update_state_display(driver_input, output)
        
        # Log if enabled
        if self.logging_check.isChecked():
            self.log_state(train_input, driver_input, output)
            
    def update_physics(self):
        """Update train physics simulation - called at 50Hz"""
        if not self.physics_enabled:
            return
            
        dt = 0.02  # 20ms time step
        
        # Get current controller output
        output = self.train_controller.get_output()
        
        # Calculate acceleration based on power and braking
        if output.emergency_brake_status:
            # Emergency brake - maximum deceleration
            acceleration = -self.emergency_deceleration
        elif output.service_brake_status:
            # Service brake - normal deceleration
            acceleration = -self.max_deceleration
        else:
            # Power-based acceleration
            # Simplified model: F = P/v, a = F/m
            # But avoid division by zero at low speeds
            if self.train_state['actual_speed'] < 0.5:  # mph
                # At very low speeds, use maximum acceleration limited by power
                acceleration = min(output.power_kw * 1000 / (self.train_mass * 0.5), 
                                 self.max_acceleration)
            else:
                # Convert mph to m/s for calculation
                speed_ms = self.train_state['actual_speed'] * 0.44704
                force = (output.power_kw * 1000) / speed_ms  # Newton
                acceleration = force / self.train_mass  # m/s^2
                acceleration = min(acceleration, self.max_acceleration)
        
        # Update speed (convert acceleration from m/s^2 to mph/s)
        speed_change = acceleration * dt * 2.23694  # Convert m/s^2 to mph/s
        self.train_state['actual_speed'] += speed_change
        
        # Clamp speed to valid range
        self.train_state['actual_speed'] = max(0, min(100, self.train_state['actual_speed']))
        
        # Update display
        self.actual_speed_label.setText(f"Actual Speed: {self.train_state['actual_speed']:.1f} mph")
        
    def update_state_display(self, driver_input, output):
        """Update the state display labels"""
        self.power_label.setText(f"Power: {output.power_kw:.1f} kW")
        self.mode_label.setText(f"Mode: {'AUTO' if driver_input.auto_mode else 'MANUAL'}")
        self.ebrake_label.setText(f"Emergency Brake: {'ON' if output.emergency_brake_status else 'OFF'}")
        
    def toggle_physics(self, checked):
        """Toggle physics simulation"""
        self.physics_enabled = checked
        
    def show_engineer_window(self):
        """Show the engineer window"""
        self.engineer_window.show()
        
    def update_controller_gains(self, engineer_input: EngineerInput):
        """Update controller gains when engineer submits new values"""
        self.train_controller.update_from_engineer_input(engineer_input)  # This sets kp_ki_set flag
        # Reset only the integral error, not the entire controller state
        self.train_controller.integral_error = 0.0
        print(f"Controller gains updated: Kp={engineer_input.kp}, Ki={engineer_input.ki}, kp_ki_set={self.train_controller.kp_ki_set}")
        
    def reset_simulation(self):
        """Reset the simulation to initial state"""
        self.train_state['actual_speed'] = 0.0
        self.cmd_speed_spin.setValue(0)
        self.train_controller.reset()
        self.driver_ui.reset_emergency_brake()
        print("Simulation reset")
        
    def log_state(self, train_input, driver_input, output):
        """Log current state for debugging"""
        print(f"\n=== Testbench Log ===")
        print(f"Time: {QTimer().remainingTime()}")
        print(f"Mode: {'AUTO' if driver_input.auto_mode else 'MANUAL'}")
        print(f"Speeds - Actual: {train_input.actual_speed:.1f}, "
              f"Commanded: {train_input.commanded_speed:.1f}, "
              f"Limit: {train_input.speed_limit:.1f}")
        print(f"Power: {output.power_kw:.1f} kW")
        print(f"Brakes - Emergency: {output.emergency_brake_status}, "
              f"Service: {output.service_brake_status}")
        print(f"Faults - Engine: {train_input.fault_status['engine']}, "
              f"Signal: {train_input.fault_status['signal']}, "
              f"Brake: {train_input.fault_status['brake']}")
        print(f"Station: {train_input.next_station} ({train_input.station_side} side)")


def main():
    """Main entry point for the testbench"""
    app = QApplication(sys.argv)
    
    # Create and show testbench window
    testbench = TestbenchWindow()
    testbench.show()
    
    # Also show engineer window initially
    testbench.show_engineer_window()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()