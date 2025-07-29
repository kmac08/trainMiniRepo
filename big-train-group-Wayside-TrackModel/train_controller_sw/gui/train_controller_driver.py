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
    from train_controller_sw.controller.data_types import DriverInput, TrainModelOutput, TrainModelInput, OutputToDriver
    from train_controller_sw.controller.train_controller import TrainController
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


        
class DriverUI(QMainWindow):
    def __init__(self):
        super().__init__() 

        # Initialize state variables
        self.emergency_brake_active = False  # Driver's emergency brake input
        self.service_brake_active = False
        self.manual_set_speed = 0.0  # Track manual speed setting
        self.manual_set_temperature = 72.0  # Track manual temperature setting
        self.controller_emergency_state = False  # Track controller's emergency brake state
        
        # Initialize train controller (optional - can be set externally)
        self.train_controller = None
        
        self.setupUI()
        self.setup_timer()
        
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
        
        # Update train ID display from train controller
        if self.train_controller:
            self.train_id_label.setText(str(self.train_controller.train_id))
        
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
        
        # Update control mode
        if driver_output.auto_mode:
            self.btn_auto.setChecked(True)
        else:
            self.btn_manual.setChecked(True)
        self.update_manual_controls_enabled()
        
        # Update headlight and interior light button states
        if driver_output.headlights_on:
            self.headlights_on_btn.setChecked(True)
        else:
            self.headlights_off_btn.setChecked(True)
            
        if driver_output.interior_lights_on:
            self.interior_on_btn.setChecked(True)
        else:
            self.interior_off_btn.setChecked(True)
        # Update environmental controls (in auto mode, these reflect controller state)
        if driver_output.auto_mode:
            self.left_door_toggle.setChecked(driver_output.left_door_open)
            self.right_door_toggle.setChecked(driver_output.right_door_open)
        
        # Update brake states
        # Update emergency brake display to show controller state
        # but don't change the driver's input state
        if driver_output.emergency_brake_active:
            self.emergency_brake_btn.setChecked(True)
            self.update_emergency_brake_style()
        else:
            # Only uncheck if driver hasn't pressed it
            if not self.emergency_brake_active:
                self.emergency_brake_btn.setChecked(False)
                self.update_emergency_brake_style()
        
        self.service_brake_active = driver_output.service_brake_active
        if driver_output.service_brake_active:
            self.brake_on_btn.setChecked(True)
        else:
            self.brake_off_btn.setChecked(True)
        
        # Update failure states
        self.set_failures(
            engine=driver_output.engine_failure,
            signal=driver_output.signal_failure,
            brake=driver_output.brake_failure
        )
        
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
    
    # Train ID methods removed - train ID now comes from controller initialization
    
    def on_train_id_changed(self, index):
        """Handle train ID dropdown selection change with error handling"""
        try:
            if 0 <= index < self.train_id_combo.count():
                item_text = self.train_id_combo.itemText(index)
                if item_text:
                    self.selected_train_id = int(item_text)
                    print(f"Train ID changed to: {self.selected_train_id}")
                else:
                    print(f"Warning: Empty item text at index {index}")
            else:
                print(f"Warning: Invalid index {index} for train ID combo box")
        except (ValueError, AttributeError) as e:
            print(f"Error updating train ID selection: {e}")
            # Fallback to default
            self.selected_train_id = 1
    
    def setupUI(self):
        self.setWindowTitle("Train Controller - Driver")
        self.setGeometry(100, 100, 1400, 700)
        self.setMinimumSize(800, 550)  
        self.setMaximumSize(800, 550)
        # Add resize event to handle dynamic scaling
        self.resizeEvent = self.on_resize
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout - using grid for compact layout
        main_layout = QGridLayout(central_widget)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)
        
        # Top section (row 0)
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)
        
        # Control Mode Group
        control_group = QGroupBox("Control Mode")
        #control_group.setMinimumWidth(200)
        control_group.setMaximumWidth(380)
        control_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin: 8px 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: palette(window);
            }
        """)
        control_layout = QHBoxLayout(control_group)
        
        self.btn_manual = QPushButton("Manual")
        self.btn_auto = QPushButton("Auto")
        
        # Compact button style for better fit
        button_style = """
            QPushButton {
                background-color: #ecf0f1;
                border: 2px solid #bdc3c7;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
                min-width: 40px;
                color: #2c3e50;
            }
            QPushButton:checked {
                background-color: #3498db;
                color: white;
                border-color: #2980b9;
            }
            QPushButton:hover {
                background-color: #d5dbdb;
                border-color: #95a5a6;
            }
            QPushButton:checked:hover {
                background-color: #2980b9;
            }
        """
        self.btn_manual.setStyleSheet(button_style)
        self.btn_auto.setStyleSheet(button_style)
        self.btn_manual.setCheckable(True)
        self.btn_auto.setCheckable(True)
        self.btn_auto.setChecked(True) #Set AUTO to be DEFAULT
        
        # Button group for exclusive selection
        self.control_button_group = QButtonGroup()
        self.control_button_group.addButton(self.btn_manual)
        self.control_button_group.addButton(self.btn_auto)
        
        control_layout.setContentsMargins(4, 2, 4, 2)
        control_layout.setSpacing(2)
        control_layout.addWidget(self.btn_manual)
        control_layout.addWidget(self.btn_auto)
        
        # Announcements Group
        announcements_group = QGroupBox("Announcements")
        announcements_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin: 4px 0px;
                padding-top: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: palette(window);
            }
        """)
        announcements_layout = QVBoxLayout(announcements_group)
        
        next_station_layout = QHBoxLayout()
        next_station_layout.setContentsMargins(0, 1, 0, 1)
        next_station_layout.setSpacing(4)
        station_label = QLabel("Next Station:")
        station_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: bold;
                color: #34495e;
                padding: 0px 0px;
            }
        """)
        next_station_layout.addWidget(station_label)
        self.next_station_line = QLineEdit("")
        self.next_station_line.setReadOnly(True)
        self.next_station_line.setMinimumHeight(24)
        self.next_station_line.setStyleSheet("""
            QLineEdit {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff, stop: 1 #f0f8ff);
                border: 2px solid #3498db;
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 13px;
                font-weight: bold;
                color: #2c3e50;
            }
            QLineEdit:focus {
                border-color: #2980b9;
                background-color: white;
            }
        """)
        next_station_layout.addWidget(self.next_station_line)
        announcements_layout.setContentsMargins(6, 3, 6, 3)
        announcements_layout.setSpacing(2)
        announcements_layout.addLayout(next_station_layout)
        
        top_layout.addWidget(control_group)
        top_layout.addWidget(announcements_group, 1)  # Give it stretch priority
        
        # Add top section to grid
        main_layout.addWidget(top_widget, 0, 0, 1, 2)  # Span all columns
        
        # Middle section - Environmental Controls (row 1, col 0)
        env_group = QGroupBox("Environmental Controls")
        #env_group.setMinimumWidth(220)
        env_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin: 3px 0px;
                padding-top: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: palette(window);
            }
        """)
        env_layout = QVBoxLayout(env_group)
        env_layout.setSpacing(4)
        env_layout.setContentsMargins(6, 24, 6, 8)
                
        # Headlights ON/OFF buttons
        headlights_group = QGroupBox("Headlights")
        headlights_group.setMinimumHeight(50)
        headlights_group.setStyleSheet("""
            QGroupBox {
                font-size: 13px;
                font-weight: bold;
                color: #2c3e50;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                margin: 4px 2px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 6px;
                background-color: palette(window);
            }
        """)
        headlights_layout = QHBoxLayout(headlights_group)
        headlights_layout.setContentsMargins(8, 6, 8, 6)
        headlights_layout.setSpacing(8)
        
        self.headlights_on_btn = QPushButton("ON")
        self.headlights_off_btn = QPushButton("OFF")
        
        headlight_style = """
            QPushButton {
                background-color: #ecf0f1;
                border: 2px solid #bdc3c7;
                border-radius: 4px;
                padding: 2px 4px;
                font-size: 9px;
                font-weight: bold;
                color: #2c3e50;
                min-width: 25px;
                max-width: 35px;
            }
            QPushButton:checked {
                background-color: #e74c3c;
                color: white;
                border-color: #c0392b;
            }
            QPushButton:hover {
                background-color: #d5dbdb;
                border-color: #95a5a6;
            }
            QPushButton:checked:hover {
                background-color: #c0392b;
            }
        """
        
        self.headlights_on_btn.setStyleSheet(headlight_style)
        self.headlights_off_btn.setStyleSheet(headlight_style)
        self.headlights_on_btn.setCheckable(True)
        self.headlights_off_btn.setCheckable(True)
        self.headlights_off_btn.setChecked(True)
        
        self.headlights_button_group = QButtonGroup()
        self.headlights_button_group.addButton(self.headlights_on_btn)
        self.headlights_button_group.addButton(self.headlights_off_btn)
        
        headlights_layout.addWidget(self.headlights_on_btn)
        headlights_layout.addWidget(self.headlights_off_btn)
        env_layout.addWidget(headlights_group)
        
        # Interior Lights ON/OFF buttons
        interior_group = QGroupBox("Interior Lights")
        interior_group.setMinimumHeight(50)
        interior_group.setStyleSheet("""
            QGroupBox {
                font-size: 13px;
                font-weight: bold;
                color: #2c3e50;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                margin: 4px 2px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 6px;
                background-color: palette(window);
            }
        """)
        interior_layout = QHBoxLayout(interior_group)
        interior_layout.setContentsMargins(8, 6, 8, 6)
        interior_layout.setSpacing(8)
        
        self.interior_on_btn = QPushButton("ON")
        self.interior_off_btn = QPushButton("OFF")
        
        interior_style = """
            QPushButton {
                background-color: #ecf0f1;
                border: 2px solid #bdc3c7;
                border-radius: 4px;
                padding: 2px 4px;
                font-size: 9px;
                font-weight: bold;
                color: #2c3e50;
                min-width: 25px;
                max-width: 35px;
            }
            QPushButton:checked {
                background-color: #e74c3c;
                color: white;
                border-color: #c0392b;
            }
            QPushButton:hover {
                background-color: #d5dbdb;
                border-color: #95a5a6;
            }
            QPushButton:checked:hover {
                background-color: #c0392b;
            }
        """
        
        self.interior_on_btn.setStyleSheet(interior_style)
        self.interior_off_btn.setStyleSheet(interior_style)
        self.interior_on_btn.setCheckable(True)
        self.interior_off_btn.setCheckable(True)
        self.interior_off_btn.setChecked(True)
        
        self.interior_button_group = QButtonGroup()
        self.interior_button_group.addButton(self.interior_on_btn)
        self.interior_button_group.addButton(self.interior_off_btn)
        
        interior_layout.addWidget(self.interior_on_btn)
        interior_layout.addWidget(self.interior_off_btn)
        env_layout.addWidget(interior_group)
        
        # Cabin Temperature section header
        temp_main_layout = QVBoxLayout()
        temp_main_layout.setSpacing(6)
        temp_label = QLabel("Cabin Temperature")
        temp_label.setAlignment(Qt.AlignCenter)
        temp_label.setMaximumHeight(20)
        temp_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: bold;
                color: #2c3e50;
                background: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 2px;
                padding: 0px 0px;
                margin: 0px 0px 0px 0px;
            }
        """)
        temp_main_layout.addWidget(temp_label)
        
        temp_control_layout = QHBoxLayout()
        temp_control_layout.setContentsMargins(0, 30, 0, 2)
        temp_control_layout.setSpacing(2)
        
        # Current temperature display (new)
        self.current_temp_display = QLabel("72°F")
        self.current_temp_display.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff, stop: 1 #f8f9fa);
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 13px;
                min-width: 60px;
                color: #2c3e50;
            }
        """)
        self.current_temp_display.setAlignment(Qt.AlignCenter)
        current_label = QLabel("Current:")
        current_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #34495e;
                padding: 2px 4px;
            }
        """)
        temp_control_layout.addWidget(current_label)
        temp_control_layout.addWidget(self.current_temp_display)
        
        temp_control_layout.addSpacing(10)
        set_label = QLabel("Set:")
        set_label.setFixedWidth(40)
        set_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #34495e;
                padding: 2px 4px;
            }
        """)
        temp_control_layout.addWidget(set_label)
        
        # Temperature input field with up/down buttons (like speed control)
        self.temp_input_field = QLineEdit("72°F")
        self.temp_input_field.setReadOnly(True)
        #self.temp_input_field.setMinimumWidth(30)
        self.temp_input_field.setMaximumWidth(60)
        self.temp_input_field.setStyleSheet("""
            QLineEdit {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff, stop: 1 #fff5f5);
                border: 2px solid #e74c3c;
                border-radius: 8px;
                padding: 4px 6px;
                font-size: 13px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        temp_control_layout.addWidget(self.temp_input_field)
        
        # Temperature up/down buttons
        temp_up_btn = QPushButton("▲")
        temp_down_btn = QPushButton("▼")
        temp_up_btn.setFixedSize(18, 13)
        temp_down_btn.setFixedSize(18, 13)
        temp_button_style = """
            QPushButton { 
                font-size: 9px; 
                padding: 0px;
                margin: 0px;
                background-color: palette(button);
                border: 1px solid palette(mid);
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: palette(light);
            }
            QPushButton:pressed {
                background-color: palette(mid);
            }
        """
        temp_up_btn.setStyleSheet(temp_button_style)
        temp_down_btn.setStyleSheet(temp_button_style)
        
        # Connect temperature buttons
        temp_up_btn.clicked.connect(self.increase_temperature)
        temp_down_btn.clicked.connect(self.decrease_temperature)
        
        # Store references for enabling/disabling
        self.temp_up_btn = temp_up_btn
        self.temp_down_btn = temp_down_btn
        
        # Temperature button layout
        temp_button_layout = QVBoxLayout()
        temp_button_layout.setContentsMargins(2, 0, 0, 0)
        temp_button_layout.setSpacing(1)
        temp_button_layout.addWidget(temp_up_btn)
        temp_button_layout.addWidget(temp_down_btn)
        
        temp_control_layout.addLayout(temp_button_layout)
        temp_control_layout.addStretch()
        
        temp_main_layout.addLayout(temp_control_layout)
        
        # Wrap temperature controls in container widget with height limit
        temp_container = QWidget()
        temp_container.setMaximumHeight(100)
        temp_container.setLayout(temp_main_layout)
        env_layout.addWidget(temp_container)
        
        # Door Control section header - compact
        door_label = QLabel("Door Control")
        door_label.setAlignment(Qt.AlignCenter)
        door_label.setMaximumHeight(18)
        door_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: bold;
                color: #2c3e50;
                background: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 1px;
                padding: 0px 0px;
                margin: 0px 0px 0px 0px;
            }
        """)
        env_layout.addWidget(door_label)
        door_layout = QHBoxLayout()
        door_layout.setContentsMargins(0, 30, 0, 0) 
        door_layout.setSpacing(20)
        
        left_door_layout = QVBoxLayout()
        left_door_layout.setSpacing(1)
        left_door_layout.setContentsMargins(0, 0, 0, 0)
        left_door_label = QLabel("Left Doors")
        left_door_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #34495e;
                padding: 0px 0px;
            }
        """)
        left_door_layout.addWidget(left_door_label)
        self.left_door_toggle = self.create_toggle_switch(False, is_door=True)
        left_door_layout.addWidget(self.left_door_toggle)
        left_door_layout.setAlignment(Qt.AlignCenter)
        
        right_door_layout = QVBoxLayout()
        right_door_layout.setSpacing(1)
        right_door_layout.setContentsMargins(0, 0, 0, 0)
        right_door_label = QLabel("Right Doors")
        right_door_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #34495e;
                padding: 0px 0px;
            }
        """)
        right_door_layout.addWidget(right_door_label)
        self.right_door_toggle = self.create_toggle_switch(False, is_door=True)
        right_door_layout.addWidget(self.right_door_toggle)
        right_door_layout.setAlignment(Qt.AlignCenter)
        
        door_layout.addLayout(left_door_layout)
        door_layout.addSpacing(14)
        door_layout.addLayout(right_door_layout)
        
        # Wrap door controls in container widget with height limit
        door_container = QWidget()
        door_container.setMaximumHeight(80)
        door_container.setLayout(door_layout)
        env_layout.addWidget(door_container)
        
        # Add stretch at the end to push all content upward
        env_layout.addStretch()
        
        # Train Information Group (row 1, col 1)
        train_info_group = QGroupBox("Train Information")
        #train_info_group.setMinimumWidth(10)
        train_info_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 1px;
                margin: 3px 0px;
                padding-top: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: palette(window);
            }
        """)
        train_info_layout = QVBoxLayout(train_info_group)
        train_info_layout.setSpacing(0)
        # Create info fields
        self.input_speed_field = self.create_info_field_with_controls(train_info_layout, "Input Speed (mph)")
        self.current_speed_field = self.create_info_field(train_info_layout, "Current speed (mph)", "")
        self.speed_limit_field = self.create_info_field(train_info_layout, "Speed limit (mph)", "")
        self.power_field = self.create_info_field(train_info_layout, "Power Output (kW)", "")
        self.authority_field = self.create_info_field(train_info_layout, "Authority (yards)", "")
        
        # Time and Service Brake (row 1, col 2)
        right_panel_widget = QWidget()
        #right_panel_widget.setMinimumWidth(100)
        right_panel_widget.setMaximumWidth(200)
        right_panel_layout = QVBoxLayout(right_panel_widget)
        right_panel_layout.setContentsMargins(0, 0, 0, 0)
        right_panel_layout.setSpacing(4)

        right_panel_widget = QWidget()
        right_panel_layout = QVBoxLayout(right_panel_widget)

        # Train ID dropdown
        train_id_group = QGroupBox("Train ID")
        train_id_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin: 2px 0px;
                padding-top: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 8px;
                background-color: palette(window);
            }
        """)
        train_id_layout = QVBoxLayout(train_id_group)

        self.train_id_label = QLabel("1")  # Will be updated from controller
        self.train_id_label.setAlignment(Qt.AlignCenter)
        self.train_id_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                padding: 5px;
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
            }
        """)
        train_id_layout.addWidget(self.train_id_label)
        right_panel_layout.addWidget(train_id_group)

        
        # Time
        time_group = QGroupBox("Time")
        time_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin: 2px 0px;
                padding-top: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 8px;
                background-color: palette(window);
            }
        """)
        time_layout = QVBoxLayout(time_group)
        self.time_label = QLabel("11:59 AM")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 8px;")
        self.time_label.setMinimumHeight(40)
        time_layout.setContentsMargins(4, 3, 4, 3)
        time_layout.addWidget(self.time_label)
        
        # Service Brake
        brake_group = QGroupBox("Service Brake")
        brake_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin: 2px 0px;
                padding-top: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 8px;
                background-color: palette(window);
            }
        """)
        brake_layout = QVBoxLayout(brake_group)
        
        brake_button_layout = QHBoxLayout()
        self.brake_on_btn = QPushButton("ON")
        self.brake_off_btn = QPushButton("OFF")
        
        brake_style = """
            QPushButton {
                background-color: #ecf0f1;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: bold;
                color: #2c3e50;
            }
            QPushButton:checked {
                background-color: #e74c3c;
                color: white;
                border-color: #c0392b;
            }
            QPushButton:hover {
                background-color: #d5dbdb;
                border-color: #95a5a6;
            }
            QPushButton:checked:hover {
                background-color: #c0392b;
            }
        """
        
        self.brake_on_btn.setStyleSheet(brake_style)
        self.brake_off_btn.setStyleSheet(brake_style)
        self.brake_on_btn.setCheckable(True)
        self.brake_off_btn.setCheckable(True)
        self.brake_off_btn.setChecked(True)
        
        self.brake_button_group = QButtonGroup()
        self.brake_button_group.addButton(self.brake_on_btn)
        self.brake_button_group.addButton(self.brake_off_btn)
        
        brake_button_layout.addWidget(self.brake_on_btn)
        brake_button_layout.addWidget(self.brake_off_btn)
        brake_layout.setContentsMargins(4, 3, 4, 3)
        brake_layout.addLayout(brake_button_layout)
        
        # PID Status
        pid_group = QGroupBox("PID Status")
        pid_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin: 2px 0px;
                padding-top: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 8px;
                background-color: palette(window);
            }
        """)
        pid_layout = QVBoxLayout(pid_group)
        
        self.kp_ki_status_label = QLabel("Kp/Ki: Not Set")
        self.kp_ki_status_label.setAlignment(Qt.AlignCenter)
        self.kp_ki_status_label.setMaximumHeight(30)
        self.kp_ki_status_label.setMinimumHeight(25)
        self.kp_ki_status_label.setStyleSheet("""
            QLabel {
                background-color: #ffcc00;
                color: #333333;
                font-weight: bold;
                font-size: 9px;
                padding: 2px;
                border: 1px solid #ff9900;
                border-radius: 3px;
            }
        """)
        pid_layout.setContentsMargins(4, 4, 4, 2)
        pid_layout.addWidget(self.kp_ki_status_label)
        
        right_panel_layout.addWidget(time_group)
        right_panel_layout.addWidget(brake_group)
        right_panel_layout.addWidget(pid_group)
        # Remove stretch completely to eliminate empty space
        
        # Add middle section widgets to grid
        main_layout.addWidget(env_group, 1, 0)
        main_layout.addWidget(train_info_group, 1, 1)
        main_layout.addWidget(right_panel_widget, 0, 2, 3, 1)
        
        # Bottom section (row 2)
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(8)
        
        # Emergency Brake
        self.emergency_brake_btn = QPushButton("Emergency Brake")
        self.emergency_brake_btn.setMinimumSize(180, 80)
        self.emergency_brake_btn.setMaximumWidth(350)
        self.emergency_brake_btn.setCheckable(True)
        self.update_emergency_brake_style()
        
        # Failures Group
        failures_group = QGroupBox("Failures")
        failures_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin: 3px 0px;
                padding-top: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: palette(window);
            }
        """)
        failures_layout = QHBoxLayout(failures_group)
        
        # Failure buttons with cross-platform styling
        failure_style_normal = """
            QPushButton {
                background-color: #ecf0f1;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px;
                color: #2c3e50;
            }
        """
        
        failure_style_active = """
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: 2px solid #c0392b;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px;
            }
        """
        
        self.engine_failure_btn = QPushButton("Engine Failure")
        self.engine_failure_btn.setMinimumSize(140, 60)
        self.engine_failure_btn.setEnabled(False)
        self.engine_failure_btn.setStyleSheet(failure_style_normal)
        
        self.signal_failure_btn = QPushButton("Signal Failure")
        self.signal_failure_btn.setMinimumSize(140, 60)
        self.signal_failure_btn.setEnabled(False)
        self.signal_failure_btn.setStyleSheet(failure_style_normal)
        
        self.brake_failure_btn = QPushButton("Brake Failure")
        self.brake_failure_btn.setMinimumSize(140, 60)
        self.brake_failure_btn.setEnabled(False)
        self.brake_failure_btn.setStyleSheet(failure_style_normal)
        
        # Store styles for reuse
        self.failure_style_normal = failure_style_normal
        self.failure_style_active = failure_style_active
        
        # Add equal spacing around failure buttons to center them
        failures_layout.addStretch(1)
        failures_layout.addWidget(self.engine_failure_btn)
        failures_layout.addStretch(1)
        failures_layout.addWidget(self.signal_failure_btn)
        failures_layout.addStretch(1)
        failures_layout.addWidget(self.brake_failure_btn)
        failures_layout.addStretch(1)
        
        bottom_layout.addWidget(self.emergency_brake_btn)
        bottom_layout.addWidget(failures_group, 1)  # Give failures group stretch priority
        
        # Add bottom section to grid
        main_layout.addWidget(bottom_widget, 2, 0, 1, 2)  # Span not all 
        
        # Set row and column stretch factors for tight layout
        main_layout.setRowStretch(0, 0)  # Top row: fixed size
        main_layout.setRowStretch(1, 1)  # Middle row: minimal stretch
        main_layout.setRowStretch(2, 0)  # Bottom row: fixed size
        main_layout.setColumnStretch(0, 0)  # Environmental controls
        main_layout.setColumnStretch(1, 1)  # Middle section (announcement, train info)
        main_layout.setColumnStretch(2, 0)  # Right panel (time, dropdown, etc.)
        
        # Connect signals
        self.connect_signals()
        
        # Initial state setup
        self.update_manual_controls_enabled()
    
    def on_resize(self, event):
        """Handle window resize events for dynamic scaling"""
        super().resizeEvent(event)
        
        # Get current window size
        width = self.width()
        height = self.height()
        
        # Dynamically adjust font sizes based on window size
        base_font_size = max(12, min(18, width // 80))
        title_font_size = base_font_size + 2
        
        # Update time label font size
        self.time_label.setStyleSheet(f"font-size: {base_font_size + 4}px; font-weight: bold; padding: 8px;")
        
        # Update emergency brake button size based on available space
        brake_width = min(400, max(250, width // 4))
        brake_height = min(100, max(70, height // 10))
        self.emergency_brake_btn.setMinimumSize(brake_width, brake_height)
        
        # Update failure button sizes
        failure_width = min(180, max(120, width // 10))
        failure_height = min(80, max(50, height // 12))
        
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
        #line_edit.setMinimumWidth(50)
        line_edit.setMaximumWidth(100)
        line_edit.setMinimumHeight(24)
        line_edit.setStyleSheet("""
            QLineEdit {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff, stop: 1 #f8f9fa);
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 13px;
                font-weight: bold;
                color: #2c3e50;
                selection-background-color: #3498db;
            }
            QLineEdit:focus {
                border-color: #3498db;
                background: white;
            }
        """)
        field_layout.addWidget(line_edit)
        
        # Up/Down buttons for manual mode - placed outside the input field
        up_btn = QPushButton("▲")
        down_btn = QPushButton("▼")
        up_btn.setFixedSize(18, 13)
        down_btn.setFixedSize(18, 13)
        button_style = """
            QPushButton { 
                font-size: 9px; 
                padding: 0px;
                margin: 0px;
                background-color: palette(button);
                border: 1px solid palette(mid);
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: palette(light);
            }
            QPushButton:pressed {
                background-color: palette(mid);
            }
        """
        up_btn.setStyleSheet(button_style)
        down_btn.setStyleSheet(button_style)
        
        # Connect buttons to speed change functions
        up_btn.clicked.connect(self.increase_manual_speed)
        down_btn.clicked.connect(self.decrease_manual_speed)
        
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
        #line_edit.setMinimumWidth(60)
        line_edit.setMaximumWidth(120)
        #line_edit.setMinimumHeight(24)
        line_edit.setStyleSheet("""
            QLineEdit {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff, stop: 1 #f8f9fa);
                border: 2px solid #bdc3c7;
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
        """Create a custom toggle switch widget"""
        toggle = QPushButton()
        toggle.setCheckable(True)
        toggle.setChecked(initial_state)
        toggle.setFixedSize(60, 28)  # Slightly larger
        
        def update_toggle_style():
            # Enhanced style with gradients and shadows
            if toggle.isChecked():
                toggle.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                            stop: 0 #27ae60, stop: 1 #2ecc71);
                        border: 2px solid #27ae60;
                        border-radius: 8px;
                        color: white;
                        font-weight: bold;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                            stop: 0 #2ecc71, stop: 1 #27ae60);
                    }
                """)
                toggle.setText("Open" if is_door else "ON")
            else:
                toggle.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                            stop: 0 #e74c3c, stop: 1 #c0392b);
                        border: 2px solid #c0392b;
                        border-radius: 8px;
                        color: white;
                        font-weight: bold;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                            stop: 0 #c0392b, stop: 1 #e74c3c);
                    }
                """)
                toggle.setText("Close" if is_door else "OFF")
        
        # Store the update function for later use
        toggle.update_style = update_toggle_style
        toggle.clicked.connect(update_toggle_style)
        update_toggle_style()
        return toggle
    
    def update_emergency_brake_style(self):
        """Update emergency brake button style and text based on its state"""
        if self.emergency_brake_btn.isChecked():
            self.emergency_brake_btn.setText("Release Emergency Brake")
            self.emergency_brake_btn.setStyleSheet("""
                QPushButton {
                    background-color: #8b0000;
                    color: white;
                    font-size: 16px;
                    font-weight: bold;
                    border: 3px solid #660000;
                    border-radius: 8px;
                }
            """)
        else:
            self.emergency_brake_btn.setText("Emergency Brake")
            self.emergency_brake_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    font-size: 18px;
                    font-weight: bold;
                    border: 3px solid #c0392b;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
    
    def setup_timer(self):
        """Setup real-time clock timer"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()
    
    def update_time(self):
        """Update the time label with current time"""
        current_time = get_time()
        time_text = current_time.strftime("%I:%M %p")
        self.time_label.setText(time_text)
    
    def connect_signals(self):
        """Connect button signals to handlers"""
        self.emergency_brake_btn.clicked.connect(self.emergency_brake_pressed)
        self.brake_button_group.buttonClicked.connect(self.service_brake_changed)
        self.control_button_group.buttonClicked.connect(self.control_mode_changed)
        self.headlights_button_group.buttonClicked.connect(self.headlights_changed)
        self.interior_button_group.buttonClicked.connect(self.interior_lights_changed)
        
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
            return
    
    def headlights_changed(self, button):
        """Handle headlights button change"""
        if self.train_controller:
            headlights_on = (button == self.headlights_on_btn)
            self.train_controller.toggle_headlights(headlights_on)
    
    def interior_lights_changed(self, button):
        """Handle interior lights button change"""
        if self.train_controller:
            interior_on = (button == self.interior_on_btn)
            self.train_controller.toggle_interior_lights(interior_on)
    
    def update_manual_controls_enabled(self):
        #helps us to enable/disable manual controls based on control mode.
        """Enable/disable manual controls based on control mode"""
        manual_mode = self.btn_manual.isChecked()
        
        # Enable/disable manual controls
        self.headlights_on_btn.setEnabled(manual_mode)
        self.headlights_off_btn.setEnabled(manual_mode)
        self.interior_on_btn.setEnabled(manual_mode)
        self.interior_off_btn.setEnabled(manual_mode)
        self.temp_up_btn.setEnabled(manual_mode)
        self.temp_down_btn.setEnabled(manual_mode)
        self.brake_on_btn.setEnabled(manual_mode)
        self.brake_off_btn.setEnabled(manual_mode)
        
        # Enable/disable speed control buttons
        self.speed_up_btn.setEnabled(manual_mode)
        self.speed_down_btn.setEnabled(manual_mode)
        
        # Update visual styles for disabled state
        self.update_headlight_button_style(manual_mode)
        self.update_interior_button_style(manual_mode)
        self.update_service_brake_button_style(manual_mode)
        
        # Emergency brake is ALWAYS enabled
        self.emergency_brake_btn.setEnabled(True)
    
    def update_door_controls_enabled(self, actual_speed, auto_mode):
        """Enable/disable door controls based on movement and mode"""
        manual_mode = not auto_mode
        is_moving = actual_speed > 0.1  # 0.1 mph threshold
        
        # Door controls are enabled only in manual mode AND when not moving
        door_controls_enabled = manual_mode and not is_moving
        
        self.left_door_toggle.setEnabled(door_controls_enabled)
        self.right_door_toggle.setEnabled(door_controls_enabled)
        
        # Update visual style for disabled state
        self.update_door_button_style(self.left_door_toggle, door_controls_enabled)
        self.update_door_button_style(self.right_door_toggle, door_controls_enabled)
    
    def update_door_button_style(self, toggle_button, enabled):
        """Update button visual style to indicate enabled/disabled state"""
        if enabled:
            # Normal enabled state - restore original toggle style
            if toggle_button.isChecked():
                toggle_button.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        border: 2px solid #45a049;
                        border-radius: 3px;
                        color: white;
                        font-weight: bold;
                    }
                """)
                toggle_button.setText("Open")
            else:
                toggle_button.setStyleSheet("""
                    QPushButton {
                        background-color: #f44336;
                        border: 2px solid #da190b;
                        border-radius: 3px;
                        color: white;
                        font-weight: bold;
                    }
                """)
                toggle_button.setText("Close")
        else:
            # Disabled state - darker, grayed out appearance
            if toggle_button.isChecked():
                toggle_button.setStyleSheet("""
                    QPushButton {
                        background-color: #2E7D32;
                        border: 2px solid #1B5E20;
                        border-radius: 3px;
                        color: #CCCCCC;
                        font-weight: bold;
                    }
                """)
                toggle_button.setText("Open")
            else:
                toggle_button.setStyleSheet("""
                    QPushButton {
                        background-color: #8B0000;
                        border: 2px solid #660000;
                        border-radius: 3px;
                        color: #CCCCCC;
                        font-weight: bold;
                    }
                """)
                toggle_button.setText("Close")
    
    def update_headlight_button_style(self, enabled):
        """Update headlight button visual style to indicate enabled/disabled state"""
        if enabled:
            # Normal enabled state - restore original style
            headlight_style = """
                QPushButton {
                    background-color: #ecf0f1;
                    border: 2px solid #bdc3c7;
                    border-radius: 4px;
                    padding: 2px 4px;
                    font-size: 9px;
                    font-weight: bold;
                    color: #2c3e50;
                    min-width: 25px;
                    max-width: 35px;
                }
                QPushButton:checked {
                    background-color: #e74c3c;
                    color: white;
                    border-color: #c0392b;
                }
                QPushButton:hover {
                    background-color: #d5dbdb;
                    border-color: #95a5a6;
                }
                QPushButton:checked:hover {
                    background-color: #c0392b;
                }
            """
        else:
            # Disabled state - slightly grayed out appearance
            headlight_style = """
                QPushButton {
                    background-color: #b0b0b0;
                    border: 2px solid #999999;
                    border-radius: 4px;
                    padding: 2px 4px;
                    font-size: 9px;
                    font-weight: bold;
                    color: #666666;
                    min-width: 25px;
                    max-width: 35px;
                }
                QPushButton:checked {
                    background-color: #e74c3c;
                    color: white;
                    border-color: #c0392b;
                }
                QPushButton:hover {
                    background-color: #b0b0b0;
                    border-color: #999999;
                }
                QPushButton:checked:hover {
                    background-color: #e74c3c;
                }
            """
        
        self.headlights_on_btn.setStyleSheet(headlight_style)
        self.headlights_off_btn.setStyleSheet(headlight_style)
    
    def update_interior_button_style(self, enabled):
        """Update interior light button visual style to indicate enabled/disabled state"""
        if enabled:
            # Normal enabled state - restore original style
            interior_style = """
                QPushButton {
                    background-color: #ecf0f1;
                    border: 2px solid #bdc3c7;
                    border-radius: 4px;
                    padding: 2px 4px;
                    font-size: 9px;
                    font-weight: bold;
                    color: #2c3e50;
                    min-width: 25px;
                    max-width: 35px;
                }
                QPushButton:checked {
                    background-color: #e74c3c;
                    color: white;
                    border-color: #c0392b;
                }
                QPushButton:hover {
                    background-color: #d5dbdb;
                    border-color: #95a5a6;
                }
                QPushButton:checked:hover {
                    background-color: #c0392b;
                }
            """
        else:
            # Disabled state - slightly grayed out appearance
            interior_style = """
                QPushButton {
                    background-color: #b0b0b0;
                    border: 2px solid #999999;
                    border-radius: 4px;
                    padding: 2px 4px;
                    font-size: 9px;
                    font-weight: bold;
                    color: #666666;
                    min-width: 25px;
                    max-width: 35px;
                }
                QPushButton:checked {
                    background-color: #e74c3c;
                    color: white;
                    border-color: #c0392b;
                }
                QPushButton:hover {
                    background-color: #b0b0b0;
                    border-color: #999999;
                }
                QPushButton:checked:hover {
                    background-color: #e74c3c;
                }
            """
        
        self.interior_on_btn.setStyleSheet(interior_style)
        self.interior_off_btn.setStyleSheet(interior_style)
    
    def update_service_brake_button_style(self, enabled):
        """Update service brake button visual style to indicate enabled/disabled state"""
        if enabled:
            # Normal enabled state - restore original style
            brake_style = """
                QPushButton {
                    background-color: #ecf0f1;
                    border: 2px solid #bdc3c7;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 12px;
                    font-weight: bold;
                    color: #2c3e50;
                }
                QPushButton:checked {
                    background-color: #e74c3c;
                    color: white;
                    border-color: #c0392b;
                }
                QPushButton:hover {
                    background-color: #d5dbdb;
                    border-color: #95a5a6;
                }
                QPushButton:checked:hover {
                    background-color: #c0392b;
                }
            """
        else:
            # Disabled state - slightly grayed out appearance
            brake_style = """
                QPushButton {
                    background-color: #b0b0b0;
                    border: 2px solid #999999;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 12px;
                    font-weight: bold;
                    color: #666666;
                }
                QPushButton:checked {
                    background-color: #e74c3c;
                    color: white;
                    border-color: #c0392b;
                }
                QPushButton:hover {
                    background-color: #b0b0b0;
                    border-color: #999999;
                }
                QPushButton:checked:hover {
                    background-color: #e74c3c;
                }
            """
        
        self.brake_on_btn.setStyleSheet(brake_style)
        self.brake_off_btn.setStyleSheet(brake_style)
    
    def update_kp_ki_status(self, kp: float, ki: float, kp_ki_set: bool):
        """Update the Kp/Ki status indicator"""
        if not kp_ki_set:
            self.kp_ki_status_label.setText("Waiting for\nKp/Ki")
            self.kp_ki_status_label.setStyleSheet("""
                QLabel {
                    background-color: #ff6b6b;
                    color: white;
                    font-weight: bold;
                    font-size: 10px;
                    padding: 5px;
                    border: 1px solid #ff5252;
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
                    font-size: 10px;
                    padding: 5px;
                    border: 1px solid #45a049;
                    border-radius: 3px;
                }
            """)
    
    def update_train_id_options(self, available_train_ids):
        """Update the train ID dropdown with available train IDs from train model input"""
        if not available_train_ids:
            return
            
        try:
            # Convert to string list and sort
            train_id_strings = [str(tid) for tid in sorted(available_train_ids)]
            
            # Get current selection
            current_text = self.train_id_combo.currentText()
            
            # Temporarily disconnect signal to prevent errors during update
            self.train_id_combo.currentIndexChanged.disconnect()
            
            # Clear and repopulate
            self.train_id_combo.clear()
            self.train_id_combo.addItems(train_id_strings)
            
            # Try to maintain current selection if it's still available
            if current_text in train_id_strings:
                index = train_id_strings.index(current_text)
                self.train_id_combo.setCurrentIndex(index)
                self.selected_train_id = int(current_text)
            else:
                # Default to first item if current selection is no longer available
                self.train_id_combo.setCurrentIndex(0)
                if train_id_strings:
                    self.selected_train_id = int(train_id_strings[0])
                    print(f"Train ID selection changed to: {self.selected_train_id}")
            
            # Reconnect signal
            self.train_id_combo.currentIndexChanged.connect(self.on_train_id_changed)
            
        except (ValueError, IndexError) as e:
            print(f"Error updating train ID options: {e}")
            # Ensure signal is reconnected even if there's an error
            try:
                self.train_id_combo.currentIndexChanged.connect(self.on_train_id_changed)
            except:
                pass
            
    def get_driver_input(self) -> DriverInput:
        """Return a DriverInput object using current widget states"""
        return DriverInput(
            auto_mode=self.btn_auto.isChecked(),
            headlights_on=self.headlights_on_btn.isChecked(),
            interior_lights_on=self.interior_on_btn.isChecked(),
            door_left_open=self.left_door_toggle.isChecked(),
            door_right_open=self.right_door_toggle.isChecked(),
            set_temperature=self.manual_set_temperature,
            emergency_brake=self.emergency_brake_active,
            set_speed=self.manual_set_speed,
            service_brake=self.service_brake_active,
            train_id=self.train_controller.train_id if self.train_controller else 1
        )
    
    
    def set_next_station(self, station_text: str):
        """Update the next station announcement"""
        self.next_station_line.setText(station_text)
    
    def set_failures(self, engine=False, signal=False, brake=False):
        """Update failure indicator buttons based on backend status"""
        # Engine failure
        if engine:
            self.engine_failure_btn.setStyleSheet(self.failure_style_active)
        else:
            self.engine_failure_btn.setStyleSheet(self.failure_style_normal)
        
        # Signal failure
        if signal:
            self.signal_failure_btn.setStyleSheet(self.failure_style_active)
        else:
            self.signal_failure_btn.setStyleSheet(self.failure_style_normal)
        
        # Brake failure
        if brake:
            self.brake_failure_btn.setStyleSheet(self.failure_style_active)
        else:
            self.brake_failure_btn.setStyleSheet(self.failure_style_normal)
    
    def get_failure_states(self):
        """Get current failure button states (for backward compatibility)"""
        return {
            'engine_failure': "CC0000" in self.engine_failure_btn.styleSheet(),
            'signal_failure': "CC0000" in self.signal_failure_btn.styleSheet(),
            'brake_failure': "CC0000" in self.brake_failure_btn.styleSheet()
        }


def main():
    app = QApplication(sys.argv)
    window = DriverUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()