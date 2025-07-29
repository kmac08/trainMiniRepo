import os
import sys
import os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QTimer, QTime
from PyQt5.QtWidgets import *

# Required imports for backend integration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import universal time function from Master Interface
try:
    from Master_Interface.master_control import get_time
except ImportError:
    raise ImportError("CRITICAL ERROR: Master Interface universal time function not available. Driver GUI requires universal time synchronization.")

# Try different import approaches to handle path issues
try:
    from train_controller_hw.controller.data_types import DriverInput, TrainModelOutput, TrainModelInput, OutputToDriver
    from train_controller_hw.controller.train_controller import TrainController
except ImportError:

    try:
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from controller.data_types import DriverInput, TrainModelOutput, TrainModelInput, OutputToDriver
        from controller.train_controller import TrainController
    except ImportError:
        # Last resort - add the controller directory directly
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'controller')))
        from data_types import DriverInput, TrainModelOutput, TrainModelInput, OutputToDriver
        from train_controller import TrainController

# Import GPIO emulator instead of direct GPIO
try:
    from train_controller_hw.gpio_emulator import create_gpio_emulator
    GPIO_EMULATOR_AVAILABLE = True
except ImportError:
    print("Warning: GPIO emulator not available. Running in simulation mode.")
    GPIO_EMULATOR_AVAILABLE = False

