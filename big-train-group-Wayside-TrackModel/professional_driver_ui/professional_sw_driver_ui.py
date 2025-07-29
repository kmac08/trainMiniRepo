#!/usr/bin/env python3
"""
Professional Software Driver UI - Fixed Version
Location: professional_driver_ui/professional_sw_driver_ui.py

A professional driver interface with fixed layouts, consistent fonts, and proper spacing.
"""

import sys
import os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QTimer, QTime, pyqtSignal
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QFont, QPalette, QColor

# Add paths for backend imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, '..', 'train_controller_sw'))
sys.path.append(os.path.join(current_dir, '..', 'train_controller_sw', 'controller'))

# Import universal time function from Master Interface
try:
    from Master_Interface.master_control import get_time
except ImportError:
    print("Warning: Master Interface not available. Using system time.")
    from datetime import datetime
    def get_time():
        return datetime.now()

# Import backend data types and controller
try:
    from controller.data_types import DriverInput, TrainModelOutput, TrainModelInput, OutputToDriver
    from controller.train_controller import TrainController
except ImportError:
    print("Warning: Backend controller not available. Running in standalone mode.")
    DriverInput = TrainModelOutput = TrainModelInput = OutputToDriver = TrainController = None


class ProfessionalSoftwareDriverUI(QMainWindow):
    """Professional Software Driver UI with fixed layouts and consistent styling"""
    
    # Signals for backend communication
    driver_input_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        
        # Initialize state variables
        self.train_controller = None
        self.train_id = "1"
        
        # Control states
        self.auto_mode = True
        self.manual_set_speed = 0.0
        self.manual_set_temperature = 72.0
        self.emergency_brake_active = False  # Driver's emergency brake input
        self.service_brake_active = False
        self.headlights_on = False
        self.interior_lights_on = False
        self.door_left_open = False
        self.door_right_open = False
        
        # UI setup
        self.setup_ui()
        self.setup_timer()
        
    def setup_ui(self):
        """Set up the main UI layout with fixed spacing and fonts"""
        self.setWindowTitle("Professional Train Driver Interface - Software Controller")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout with adaptive margins
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(18)
        
        # Apply global styles
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QWidget {
                font-family: "Segoe UI", Arial, sans-serif;
            }
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QLabel {
                color: #333;
            }
            QPushButton {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 4px 8px;
                background-color: white;
                min-height: 30px;
            }
            QPushButton:hover {
                background-color: #e9e9e9;
            }
            QPushButton:pressed {
                background-color: #ddd;
            }
        """)
        
        # Top panel
        self.create_top_panel(main_layout)
        
        # Main content area with better spacing
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)
        
        # Left panel - Controls (30% width)
        left_panel = self.create_left_panel()
        content_layout.addWidget(left_panel, 3)
        
        # Center panel - Train Status (40% width)
        center_panel = self.create_center_panel()
        content_layout.addWidget(center_panel, 4)
        
        # Right panel - System Status (30% width)
        right_panel = self.create_right_panel()
        content_layout.addWidget(right_panel, 3)
        
        main_layout.addWidget(content_widget, 1)
        
        # Bottom panel
        self.create_bottom_panel(main_layout)
        
    def create_top_panel(self, layout):
        """Create top panel with time, train ID, and next station"""
        top_frame = QFrame()
        top_layout = QHBoxLayout(top_frame)
        top_layout.setContentsMargins(8, 8, 8, 8)
        top_layout.setSpacing(8)
        
        # System Time (compact)
        time_widget = QWidget()
        time_layout = QVBoxLayout(time_widget)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(2)
        
        time_label = QLabel("System Time")
        time_label.setStyleSheet("font-size: 12pt; color: #666;")
        self.time_display = QLabel("12:00 PM")
        self.time_display.setStyleSheet("font-size: 16pt; font-weight: bold; color: #333;")
        
        time_layout.addWidget(time_label)
        time_layout.addWidget(self.time_display)
        top_layout.addWidget(time_widget)
        
        # Train ID (compact)
        train_id_widget = QWidget()
        train_id_layout = QVBoxLayout(train_id_widget)
        train_id_layout.setContentsMargins(0, 0, 0, 0)
        train_id_layout.setSpacing(2)
        
        train_id_label = QLabel("Train ID")
        train_id_label.setStyleSheet("font-size: 12pt; color: #666;")
        self.train_id_display = QLabel(self.train_id)
        self.train_id_display.setStyleSheet("font-size: 16pt; font-weight: bold; color: #2E7D32;")
        
        train_id_layout.addWidget(train_id_label)
        train_id_layout.addWidget(self.train_id_display)
        top_layout.addWidget(train_id_widget)
        
        # Next Station (expandable)
        station_widget = QWidget()
        station_layout = QVBoxLayout(station_widget)
        station_layout.setContentsMargins(0, 0, 0, 0)
        station_layout.setSpacing(2)
        
        station_label = QLabel("Next Station")
        station_label.setStyleSheet("font-size: 12pt; color: #666;")
        self.next_station_display = QLabel("No Station Information")
        self.next_station_display.setStyleSheet("""
            font-size: 14pt; 
            font-weight: bold; 
            color: #333;
            background-color: #f9f9f9;
            padding: 4px 8px;
            border-radius: 3px;
        """)
        self.next_station_display.setWordWrap(True)
        
        station_layout.addWidget(station_label)
        station_layout.addWidget(self.next_station_display)
        top_layout.addWidget(station_widget, 1)  # Expandable
        
        layout.addWidget(top_frame)
        
    def create_left_panel(self):
        """Create left panel with control mode and manual controls"""
        left_widget = QWidget()
        left_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(20)  # Increased spacing between sections
        
        # Control Mode Section
        mode_frame = QFrame()
        mode_layout = QVBoxLayout(mode_frame)
        mode_layout.setContentsMargins(8, 8, 8, 8)
        mode_layout.setSpacing(6)
        
        mode_title = QLabel("Control Mode")
        mode_title.setStyleSheet("font-size: 14pt; font-weight: 600; color: #333;")
        mode_layout.addWidget(mode_title)
        
        # Mode buttons with proper spacing
        mode_button_layout = QHBoxLayout()
        mode_button_layout.setSpacing(6)
        
        self.auto_mode_btn = QPushButton("AUTO")
        self.manual_mode_btn = QPushButton("MANUAL")
        
        # Button group for mutual exclusion
        self.mode_button_group = QButtonGroup()
        self.mode_button_group.addButton(self.auto_mode_btn, 0)
        self.mode_button_group.addButton(self.manual_mode_btn, 1)
        
        self.auto_mode_btn.setCheckable(True)
        self.manual_mode_btn.setCheckable(True)
        self.auto_mode_btn.setChecked(True)
        
        # Style mode buttons
        mode_button_style = """
            QPushButton {
                min-height: 40px;
                font-size: 12pt;
                font-weight: bold;
                border: 2px solid #ccc;
                border-radius: 5px;
            }
            QPushButton:checked {
                background-color: #4CAF50;
                color: white;
                border-color: #4CAF50;
            }
        """
        self.auto_mode_btn.setStyleSheet(mode_button_style)
        self.manual_mode_btn.setStyleSheet(mode_button_style)
        
        self.auto_mode_btn.clicked.connect(self.set_auto_mode)
        self.manual_mode_btn.clicked.connect(self.set_manual_mode)
        
        mode_button_layout.addWidget(self.auto_mode_btn)
        mode_button_layout.addWidget(self.manual_mode_btn)
        mode_layout.addLayout(mode_button_layout)
        
        # Removed mode status label - button state is clear enough
        
        left_layout.addWidget(mode_frame)
        
        # Manual Controls Section
        controls_frame = QFrame()
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setContentsMargins(8, 8, 8, 8)
        controls_layout.setSpacing(6)
        
        controls_title = QLabel("Manual Controls")
        controls_title.setStyleSheet("font-size: 14pt; font-weight: 600; color: #333;")
        controls_layout.addWidget(controls_title)
        
        # Speed control
        speed_group = QWidget()
        speed_layout = QVBoxLayout(speed_group)
        speed_layout.setContentsMargins(0, 0, 0, 0)
        speed_layout.setSpacing(4)
        
        speed_label = QLabel("Speed Control")
        speed_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #555;")
        speed_layout.addWidget(speed_label)
        
        speed_display_layout = QHBoxLayout()
        speed_display_layout.setSpacing(4)
        
        speed_value_label = QLabel("Set Speed:")
        speed_value_label.setStyleSheet("font-size: 12pt; color: #666;")
        self.speed_value_display = QLabel("0.0 mph")
        self.speed_value_display.setStyleSheet("font-size: 14pt; font-weight: bold; color: #333;")
        
        speed_display_layout.addWidget(speed_value_label)
        speed_display_layout.addWidget(self.speed_value_display)
        speed_display_layout.addStretch()
        speed_layout.addLayout(speed_display_layout)
        
        speed_button_layout = QHBoxLayout()
        speed_button_layout.setSpacing(4)
        
        self.speed_down_btn = QPushButton("Speed -")
        self.speed_up_btn = QPushButton("Speed +")
        self.speed_down_btn.clicked.connect(self.decrease_speed)
        self.speed_up_btn.clicked.connect(self.increase_speed)
        
        # Initial styling for speed buttons
        speed_button_style = """
            QPushButton {
                min-height: 30px;
                font-size: 11pt;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: white;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #999;
                border-color: #ddd;
            }
        """
        self.speed_down_btn.setStyleSheet(speed_button_style)
        self.speed_up_btn.setStyleSheet(speed_button_style)
        
        speed_button_layout.addWidget(self.speed_down_btn)
        speed_button_layout.addWidget(self.speed_up_btn)
        speed_layout.addLayout(speed_button_layout)
        
        controls_layout.addWidget(speed_group)
        
        # Temperature control
        temp_group = QWidget()
        temp_layout = QVBoxLayout(temp_group)
        temp_layout.setContentsMargins(0, 0, 0, 0)
        temp_layout.setSpacing(4)
        
        temp_label = QLabel("Temperature Control")
        temp_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #555;")
        temp_layout.addWidget(temp_label)
        
        temp_display_layout = QHBoxLayout()
        temp_display_layout.setSpacing(4)
        
        temp_value_label = QLabel("Set Temp:")
        temp_value_label.setStyleSheet("font-size: 12pt; color: #666;")
        self.temp_value_display = QLabel("72°F")
        self.temp_value_display.setStyleSheet("font-size: 14pt; font-weight: bold; color: #333;")
        
        temp_display_layout.addWidget(temp_value_label)
        temp_display_layout.addWidget(self.temp_value_display)
        temp_display_layout.addStretch()
        temp_layout.addLayout(temp_display_layout)
        
        temp_button_layout = QHBoxLayout()
        temp_button_layout.setSpacing(4)
        
        self.temp_down_btn = QPushButton("Temp -")
        self.temp_up_btn = QPushButton("Temp +")
        self.temp_down_btn.clicked.connect(self.decrease_temperature)
        self.temp_up_btn.clicked.connect(self.increase_temperature)
        
        # Apply same styling to temperature buttons
        self.temp_down_btn.setStyleSheet(speed_button_style)
        self.temp_up_btn.setStyleSheet(speed_button_style)
        
        temp_button_layout.addWidget(self.temp_down_btn)
        temp_button_layout.addWidget(self.temp_up_btn)
        temp_layout.addLayout(temp_button_layout)
        
        controls_layout.addWidget(temp_group)
        
        left_layout.addWidget(controls_frame)
        
        # Environment Controls
        env_frame = QFrame()
        env_layout = QVBoxLayout(env_frame)
        env_layout.setContentsMargins(8, 8, 8, 8)
        env_layout.setSpacing(6)
        
        env_title = QLabel("Environment Controls")
        env_title.setStyleSheet("font-size: 14pt; font-weight: 600; color: #333;")
        env_layout.addWidget(env_title)
        
        # Use a grid for better organization
        env_grid = QGridLayout()
        env_grid.setSpacing(4)
        
        self.headlights_btn = QPushButton("Headlights")
        self.interior_lights_btn = QPushButton("Interior Lights")
        self.left_door_btn = QPushButton("Left Door")
        self.right_door_btn = QPushButton("Right Door")
        
        self.headlights_btn.setCheckable(True)
        self.interior_lights_btn.setCheckable(True)
        self.left_door_btn.setCheckable(True)
        self.right_door_btn.setCheckable(True)
        
        # Environment buttons will be styled dynamically based on mode and state
        for btn in [self.headlights_btn, self.interior_lights_btn, self.left_door_btn, self.right_door_btn]:
            btn.setMinimumHeight(35)
            
        self.headlights_btn.clicked.connect(self.toggle_headlights)
        self.interior_lights_btn.clicked.connect(self.toggle_interior_lights)
        self.left_door_btn.clicked.connect(self.toggle_left_door)
        self.right_door_btn.clicked.connect(self.toggle_right_door)
        
        env_grid.addWidget(self.headlights_btn, 0, 0)
        env_grid.addWidget(self.interior_lights_btn, 0, 1)
        env_grid.addWidget(self.left_door_btn, 1, 0)
        env_grid.addWidget(self.right_door_btn, 1, 1)
        
        env_layout.addLayout(env_grid)
        left_layout.addWidget(env_frame)
        
        left_layout.addStretch()
        return left_widget
        
    def create_center_panel(self):
        """Create center panel with train status information"""
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(8, 8, 8, 8)
        center_layout.setSpacing(15)
        
        # Speed and Power Information
        speed_frame = QFrame()
        speed_layout = QVBoxLayout(speed_frame)
        speed_layout.setContentsMargins(8, 8, 8, 8)
        speed_layout.setSpacing(6)
        
        speed_title = QLabel("Speed & Power Information")
        speed_title.setStyleSheet("font-size: 14pt; font-weight: 600; color: #333;")
        speed_layout.addWidget(speed_title)
        
        # Use grid for organized display
        speed_grid = QGridLayout()
        speed_grid.setSpacing(6)
        
        # Create value display pairs
        speed_pairs = [
            ("Current Speed:", "0.0 mph", "current_speed"),
            ("Set Speed:", "0.0 mph", "set_speed"),
            ("Speed Limit:", "40.0 mph", "speed_limit"),
            ("Power Output:", "0.0 kW", "power_output")
        ]
        
        for i, (label_text, initial_value, attr_name) in enumerate(speed_pairs):
            row, col = divmod(i, 2)
            
            pair_widget = QWidget()
            pair_layout = QVBoxLayout(pair_widget)
            pair_layout.setContentsMargins(4, 4, 4, 4)
            pair_layout.setSpacing(2)
            
            label = QLabel(label_text)
            label.setStyleSheet("font-size: 12pt; color: #666;")
            
            value = QLabel(initial_value)
            value.setStyleSheet("""
                font-size: 16pt; 
                font-weight: bold; 
                color: #333;
                background-color: #f9f9f9;
                padding: 4px 8px;
                border-radius: 3px;
                border: 1px solid #ddd;
            """)
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            pair_layout.addWidget(label)
            pair_layout.addWidget(value)
            
            speed_grid.addWidget(pair_widget, row, col)
            setattr(self, f"{attr_name}_display", value)
            
        speed_layout.addLayout(speed_grid)
        center_layout.addWidget(speed_frame)
        
        # System Status
        status_frame = QFrame()
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(8, 8, 8, 8)
        status_layout.setSpacing(6)
        
        status_title = QLabel("System Status")
        status_title.setStyleSheet("font-size: 14pt; font-weight: 600; color: #333;")
        status_layout.addWidget(status_title)
        
        status_grid = QGridLayout()
        status_grid.setSpacing(6)
        
        # Authority and Temperature
        status_pairs = [
            ("Authority:", "0.0 yards", "authority"),
            ("Current Temp:", "72°F", "current_temp")
        ]
        
        for i, (label_text, initial_value, attr_name) in enumerate(status_pairs):
            pair_widget = QWidget()
            pair_layout = QVBoxLayout(pair_widget)
            pair_layout.setContentsMargins(4, 4, 4, 4)
            pair_layout.setSpacing(2)
            
            label = QLabel(label_text)
            label.setStyleSheet("font-size: 12pt; color: #666;")
            
            value = QLabel(initial_value)
            value.setStyleSheet("""
                font-size: 16pt; 
                font-weight: bold; 
                color: #333;
                background-color: #f9f9f9;
                padding: 4px 8px;
                border-radius: 3px;
                border: 1px solid #ddd;
            """)
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            pair_layout.addWidget(label)
            pair_layout.addWidget(value)
            
            status_grid.addWidget(pair_widget, 0, i)
            setattr(self, f"{attr_name}_display", value)
            
        status_layout.addLayout(status_grid)
        center_layout.addWidget(status_frame)
        
        # Brake System
        brake_frame = QFrame()
        brake_layout = QVBoxLayout(brake_frame)
        brake_layout.setContentsMargins(8, 8, 8, 8)
        brake_layout.setSpacing(6)
        
        brake_title = QLabel("Brake System")
        brake_title.setStyleSheet("font-size: 14pt; font-weight: 600; color: #333;")
        brake_layout.addWidget(brake_title)
        
        # Service brake controls
        service_brake_layout = QHBoxLayout()
        service_brake_layout.setSpacing(4)
        
        service_brake_label = QLabel("Service Brake:")
        service_brake_label.setStyleSheet("font-size: 12pt; color: #666;")
        
        # OFF and ON buttons for manual mode
        self.service_brake_off_btn = QPushButton("OFF")
        self.service_brake_on_btn = QPushButton("ON")
        
        # Default styling for OFF/ON buttons
        self.service_brake_off_btn.setStyleSheet("""
            QPushButton {
                min-height: 30px;
                font-size: 11pt;
                font-weight: bold;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #999;
                border: 1px solid #ddd;
            }
        """)
        
        self.service_brake_on_btn.setStyleSheet("""
            QPushButton {
                min-height: 30px;
                font-size: 11pt;
                font-weight: bold;
                background-color: rgba(255, 255, 255, 0.3);
                color: #333;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.5);
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #999;
                border: 1px solid #ddd;
            }
        """)
        
        self.service_brake_off_btn.clicked.connect(lambda: self.set_service_brake(False))
        self.service_brake_on_btn.clicked.connect(lambda: self.set_service_brake(True))
        
        service_brake_layout.addWidget(service_brake_label)
        service_brake_layout.addWidget(self.service_brake_off_btn)
        service_brake_layout.addWidget(self.service_brake_on_btn)
        service_brake_layout.addStretch()
        
        brake_layout.addLayout(service_brake_layout)
        
        # Removed brake status label - button colors already show state clearly
        
        center_layout.addWidget(brake_frame)
        center_layout.addStretch()
        return center_widget
        
    def create_right_panel(self):
        """Create right panel with system status and failures"""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(15)
        
        # Controller Status
        controller_frame = QFrame()
        controller_layout = QVBoxLayout(controller_frame)
        controller_layout.setContentsMargins(8, 8, 8, 8)
        controller_layout.setSpacing(6)
        
        controller_title = QLabel("Controller Status")
        controller_title.setStyleSheet("font-size: 14pt; font-weight: 600; color: #333;")
        controller_layout.addWidget(controller_title)
        
        self.pid_status_display = QLabel("Waiting for Kp/Ki")
        self.pid_status_display.setStyleSheet("""
            font-size: 12pt; 
            font-weight: bold; 
            color: #FF9800;
            background-color: #FFF3E0;
            padding: 8px;
            border-radius: 3px;
            border: 1px solid #FFB74D;
        """)
        self.pid_status_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pid_status_display.setWordWrap(True)
        controller_layout.addWidget(self.pid_status_display)
        
        right_layout.addWidget(controller_frame)
        
        # System Health - Expanded with better spacing
        health_frame = QFrame()
        health_layout = QVBoxLayout(health_frame)
        health_layout.setContentsMargins(12, 12, 12, 12)
        health_layout.setSpacing(15)  # Increased spacing
        
        health_title = QLabel("System Health")
        health_title.setStyleSheet("font-size: 14pt; font-weight: 600; color: #333; margin-bottom: 10px;")
        health_layout.addWidget(health_title)
        
        # Create individual status indicators with frames
        self.engine_status = self.create_health_indicator("Engine", True)
        self.signal_status = self.create_health_indicator("Signal", True)
        self.brake_system_status = self.create_health_indicator("Brake System", True)
        
        health_layout.addWidget(self.engine_status)
        health_layout.addWidget(self.signal_status)
        health_layout.addWidget(self.brake_system_status)
        
        # Add extra spacing at the bottom
        health_layout.addSpacing(20)
        
        right_layout.addWidget(health_frame)
        right_layout.addStretch()
        return right_widget
        
    def create_health_indicator(self, system_name, is_ok):
        """Create a health indicator with its own frame"""
        indicator_frame = QFrame()
        indicator_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                margin: 2px;
            }
        """)
        
        indicator_layout = QVBoxLayout(indicator_frame)
        indicator_layout.setContentsMargins(15, 12, 15, 12)
        indicator_layout.setSpacing(5)
        
        # System name label
        name_label = QLabel(system_name)
        name_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #555;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Status label
        status_label = QLabel("OK" if is_ok else "FAILED")
        if is_ok:
            status_label.setStyleSheet("""
                font-size: 14pt; 
                font-weight: bold; 
                color: #4CAF50;
                background-color: #E8F5E8;
                padding: 8px 12px;
                border-radius: 5px;
                border: 1px solid #81C784;
            """)
        else:
            status_label.setStyleSheet("""
                font-size: 14pt; 
                font-weight: bold; 
                color: #f44336;
                background-color: #ffebee;
                padding: 8px 12px;
                border-radius: 5px;
                border: 1px solid #ef5350;
            """)
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        indicator_layout.addWidget(name_label)
        indicator_layout.addWidget(status_label)
        
        # Store the status label for updates
        setattr(indicator_frame, 'status_label', status_label)
        setattr(indicator_frame, 'system_name', system_name)
        
        return indicator_frame
        
    def create_bottom_panel(self, layout):
        """Create bottom panel with emergency brake and system summary"""
        bottom_frame = QFrame()
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(8, 8, 8, 8)
        bottom_layout.setSpacing(12)
        
        # Emergency Brake - single, prominent button
        emergency_section = QVBoxLayout()
        emergency_section.setSpacing(4)
        
        emergency_label = QLabel("EMERGENCY BRAKE")
        emergency_label.setStyleSheet("""
            font-size: 14pt; 
            font-weight: bold; 
            color: #d32f2f;
        """)
        emergency_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.emergency_brake_btn = QPushButton("EMERGENCY BRAKE")
        self.emergency_brake_btn.setCheckable(True)
        self.emergency_brake_btn.setMinimumHeight(60)
        self.emergency_brake_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: 2px solid #d32f2f;
                border-radius: 5px;
                font-size: 14pt;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:checked {
                background-color: #b71c1c;
                border-color: #b71c1c;
            }
        """)
        self.emergency_brake_btn.clicked.connect(self.toggle_emergency_brake)
        
        emergency_section.addWidget(emergency_label)
        emergency_section.addWidget(self.emergency_brake_btn)
        bottom_layout.addLayout(emergency_section)
        
        # System Summary
        summary_section = QVBoxLayout()
        summary_section.setSpacing(4)
        
        summary_label = QLabel("System Summary")
        summary_label.setStyleSheet("font-size: 14pt; font-weight: 600; color: #333;")
        
        self.system_summary = QLabel()
        self.system_summary.setStyleSheet("""
            font-size: 12pt;
            color: #333;
            background-color: #f9f9f9;
            padding: 8px;
            border-radius: 3px;
            border: 1px solid #ddd;
        """)
        self.system_summary.setWordWrap(True)
        
        summary_section.addWidget(summary_label)
        summary_section.addWidget(self.system_summary)
        summary_section.addStretch()
        bottom_layout.addLayout(summary_section, 1)
        
        layout.addWidget(bottom_frame)
        
    def setup_timer(self):
        """Set up timers for UI updates"""
        # Main update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(100)  # 10 FPS
        
        # Time display timer
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time_display)
        self.time_timer.start(1000)  # 1 FPS
        self.update_time_display()
        
    def update_time_display(self):
        """Update the time display"""
        try:
            current_time = get_time()
            time_text = current_time.strftime("%I:%M %p")
            self.time_display.setText(time_text)
        except:
            self.time_display.setText("--:-- --")
            
    def set_train_controller(self, train_controller):
        """Set the train controller reference"""
        self.train_controller = train_controller
        if train_controller and hasattr(train_controller, 'train_id'):
            self.train_id = str(train_controller.train_id)
            self.train_id_display.setText(self.train_id)
            print(f"DEBUG: Train controller set with ID: {self.train_id}")
            print(f"DEBUG: Train controller next_station_number: {getattr(train_controller, 'next_station_number', 'NOT SET')}")
            
            # Try to get initial station info
            try:
                driver_output = train_controller.get_output_to_driver()
                print(f"DEBUG: Initial station info - next_station: '{driver_output.next_station}', station_side: '{driver_output.station_side}'")
                if driver_output.next_station and driver_output.station_side:
                    station_text = f"{driver_output.next_station} (Platform: {driver_output.station_side.title()})"
                    self.next_station_display.setText(station_text)
                    print(f"DEBUG: Set initial station display to: {station_text}")
            except Exception as e:
                print(f"DEBUG: Error getting initial station info: {e}")
            
    def update_ui(self):
        """Main UI update function"""
        if self.train_controller:
            self.update_from_train_controller()
        self.update_control_states()
        self.update_system_summary()
        
    def update_from_train_controller(self):
        """Update UI from train controller data"""
        if not self.train_controller:
            return
            
        try:
            # Get controller output
            driver_output = self.train_controller.get_output_to_driver()
            
            # Update displays
            self.current_speed_display.setText(f"{driver_output.actual_speed:.1f} mph")
            self.set_speed_display.setText(f"{driver_output.input_speed:.1f} mph")
            self.speed_limit_display.setText(f"{driver_output.speed_limit:.1f} mph")
            self.power_output_display.setText(f"{driver_output.power_output:.1f} kW")
            self.authority_display.setText(f"{driver_output.authority:.1f} yards")
            self.current_temp_display.setText(f"{driver_output.current_cabin_temp:.0f}°F")
            
            # Update mode from controller
            self.auto_mode = driver_output.auto_mode
            self.auto_mode_btn.setChecked(driver_output.auto_mode)
            self.manual_mode_btn.setChecked(not driver_output.auto_mode)
            
            # Update manual settings displays
            if driver_output.auto_mode:
                # In auto mode, show what the controller has set
                self.temp_value_display.setText(f"{driver_output.set_cabin_temp:.0f}°F")
            else:
                # In manual mode, show the manual setting
                self.temp_value_display.setText(f"{self.manual_set_temperature:.0f}°F")
            
            # Update control states from controller output
            self.headlights_on = driver_output.headlights_on
            self.interior_lights_on = driver_output.interior_lights_on
            self.door_left_open = driver_output.left_door_open
            self.door_right_open = driver_output.right_door_open
            self.service_brake_active = driver_output.service_brake_active
            
            # Update emergency brake display based on controller state
            # The button should show the actual emergency brake state from the controller
            # but we need to distinguish between driver input and controller output
            if driver_output.emergency_brake_active:
                self.emergency_brake_btn.setChecked(True)
            else:
                # If controller says emergency brake is off, uncheck the button
                # and reset the driver's input state if it was only due to faults
                self.emergency_brake_btn.setChecked(False)
                # Reset driver input if emergency brake was only due to faults
                # (this allows the emergency brake to be released when faults clear)
                if self.emergency_brake_active and not driver_output.emergency_brake_active:
                    print(f"DEBUG: Resetting emergency brake - driver had: {self.emergency_brake_active}, controller has: {driver_output.emergency_brake_active}")
                    self.emergency_brake_active = False
            
            # Update failures
            self.update_failure_status(self.engine_status, "Engine", driver_output.engine_failure)
            self.update_failure_status(self.signal_status, "Signal", driver_output.signal_failure)
            self.update_failure_status(self.brake_system_status, "Brake System", driver_output.brake_failure)
            
            # Update PID status
            if driver_output.kp_ki_set:
                self.pid_status_display.setText(f"Controller Active\nKp: {driver_output.kp:.1f}, Ki: {driver_output.ki:.1f}")
                self.pid_status_display.setStyleSheet("""
                    font-size: 12pt; 
                    font-weight: bold; 
                    color: #4CAF50;
                    background-color: #E8F5E8;
                    padding: 8px;
                    border-radius: 3px;
                    border: 1px solid #81C784;
                """)
            else:
                self.pid_status_display.setText("Waiting for Kp/Ki")
                self.pid_status_display.setStyleSheet("""
                    font-size: 12pt; 
                    font-weight: bold; 
                    color: #FF9800;
                    background-color: #FFF3E0;
                    padding: 8px;
                    border-radius: 3px;
                    border: 1px solid #FFB74D;
                """)
                
            # Update next station
            if driver_output.next_station and driver_output.station_side:
                station_text = f"{driver_output.next_station} (Platform: {driver_output.station_side.title()})"
                self.next_station_display.setText(station_text)
                print(f"DEBUG: Next station updated to: {station_text}")
            else:
                self.next_station_display.setText("No Station Information")
                print(f"DEBUG: No station info - next_station: '{driver_output.next_station}', station_side: '{driver_output.station_side}'")
                
        except Exception as e:
            print(f"Error updating from train controller: {e}")
            
    def update_failure_status(self, indicator_frame, system_name, has_failure):
        """Update failure status for health indicator"""
        status_label = indicator_frame.status_label
        
        if has_failure:
            status_label.setText("FAILED")
            status_label.setStyleSheet("""
                font-size: 14pt; 
                font-weight: bold; 
                color: #f44336;
                background-color: #ffebee;
                padding: 8px 12px;
                border-radius: 5px;
                border: 1px solid #ef5350;
            """)
            # Update frame border color for failed systems
            indicator_frame.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 2px solid #f44336;
                    border-radius: 8px;
                    margin: 2px;
                }
            """)
        else:
            status_label.setText("OK")
            status_label.setStyleSheet("""
                font-size: 14pt; 
                font-weight: bold; 
                color: #4CAF50;
                background-color: #E8F5E8;
                padding: 8px 12px;
                border-radius: 5px;
                border: 1px solid #81C784;
            """)
            # Update frame border color for healthy systems
            indicator_frame.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 2px solid #4CAF50;
                    border-radius: 8px;
                    margin: 2px;
                }
            """)
            
    def update_control_states(self):
        """Update control button states and enable/disable logic"""
        # Mode status removed - button states are clear enough
            
        # Enable/disable manual controls
        manual_enabled = not self.auto_mode
        self.speed_up_btn.setEnabled(manual_enabled)
        self.speed_down_btn.setEnabled(manual_enabled)
        self.temp_up_btn.setEnabled(manual_enabled)
        self.temp_down_btn.setEnabled(manual_enabled)
        self.headlights_btn.setEnabled(manual_enabled)
        self.interior_lights_btn.setEnabled(manual_enabled)
        self.service_brake_off_btn.setEnabled(manual_enabled)
        self.service_brake_on_btn.setEnabled(manual_enabled)
        
        # Door controls - only enabled in manual mode and when stopped
        current_speed = 0.0
        if self.train_controller:
            try:
                driver_output = self.train_controller.get_output_to_driver()
                current_speed = driver_output.actual_speed
            except:
                pass
                
        doors_enabled = manual_enabled and current_speed <= 0.1
        self.left_door_btn.setEnabled(doors_enabled)
        self.right_door_btn.setEnabled(doors_enabled)
        
        # Update displays
        self.speed_value_display.setText(f"{self.manual_set_speed:.1f} mph")
        # Temperature display is updated in update_from_train_controller
        
        # Update environment button states and styles
        self.update_environment_button(self.headlights_btn, self.headlights_on, manual_enabled, "Headlights")
        self.update_environment_button(self.interior_lights_btn, self.interior_lights_on, manual_enabled, "Interior Lights")
        self.update_environment_button(self.left_door_btn, self.door_left_open, doors_enabled, "Left Door")
        self.update_environment_button(self.right_door_btn, self.door_right_open, doors_enabled, "Right Door")
        
        # Update service brake button styling
        self.update_service_brake_buttons()
            
    def update_environment_button(self, button, is_active, is_enabled, name):
        """Update environment button styling based on state and mode"""
        button.setChecked(is_active)
        button.setEnabled(is_enabled)
        
        if is_active:
            if is_enabled:
                # Manual mode - active (green)
                button.setStyleSheet("""
                    QPushButton {
                        min-height: 35px;
                        font-size: 11pt;
                        font-weight: bold;
                        background-color: #4CAF50;
                        color: white;
                        border: 2px solid #45a049;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                """)
            else:
                # Auto mode - active but disabled (yellow)
                button.setStyleSheet("""
                    QPushButton {
                        min-height: 35px;
                        font-size: 11pt;
                        font-weight: bold;
                        background-color: #FF9800;
                        color: white;
                        border: 2px solid #F57C00;
                        border-radius: 3px;
                    }
                """)
        else:
            if is_enabled:
                # Manual mode - inactive (normal)
                button.setStyleSheet("""
                    QPushButton {
                        min-height: 35px;
                        font-size: 11pt;
                        background-color: white;
                        color: #333;
                        border: 1px solid #ccc;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #f0f0f0;
                    }
                """)
            else:
                # Auto mode - inactive and disabled (grayed out)
                button.setStyleSheet("""
                    QPushButton {
                        min-height: 35px;
                        font-size: 11pt;
                        background-color: #f5f5f5;
                        color: #999;
                        border: 1px solid #ddd;
                        border-radius: 3px;
                    }
                """)
            
    def update_system_summary(self):
        """Update the system summary display"""
        mode_text = "AUTO" if self.auto_mode else "MANUAL"
        speed_text = "0.0"
        status_text = "READY"
        
        if self.train_controller:
            try:
                driver_output = self.train_controller.get_output_to_driver()
                speed_text = f"{driver_output.actual_speed:.1f}"
                
                if driver_output.engine_failure or driver_output.signal_failure or driver_output.brake_failure:
                    status_text = "SYSTEM FAILURE"
                elif self.emergency_brake_active:
                    status_text = "EMERGENCY BRAKE"
                elif driver_output.actual_speed > 0.1:
                    status_text = "MOVING"
                else:
                    status_text = "READY"
            except:
                pass
                
        summary_text = f"Mode: {mode_text} | Speed: {speed_text} mph | Status: {status_text}"
        self.system_summary.setText(summary_text)
        
    # Control handlers
    def set_auto_mode(self):
        """Set auto mode"""
        self.auto_mode = True
        
    def set_manual_mode(self):
        """Set manual mode"""
        self.auto_mode = False
        
    def increase_speed(self):
        """Increase manual speed setting"""
        if not self.auto_mode:
            self.manual_set_speed = min(self.manual_set_speed + 1.0, 100.0)
            
    def decrease_speed(self):
        """Decrease manual speed setting"""
        if not self.auto_mode:
            self.manual_set_speed = max(self.manual_set_speed - 1.0, 0.0)
            
    def increase_temperature(self):
        """Increase temperature setting"""
        if not self.auto_mode:
            self.manual_set_temperature = min(self.manual_set_temperature + 1.0, 100.0)
            
    def decrease_temperature(self):
        """Decrease temperature setting"""
        if not self.auto_mode:
            self.manual_set_temperature = max(self.manual_set_temperature - 1.0, 32.0)
            
    def toggle_headlights(self):
        """Toggle headlights"""
        if not self.auto_mode:
            self.headlights_on = not self.headlights_on
            
    def toggle_interior_lights(self):
        """Toggle interior lights"""
        if not self.auto_mode:
            self.interior_lights_on = not self.interior_lights_on
            
    def toggle_left_door(self):
        """Toggle left door"""
        if not self.auto_mode:
            # Check if train is stopped
            current_speed = 0.0
            if self.train_controller:
                try:
                    driver_output = self.train_controller.get_output_to_driver()
                    current_speed = driver_output.actual_speed
                except:
                    pass
                    
            if current_speed <= 0.1:
                self.door_left_open = not self.door_left_open
                
    def toggle_right_door(self):
        """Toggle right door"""
        if not self.auto_mode:
            # Check if train is stopped
            current_speed = 0.0
            if self.train_controller:
                try:
                    driver_output = self.train_controller.get_output_to_driver()
                    current_speed = driver_output.actual_speed
                except:
                    pass
                    
            if current_speed <= 0.1:
                self.door_right_open = not self.door_right_open
                
    def set_service_brake(self, active):
        """Set service brake state"""
        if not self.auto_mode:
            self.service_brake_active = active
        self.update_service_brake_buttons()
            
    def update_service_brake_buttons(self):
        """Update service brake button styling based on state and mode"""
        manual_enabled = not self.auto_mode
        
        if self.service_brake_active:
            # ON button is active
            if manual_enabled:
                # Manual mode - full red color
                on_color = "#f44336"
                on_hover = "#d32f2f"
            else:
                # Auto mode - darker red
                on_color = "#b71c1c"
                on_hover = "#b71c1c"
                
            self.service_brake_on_btn.setStyleSheet(f"""
                QPushButton {{
                    min-height: 30px;
                    font-size: 11pt;
                    font-weight: bold;
                    background-color: {on_color};
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 4px 12px;
                }}
                QPushButton:hover {{
                    background-color: {on_hover};
                }}
                QPushButton:disabled {{
                    background-color: {on_color};
                    color: white;
                }}
            """)
            
            # OFF button is inactive
            self.service_brake_off_btn.setStyleSheet("""
                QPushButton {
                    min-height: 30px;
                    font-size: 11pt;
                    font-weight: bold;
                    background-color: rgba(255, 255, 255, 0.3);
                    color: #333;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    padding: 4px 12px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.5);
                }
                QPushButton:disabled {
                    background-color: rgba(255, 255, 255, 0.3);
                    color: #333;
                    border: 1px solid #ccc;
                }
            """)
        else:
            # OFF button is active
            if manual_enabled:
                # Manual mode - full green color
                off_color = "#4CAF50"
                off_hover = "#45a049"
            else:
                # Auto mode - darker green
                off_color = "#2e7d32"
                off_hover = "#2e7d32"
                
            self.service_brake_off_btn.setStyleSheet(f"""
                QPushButton {{
                    min-height: 30px;
                    font-size: 11pt;
                    font-weight: bold;
                    background-color: {off_color};
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 4px 12px;
                }}
                QPushButton:hover {{
                    background-color: {off_hover};
                }}
                QPushButton:disabled {{
                    background-color: {off_color};
                    color: white;
                }}
            """)
            
            # ON button is inactive
            self.service_brake_on_btn.setStyleSheet("""
                QPushButton {
                    min-height: 30px;
                    font-size: 11pt;
                    font-weight: bold;
                    background-color: rgba(255, 255, 255, 0.3);
                    color: #333;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    padding: 4px 12px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.5);
                }
                QPushButton:disabled {
                    background-color: rgba(255, 255, 255, 0.3);
                    color: #333;
                    border: 1px solid #ccc;
                }
            """)
            
    def toggle_emergency_brake(self):
        """Toggle emergency brake - always available"""
        self.emergency_brake_active = not self.emergency_brake_active
        # Update button appearance immediately
        self.emergency_brake_btn.setChecked(self.emergency_brake_active)
        
    def reset_emergency_brake(self):
        """Reset emergency brake (for external control)"""
        self.emergency_brake_active = False
        self.emergency_brake_btn.setChecked(False)
        
    def get_driver_input(self):
        """Return DriverInput object with current states"""
        if DriverInput:
            return DriverInput(
                auto_mode=self.auto_mode,
                headlights_on=self.headlights_on,
                interior_lights_on=self.interior_lights_on,
                door_left_open=self.door_left_open,
                door_right_open=self.door_right_open,
                set_temperature=self.manual_set_temperature,
                emergency_brake=self.emergency_brake_active,
                set_speed=self.manual_set_speed,
                service_brake=self.service_brake_active,
                train_id=self.train_id
            )
        return None
        
    def set_next_station(self, station_text):
        """Update next station display"""
        self.next_station_display.setText(station_text)
        
    def is_emergency_brake_active(self) -> bool:
        """Check if emergency brake is currently active"""
        return self.emergency_brake_active
        
    def closeEvent(self, event):
        """Handle window close event"""
        print("Professional Software Driver UI closing...")
        event.accept()


def main():
    """Main function for standalone testing"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Professional Train Driver Interface")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Train Control Systems")
    
    # Create and show the window
    window = ProfessionalSoftwareDriverUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()