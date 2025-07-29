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

# GPIO imports for Raspberry Pi hardware
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("Warning: RPi.GPIO not available. Running in simulation mode.")
    GPIO_AVAILABLE = False
        
class DriverUI(QMainWindow):
    def __init__(self):
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
        
        # Train ID comes from train controller initialization
        
        self.setup_gpio()
        self.setupUI()
        self.setup_timer()
        
    def setup_gpio(self):
        """Initialize GPIO pins for input reading"""
        if not GPIO_AVAILABLE:
            print("GPIO not available - running in simulation mode")
            # Initialize previous states to HIGH (button not pressed)
            for pin_name in self.GPIO_PINS:
                self.gpio_prev_states[pin_name] = True
            return
            
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup all pins as input with pull-up resistors
        for pin_name, pin_num in self.GPIO_PINS.items():
            GPIO.setup(pin_num, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self.gpio_prev_states[pin_name] = GPIO.input(pin_num)
            print(f"GPIO pin {pin_num} ({pin_name}) initialized")
    
    def read_gpio_inputs(self):
        """Read GPIO pins and detect button presses (high-to-low transitions)"""
        if not GPIO_AVAILABLE:
            return
            
        # Read all GPIO pins and detect edge transitions
        for pin_name, pin_num in self.GPIO_PINS.items():
            current_state = GPIO.input(pin_num)
            prev_state = self.gpio_prev_states[pin_name]
            
            # Handle mode control pin (GPIO 13) - level-triggered, not edge-triggered
            if pin_name == 'AUTO_MANUAL_MODE':
                # GPIO 13: HIGH = manual mode, LOW = auto mode
                self.gpio_auto_mode = not current_state  # Inverted: LOW = auto (True), HIGH = manual (False)
                self.update_mode_display()
            else:
                # Handle other pins with edge detection (button press: high to low)
                if prev_state == True and current_state == False:
                    self.handle_button_press(pin_name)
            
            # Update previous state
            self.gpio_prev_states[pin_name] = current_state
    
    def handle_button_press(self, button_name):
        """Handle button press events - Only emergency brake allowed in auto mode"""
        print(f"Button pressed: {button_name}")
        
        # Emergency brake is always allowed regardless of mode
        if button_name == 'EMERGENCY_BRAKE':
            self.emergency_brake_active = not self.emergency_brake_active
            return
        
        # All other controls are disabled in auto mode
        if self.gpio_auto_mode:
            print(f"Control {button_name} ignored - system is in AUTO mode")
            return
        
        # Manual mode controls
        if button_name == 'HEADLIGHT':
            self.gpio_inputs['headlights_on'] = not self.gpio_inputs['headlights_on']
            
        elif button_name == 'INTERIOR_LIGHT':
            self.gpio_inputs['interior_lights_on'] = not self.gpio_inputs['interior_lights_on']
            
        elif button_name == 'SERVICE_BRAKE':
            self.service_brake_active = not self.service_brake_active
            
        elif button_name == 'LEFT_DOOR':
            # Check if train is moving before allowing door operation
            if self.train_controller and self.train_controller.get_output_to_driver().actual_speed > 0:
                print(f"Door operation blocked - train is moving at {self.train_controller.get_output_to_driver().actual_speed:.1f} mph")
                return
            self.gpio_inputs['door_left_open'] = not self.gpio_inputs['door_left_open']
            
        elif button_name == 'RIGHT_DOOR':
            # Check if train is moving before allowing door operation
            if self.train_controller and self.train_controller.get_output_to_driver().actual_speed > 0:
                print(f"Door operation blocked - train is moving at {self.train_controller.get_output_to_driver().actual_speed:.1f} mph")
                return
            self.gpio_inputs['door_right_open'] = not self.gpio_inputs['door_right_open']
            
        elif button_name == 'SPEED_UP':
            self.manual_set_speed = min(self.manual_set_speed + 1.0, 100.0)
            
        elif button_name == 'SPEED_DOWN':
            self.manual_set_speed = max(self.manual_set_speed - 1.0, 0.0)
            
        elif button_name == 'TEMP_UP':
            self.manual_set_temperature = min(self.manual_set_temperature + 1.0, 100.0)
            
        elif button_name == 'TEMP_DOWN':
            self.manual_set_temperature = max(self.manual_set_temperature - 1.0, 32.0)
    
    def update_mode_display(self):
        """Update the mode buttons based on GPIO input"""
        if self.gpio_auto_mode:
            self.btn_auto.setChecked(True)
            self.btn_manual.setChecked(False)
        else:
            self.btn_auto.setChecked(False)
            self.btn_manual.setChecked(True)
    
    def set_train_controller(self, train_controller: TrainController):
        """Set the train controller instance to pull data from"""
        self.train_controller = train_controller
        
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
        
        # Update brake states display
        # Emergency brake display reflects GPIO/controller state
        self.emergency_brake_btn.setChecked(self.emergency_brake_active or driver_output.emergency_brake_active)
        self.update_emergency_brake_style()
        
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
        
    def setupUI(self):
        self.setWindowTitle("Train Controller Hardware - Driver Display")
        self.setGeometry(100, 100, 900, 500)
        self.setMinimumSize(750, 460)
        self.setMaximumSize(750, 460)  # Fixed compact size - no resizing needed
        
        # Add resize event to handle dynamic scaling
        self.resizeEvent = self.on_resize
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout - vertical for new arrangement
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(4)
        
        # =================================================================
        # TOP PANEL - Next Station and Time
        # =================================================================
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(6)
        
        # Next Station Section (moved to top)
        station_group = QGroupBox("Next Station")
        station_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 14px; 
                border: 2px solid #888888;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 5px;
            } 
            QGroupBox::title { 
                text-align: center; 
                font-weight: bold; 
                font-size: 14px;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: white;
            }
        """)
        station_group.setMaximumHeight(80)
        station_layout = QVBoxLayout(station_group)
        station_layout.setContentsMargins(4, 4, 4, 4)
        
        self.next_station_line = QLabel("No station information")
        self.next_station_line.setAlignment(Qt.AlignCenter)
        self.next_station_line.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #888888;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
                font-size: 16px;
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
                font-size: 14px; 
                border: 2px solid #888888;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 5px;
            } 
            QGroupBox::title { 
                text-align: center; 
                font-weight: bold; 
                font-size: 14px;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: white;
            }
        """)
        time_group.setFixedWidth(160)
        time_group.setMaximumHeight(80)
        time_layout = QVBoxLayout(time_group)
        time_layout.setContentsMargins(4, 4, 4, 4)
        
        self.time_label = QLabel("11:59 AM")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("""
            QLabel {
                background-color: white;
                color: black;
                font-size: 18px;
                font-weight: bold;
                padding: 12px;
                border-radius: 4px;
            }
        """)
        time_layout.addWidget(self.time_label)
        top_layout.addWidget(time_group)
        
        main_layout.addWidget(top_panel)
        
        # =================================================================
        # CONTENT PANEL - Horizontal layout for the rest
        # =================================================================
        content_panel = QWidget()
        content_layout = QHBoxLayout(content_panel)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(6)
        
        # =================================================================
        # LEFT PANEL - Controls and Status
        # =================================================================
        left_panel = QWidget()
        left_panel.setFixedWidth(260)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)
        
        # Control Mode Section
        mode_group = QGroupBox("Control Mode")
        mode_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 14px; 
                border: 2px solid #888888;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 5px;
            } 
            QGroupBox::title { 
                text-align: center; 
                font-weight: bold; 
                font-size: 14px;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: white;
            }
        """)
        mode_group.setFixedHeight(70)
        mode_layout = QHBoxLayout(mode_group)
        mode_layout.setContentsMargins(4, 4, 4, 4)
        
        self.btn_manual = QPushButton("Manual")
        self.btn_auto = QPushButton("Auto")
        
        button_style = """
            QPushButton {
                background-color: #ecf0f1;
                border: 2px solid #888888;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
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
                font-size: 14px; 
                border: 2px solid #888888;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 5px;
            } 
            QGroupBox::title { 
                text-align: center; 
                font-weight: bold; 
                font-size: 14px;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: white;
            }
        """)
        gpio_group.setFixedHeight(160)
        gpio_layout = QVBoxLayout(gpio_group)
        gpio_layout.setContentsMargins(4, 4, 4, 4)
        gpio_layout.setSpacing(2)
        
        # Create compact status indicators with smaller fonts to fit the panel
        status_layout1 = QHBoxLayout()
        self.mode_status = QLabel("Mode: AUTO")
        self.mode_status.setStyleSheet("color: #007bff; font-weight: bold; font-size: 12px;")
        status_layout1.addWidget(self.mode_status)
        status_layout1.addStretch()
        
        status_layout2 = QHBoxLayout()
        self.headlight_status = QLabel("Headlights: OFF")
        self.headlight_status.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.interior_status = QLabel("Interior: OFF")
        self.interior_status.setStyleSheet("font-size: 12px; font-weight: bold;")
        status_layout2.addWidget(self.headlight_status)
        status_layout2.addWidget(self.interior_status)
        
        status_layout3 = QHBoxLayout()
        self.left_door_status = QLabel("L Door: CLOSED")
        self.left_door_status.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.right_door_status = QLabel("R Door: CLOSED")
        self.right_door_status.setStyleSheet("font-size: 12px; font-weight: bold;")
        status_layout3.addWidget(self.left_door_status)
        status_layout3.addWidget(self.right_door_status)
        
        status_layout4 = QHBoxLayout()
        self.brake_status = QLabel("Service Brake: OFF")
        self.brake_status.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.emergency_status = QLabel("Emergency Brake: OFF")
        self.emergency_status.setStyleSheet("font-size: 12px; font-weight: bold;")
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
                font-size: 14px; 
                border: 2px solid #888888;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 5px;
            } 
            QGroupBox::title { 
                text-align: center; 
                font-weight: bold; 
                font-size: 14px;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: white;
            }
        """)
        temp_layout = QVBoxLayout(temp_group)
        temp_layout.setContentsMargins(4, 4, 4, 4)
        temp_layout.setSpacing(2)
        
        temp_display_layout = QHBoxLayout()
        current_label = QLabel("Current:")
        current_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        temp_display_layout.addWidget(current_label)
        self.current_temp_display = QLabel("72°F")
        self.current_temp_display.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 14px;")
        temp_display_layout.addWidget(self.current_temp_display)
        temp_display_layout.addStretch()
        set_label = QLabel("Set:")
        set_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        temp_display_layout.addWidget(set_label)
        self.temp_input_field = QLabel("72°F")
        self.temp_input_field.setStyleSheet("font-weight: bold; color: #e74c3c; font-size: 14px;")
        temp_display_layout.addWidget(self.temp_input_field)
        
        temp_layout.addLayout(temp_display_layout)
        left_layout.addWidget(temp_group)
        
        # Emergency Brake (moved below temperature control)
        self.emergency_brake_btn = QPushButton("EMERGENCY\nBRAKE")
        self.emergency_brake_btn.setFixedHeight(80)
        self.emergency_brake_btn.setCheckable(True)
        self.emergency_brake_btn.setEnabled(False)
        self.update_emergency_brake_style()
        left_layout.addWidget(self.emergency_brake_btn)
        
        content_layout.addWidget(left_panel)
        
        # =================================================================
        # CENTER PANEL - Train Information
        # =================================================================
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(4)
        
        # Train Information Section
        speed_group = QGroupBox("Train Information")
        speed_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 14px; 
                border: 2px solid #888888;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 5px;
            } 
            QGroupBox::title { 
                text-align: center; 
                font-weight: bold; 
                font-size: 14px;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: white;
            }
        """)
        speed_layout = QVBoxLayout(speed_group)
        speed_layout.setContentsMargins(4, 4, 4, 4)
        speed_layout.setSpacing(2)
        
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
        
        content_layout.addWidget(center_panel)
        
        # =================================================================
        # RIGHT PANEL - Failures and PID Status
        # =================================================================
        right_panel = QWidget()
        right_panel.setFixedWidth(180)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)
        
        # PID Status (made smaller)
        pid_group = QGroupBox("PID Status")
        pid_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 14px; 
                border: 2px solid #888888;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 5px;
            } 
            QGroupBox::title { 
                text-align: center; 
                font-weight: bold; 
                font-size: 14px;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: white;
            }
        """)
        pid_group.setMaximumHeight(80)
        pid_layout = QVBoxLayout(pid_group)
        pid_layout.setContentsMargins(4, 4, 4, 4)
        
        self.kp_ki_status_label = QLabel("Kp/Ki: Not Set")
        self.kp_ki_status_label.setAlignment(Qt.AlignCenter)
        self.kp_ki_status_label.setStyleSheet("""
            QLabel {
                background-color: #ffcc00;
                color: #333333;
                font-weight: bold;
                font-size: 12px;
                padding: 6px;
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
                font-size: 14px; 
                border: 2px solid #888888;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 5px;
            } 
            QGroupBox::title { 
                text-align: center; 
                font-weight: bold; 
                font-size: 14px;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: white;
            }
        """)
        failures_layout = QVBoxLayout(failures_group)
        failures_layout.setContentsMargins(4, 4, 4, 4)
        failures_layout.setSpacing(4)
        
        self.engine_failure_btn = QPushButton("Engine: OK")
        self.signal_failure_btn = QPushButton("Signal: OK")
        self.brake_failure_btn = QPushButton("Brake: OK")
        
        failure_style = """
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
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
        
        content_layout.addWidget(right_panel)
        
        main_layout.addWidget(content_panel)
        
        # Connect signals
        self.connect_signals()
        
        # Initialize state
        self.update_gpio_status_display()
        
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
    
    def create_compact_info_field(self, label_text, initial_value):
        """Create a compact horizontal info field with bigger fonts and better spacing"""
        field_widget = QWidget()
        field_layout = QHBoxLayout(field_widget)
        field_layout.setContentsMargins(4, 4, 4, 4)
        field_layout.setSpacing(8)  # Increased spacing
        
        # Label with better width to prevent overlap
        label = QLabel(label_text + ":")
        label.setStyleSheet("font-size: 14px; font-weight: bold; color: #495057;")
        label.setFixedWidth(140)  # Increased width to accommodate longer labels
        label.setWordWrap(True)  # Allow text wrapping if needed
        field_layout.addWidget(label)
        
        # Value with minimum width to prevent overlap
        value_label = QLabel(initial_value)
        value_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #212529;
                background-color: #f8f9fa;
                border: 1px solid #888888;
                border-radius: 3px;
                padding: 6px 10px;
                min-width: 60px;
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
            self.headlight_status.setStyleSheet("color: #28a745; font-weight: bold; font-size: 12px;")
        else:
            self.headlight_status.setText("Headlights: OFF")
            self.headlight_status.setStyleSheet("color: #6c757d; font-weight: bold; font-size: 12px;")
        
        # Update interior lights status
        if self.gpio_inputs['interior_lights_on']:
            self.interior_status.setText("Interior: ON")
            self.interior_status.setStyleSheet("color: #28a745; font-weight: bold; font-size: 12px;")
        else:
            self.interior_status.setText("Interior: OFF")
            self.interior_status.setStyleSheet("color: #6c757d; font-weight: bold; font-size: 12px;")
        
        # Update door status
        if self.gpio_inputs['door_left_open']:
            self.left_door_status.setText("L Door: OPEN")
            self.left_door_status.setStyleSheet("color: #ffc107; font-weight: bold; font-size: 12px;")
        else:
            self.left_door_status.setText("L Door: CLOSED")
            self.left_door_status.setStyleSheet("color: #6c757d; font-weight: bold; font-size: 12px;")
        
        if self.gpio_inputs['door_right_open']:
            self.right_door_status.setText("R Door: OPEN")
            self.right_door_status.setStyleSheet("color: #ffc107; font-weight: bold; font-size: 12px;")
        else:
            self.right_door_status.setText("R Door: CLOSED")
            self.right_door_status.setStyleSheet("color: #6c757d; font-weight: bold; font-size: 12px;")
        
        # Update brake status
        if self.service_brake_active:
            self.brake_status.setText("Service Brake: ON")
            self.brake_status.setStyleSheet("color: #dc3545; font-weight: bold; font-size: 12px;")
        else:
            self.brake_status.setText("Service Brake: OFF")
            self.brake_status.setStyleSheet("color: #6c757d; font-weight: bold; font-size: 12px;")
        
        if self.emergency_brake_active:
            self.emergency_status.setText("Emergency Brake: ON")
            self.emergency_status.setStyleSheet("color: #dc3545; font-weight: bold; font-size: 12px;")
        else:
            self.emergency_status.setText("Emergency Brake: OFF")
            self.emergency_status.setStyleSheet("color: #6c757d; font-weight: bold; font-size: 12px;")
        
        # Update mode status
        if self.gpio_auto_mode:
            self.mode_status.setText("Mode: AUTO")
            self.mode_status.setStyleSheet("color: #007bff; font-weight: bold; font-size: 12px;")
        else:
            self.mode_status.setText("Mode: MANUAL")
            self.mode_status.setStyleSheet("color: #fd7e14; font-weight: bold; font-size: 12px;")
    
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

    def create_info_field_with_controls(self, parent_layout, label_text):
        """Create an info field with up/down controls for manual speed input"""
        field_layout = QHBoxLayout()
        field_layout.setContentsMargins(0, 0, 0, 0)  # No vertical margins
        field_layout.setSpacing(8)
        
        # Enhanced label styling with fixed width
        label = QLabel(label_text)
        label.setFixedWidth(140)
        label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: bold;
                color: #34495e;
                padding: 0px 0px;
            }
        """)
        field_layout.addWidget(label)
        field_layout.addStretch()  # Push input field to the right
        
        # Enhanced input field with better styling
        line_edit = QLineEdit("")
        line_edit.setReadOnly(True)
        line_edit.setMinimumWidth(50)
        line_edit.setMaximumWidth(100)
        line_edit.setMinimumHeight(24)
        line_edit.setStyleSheet("""
            QLineEdit {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff, stop: 1 #f8f9fa);
                border: 2px solid #888888;
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 13px;
                font-weight: bold;
                color: #2c3e50;
                selection-background-color: #3498db;
            }
            QLineEdit:focus {
                border-color: #888888;
                background: white;
            }
        """)
        field_layout.addWidget(line_edit)
        
        # Up/Down buttons for manual mode - disabled (GPIO controlled)
        up_btn = QPushButton("▲")
        down_btn = QPushButton("▼")
        up_btn.setFixedSize(18, 13)
        down_btn.setFixedSize(18, 13)
        button_style = """
            QPushButton { 
                font-size: 9px; 
                padding: 0px;
                margin: 0px;
                background-color: #cccccc;
                border: 1px solid #888888;
                border-radius: 2px;
                color: #666666;
            }
        """
        up_btn.setStyleSheet(button_style)
        down_btn.setStyleSheet(button_style)
        up_btn.setEnabled(False)  # Disabled - GPIO controlled
        down_btn.setEnabled(False)  # Disabled - GPIO controlled
        
        # Store references for enabling/disabling
        self.speed_up_btn = up_btn
        self.speed_down_btn = down_btn
        
        # Vertical layout for up/down buttons
        button_layout = QVBoxLayout()
        button_layout.setContentsMargins(2, 0, 0, 0)
        button_layout.setSpacing(1)
        button_layout.addWidget(up_btn)
        button_layout.addWidget(down_btn)
        
        field_layout.addLayout(button_layout)
        parent_layout.addLayout(field_layout)
        return line_edit
        
    def increase_manual_speed(self):
        """Increase manual speed setting"""
        self.manual_set_speed = min(self.manual_set_speed + 1.0, 100.0)
        if not self.btn_auto.isChecked():
            self.input_speed_field.setText(f"{self.manual_set_speed:.1f}")
    
    def decrease_manual_speed(self):
        """Decrease manual speed setting"""
        self.manual_set_speed = max(self.manual_set_speed - 1.0, 0.0)
        if not self.btn_auto.isChecked():
            self.input_speed_field.setText(f"{self.manual_set_speed:.1f}")
    
    def increase_temperature(self):
        """Increase manual temperature setting"""
        self.manual_set_temperature = min(self.manual_set_temperature + 1.0, 100.0)
        self.temp_input_field.setText(f"{self.manual_set_temperature:.0f}°F")
    
    def decrease_temperature(self):
        """Decrease manual temperature setting"""
        self.manual_set_temperature = max(self.manual_set_temperature - 1.0, 32.0)
        self.temp_input_field.setText(f"{self.manual_set_temperature:.0f}°F")
        
    def create_info_field(self, parent_layout, label_text, initial_value):
        """Create an info field and return the QLineEdit widget reference"""
        field_layout = QHBoxLayout()
        field_layout.setContentsMargins(0, 0, 0, 0)  # No vertical margins
        field_layout.setSpacing(8)
        
        # Enhanced label styling with fixed width
        label = QLabel(label_text)
        label.setFixedWidth(140)
        label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: bold;
                color: #34495e;
                padding: 0px 0px;
            }
        """)
        field_layout.addWidget(label)
        field_layout.addStretch()  # Push input field to the right
        
        # Enhanced input field with gradient and better styling
        line_edit = QLineEdit(initial_value)
        line_edit.setReadOnly(True)
        line_edit.setMinimumWidth(60)
        line_edit.setMaximumWidth(120)
        line_edit.setMinimumHeight(24)
        line_edit.setStyleSheet("""
            QLineEdit {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff, stop: 1 #f8f9fa);
                border: 2px solid #888888;
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 13px;
                font-weight: bold;
                color: #2c3e50;
                selection-background-color: #3498db;
            }
        """)
        field_layout.addWidget(line_edit)
        parent_layout.addLayout(field_layout)
        return line_edit
        
    def create_toggle_switch(self, initial_state=False, is_door=False):
        """Create a custom toggle switch widget (display only - GPIO controlled)"""
        toggle = QPushButton()
        toggle.setCheckable(True)
        toggle.setChecked(initial_state)
        toggle.setFixedSize(60, 28)  # Slightly larger
        toggle.setEnabled(False)  # Display only - GPIO controlled
        
        def update_toggle_style():
            # Enhanced style with gradients and shadows
            if toggle.isChecked():
                toggle.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                            stop: 0 #27ae60, stop: 1 #2ecc71);
                        border: 2px solid #888888;
                        border-radius: 8px;
                        color: white;
                        font-weight: bold;
                        font-size: 11px;
                        box-shadow: 0 2px 4px rgba(46, 204, 113, 0.3);
                    }
                """)
                toggle.setText("Open" if is_door else "ON")
            else:
                toggle.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                            stop: 0 #e74c3c, stop: 1 #c0392b);
                        border: 2px solid #888888;
                        border-radius: 8px;
                        color: white;
                        font-weight: bold;
                        font-size: 11px;
                        box-shadow: 0 2px 4px rgba(231, 76, 60, 0.3);
                    }
                """)
                toggle.setText("Close" if is_door else "OFF")
        
        # Store the update function for later use
        toggle.update_style = update_toggle_style
        update_toggle_style()
        return toggle
    
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
        self.gpio_timer.start(50)  # Read GPIO every 50ms
    
    def update_time(self):
        """Update the time label with current simulation time from Master Interface"""
        current_time = get_time()
        time_text = current_time.strftime("%I:%M %p")
        self.time_label.setText(time_text)
    
    def connect_signals(self):
        """Connect button signals to handlers - Modified for GPIO-only input"""
        # No signal connections needed - all input now comes from GPIO
        # Mode control, emergency brake, service brake, and environmental controls are GPIO-controlled
        pass
        
    def emergency_brake_pressed(self):
        """Handle emergency brake button press"""
        self.emergency_brake_active = self.emergency_brake_btn.isChecked()
        self.update_emergency_brake_style()
    
    def is_emergency_brake_active(self) -> bool:
        """Check if emergency brake is currently active"""
        return self.emergency_brake_active
    
    def reset_emergency_brake(self):
        """Reset emergency brake (for external control)"""
        self.emergency_brake_active = False
        self.emergency_brake_btn.setChecked(False)
        self.update_emergency_brake_style()
        
    def service_brake_changed(self, button):
        """Handle service brake state change"""
        self.service_brake_active = (button == self.brake_on_btn)
    
    def control_mode_changed(self, button):
        """Handle control mode change"""
        self.update_manual_controls_enabled()
        
        # Update speed display based on mode
        if self.btn_manual.isChecked():
            self.input_speed_field.setText(f"{self.manual_set_speed:.1f}")
        else:
            # In auto mode, the display will be updated by update_from_train_controller
            pass
    
    def update_manual_controls_enabled(self):
        """Update display based on control mode - all controls are GPIO only"""
        manual_mode = self.btn_manual.isChecked()
        
        # All controls remain disabled since they're GPIO controlled
        # This method now only serves to track mode for display purposes
        # Controls are always display-only in hardware mode
    
    def update_door_controls_enabled(self, actual_speed, auto_mode):
        """Update display based on movement and mode - GPIO controlled"""
        # In the new GPIO-controlled interface, this method is for compatibility
        # Door control is handled entirely through GPIO
        pass
    
    def update_door_button_style(self, toggle_button, enabled):
        """Update button visual style - compatibility method"""
        # No longer needed in GPIO-controlled interface
        pass
    
    def update_kp_ki_status(self, kp: float, ki: float, kp_ki_set: bool):
        """Update the Kp/Ki status indicator"""
        if not kp_ki_set:
            self.kp_ki_status_label.setText("Waiting for\nKp/Ki")
            self.kp_ki_status_label.setStyleSheet("""
                QLabel {
                    background-color: #ff6b6b;
                    color: white;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 6px;
                    border: 1px solid #888888;
                    border-radius: 3px;
                }
            """)
        else:
            self.kp_ki_status_label.setText(f"Kp/Ki: Set\n({kp:.1f}, {ki:.1f})")
            self.kp_ki_status_label.setStyleSheet("""
                QLabel {
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 6px;
                    border: 1px solid #888888;
                    border-radius: 3px;
                }
            """)
            
    def get_driver_input(self) -> DriverInput:
        """Return a DriverInput object using GPIO inputs instead of UI widgets"""
        return DriverInput(
            auto_mode=self.gpio_auto_mode,  # Use GPIO pin 13 for mode control
            headlights_on=self.gpio_inputs['headlights_on'],
            interior_lights_on=self.gpio_inputs['interior_lights_on'],
            door_left_open=self.gpio_inputs['door_left_open'],
            door_right_open=self.gpio_inputs['door_right_open'],
            set_temperature=self.manual_set_temperature,
            emergency_brake=self.emergency_brake_active,
            set_speed=self.manual_set_speed,
            service_brake=self.service_brake_active,
            train_id=self.train_controller.train_id if self.train_controller else 1
        )
    
    def set_outputs(self, output: TrainModelOutput):
        """Update output fields in the UI with TrainModelOutput data"""
        # Deprecated - use update_from_train_controller() instead
        # This method is kept for backward compatibility only
        pass
    
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
                    font-size: 14px;
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
                    font-size: 14px;
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
                    font-size: 14px;
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
                    font-size: 14px;
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
                    font-size: 14px;
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
                    font-size: 14px;
                    font-weight: bold;
                    padding: 10px;
                }
            """)
    
    def get_failure_states(self):
        """Get current failure button states (for backward compatibility)"""
        return {
            'engine_failure': "CC0000" in self.engine_failure_btn.styleSheet(),
            'signal_failure': "CC0000" in self.signal_failure_btn.styleSheet(),
            'brake_failure': "CC0000" in self.brake_failure_btn.styleSheet()
        }
    
    def cleanup_gpio(self):
        """Clean up GPIO resources when closing application"""
        if GPIO_AVAILABLE:
            GPIO.cleanup()
            print("GPIO cleanup completed")
    
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