class DriverUI(QMainWindow):
    def __init__(self, serial_port='COM4', baud_rate=9600):
        super().__init__()
        
        # GPIO pin definitions
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
        self.emergency_brake_active = False  # Driver's emergency brake input
        self.service_brake_active = False
        self.manual_set_speed = 0.0  # Track manual speed setting
        self.manual_set_temperature = 72.0  # Track manual temperature setting
        self.controller_emergency_state = False  # Track controller's emergency brake state
        
        # GPIO previous states for edge detection (button press detection)
        self.gpio_prev_states = {}
        self.gpio_inputs = {
            'headlights_on': False,
            'interior_lights_on': False,
            'emergency_brake': False,
            'service_brake': False,
            'door_left_open': False,
            'door_right_open': False
        }
        
        # GPIO mode control (GPIO 13: HIGH = manual, LOW = auto)
        self.gpio_auto_mode = True  # Default to auto mode
        
        # Initialize train controller (optional - can be set externally)
        self.train_controller = None
        
        # Train ID (will be set from train controller)
        self.train_id = 1
        
        # Setup GPIO emulator instead of direct GPIO
        self.setup_gpio_emulator(serial_port, baud_rate)
        self.setupUI()
        self.setup_timer()
        
    def setup_gpio_emulator(self, serial_port, baud_rate):
        """Initialize GPIO emulator for remote Pi communication"""
        if not GPIO_EMULATOR_AVAILABLE:
            print("GPIO emulator not available - running in simulation mode")
            # Initialize previous states to HIGH (button not pressed)
            for pin_name in self.GPIO_PINS:
                self.gpio_prev_states[pin_name] = True
            return
            
        # Create GPIO emulator instance
        self.gpio_emulator = create_gpio_emulator(serial_port, baud_rate)
        
        # Setup GPIO callbacks for button presses
        self.setup_gpio_callbacks()
        
        # Initialize previous states to HIGH (button not pressed)
        for pin_name in self.GPIO_PINS:
            self.gpio_prev_states[pin_name] = True
        
        print(f"GPIO emulator initialized on {serial_port} at {baud_rate} baud")
    
    def setup_gpio_callbacks(self):
        """Setup callbacks for GPIO button presses from Pi"""
        if not hasattr(self, 'gpio_emulator'):
            return
            
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
        if not self.get_gpio_auto_mode():
            self.gpio_inputs['headlights_on'] = not self.gpio_inputs['headlights_on']
            print(f"Headlights: {'ON' if self.gpio_inputs['headlights_on'] else 'OFF'}")
    
    def on_interior_light_press(self):
        """Handle interior light button press"""
        if not self.get_gpio_auto_mode():
            self.gpio_inputs['interior_lights_on'] = not self.gpio_inputs['interior_lights_on']
            print(f"Interior lights: {'ON' if self.gpio_inputs['interior_lights_on'] else 'OFF'}")
    
    def on_emergency_brake_press(self):
        """Handle emergency brake button press"""
        self.emergency_brake_active = not self.emergency_brake_active
        print(f"Emergency brake: {'ACTIVE' if self.emergency_brake_active else 'INACTIVE'}")
    
    def on_service_brake_press(self):
        """Handle service brake button press"""
        if not self.get_gpio_auto_mode():
            self.service_brake_active = not self.service_brake_active
            print(f"Service brake: {'ACTIVE' if self.service_brake_active else 'INACTIVE'}")
    
    def on_left_door_press(self):
        """Handle left door button press"""
        if not self.get_gpio_auto_mode():
            if self.train_controller and self.train_controller.get_output_to_driver().actual_speed > 0:
                print("Door operation blocked - train is moving")
                return
            self.gpio_inputs['door_left_open'] = not self.gpio_inputs['door_left_open']
            print(f"Left door: {'OPEN' if self.gpio_inputs['door_left_open'] else 'CLOSED'}")
    
    def on_right_door_press(self):
        """Handle right door button press"""
        if not self.get_gpio_auto_mode():
            if self.train_controller and self.train_controller.get_output_to_driver().actual_speed > 0:
                print("Door operation blocked - train is moving")
                return
            self.gpio_inputs['door_right_open'] = not self.gpio_inputs['door_right_open']
            print(f"Right door: {'OPEN' if self.gpio_inputs['door_right_open'] else 'CLOSED'}")
    
    def on_speed_up_press(self):
        """Handle speed up button press"""
        if not self.get_gpio_auto_mode():
            self.manual_set_speed = min(self.manual_set_speed + 1.0, 100.0)
            print(f"Speed set to: {self.manual_set_speed:.1f} mph")
    
    def on_speed_down_press(self):
        """Handle speed down button press"""
        if not self.get_gpio_auto_mode():
            self.manual_set_speed = max(self.manual_set_speed - 1.0, 0.0)
            print(f"Speed set to: {self.manual_set_speed:.1f} mph")
    
    def on_temp_up_press(self):
        """Handle temperature up button press"""
        if not self.get_gpio_auto_mode():
            self.manual_set_temperature = min(self.manual_set_temperature + 1.0, 100.0)
            print(f"Temperature set to: {self.manual_set_temperature:.1f}°F")
    
    def on_temp_down_press(self):
        """Handle temperature down button press"""
        if not self.get_gpio_auto_mode():
            self.manual_set_temperature = max(self.manual_set_temperature - 1.0, 32.0)
            print(f"Temperature set to: {self.manual_set_temperature:.1f}°F")
    
    def get_gpio_auto_mode(self):
        """Get current auto mode state from GPIO emulator"""
        if hasattr(self, 'gpio_emulator'):
            return self.gpio_emulator.get_auto_mode()
        return self.gpio_auto_mode
    
    def is_gpio_connected(self):
        """Check if GPIO emulator is connected to Pi"""
        if hasattr(self, 'gpio_emulator'):
            return self.gpio_emulator.is_connected()
        return False
    
    def read_gpio_inputs(self):
        """Compatibility method - GPIO inputs now come via callbacks"""
        # Update auto mode from emulator
        if hasattr(self, 'gpio_emulator'):
            self.gpio_auto_mode = self.gpio_emulator.get_auto_mode()
        
        # Update mode display
        self.update_mode_display()
    
    def handle_button_press(self, button_name):
        """Handle button press events - Only emergency brake allowed in auto mode"""
        # This method is now handled by individual callback methods
        # Keeping for compatibility
        pass
    
    def update_mode_display(self):
        """Update the mode buttons based on GPIO input"""
        if self.get_gpio_auto_mode():
            self.btn_auto.setChecked(True)
            self.btn_manual.setChecked(False)
        else:
            self.btn_auto.setChecked(False)
            self.btn_manual.setChecked(True)
    
    def set_train_controller(self, train_controller: TrainController):
        """Set the train controller instance to pull data from"""
        self.train_controller = train_controller
        
        # Update train ID from controller
        if train_controller and hasattr(train_controller, 'train_id'):
            self.train_id = train_controller.train_id
            self.train_id_label.setText(str(self.train_id))
            print(f"Hardware Driver UI: Train ID set to {self.train_id}")
        
    def update_from_train_controller(self):
        """Update all UI fields from the train controller using OutputToDriver"""
        if self.train_controller is None:
            print("Warning: No train controller set")
            return
        
        # Get all driver display data from controller
        driver_output = self.train_controller.get_output_to_driver()
        
        # Update speed information fields
        self.input_speed_field.setText(f"{driver_output.input_speed:.1f}")
        self.current_speed_field.setText(f"{driver_output.actual_speed:.1f}")
        self.speed_limit_field.setText(f"{driver_output.speed_limit:.1f}")
        
        # Update power and authority
        self.power_field.setText(f"{driver_output.power_output:.1f}")
        self.authority_field.setText(f"{driver_output.authority:.1f}")
        
        # Update temperature displays
        self.current_temp_display.setText(f"{driver_output.current_cabin_temp:.0f}°F")
        if driver_output.auto_mode:
            # In auto mode, display the controller's set temperature
            self.temp_input_field.setText(f"{driver_output.set_cabin_temp:.0f}°F")
        else:
            # In manual mode, display the manual setting
            self.temp_input_field.setText(f"{self.manual_set_temperature:.0f}°F")
        
        # Update control mode display (but actual mode comes from GPIO)
        self.update_mode_display()
        self.update_manual_controls_enabled()
        
        # Update GPIO status display
        self.update_gpio_status_display()
        
        # Update connection status
        self.update_connection_status()
        
        # Update brake states display
        # Emergency brake display reflects GPIO/controller state
        self.emergency_brake_btn.setChecked(self.emergency_brake_active or driver_output.emergency_brake_active)
        self.update_emergency_brake_style()
        
        # Update service brake display to reflect actual controller state, not just GPIO
        self.service_brake_display_state = driver_output.service_brake_active
        
        # Update failure states
        self.set_failures(
            engine=driver_output.engine_failure,
            signal=driver_output.signal_failure,
            brake=driver_output.brake_failure
        )

        # --- Update door statuses based on controller output ---
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

        
        # Update next station info
        if driver_output.next_station and driver_output.station_side:
            station_text = f"{driver_output.next_station} on the {driver_output.station_side.title()} Hand Side"
            self.set_next_station(station_text)
        else:
            self.set_next_station("")
        
        # Update door button states based on movement and mode
        self.update_door_controls_enabled(driver_output.actual_speed, driver_output.auto_mode)
        
        # Update Kp/Ki status indicator
        self.update_kp_ki_status(driver_output.kp, driver_output.ki, driver_output.kp_ki_set)
        
    def update_connection_status(self):
        """Update connection status in GPIO status display"""
        if self.is_gpio_connected():
            connection_text = "Pi: CONNECTED"
            connection_style = "color: #28a745; font-weight: bold; font-size: 12px;"
        else:
            connection_text = "Pi: DISCONNECTED"
            connection_style = "color: #dc3545; font-weight: bold; font-size: 12px;"
        
        # Update connection status in GPIO status area
        if hasattr(self, 'connection_status_label'):
            self.connection_status_label.setText(connection_text)
            self.connection_status_label.setStyleSheet(connection_style)
    
    def setupUI(self):
        self.setWindowTitle("Train Controller Hardware - Driver Display")
        self.setGeometry(100, 100, 1500, 920)
        self.setMinimumSize(1500, 920)
        self.setMaximumSize(1500, 920)  # Fixed compact size - no resizing needed
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout - vertical for new arrangement
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(8)
        
        # =================================================================
        # TOP PANEL - Next Station and Time
        # =================================================================
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)
        
        # Next Station Section (moved to top)
        station_group = QGroupBox("Next Station")
        station_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 28px; 
                border: 2px solid #888888;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 5px;
            } 
            QGroupBox::title { 
                text-align: center; 
                font-weight: bold; 
                font-size: 28px;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: white;
            }
        """)
        station_group.setMaximumHeight(160)
        station_layout = QVBoxLayout(station_group)
        station_layout.setContentsMargins(4, 4, 4, 4)
        
        self.next_station_line = QLabel("No station information")
        self.next_station_line.setAlignment(Qt.AlignCenter)
        self.next_station_line.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #888888;
                border-radius: 4px;
                padding: 16px;
                font-weight: bold;
                font-size: 32px;
                color: #495057;
            }
        """)
        station_layout.addWidget(self.next_station_line)
        top_layout.addWidget(station_group)
        
        # Time (moved to top)
        time_group = QGroupBox("Time")
        time_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 16px; 
                border: 2px solid #888888;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 5px;
            } 
            QGroupBox::title { 
                text-align: center; 
                font-weight: bold; 
                font-size: 16px;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: white;
            }
        """)
        time_group.setFixedWidth(320)
        time_group.setMaximumHeight(160)
        time_layout = QVBoxLayout(time_group)
        time_layout.setContentsMargins(4, 4, 4, 4)
        
        self.time_label = QLabel("11:59 AM")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("""
            QLabel {
                background-color: white;
                color: black;
                font-size: 36px;
                font-weight: bold;
                padding: 24px;
                border-radius: 4px;
            }
        """)
        time_layout.addWidget(self.time_label)
        top_layout.addWidget(time_group)
        
        # Train ID (added to top panel)
        train_id_group = QGroupBox("Train ID")
        train_id_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 16px; 
                border: 2px solid #888888;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 5px;
            } 
            QGroupBox::title { 
                text-align: center; 
                font-weight: bold; 
                font-size: 16px;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: white;
            }
        """)
        train_id_group.setFixedWidth(200)
        train_id_group.setMaximumHeight(160)
        train_id_layout = QVBoxLayout(train_id_group)
        train_id_layout.setContentsMargins(4, 4, 4, 4)
        
        self.train_id_label = QLabel("1")
        self.train_id_label.setAlignment(Qt.AlignCenter)
        self.train_id_label.setStyleSheet("""
            QLabel {
                background-color: white;
                color: black;
                font-size: 36px;
                font-weight: bold;
                padding: 24px;
                border-radius: 4px;
            }
        """)
        train_id_layout.addWidget(self.train_id_label)
        top_layout.addWidget(train_id_group)
        
        main_layout.addWidget(top_panel)
        
        # =================================================================
        # CONTENT PANEL - Horizontal layout for the rest
        # =================================================================
        content_panel = QWidget()
        content_layout = QHBoxLayout(content_panel)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)
        
        # =================================================================
        # LEFT PANEL - Controls and Status
        # =================================================================
        left_panel = QWidget()
        left_panel.setFixedWidth(520)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        
        # Control Mode Section
        mode_group = QGroupBox("Control Mode")
        mode_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 28px; 
                border: 2px solid #888888;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 5px;
            } 
            QGroupBox::title { 
                text-align: center; 
                font-weight: bold; 
                font-size: 28px;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: white;
            }
        """)
        mode_group.setFixedHeight(140)
        mode_layout = QHBoxLayout(mode_group)
        mode_layout.setContentsMargins(4, 4, 4, 4)
        
        self.btn_manual = QPushButton("Manual")
        self.btn_auto = QPushButton("Auto")
        
        button_style = """
            QPushButton {
                background-color: #ecf0f1;
                border: 2px solid #888888;
                border-radius: 4px;
                padding: 16px;
                font-size: 28px;
                font-weight: bold;
                color: #2c3e50;
            }
            QPushButton:checked {
                background-color: #3498db;
                color: white;
                border-color: #666666;
            }
        """
        self.btn_manual.setStyleSheet(button_style)
        self.btn_auto.setStyleSheet(button_style)
        self.btn_manual.setCheckable(True)
        self.btn_auto.setCheckable(True)
        self.btn_manual.setChecked(True)
        
        # Disable buttons since they're GPIO controlled
        self.btn_manual.setEnabled(False)
        self.btn_auto.setEnabled(False)
        
        self.control_button_group = QButtonGroup()
        self.control_button_group.addButton(self.btn_manual)
        self.control_button_group.addButton(self.btn_auto)
        
        mode_layout.addWidget(self.btn_manual)
        mode_layout.addWidget(self.btn_auto)
        left_layout.addWidget(mode_group)
        
        # GPIO Input Status Section
        gpio_group = QGroupBox("GPIO Status (Hardware Input)")
        gpio_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 16px; 
                border: 2px solid #888888;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 5px;
            } 
            QGroupBox::title { 
                text-align: center; 
                font-weight: bold; 
                font-size: 16px;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: white;
            }
        """)
        gpio_group.setFixedHeight(320)
        gpio_layout = QVBoxLayout(gpio_group)
        gpio_layout.setContentsMargins(4, 4, 4, 4)
        gpio_layout.setSpacing(2)
        
        # Create compact status indicators with smaller fonts to fit the panel
        status_layout1 = QHBoxLayout()
        self.mode_status = QLabel("Mode: AUTO")
        self.mode_status.setStyleSheet("color: #007bff; font-weight: bold; font-size: 24px;")
        status_layout1.addWidget(self.mode_status)
        status_layout1.addStretch()
        
        status_layout2 = QHBoxLayout()
        self.headlight_status = QLabel("Headlights: OFF")
        self.headlight_status.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.interior_status = QLabel("Interior: OFF")
        self.interior_status.setStyleSheet("font-size: 24px; font-weight: bold;")
        status_layout2.addWidget(self.headlight_status)
        status_layout2.addWidget(self.interior_status)
        
        status_layout3 = QHBoxLayout()
        self.left_door_status = QLabel("L Door: CLOSED")
        self.left_door_status.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.right_door_status = QLabel("R Door: CLOSED")
        self.right_door_status.setStyleSheet("font-size: 24px; font-weight: bold;")
        status_layout3.addWidget(self.left_door_status)
        status_layout3.addWidget(self.right_door_status)
        
        status_layout4 = QHBoxLayout()
        self.brake_status = QLabel("Service Brake: OFF")
        self.brake_status.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.emergency_status = QLabel("Emergency Brake: OFF")
        self.emergency_status.setStyleSheet("font-size: 24px; font-weight: bold;")
        status_layout4.addWidget(self.brake_status)
        status_layout4.addWidget(self.emergency_status)
        
        gpio_layout.addLayout(status_layout1)
        gpio_layout.addLayout(status_layout2)
        gpio_layout.addLayout(status_layout3)
        gpio_layout.addLayout(status_layout4)
        
        left_layout.addWidget(gpio_group)
        
        # Temperature Control Section (moved above emergency brake)
        temp_group = QGroupBox("Temperature Control")
        temp_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 28px; 
                border: 2px solid #888888;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 5px;
            } 
            QGroupBox::title { 
                text-align: center; 
                font-weight: bold; 
                font-size: 28px;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: white;
            }
        """)
        temp_layout = QVBoxLayout(temp_group)
        temp_layout.setContentsMargins(4, 4, 4, 4)
        temp_layout.setSpacing(4)
        
        temp_display_layout = QHBoxLayout()
        current_label = QLabel("Current:")
        current_label.setStyleSheet("font-size: 28px; font-weight: bold;")
        temp_display_layout.addWidget(current_label)
        self.current_temp_display = QLabel("72°F")
        self.current_temp_display.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 28px;")
        temp_display_layout.addWidget(self.current_temp_display)
        temp_display_layout.addStretch()
        set_label = QLabel("Set:")
        set_label.setStyleSheet("font-size: 28px; font-weight: bold;")
        temp_display_layout.addWidget(set_label)
        self.temp_input_field = QLabel("72°F")
        self.temp_input_field.setStyleSheet("font-weight: bold; color: #e74c3c; font-size: 28px;")
        temp_display_layout.addWidget(self.temp_input_field)
        
        temp_layout.addLayout(temp_display_layout)
        left_layout.addWidget(temp_group)
        
        # Emergency Brake (moved below temperature control)
        self.emergency_brake_btn = QPushButton("EMERGENCY\nBRAKE")
        self.emergency_brake_btn.setFixedHeight(160)
        self.emergency_brake_btn.setCheckable(True)
        self.emergency_brake_btn.setEnabled(False)
        self.update_emergency_brake_style()
        left_layout.addWidget(self.emergency_brake_btn)
        
        content_layout.addWidget(left_panel, 0)  # Fixed ratio
        
        # =================================================================
        # CENTER PANEL - Train Information
        # =================================================================
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)
        
        # Train Information Section
        speed_group = QGroupBox("Train Information")
        speed_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 28px; 
                border: 2px solid #888888;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 5px;
            } 
            QGroupBox::title { 
                text-align: center; 
                font-weight: bold; 
                font-size: 28px;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: white;
            }
        """)
        speed_layout = QVBoxLayout(speed_group)
        speed_layout.setContentsMargins(4, 4, 4, 4)
        speed_layout.setSpacing(4)
        
        # Create compact info fields with bigger fonts
        self.input_speed_field = self.create_compact_info_field("Input Speed (mph)", "0.0")
        self.current_speed_field = self.create_compact_info_field("Current Speed (mph)", "0.0")
        self.speed_limit_field = self.create_compact_info_field("Speed Limit (mph)", "40.0")
        self.power_field = self.create_compact_info_field("Power Output (kW)", "0.0")
        self.authority_field = self.create_compact_info_field("Authority (yards)", "0.0")
        
        speed_layout.addWidget(self.input_speed_field)
        speed_layout.addWidget(self.current_speed_field)
        speed_layout.addWidget(self.speed_limit_field)
        speed_layout.addWidget(self.power_field)
        speed_layout.addWidget(self.authority_field)
        
        center_layout.addWidget(speed_group)
        
        content_layout.addWidget(center_panel, 1)  # Stretch to fill remaining space
        
        # =================================================================
        # RIGHT PANEL - Failures and PID Status
        # =================================================================
        right_panel = QWidget()
        # Fixed width for compact layout
        right_panel.setFixedWidth(360)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        
        # PID Status (made smaller)
        pid_group = QGroupBox("PID Status")
        pid_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 28px; 
                border: 2px solid #888888;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 5px;
            } 
            QGroupBox::title { 
                text-align: center; 
                font-weight: bold; 
                font-size: 28px;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: white;
            }
        """)
        pid_group.setMaximumHeight(160)
        pid_layout = QVBoxLayout(pid_group)
        pid_layout.setContentsMargins(4, 4, 4, 4)
        
        self.kp_ki_status_label = QLabel("Kp/Ki: Not Set")
        self.kp_ki_status_label.setAlignment(Qt.AlignCenter)
        self.kp_ki_status_label.setStyleSheet("""
            QLabel {
                background-color: #ffcc00;
                color: #333333;
                font-weight: bold;
                font-size: 24px;
                padding: 12px;
                border: 1px solid #888888;
                border-radius: 4px;
            }
        """)
        pid_layout.addWidget(self.kp_ki_status_label)
        right_layout.addWidget(pid_group)
        
        # Failures Section
        failures_group = QGroupBox("System Failures")
        failures_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 28px; 
                border: 2px solid #888888;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 5px;
            } 
            QGroupBox::title { 
                text-align: center; 
                font-weight: bold; 
                font-size: 28px;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: white;
            }
        """)
        failures_layout = QVBoxLayout(failures_group)
        failures_layout.setContentsMargins(4, 4, 4, 4)
        failures_layout.setSpacing(8)
        
        self.engine_failure_btn = QPushButton("Engine: OK")
        self.signal_failure_btn = QPushButton("Signal: OK")
        self.brake_failure_btn = QPushButton("Brake: OK")
        
        failure_style = """
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 28px;
                font-weight: bold;
                padding: 20px;
            }
        """
        
        self.engine_failure_btn.setStyleSheet(failure_style)
        self.signal_failure_btn.setStyleSheet(failure_style)
        self.brake_failure_btn.setStyleSheet(failure_style)
        self.engine_failure_btn.setEnabled(False)
        self.signal_failure_btn.setEnabled(False)
        self.brake_failure_btn.setEnabled(False)
        
        failures_layout.addWidget(self.engine_failure_btn)
        failures_layout.addWidget(self.signal_failure_btn)
        failures_layout.addWidget(self.brake_failure_btn)
        
        right_layout.addWidget(failures_group)
        
        content_layout.addWidget(right_panel, 0)  # Fixed ratio
        
        main_layout.addWidget(content_panel)
        
        # Connect signals
        self.connect_signals()
        
        # Initialize state
        self.update_gpio_status_display()
        
        # Apply initial scaling
        self.update_dynamic_scaling()
        
        # Store old references that other methods might expect
        self.headlights_toggle = None
        self.interior_toggle = None
        self.left_door_toggle = None
        self.right_door_toggle = None
        self.brake_on_btn = None
        self.brake_off_btn = None
        self.temp_up_btn = None
        self.temp_down_btn = None
        self.speed_up_btn = None
        self.speed_down_btn = None
    
    def resizeEvent(self, event):
        """Handle window resize events for dynamic scaling"""
        super().resizeEvent(event)
        self.update_dynamic_scaling()
    
    def update_dynamic_scaling(self):
        """Update all UI elements with dynamic scaling based on current window size"""
        # Get current window size
        width = self.width()
        height = self.height()
        
        # Calculate scaling factors based on window size
        width_factor = width / 900  # Base width
        height_factor = height / 600  # Base height
        scale_factor = min(width_factor, height_factor)
        
        # Ensure minimum readable scale
        scale_factor = max(scale_factor, 0.8)
        
        # Dynamic font size calculation
        base_font_size = int(14 * scale_factor)
        title_font_size = int(16 * scale_factor)
        small_font_size = int(12 * scale_factor)
        time_font_size = int(18 * scale_factor)
        group_font_size = int(14 * scale_factor)
        
        # Update margins and spacing
        margin_size = int(10 * scale_factor)
        spacing_size = int(6 * scale_factor)
        
        # Update main layout margins
        if hasattr(self, 'centralWidget'):
            main_layout = self.centralWidget().layout()
            if main_layout:
                main_layout.setContentsMargins(margin_size, margin_size, margin_size, margin_size)
                main_layout.setSpacing(spacing_size)
        
        # Update all group boxes with dynamic styling
        group_style_template = f"""
            QGroupBox {{ 
                font-weight: bold; 
                font-size: {group_font_size}px; 
                border: 2px solid #888888;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 5px;
            }} 
            QGroupBox::title {{ 
                text-align: center; 
                font-weight: bold; 
                font-size: {group_font_size}px;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: white;
            }}
        """
        
        # Update time label with dynamic font size
        if hasattr(self, 'time_label'):
            self.time_label.setStyleSheet(f"""
                QLabel {{
                    background-color: white;
                    color: black;
                    font-size: {time_font_size}px;
                    font-weight: bold;
                    padding: {int(12 * scale_factor)}px;
                    border-radius: 4px;
                }}
            """)
        
        # Update train ID label with dynamic font size
        if hasattr(self, 'train_id_label'):
            self.train_id_label.setStyleSheet(f"""
                QLabel {{
                    background-color: white;
                    color: black;
                    font-size: {time_font_size}px;
                    font-weight: bold;
                    padding: {int(12 * scale_factor)}px;
                    border-radius: 4px;
                }}
            """)
        
        # Update next station label with dynamic font size
        if hasattr(self, 'next_station_line'):
            self.next_station_line.setStyleSheet(f"""
                QLabel {{
                    background-color: #f8f9fa;
                    border: 1px solid #888888;
                    border-radius: 4px;
                    padding: {int(8 * scale_factor)}px;
                    font-weight: bold;
                    font-size: {title_font_size}px;
                    color: #495057;
                }}
            """)
        
        # Update emergency brake button
        if hasattr(self, 'emergency_brake_btn'):
            brake_height = int(80 * scale_factor)
            self.emergency_brake_btn.setMinimumHeight(brake_height)
            self.emergency_brake_btn.setMaximumHeight(brake_height + 20)
            self.emergency_brake_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #e74c3c;
                    color: white;
                    font-size: {title_font_size}px;
                    font-weight: bold;
                    border: 2px solid #888888;
                    border-radius: 6px;
                }}
            """)
        
        # Update mode buttons
        if hasattr(self, 'btn_manual') and hasattr(self, 'btn_auto'):
            button_style = f"""
                QPushButton {{
                    background-color: #ecf0f1;
                    border: 2px solid #888888;
                    border-radius: 4px;
                    padding: {int(8 * scale_factor)}px;
                    font-size: {base_font_size}px;
                    font-weight: bold;
                    color: #2c3e50;
                }}
                QPushButton:checked {{
                    background-color: #3498db;
                    color: white;
                    border-color: #666666;
                }}
            """
            self.btn_manual.setStyleSheet(button_style)
            self.btn_auto.setStyleSheet(button_style)
        
        # Update status label font sizes
        status_labels = [
            'headlight_status', 'interior_status', 'left_door_status', 'right_door_status',
            'brake_status', 'emergency_status', 'mode_status'
        ]
        for label_name in status_labels:
            if hasattr(self, label_name):
                label = getattr(self, label_name)
                current_style = label.styleSheet()
                # Replace font-size in current style
                import re
                new_style = re.sub(r'font-size: \d+px;', f'font-size: {small_font_size}px;', current_style)
                label.setStyleSheet(new_style)
        
        # Update temperature labels
        temp_labels = ['current_temp_display', 'temp_input_field']
        for label_name in temp_labels:
            if hasattr(self, label_name):
                label = getattr(self, label_name)
                current_style = label.styleSheet()
                new_style = re.sub(r'font-size: \d+px;', f'font-size: {base_font_size}px;', current_style)
                label.setStyleSheet(new_style)
        
        # Update compact info fields
        info_fields = ['input_speed_field', 'current_speed_field', 'speed_limit_field', 'power_field', 'authority_field']
        for field_name in info_fields:
            if hasattr(self, field_name):
                field = getattr(self, field_name)
                if hasattr(field, 'value_label'):
                    field.value_label.setStyleSheet(f"""
                        QLabel {{
                            font-size: {title_font_size}px;
                            font-weight: bold;
                            color: #212529;
                            background-color: #f8f9fa;
                            border: 1px solid #888888;
                            border-radius: 3px;
                            padding: {int(8 * scale_factor)}px {int(12 * scale_factor)}px;
                            min-width: {int(80 * scale_factor)}px;
                        }}
                    """)
                # Update the label in the field
                for i in range(field.layout().count()):
                    item = field.layout().itemAt(i)
                    if item and item.widget() and isinstance(item.widget(), QLabel):
                        widget = item.widget()
                        if ':' in widget.text():  # This is a field label
                            widget.setStyleSheet(f"font-size: {base_font_size}px; font-weight: bold; color: #495057;")
                            widget.setFixedWidth(int(140 * scale_factor))
        
        # Update failure buttons
        failure_buttons = ['engine_failure_btn', 'signal_failure_btn', 'brake_failure_btn']
        for button_name in failure_buttons:
            if hasattr(self, button_name):
                button = getattr(self, button_name)
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #28a745;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        font-size: {base_font_size}px;
                        font-weight: bold;
                        padding: {int(10 * scale_factor)}px;
                    }}
                """)
        
        # Update Kp/Ki status label
        if hasattr(self, 'kp_ki_status_label'):
            self.kp_ki_status_label.setStyleSheet(f"""
                QLabel {{
                    background-color: #ffcc00;
                    color: #333333;
                    font-weight: bold;
                    font-size: {small_font_size}px;
                    padding: {int(6 * scale_factor)}px;
                    border: 1px solid #888888;
                    border-radius: 4px;
                }}
            """)
        
        # Update widget size constraints
        if hasattr(self, 'left_panel'):
            # Update left panel size
            min_width = int(260 * scale_factor)
            max_width = int(400 * scale_factor)
            # Don't change these during resize as it causes layout issues
            
        if hasattr(self, 'right_panel'):
            # Update right panel size
            min_width = int(180 * scale_factor)
            max_width = int(300 * scale_factor)
            # Don't change these during resize as it causes layout issues
    
    def create_compact_info_field(self, label_text, initial_value):
        """Create a compact horizontal info field with bigger fonts and better spacing"""
        field_widget = QWidget()
        field_layout = QHBoxLayout(field_widget)
        field_layout.setContentsMargins(8, 8, 8, 8)
        field_layout.setSpacing(16)  # Increased spacing
        
        # Label with better width to prevent overlap
        label = QLabel(label_text + ":")
        label.setStyleSheet("font-size: 28px; font-weight: bold; color: #495057;")
        label.setFixedWidth(280)  # Increased width to accommodate longer labels
        label.setWordWrap(True)  # Allow text wrapping if needed
        field_layout.addWidget(label)
        
        # Value with minimum width to prevent overlap
        value_label = QLabel(initial_value)
        value_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: bold;
                color: #212529;
                background-color: #f8f9fa;
                border: 1px solid #888888;
                border-radius: 3px;
                padding: 12px 20px;
                min-width: 120px;
            }
        """)
        field_layout.addWidget(value_label)
        field_layout.addStretch()
        
        # Store reference to the value label for updates
        setattr(field_widget, 'value_label', value_label)
        setattr(field_widget, 'setText', lambda text: value_label.setText(text))
        
        return field_widget
    
    def update_gpio_status_display(self):
        """Update the GPIO status indicators"""
        # Update headlight status
        if self.gpio_inputs['headlights_on']:
            self.headlight_status.setText("Headlights: ON")
            self.headlight_status.setStyleSheet("color: #28a745; font-weight: bold; font-size: 24px;")
        else:
            self.headlight_status.setText("Headlights: OFF")
            self.headlight_status.setStyleSheet("color: #6c757d; font-weight: bold; font-size: 24px;")
        
        # Update interior lights status
        if self.gpio_inputs['interior_lights_on']:
            self.interior_status.setText("Interior: ON")
            self.interior_status.setStyleSheet("color: #28a745; font-weight: bold; font-size: 24px;")
        else:
            self.interior_status.setText("Interior: OFF")
            self.interior_status.setStyleSheet("color: #6c757d; font-weight: bold; font-size: 24px;")
        
        # Update brake status - use actual controller state for service brake, not GPIO state
        service_brake_state = getattr(self, 'service_brake_display_state', self.service_brake_active)
        if service_brake_state:
            self.brake_status.setText("Service Brake: ON")
            self.brake_status.setStyleSheet("color: #dc3545; font-weight: bold; font-size: 24px;")
        else:
            self.brake_status.setText("Service Brake: OFF")
            self.brake_status.setStyleSheet("color: #6c757d; font-weight: bold; font-size: 24px;")
        
        if self.emergency_brake_active:
            self.emergency_status.setText("Emergency Brake: ON")
            self.emergency_status.setStyleSheet("color: #dc3545; font-weight: bold; font-size: 24px;")
        else:
            self.emergency_status.setText("Emergency Brake: OFF")
            self.emergency_status.setStyleSheet("color: #6c757d; font-weight: bold; font-size: 24px;")
    
    def on_resize(self, event):
        """Handle window resize events for dynamic scaling"""
        super().resizeEvent(event)
        
        # Get current window size
        width = self.width()
        height = self.height()
        
        # Dynamically adjust font sizes based on window size
        base_font_size = max(12, min(16, width // 60))
        title_font_size = base_font_size + 2
        
        # Update time label font size
        time_font_size = max(14, min(18, width // 50))
        self.time_label.setStyleSheet(f"""
            QLabel {{
                background-color: white;
                color: black;
                font-size: {time_font_size}px;
                font-weight: bold;
                padding: 12px;
                border-radius: 4px;
            }}
        """)
        
        # Update emergency brake button size based on available space (adjusted for smaller window)
        brake_width = min(250, max(200, width // 5))
        brake_height = min(80, max(60, height // 12))
        self.emergency_brake_btn.setMinimumSize(brake_width, brake_height)
        
        # Update failure button sizes (adjusted for smaller right panel)
        failure_width = min(160, max(100, width // 12))
        failure_height = min(70, max(45, height // 14))
        
        self.engine_failure_btn.setMinimumSize(failure_width, failure_height)
        self.signal_failure_btn.setMinimumSize(failure_width, failure_height)
        self.brake_failure_btn.setMinimumSize(failure_width, failure_height)
    
    def update_emergency_brake_style(self):
        """Update emergency brake button style based on its state"""
        if self.emergency_brake_btn.isChecked():
            self.emergency_brake_btn.setStyleSheet("""
                QPushButton {
                    background-color: #8b0000;
                    color: white;
                    font-size: 16px;
                    font-weight: bold;
                    border: 2px solid #888888;
                    border-radius: 6px;
                }
            """)
        else:
            self.emergency_brake_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    font-size: 16px;
                    font-weight: bold;
                    border: 2px solid #888888;
                    border-radius: 6px;
                }
            """)
    
    def setup_timer(self):
        """Setup simulation time clock timer and GPIO reading"""
        # Clock timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()
        
        # GPIO reading timer (faster for responsiveness)
        self.gpio_timer = QTimer()
        self.gpio_timer.timeout.connect(self.read_gpio_inputs)
        self.gpio_timer.start(100)  # Read GPIO every 100ms
    
    def update_time(self):
        """Update the time label with current simulation time from Master Interface"""
        try:
            current_time = get_time()
        except RuntimeError:
            # Master Interface not running, show default time
            self.time_label.setText("--:-- --")
            return
        time_text = current_time.strftime("%I:%M %p")
        self.time_label.setText(time_text)
    
    def connect_signals(self):
        """Connect button signals to handlers - Modified for GPIO-only input"""
        # No signal connections needed - all input now comes from GPIO
        # Mode control, emergency brake, service brake, and environmental controls are GPIO-controlled
        pass
    
    def get_driver_input(self) -> DriverInput:
        """Return a DriverInput object using GPIO inputs instead of UI widgets"""
        return DriverInput(
            auto_mode=self.get_gpio_auto_mode(),
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
    
    def set_next_station(self, station_text: str):
        """Update the next station announcement"""
        self.next_station_line.setText(station_text)
    
    def set_failures(self, engine=False, signal=False, brake=False):
        """Update failure indicator buttons based on backend status"""
        # Engine failure
        if engine:
            self.engine_failure_btn.setText("Engine: FAILED")
            self.engine_failure_btn.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 28px;
                    font-weight: bold;
                    padding: 10px;
                }
            """)
        else:
            self.engine_failure_btn.setText("Engine: OK")
            self.engine_failure_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 28px;
                    font-weight: bold;
                    padding: 10px;
                }
            """)
        
        # Signal failure
        if signal:
            self.signal_failure_btn.setText("Signal: FAILED")
            self.signal_failure_btn.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 28px;
                    font-weight: bold;
                    padding: 10px;
                }
            """)
        else:
            self.signal_failure_btn.setText("Signal: OK")
            self.signal_failure_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 28px;
                    font-weight: bold;
                    padding: 10px;
                }
            """)
        
        # Brake failure
        if brake:
            self.brake_failure_btn.setText("Brake: FAILED")
            self.brake_failure_btn.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 28px;
                    font-weight: bold;
                    padding: 10px;
                }
            """)
        else:
            self.brake_failure_btn.setText("Brake: OK")
            self.brake_failure_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 28px;
                    font-weight: bold;
                    padding: 10px;
                }
            """)
    
    def update_kp_ki_status(self, kp: float, ki: float, kp_ki_set: bool):
        """Update the Kp/Ki status indicator"""
        if not kp_ki_set:
            self.kp_ki_status_label.setText("Waiting for\nKp/Ki")
            self.kp_ki_status_label.setStyleSheet("""
                QLabel {
                    background-color: #ff6b6b;
                    color: white;
                    font-weight: bold;
                    font-size: 16px;
                    padding: 8px;
                    border: 1px solid #888888;
                    border-radius: 4px;
                }
            """)
        else:
            self.kp_ki_status_label.setText(f"Kp/Ki: Set\n({kp:.1f}, {ki:.1f})")
            self.kp_ki_status_label.setStyleSheet("""
                QLabel {
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    font-size: 16px;
                    padding: 8px;
                    border: 1px solid #888888;
                    border-radius: 4px;
                }
            """)
    
    def update_manual_controls_enabled(self):
        """Update display based on control mode - all controls are GPIO only"""
        # All controls remain disabled since they're GPIO controlled
        # This method now only serves to track mode for display purposes
        pass
    
    def update_door_controls_enabled(self, actual_speed, auto_mode):
        """Update display based on movement and mode - GPIO controlled"""
        # In the new GPIO-controlled interface, this method is for compatibility
        # Door control is handled entirely through GPIO
        pass
    
    def cleanup_gpio(self):
        """Clean up GPIO emulator resources when closing application"""
        if hasattr(self, 'gpio_emulator'):
            self.gpio_emulator.stop()
            print("GPIO emulator cleanup completed")
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.cleanup_gpio()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = DriverUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()