#!/usr/bin/env python3
"""
Modified Train Controller Driver with Remote GPIO via Serial
Integrates with Pi GPIO handler for remote GPIO access
"""

import os
import sys
import time
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QTimer, QTime
from PyQt5.QtWidgets import *

# Add parent directories to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import universal time function from Master Interface
try:
    from Master_Interface.master_control import get_time
except ImportError:
    raise ImportError("CRITICAL ERROR: Master Interface universal time function not available. Driver GUI requires universal time synchronization.")

# Import data types and controller
try:
    from train_controller_hw.controller.data_types import DriverInput, TrainModelOutput, TrainModelInput, OutputToDriver
    from train_controller_hw.controller.train_controller import TrainController
    from train_controller_hw.gpio_emulator import create_gpio_emulator
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

class RemoteDriverUI(QMainWindow):
    """Driver UI with remote GPIO access via Raspberry Pi"""
    
    def __init__(self, serial_port='COM4', baud_rate=9600):
        super().__init__()
        
        # Initialize GPIO emulator for Pi communication
        self.gpio_emulator = create_gpio_emulator(serial_port, baud_rate)
        
        # GPIO pin definitions (for reference)
        self.GPIO_PINS = {
            'HEADLIGHT': 17,
            'INTERIOR_LIGHT': 27,
            'EMERGENCY_BRAKE': 21,
            'SERVICE_BRAKE': 26,
            'LEFT_DOOR': 6,
            'RIGHT_DOOR': 19,
            'SPEED_UP': 20,
            'SPEED_DOWN': 16,
            'TEMP_UP': 23,
            'TEMP_DOWN': 24,
            'AUTO_MANUAL_MODE': 13
        }
        
        # Initialize state variables
        self.emergency_brake_active = False
        self.service_brake_active = False
        self.manual_set_speed = 0.0
        self.manual_set_temperature = 72.0
        self.controller_emergency_state = False
        
        # GPIO input states
        self.gpio_inputs = {
            'headlights_on': False,
            'interior_lights_on': False,
            'emergency_brake': False,
            'service_brake': False,
            'door_left_open': False,
            'door_right_open': False
        }
        
        # Train controller instance
        self.train_controller = None
        self.train_id = 1
        
        # Setup GPIO callbacks
        self.setup_gpio_callbacks()
        
        # Initialize UI
        self.setupUI()
        self.setup_timer()
        
        # Connection status
        self.connection_status_timer = QTimer()
        self.connection_status_timer.timeout.connect(self.update_connection_status)
        self.connection_status_timer.start(2000)  # Check every 2 seconds
    
    def setup_gpio_callbacks(self):
        """Setup callbacks for GPIO button presses from Pi"""
        self.gpio_emulator.register_button_callback('HEADLIGHT', self.on_headlight_press)
        self.gpio_emulator.register_button_callback('INTERIOR_LIGHT', self.on_interior_light_press)
        self.gpio_emulator.register_button_callback('EMERGENCY_BRAKE', self.on_emergency_brake_press)
        self.gpio_emulator.register_button_callback('SERVICE_BRAKE', self.on_service_brake_press)
        self.gpio_emulator.register_button_callback('LEFT_DOOR', self.on_left_door_press)
        self.gpio_emulator.register_button_callback('RIGHT_DOOR', self.on_right_door_press)
        self.gpio_emulator.register_button_callback('SPEED_UP', self.on_speed_up_press)
        self.gpio_emulator.register_button_callback('SPEED_DOWN', self.on_speed_down_press)
        self.gpio_emulator.register_button_callback('TEMP_UP', self.on_temp_up_press)
        self.gpio_emulator.register_button_callback('TEMP_DOWN', self.on_temp_down_press)
    
    def on_headlight_press(self):
        """Handle headlight button press"""
        if not self.gpio_emulator.get_auto_mode():
            self.gpio_inputs['headlights_on'] = not self.gpio_inputs['headlights_on']
            print(f"Headlights: {'ON' if self.gpio_inputs['headlights_on'] else 'OFF'}")
    
    def on_interior_light_press(self):
        """Handle interior light button press"""
        if not self.gpio_emulator.get_auto_mode():
            self.gpio_inputs['interior_lights_on'] = not self.gpio_inputs['interior_lights_on']
            print(f"Interior lights: {'ON' if self.gpio_inputs['interior_lights_on'] else 'OFF'}")
    
    def on_emergency_brake_press(self):
        """Handle emergency brake button press"""
        self.emergency_brake_active = not self.emergency_brake_active
        print(f"Emergency brake: {'ACTIVE' if self.emergency_brake_active else 'INACTIVE'}")
    
    def on_service_brake_press(self):
        """Handle service brake button press"""
        if not self.gpio_emulator.get_auto_mode():
            self.service_brake_active = not self.service_brake_active
            print(f"Service brake: {'ACTIVE' if self.service_brake_active else 'INACTIVE'}")
    
    def on_left_door_press(self):
        """Handle left door button press"""
        if not self.gpio_emulator.get_auto_mode():
            if self.train_controller and self.train_controller.get_output_to_driver().actual_speed > 0:
                print("Door operation blocked - train is moving")
                return
            self.gpio_inputs['door_left_open'] = not self.gpio_inputs['door_left_open']
            print(f"Left door: {'OPEN' if self.gpio_inputs['door_left_open'] else 'CLOSED'}")
    
    def on_right_door_press(self):
        """Handle right door button press"""
        if not self.gpio_emulator.get_auto_mode():
            if self.train_controller and self.train_controller.get_output_to_driver().actual_speed > 0:
                print("Door operation blocked - train is moving")
                return
            self.gpio_inputs['door_right_open'] = not self.gpio_inputs['door_right_open']
            print(f"Right door: {'OPEN' if self.gpio_inputs['door_right_open'] else 'CLOSED'}")
    
    def on_speed_up_press(self):
        """Handle speed up button press"""
        if not self.gpio_emulator.get_auto_mode():
            self.manual_set_speed = min(self.manual_set_speed + 1.0, 100.0)
            print(f"Speed set to: {self.manual_set_speed:.1f} mph")
    
    def on_speed_down_press(self):
        """Handle speed down button press"""
        if not self.gpio_emulator.get_auto_mode():
            self.manual_set_speed = max(self.manual_set_speed - 1.0, 0.0)
            print(f"Speed set to: {self.manual_set_speed:.1f} mph")
    
    def on_temp_up_press(self):
        """Handle temperature up button press"""
        if not self.gpio_emulator.get_auto_mode():
            self.manual_set_temperature = min(self.manual_set_temperature + 1.0, 100.0)
            print(f"Temperature set to: {self.manual_set_temperature:.1f}°F")
    
    def on_temp_down_press(self):
        """Handle temperature down button press"""
        if not self.gpio_emulator.get_auto_mode():
            self.manual_set_temperature = max(self.manual_set_temperature - 1.0, 32.0)
            print(f"Temperature set to: {self.manual_set_temperature:.1f}°F")
    
    def update_connection_status(self):
        """Update connection status indicator"""
        if self.gpio_emulator.is_connected():
            self.connection_status.setText("Pi Status: CONNECTED")
            self.connection_status.setStyleSheet("color: #28a745; font-weight: bold; font-size: 12px;")
        else:
            self.connection_status.setText("Pi Status: DISCONNECTED")
            self.connection_status.setStyleSheet("color: #dc3545; font-weight: bold; font-size: 12px;")
    
    def set_train_controller(self, train_controller: TrainController):
        """Set the train controller instance"""
        self.train_controller = train_controller
    
    def get_driver_input(self) -> DriverInput:
        """Return a DriverInput object using remote GPIO inputs"""
        return DriverInput(
            auto_mode=self.gpio_emulator.get_auto_mode(),
            headlights_on=self.gpio_inputs['headlights_on'],
            interior_lights_on=self.gpio_inputs['interior_lights_on'],
            door_left_open=self.gpio_inputs['door_left_open'],
            door_right_open=self.gpio_inputs['door_right_open'],
            set_temperature=self.manual_set_temperature,
            emergency_brake=self.emergency_brake_active,
            set_speed=self.manual_set_speed,
            service_brake=self.service_brake_active,
            train_id=self.train_id
        )
    
    def update_from_train_controller(self):
        """Update all UI fields from the train controller"""
        if self.train_controller is None:
            return
        
        # Get driver output data
        driver_output = self.train_controller.get_output_to_driver()
        
        # Update speed information
        self.input_speed_field.setText(f"{driver_output.input_speed:.1f}")
        self.current_speed_field.setText(f"{driver_output.actual_speed:.1f}")
        self.speed_limit_field.setText(f"{driver_output.speed_limit:.1f}")
        
        # Update power and authority
        self.power_field.setText(f"{driver_output.power_output:.1f}")
        self.authority_field.setText(f"{driver_output.authority:.1f}")
        
        # Update temperature
        self.current_temp_display.setText(f"{driver_output.current_cabin_temp:.0f}°F")
        if driver_output.auto_mode:
            self.temp_input_field.setText(f"{driver_output.set_cabin_temp:.0f}°F")
        else:
            self.temp_input_field.setText(f"{self.manual_set_temperature:.0f}°F")
        
        # Update mode display
        self.update_mode_display()
        
        # Update GPIO status
        self.update_gpio_status_display()
        
        # Update brake states
        self.emergency_brake_btn.setChecked(self.emergency_brake_active or driver_output.emergency_brake_active)
        self.update_emergency_brake_style()
        
        # Update failure states
        self.set_failures(
            engine=driver_output.engine_failure,
            signal=driver_output.signal_failure,
            brake=driver_output.brake_failure
        )
        
        # Update door status
        if driver_output.left_door_open:
            self.left_door_status.setText("L Door: OPEN")
            self.left_door_status.setStyleSheet("color: #ffc107; font-weight: bold; font-size: 12px;")
        else:
            self.left_door_status.setText("L Door: CLOSED")
            self.left_door_status.setStyleSheet("color: #6c757d; font-weight: bold; font-size: 12px;")
        
        if driver_output.right_door_open:
            self.right_door_status.setText("R Door: OPEN")
            self.right_door_status.setStyleSheet("color: #ffc107; font-weight: bold; font-size: 12px;")
        else:
            self.right_door_status.setText("R Door: CLOSED")
            self.right_door_status.setStyleSheet("color: #6c757d; font-weight: bold; font-size: 12px;")
        
        # Update station info
        if driver_output.next_station and driver_output.station_side:
            station_text = f"{driver_output.next_station} on the {driver_output.station_side.title()} Hand Side"
            self.set_next_station(station_text)
        else:
            self.set_next_station("")
        
        # Update Kp/Ki status
        self.update_kp_ki_status(driver_output.kp, driver_output.ki, driver_output.kp_ki_set)
    
    def update_mode_display(self):
        """Update mode buttons based on remote GPIO state"""
        if self.gpio_emulator.get_auto_mode():
            self.btn_auto.setChecked(True)
            self.btn_manual.setChecked(False)
        else:
            self.btn_auto.setChecked(False)
            self.btn_manual.setChecked(True)
    
    def update_gpio_status_display(self):
        """Update GPIO status indicators"""
        # Mode status
        if self.gpio_emulator.get_auto_mode():
            self.mode_status.setText("Mode: AUTO")
            self.mode_status.setStyleSheet("color: #007bff; font-weight: bold; font-size: 12px;")
        else:
            self.mode_status.setText("Mode: MANUAL")
            self.mode_status.setStyleSheet("color: #fd7e14; font-weight: bold; font-size: 12px;")
        
        # Other GPIO states
        self.headlight_status.setText(f"Headlights: {'ON' if self.gpio_inputs['headlights_on'] else 'OFF'}")
        self.headlight_status.setStyleSheet(f"color: {'#28a745' if self.gpio_inputs['headlights_on'] else '#6c757d'}; font-weight: bold; font-size: 12px;")
        
        self.interior_status.setText(f"Interior: {'ON' if self.gpio_inputs['interior_lights_on'] else 'OFF'}")
        self.interior_status.setStyleSheet(f"color: {'#28a745' if self.gpio_inputs['interior_lights_on'] else '#6c757d'}; font-weight: bold; font-size: 12px;")
        
        self.brake_status.setText(f"Service Brake: {'ON' if self.service_brake_active else 'OFF'}")
        self.brake_status.setStyleSheet(f"color: {'#dc3545' if self.service_brake_active else '#6c757d'}; font-weight: bold; font-size: 12px;")
        
        self.emergency_status.setText(f"Emergency Brake: {'ON' if self.emergency_brake_active else 'OFF'}")
        self.emergency_status.setStyleSheet(f"color: {'#dc3545' if self.emergency_brake_active else '#6c757d'}; font-weight: bold; font-size: 12px;")
    
    def setupUI(self):
        """Setup the user interface (reusing most of the original UI code)"""
        self.setWindowTitle("Train Controller Hardware - Remote GPIO Driver")
        self.setGeometry(100, 100, 900, 500)
        self.setMinimumSize(750, 460)
        self.setMaximumSize(750, 460)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(4)
        
        # Top panel - Connection status and time
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        
        # Connection status
        self.connection_status = QLabel("Pi Status: CONNECTING...")
        self.connection_status.setStyleSheet("color: #ffc107; font-weight: bold; font-size: 14px;")
        top_layout.addWidget(self.connection_status)
        
        top_layout.addStretch()
        
        # Time
        self.time_label = QLabel("11:59 AM")
        self.time_label.setStyleSheet("color: #2c3e50; font-weight: bold; font-size: 18px;")
        top_layout.addWidget(self.time_label)
        
        main_layout.addWidget(top_panel)
        
        # Content panel
        content_panel = QWidget()
        content_layout = QHBoxLayout(content_panel)
        
        # Left panel - Controls
        left_panel = self.create_left_panel()
        content_layout.addWidget(left_panel)
        
        # Center panel - Train info
        center_panel = self.create_center_panel()
        content_layout.addWidget(center_panel)
        
        # Right panel - Status
        right_panel = self.create_right_panel()
        content_layout.addWidget(right_panel)
        
        main_layout.addWidget(content_panel)
        
        # Initialize displays
        self.update_gpio_status_display()
    
    def create_left_panel(self):
        """Create the left control panel"""
        left_panel = QWidget()
        left_panel.setFixedWidth(260)
        left_layout = QVBoxLayout(left_panel)
        
        # Control mode
        mode_group = QGroupBox("Control Mode")
        mode_layout = QHBoxLayout(mode_group)
        
        self.btn_manual = QPushButton("Manual")
        self.btn_auto = QPushButton("Auto")
        self.btn_manual.setCheckable(True)
        self.btn_auto.setCheckable(True)
        self.btn_manual.setEnabled(False)
        self.btn_auto.setEnabled(False)
        
        mode_layout.addWidget(self.btn_manual)
        mode_layout.addWidget(self.btn_auto)
        left_layout.addWidget(mode_group)
        
        # GPIO status
        gpio_group = QGroupBox("Remote GPIO Status")
        gpio_layout = QVBoxLayout(gpio_group)
        
        self.mode_status = QLabel("Mode: AUTO")
        self.headlight_status = QLabel("Headlights: OFF")
        self.interior_status = QLabel("Interior: OFF")
        self.brake_status = QLabel("Service Brake: OFF")
        self.emergency_status = QLabel("Emergency Brake: OFF")
        
        gpio_layout.addWidget(self.mode_status)
        gpio_layout.addWidget(self.headlight_status)
        gpio_layout.addWidget(self.interior_status)
        gpio_layout.addWidget(self.brake_status)
        gpio_layout.addWidget(self.emergency_status)
        
        left_layout.addWidget(gpio_group)
        
        # Temperature
        temp_group = QGroupBox("Temperature")
        temp_layout = QVBoxLayout(temp_group)
        
        temp_display_layout = QHBoxLayout()
        temp_display_layout.addWidget(QLabel("Current:"))
        self.current_temp_display = QLabel("72°F")
        temp_display_layout.addWidget(self.current_temp_display)
        temp_display_layout.addStretch()
        temp_display_layout.addWidget(QLabel("Set:"))
        self.temp_input_field = QLabel("72°F")
        temp_display_layout.addWidget(self.temp_input_field)
        
        temp_layout.addLayout(temp_display_layout)
        left_layout.addWidget(temp_group)
        
        # Emergency brake
        self.emergency_brake_btn = QPushButton("EMERGENCY\nBRAKE")
        self.emergency_brake_btn.setFixedHeight(80)
        self.emergency_brake_btn.setCheckable(True)
        self.emergency_brake_btn.setEnabled(False)
        left_layout.addWidget(self.emergency_brake_btn)
        
        return left_panel
    
    def create_center_panel(self):
        """Create the center information panel"""
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        
        # Station info
        station_group = QGroupBox("Next Station")
        station_layout = QVBoxLayout(station_group)
        
        self.next_station_line = QLabel("No station information")
        self.next_station_line.setAlignment(Qt.AlignCenter)
        station_layout.addWidget(self.next_station_line)
        center_layout.addWidget(station_group)
        
        # Train information
        info_group = QGroupBox("Train Information")
        info_layout = QVBoxLayout(info_group)
        
        # Create info fields
        self.input_speed_field = self.create_info_field("Input Speed", "0.0")
        self.current_speed_field = self.create_info_field("Current Speed", "0.0")
        self.speed_limit_field = self.create_info_field("Speed Limit", "40.0")
        self.power_field = self.create_info_field("Power Output", "0.0")
        self.authority_field = self.create_info_field("Authority", "0.0")
        
        info_layout.addWidget(self.input_speed_field)
        info_layout.addWidget(self.current_speed_field)
        info_layout.addWidget(self.speed_limit_field)
        info_layout.addWidget(self.power_field)
        info_layout.addWidget(self.authority_field)
        
        center_layout.addWidget(info_group)
        
        # Door status
        door_group = QGroupBox("Door Status")
        door_layout = QHBoxLayout(door_group)
        
        self.left_door_status = QLabel("L Door: CLOSED")
        self.right_door_status = QLabel("R Door: CLOSED")
        
        door_layout.addWidget(self.left_door_status)
        door_layout.addWidget(self.right_door_status)
        center_layout.addWidget(door_group)
        
        return center_panel
    
    def create_right_panel(self):
        """Create the right status panel"""
        right_panel = QWidget()
        right_panel.setFixedWidth(180)
        right_layout = QVBoxLayout(right_panel)
        
        # PID status
        pid_group = QGroupBox("PID Status")
        pid_layout = QVBoxLayout(pid_group)
        
        self.kp_ki_status_label = QLabel("Kp/Ki: Not Set")
        self.kp_ki_status_label.setAlignment(Qt.AlignCenter)
        pid_layout.addWidget(self.kp_ki_status_label)
        right_layout.addWidget(pid_group)
        
        # Failures
        failures_group = QGroupBox("System Failures")
        failures_layout = QVBoxLayout(failures_group)
        
        self.engine_failure_btn = QPushButton("Engine: OK")
        self.signal_failure_btn = QPushButton("Signal: OK")
        self.brake_failure_btn = QPushButton("Brake: OK")
        
        self.engine_failure_btn.setEnabled(False)
        self.signal_failure_btn.setEnabled(False)
        self.brake_failure_btn.setEnabled(False)
        
        failures_layout.addWidget(self.engine_failure_btn)
        failures_layout.addWidget(self.signal_failure_btn)
        failures_layout.addWidget(self.brake_failure_btn)
        
        right_layout.addWidget(failures_group)
        
        return right_panel
    
    def create_info_field(self, label_text, initial_value):
        """Create an info field widget"""
        field_widget = QWidget()
        field_layout = QHBoxLayout(field_widget)
        
        label = QLabel(label_text + ":")
        label.setFixedWidth(120)
        field_layout.addWidget(label)
        
        value_label = QLabel(initial_value)
        value_label.setStyleSheet("font-weight: bold; border: 1px solid #888; padding: 4px;")
        field_layout.addWidget(value_label)
        
        # Store reference for updates
        setattr(field_widget, 'setText', lambda text: value_label.setText(text))
        
        return field_widget
    
    def setup_timer(self):
        """Setup timers for updates"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()
    
    def update_time(self):
        """Update time display"""
        current_time = get_time()
        time_text = current_time.strftime("%I:%M %p")
        self.time_label.setText(time_text)
    
    def update_emergency_brake_style(self):
        """Update emergency brake button style"""
        if self.emergency_brake_btn.isChecked():
            self.emergency_brake_btn.setStyleSheet("background-color: #8b0000; color: white; font-weight: bold;")
        else:
            self.emergency_brake_btn.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")
    
    def set_next_station(self, station_text):
        """Set next station text"""
        self.next_station_line.setText(station_text)
    
    def set_failures(self, engine=False, signal=False, brake=False):
        """Update failure indicators"""
        # Engine
        if engine:
            self.engine_failure_btn.setText("Engine: FAILED")
            self.engine_failure_btn.setStyleSheet("background-color: #dc3545; color: white;")
        else:
            self.engine_failure_btn.setText("Engine: OK")
            self.engine_failure_btn.setStyleSheet("background-color: #28a745; color: white;")
        
        # Signal
        if signal:
            self.signal_failure_btn.setText("Signal: FAILED")
            self.signal_failure_btn.setStyleSheet("background-color: #dc3545; color: white;")
        else:
            self.signal_failure_btn.setText("Signal: OK")
            self.signal_failure_btn.setStyleSheet("background-color: #28a745; color: white;")
        
        # Brake
        if brake:
            self.brake_failure_btn.setText("Brake: FAILED")
            self.brake_failure_btn.setStyleSheet("background-color: #dc3545; color: white;")
        else:
            self.brake_failure_btn.setText("Brake: OK")
            self.brake_failure_btn.setStyleSheet("background-color: #28a745; color: white;")
    
    def update_kp_ki_status(self, kp, ki, kp_ki_set):
        """Update Kp/Ki status indicator"""
        if kp_ki_set:
            self.kp_ki_status_label.setText(f"Kp/Ki: Set\n({kp:.1f}, {ki:.1f})")
            self.kp_ki_status_label.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        else:
            self.kp_ki_status_label.setText("Waiting for\nKp/Ki")
            self.kp_ki_status_label.setStyleSheet("background-color: #ff6b6b; color: white; font-weight: bold;")
    
    def cleanup_gpio(self):
        """Clean up GPIO emulator"""
        self.gpio_emulator.stop()
    
    def closeEvent(self, event):
        """Handle window close"""
        self.cleanup_gpio()
        event.accept()

def main():
    """Main function for standalone testing"""
    app = QApplication(sys.argv)
    
    # You can specify different COM port here
    window = RemoteDriverUI(serial_port='COM4')
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()