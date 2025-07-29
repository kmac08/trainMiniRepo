#!/usr/bin/env python3
"""
Professional Hardware Driver UI
Location: professional_driver_ui/professional_hw_driver_ui.py

A completely redesigned, professional-grade driver interface for the hardware train controller.
Features modern UI design, GPIO integration, responsive layout, and enhanced readability across 
Windows and Mac platforms.
"""

import sys
import os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QTimer, QTime, pyqtSignal
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap, QPainter, QLinearGradient

# Add paths for backend imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, '..', 'train_controller_hw'))
sys.path.append(os.path.join(current_dir, '..', 'train_controller_hw', 'controller'))

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

# Import GPIO emulator
try:
    from train_controller_hw.gpio_emulator import create_gpio_emulator
    GPIO_EMULATOR_AVAILABLE = True
except ImportError:
    print("Warning: GPIO emulator not available. Running in simulation mode.")
    GPIO_EMULATOR_AVAILABLE = False


class ModernCard(QFrame):
    """A modern card widget with shadow effect and rounded corners"""
    
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.NoFrame)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 16px;
                border: 2px solid #E5E7EB;
            }
        """)
        self.setup_layout(title)
        
    def setup_layout(self, title):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(18)
        
        if title:
            title_label = QLabel(title)
            title_label.setStyleSheet("""
                QLabel {
                    font-size: 20px;
                    font-weight: 600;
                    color: #1F2937;
                    margin-bottom: 15px;
                    border: none;
                }
            """)
            layout.addWidget(title_label)
        
        self.content_layout = layout


class StatusIndicator(QLabel):
    """A modern status indicator with colored background and larger text"""
    
    def __init__(self, text="", status="normal", parent=None):
        super().__init__(text, parent)
        self.status = status
        self.setMinimumHeight(50)
        self.update_style()
        
    def set_status(self, status, text=None):
        self.status = status
        if text:
            self.setText(text)
        self.update_style()
        
    def update_style(self):
        colors = {
            'normal': {'bg': '#F3F4F6', 'text': '#374151', 'border': '#D1D5DB'},
            'success': {'bg': '#D1FAE5', 'text': '#065F46', 'border': '#10B981'},
            'warning': {'bg': '#FEF3C7', 'text': '#92400E', 'border': '#F59E0B'},
            'error': {'bg': '#FEE2E2', 'text': '#991B1B', 'border': '#EF4444'},
            'info': {'bg': '#DBEAFE', 'text': '#1E40AF', 'border': '#3B82F6'},
            'connected': {'bg': '#D1FAE5', 'text': '#065F46', 'border': '#10B981'},
            'disconnected': {'bg': '#FEE2E2', 'text': '#991B1B', 'border': '#EF4444'}
        }
        
        color = colors.get(self.status, colors['normal'])
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color['bg']};
                color: {color['text']};
                border: 3px solid {color['border']};
                border-radius: 12px;
                padding: 12px 16px;
                font-weight: 700;
                font-size: 16px;
                qproperty-alignment: AlignCenter;
            }}
        """)


class ModernButton(QPushButton):
    """A modern button with hover effects and different styles"""
    
    def __init__(self, text="", button_type="primary", parent=None):
        super().__init__(text, parent)
        self.button_type = button_type
        self.setMinimumHeight(55)
        self.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.update_style()
        
    def update_style(self):
        styles = {
            'primary': {
                'bg': '#3B82F6', 'hover': '#2563EB', 'text': 'white',
                'border': '#3B82F6', 'shadow': 'rgba(59, 130, 246, 0.5)'
            },
            'success': {
                'bg': '#10B981', 'hover': '#059669', 'text': 'white',
                'border': '#10B981', 'shadow': 'rgba(16, 185, 129, 0.5)'
            },
            'warning': {
                'bg': '#F59E0B', 'hover': '#D97706', 'text': 'white',
                'border': '#F59E0B', 'shadow': 'rgba(245, 158, 11, 0.5)'
            },
            'danger': {
                'bg': '#EF4444', 'hover': '#DC2626', 'text': 'white',
                'border': '#EF4444', 'shadow': 'rgba(239, 68, 68, 0.5)'
            },
            'secondary': {
                'bg': '#F3F4F6', 'hover': '#E5E7EB', 'text': '#374151',
                'border': '#D1D5DB', 'shadow': 'rgba(0, 0, 0, 0.1)'
            },
            'emergency': {
                'bg': '#DC2626', 'hover': '#B91C1C', 'text': 'white',
                'border': '#DC2626', 'shadow': 'rgba(220, 38, 38, 0.8)'
            },
            'gpio_active': {
                'bg': '#059669', 'hover': '#047857', 'text': 'white',
                'border': '#059669', 'shadow': 'rgba(5, 150, 105, 0.5)'
            },
            'gpio_inactive': {
                'bg': '#6B7280', 'hover': '#4B5563', 'text': 'white',
                'border': '#6B7280', 'shadow': 'rgba(107, 114, 128, 0.5)'
            }
        }
        
        style = styles.get(self.button_type, styles['primary'])
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {style['bg']};
                color: {style['text']};
                border: 3px solid {style['border']};
                border-radius: 12px;
                padding: 15px 25px;
                font-weight: 600;
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {style['hover']};
                transform: translateY(-2px);
            }}
            QPushButton:pressed {{
                transform: translateY(0px);
            }}
            QPushButton:disabled {{
                background-color: #F3F4F6;
                color: #9CA3AF;
                border-color: #E5E7EB;
            }}
        """)


class DataDisplay(QLabel):
    """A modern data display widget with large, readable text"""
    
    def __init__(self, label="", value="", unit="", parent=None):
        super().__init__(parent)
        self.label_text = label
        self.value_text = value
        self.unit_text = unit
        self.setMinimumHeight(120)
        self.update_display()
        
    def set_value(self, value, unit=None):
        self.value_text = str(value)
        if unit:
            self.unit_text = unit
        self.update_display()
        
    def update_display(self):
        self.setText(f"""
            <div style='text-align: center; margin: 10px;'>
                <div style='font-size: 18px; color: #6B7280; margin-bottom: 8px; font-weight: 500;'>
                    {self.label_text}
                </div>
                <div style='font-size: 36px; font-weight: bold; color: #111827; margin-bottom: 5px;'>
                    {self.value_text}
                </div>
                <div style='font-size: 16px; color: #9CA3AF; font-weight: 600;'>
                    {self.unit_text}
                </div>
            </div>
        """)
        self.setStyleSheet("""
            QLabel {
                background-color: #F9FAFB;
                border: 3px solid #E5E7EB;
                border-radius: 16px;
                padding: 20px;
                min-height: 120px;
            }
        """)


class GPIOStatusWidget(QFrame):
    """A specialized widget for GPIO status display"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.NoFrame)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Hardware GPIO Status")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: 600;
            color: #1F2937;
            margin-bottom: 10px;
        """)
        layout.addWidget(title)
        
        # Connection status
        self.connection_status = StatusIndicator("Pi: DISCONNECTED", "disconnected")
        layout.addWidget(self.connection_status)
        
        # GPIO inputs grid
        gpio_grid = QGridLayout()
        gpio_grid.setSpacing(8)
        
        # Create GPIO status indicators
        self.gpio_indicators = {}
        gpio_pins = [
            ("Mode", "AUTO"),
            ("Headlights", "OFF"),
            ("Interior", "OFF"),
            ("Emergency", "OFF"),
            ("Service Brake", "OFF"),
            ("Left Door", "CLOSED"),
            ("Right Door", "CLOSED"),
            ("Speed", "0.0 mph"),
            ("Temperature", "72°F")
        ]
        
        for i, (name, initial_status) in enumerate(gpio_pins):
            indicator = StatusIndicator(f"{name}: {initial_status}", "normal")
            indicator.setMinimumHeight(40)
            indicator.setStyleSheet(indicator.styleSheet().replace("font-size: 16px", "font-size: 14px"))
            row, col = divmod(i, 3)
            gpio_grid.addWidget(indicator, row, col)
            self.gpio_indicators[name.lower().replace(" ", "_")] = indicator
            
        layout.addLayout(gpio_grid)
        
        # Style the frame
        self.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 2px solid #E2E8F0;
                border-radius: 12px;
                padding: 10px;
            }
        """)
        
    def update_connection_status(self, connected):
        """Update GPIO connection status"""
        if connected:
            self.connection_status.set_status("connected", "Pi: CONNECTED")
        else:
            self.connection_status.set_status("disconnected", "Pi: DISCONNECTED")
            
    def update_gpio_status(self, gpio_name, status, text=None):
        """Update specific GPIO status"""
        if gpio_name in self.gpio_indicators:
            indicator = self.gpio_indicators[gpio_name]
            if text:
                indicator.setText(text)
            indicator.set_status(status)


class ProfessionalHardwareDriverUI(QMainWindow):
    """Professional Hardware Driver UI with modern design and GPIO integration"""
    
    # Signals for backend communication
    driver_input_changed = pyqtSignal()
    
    def __init__(self, serial_port='COM4', baud_rate=9600):
        super().__init__()
        
        # Store GPIO parameters
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        
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
        self.train_controller = None
        self.train_id = "1"
        
        # GPIO states
        self.gpio_inputs = {
            'headlights_on': False,
            'interior_lights_on': False,
            'emergency_brake': False,
            'service_brake': False,
            'door_left_open': False,
            'door_right_open': False
        }
        
        # Control states
        self.gpio_auto_mode = True
        self.manual_set_speed = 0.0
        self.manual_set_temperature = 72.0
        self.emergency_brake_active = False
        self.service_brake_active = False
        
        # GPIO previous states for edge detection
        self.gpio_prev_states = {}
        
        # Initialize GPIO
        self.setup_gpio_emulator()
        
        # UI setup
        self.setup_ui()
        self.setup_timer()
        self.apply_global_styles()
        
    def setup_gpio_emulator(self):
        """Initialize GPIO emulator for remote Pi communication"""
        if not GPIO_EMULATOR_AVAILABLE:
            print("GPIO emulator not available - running in simulation mode")
            for pin_name in self.GPIO_PINS:
                self.gpio_prev_states[pin_name] = True
            return
            
        # Create GPIO emulator instance
        try:
            self.gpio_emulator = create_gpio_emulator(self.serial_port, self.baud_rate)
            self.setup_gpio_callbacks()
            
            # Initialize previous states to HIGH (button not pressed)
            for pin_name in self.GPIO_PINS:
                self.gpio_prev_states[pin_name] = True
                
            print(f"GPIO emulator initialized on {self.serial_port} at {self.baud_rate} baud")
        except Exception as e:
            print(f"Failed to initialize GPIO emulator: {e}")
            self.gpio_emulator = None
            
    def setup_gpio_callbacks(self):
        """Setup callbacks for GPIO button presses from Pi"""
        if not hasattr(self, 'gpio_emulator') or not self.gpio_emulator:
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
        
    # GPIO callback handlers
    def on_headlight_press(self):
        """Handle headlight button press"""
        if not self.get_gpio_auto_mode():
            self.gpio_inputs['headlights_on'] = not self.gpio_inputs['headlights_on']
            print(f"GPIO: Headlights {'ON' if self.gpio_inputs['headlights_on'] else 'OFF'}")
            
    def on_interior_light_press(self):
        """Handle interior light button press"""
        if not self.get_gpio_auto_mode():
            self.gpio_inputs['interior_lights_on'] = not self.gpio_inputs['interior_lights_on']
            print(f"GPIO: Interior lights {'ON' if self.gpio_inputs['interior_lights_on'] else 'OFF'}")
            
    def on_emergency_brake_press(self):
        """Handle emergency brake button press"""
        self.emergency_brake_active = not self.emergency_brake_active
        print(f"GPIO: Emergency brake {'ACTIVE' if self.emergency_brake_active else 'INACTIVE'}")
        
    def on_service_brake_press(self):
        """Handle service brake button press"""
        if not self.get_gpio_auto_mode():
            self.service_brake_active = not self.service_brake_active
            print(f"GPIO: Service brake {'ACTIVE' if self.service_brake_active else 'INACTIVE'}")
            
    def on_left_door_press(self):
        """Handle left door button press"""
        if not self.get_gpio_auto_mode():
            if self.train_controller and self.train_controller.get_output_to_driver().actual_speed > 0.1:
                print("GPIO: Door operation blocked - train is moving")
                return
            self.gpio_inputs['door_left_open'] = not self.gpio_inputs['door_left_open']
            print(f"GPIO: Left door {'OPEN' if self.gpio_inputs['door_left_open'] else 'CLOSED'}")
            
    def on_right_door_press(self):
        """Handle right door button press"""
        if not self.get_gpio_auto_mode():
            if self.train_controller and self.train_controller.get_output_to_driver().actual_speed > 0.1:
                print("GPIO: Door operation blocked - train is moving")
                return
            self.gpio_inputs['door_right_open'] = not self.gpio_inputs['door_right_open']
            print(f"GPIO: Right door {'OPEN' if self.gpio_inputs['door_right_open'] else 'CLOSED'}")
            
    def on_speed_up_press(self):
        """Handle speed up button press"""
        if not self.get_gpio_auto_mode():
            self.manual_set_speed = min(self.manual_set_speed + 1.0, 100.0)
            print(f"GPIO: Speed set to {self.manual_set_speed:.1f} mph")
            
    def on_speed_down_press(self):
        """Handle speed down button press"""
        if not self.get_gpio_auto_mode():
            self.manual_set_speed = max(self.manual_set_speed - 1.0, 0.0)
            print(f"GPIO: Speed set to {self.manual_set_speed:.1f} mph")
            
    def on_temp_up_press(self):
        """Handle temperature up button press"""
        if not self.get_gpio_auto_mode():
            self.manual_set_temperature = min(self.manual_set_temperature + 1.0, 100.0)
            print(f"GPIO: Temperature set to {self.manual_set_temperature:.1f}°F")
            
    def on_temp_down_press(self):
        """Handle temperature down button press"""
        if not self.get_gpio_auto_mode():
            self.manual_set_temperature = max(self.manual_set_temperature - 1.0, 32.0)
            print(f"GPIO: Temperature set to {self.manual_set_temperature:.1f}°F")
            
    def get_gpio_auto_mode(self):
        """Get current auto mode state from GPIO emulator"""
        if hasattr(self, 'gpio_emulator') and self.gpio_emulator:
            return self.gpio_emulator.get_auto_mode()
        return self.gpio_auto_mode
        
    def is_gpio_connected(self):
        """Check if GPIO emulator is connected to Pi"""
        if hasattr(self, 'gpio_emulator') and self.gpio_emulator:
            return self.gpio_emulator.is_connected()
        return False
        
    def read_gpio_inputs(self):
        """Update GPIO inputs and mode"""
        if hasattr(self, 'gpio_emulator') and self.gpio_emulator:
            self.gpio_auto_mode = self.gpio_emulator.get_auto_mode()
        
    def setup_ui(self):
        """Set up the main UI layout"""
        self.setWindowTitle("Professional Train Driver Interface - Hardware Controller")
        self.setMinimumSize(1600, 1000)
        self.resize(1800, 1200)
        
        # Set application icon
        self.setWindowIcon(self.create_app_icon())
        
        # Central widget with main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Header section
        self.create_header_section(main_layout)
        
        # Content sections in a grid layout
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setSpacing(20)
        
        # Left column - GPIO status and mode
        left_column = self.create_left_column()
        content_layout.addWidget(left_column, 1)
        
        # Center column - Train status
        center_column = self.create_center_column()
        content_layout.addWidget(center_column, 2)
        
        # Right column - System status
        right_column = self.create_right_column()
        content_layout.addWidget(right_column, 1)
        
        main_layout.addWidget(content_widget, 1)
        
        # Footer with emergency controls
        self.create_footer_section(main_layout)
        
    def create_app_icon(self):
        """Create a custom application icon"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(220, 38, 38))  # Red background for hardware
        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "H")
        painter.end()
        return QtGui.QIcon(pixmap)
        
    def create_header_section(self, layout):
        """Create the header section with time, train ID, and next station"""
        header_card = ModernCard()
        header_layout = QHBoxLayout()
        header_card.content_layout.addLayout(header_layout)
        
        # Time display
        time_section = QVBoxLayout()
        time_label = QLabel("System Time")
        time_label.setStyleSheet("font-size: 18px; color: #6B7280; font-weight: 500;")
        self.time_display = QLabel("12:00 PM")
        self.time_display.setStyleSheet("""
            font-size: 40px; 
            font-weight: bold; 
            color: #111827;
            margin: 8px 0;
        """)
        time_section.addWidget(time_label, alignment=Qt.AlignmentFlag.AlignCenter)
        time_section.addWidget(self.time_display, alignment=Qt.AlignmentFlag.AlignCenter)
        header_layout.addLayout(time_section)
        
        # Separator
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.VLine)
        separator1.setStyleSheet("color: #E5E7EB; background-color: #E5E7EB; max-width: 2px;")
        header_layout.addWidget(separator1)
        
        # Train ID display
        train_id_section = QVBoxLayout()
        train_id_label = QLabel("Train ID")
        train_id_label.setStyleSheet("font-size: 18px; color: #6B7280; font-weight: 500;")
        self.train_id_display = QLabel(self.train_id)
        self.train_id_display.setStyleSheet("""
            font-size: 40px; 
            font-weight: bold; 
            color: #DC2626;
            margin: 8px 0;
        """)
        train_id_section.addWidget(train_id_label, alignment=Qt.AlignmentFlag.AlignCenter)
        train_id_section.addWidget(self.train_id_display, alignment=Qt.AlignmentFlag.AlignCenter)
        header_layout.addLayout(train_id_section)
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.VLine)
        separator2.setStyleSheet("color: #E5E7EB; background-color: #E5E7EB; max-width: 2px;")
        header_layout.addWidget(separator2)
        
        # Next station display
        station_section = QVBoxLayout()
        station_label = QLabel("Next Station")
        station_label.setStyleSheet("font-size: 18px; color: #6B7280; font-weight: 500;")
        self.next_station_display = QLabel("No Station Information")
        self.next_station_display.setStyleSheet("""
            font-size: 22px; 
            font-weight: 600; 
            color: #374151;
            margin: 8px 0;
            padding: 15px;
            background-color: #F3F4F6;
            border-radius: 12px;
        """)
        self.next_station_display.setWordWrap(True)
        station_section.addWidget(station_label, alignment=Qt.AlignmentFlag.AlignCenter)
        station_section.addWidget(self.next_station_display)
        header_layout.addLayout(station_section)
        
        layout.addWidget(header_card)
        
    def create_left_column(self):
        """Create the left column with GPIO status and control mode"""
        column_widget = QWidget()
        column_layout = QVBoxLayout(column_widget)
        column_layout.setSpacing(20)
        
        # GPIO Status Section
        self.gpio_status_widget = GPIOStatusWidget()
        column_layout.addWidget(self.gpio_status_widget)
        
        # Control Mode Section
        mode_card = ModernCard("Control Mode")
        mode_layout = QVBoxLayout()
        
        # Mode indicator
        self.mode_status = StatusIndicator("AUTO MODE ACTIVE", "success")
        self.mode_status.setMinimumHeight(60)
        mode_layout.addWidget(self.mode_status)
        
        # Mode description
        mode_description = QLabel("""
            <div style='font-size: 14px; color: #6B7280; text-align: center; line-height: 1.4;'>
                Control mode is managed by GPIO PIN 13<br>
                <strong>HIGH:</strong> Manual Mode &nbsp;&nbsp; <strong>LOW:</strong> Auto Mode
            </div>
        """)
        mode_description.setStyleSheet("""
            QLabel {
                background-color: #F8FAFC;
                padding: 12px;
                border-radius: 8px;
                border: 1px solid #E2E8F0;
            }
        """)
        mode_layout.addWidget(mode_description)
        
        mode_card.content_layout.addLayout(mode_layout)
        column_layout.addWidget(mode_card)
        
        # Manual Control Values
        values_card = ModernCard("Current Manual Settings")
        values_layout = QVBoxLayout()
        
        # Speed and temperature displays
        self.speed_display = DataDisplay("Set Speed", "0.0", "mph")
        self.temp_display = DataDisplay("Set Temperature", "72.0", "°F")
        
        values_layout.addWidget(self.speed_display)
        values_layout.addWidget(self.temp_display)
        
        # GPIO control instructions
        instructions = QLabel("""
            <div style='font-size: 13px; color: #6B7280; line-height: 1.4;'>
                <strong>GPIO Controls (Manual Mode Only):</strong><br>
                • Speed: PIN 20 (UP) / PIN 16 (DOWN)<br>
                • Temperature: PIN 23 (UP) / PIN 24 (DOWN)<br>
                • Headlights: PIN 17 (TOGGLE)<br>
                • Interior Lights: PIN 27 (TOGGLE)<br>
                • Doors: PIN 6 (LEFT) / PIN 19 (RIGHT)<br>
                • Service Brake: PIN 26 (TOGGLE)<br>
                • Emergency Brake: PIN 21 (ALWAYS ACTIVE)
            </div>
        """)
        instructions.setStyleSheet("""
            QLabel {
                background-color: #FEF3C7;
                padding: 15px;
                border-radius: 8px;
                border: 1px solid #F59E0B;
            }
        """)
        values_layout.addWidget(instructions)
        
        values_card.content_layout.addLayout(values_layout)
        column_layout.addWidget(values_card)
        
        column_layout.addStretch()
        return column_widget
        
    def create_center_column(self):
        """Create the center column with train status information"""
        column_widget = QWidget()
        column_layout = QVBoxLayout(column_widget)
        column_layout.setSpacing(20)
        
        # Speed Information
        speed_card = ModernCard("Speed & Power Information")
        speed_grid = QGridLayout()
        speed_grid.setSpacing(15)
        
        self.current_speed_display = DataDisplay("Current Speed", "0.0", "mph")
        self.set_speed_display = DataDisplay("Set Speed", "0.0", "mph")
        self.speed_limit_display = DataDisplay("Speed Limit", "40.0", "mph")
        self.power_output_display = DataDisplay("Power Output", "0.0", "kW")
        
        speed_grid.addWidget(self.current_speed_display, 0, 0)
        speed_grid.addWidget(self.set_speed_display, 0, 1)
        speed_grid.addWidget(self.speed_limit_display, 1, 0)
        speed_grid.addWidget(self.power_output_display, 1, 1)
        
        speed_card.content_layout.addLayout(speed_grid)
        column_layout.addWidget(speed_card)
        
        # Authority and Temperature
        status_card = ModernCard("System Status")
        status_grid = QGridLayout()
        status_grid.setSpacing(15)
        
        self.authority_display = DataDisplay("Authority", "0.0", "yards")
        self.current_temp_display = DataDisplay("Current Temp", "72.0", "°F")
        
        status_grid.addWidget(self.authority_display, 0, 0)
        status_grid.addWidget(self.current_temp_display, 0, 1)
        
        status_card.content_layout.addLayout(status_grid)
        column_layout.addWidget(status_card)
        
        # Brake and Door Status
        controls_card = ModernCard("Control System Status")
        controls_layout = QVBoxLayout()
        
        # Brake status
        brake_section = QVBoxLayout()
        brake_title = QLabel("Brake System Status")
        brake_title.setStyleSheet("font-size: 16px; font-weight: 500; color: #374151; margin-bottom: 10px;")
        brake_section.addWidget(brake_title)
        
        brake_grid = QGridLayout()
        brake_grid.setSpacing(10)
        
        self.emergency_brake_status = StatusIndicator("Emergency Brake: OFF", "normal")
        self.service_brake_status = StatusIndicator("Service Brake: OFF", "normal")
        
        brake_grid.addWidget(self.emergency_brake_status, 0, 0)
        brake_grid.addWidget(self.service_brake_status, 0, 1)
        brake_section.addLayout(brake_grid)
        
        controls_layout.addLayout(brake_section)
        
        # Door status
        door_section = QVBoxLayout()
        door_title = QLabel("Door System Status")
        door_title.setStyleSheet("font-size: 16px; font-weight: 500; color: #374151; margin: 15px 0 10px 0;")
        door_section.addWidget(door_title)
        
        door_grid = QGridLayout()
        door_grid.setSpacing(10)
        
        self.left_door_status = StatusIndicator("Left Door: CLOSED", "normal")
        self.right_door_status = StatusIndicator("Right Door: CLOSED", "normal")
        
        door_grid.addWidget(self.left_door_status, 0, 0)
        door_grid.addWidget(self.right_door_status, 0, 1)
        door_section.addLayout(door_grid)
        
        controls_layout.addLayout(door_section)
        
        controls_card.content_layout.addLayout(controls_layout)
        column_layout.addWidget(controls_card)
        
        column_layout.addStretch()
        return column_widget
        
    def create_right_column(self):
        """Create the right column with system status and failures"""
        column_widget = QWidget()
        column_layout = QVBoxLayout(column_widget)
        column_layout.setSpacing(20)
        
        # PID Controller Status
        pid_card = ModernCard("Controller Status")
        pid_layout = QVBoxLayout()
        
        self.pid_status_display = StatusIndicator("Waiting for Kp/Ki Parameters", "warning")
        self.pid_status_display.setMinimumHeight(70)
        pid_layout.addWidget(self.pid_status_display)
        
        pid_card.content_layout.addLayout(pid_layout)
        column_layout.addWidget(pid_card)
        
        # System Failures
        failures_card = ModernCard("System Health")
        failures_layout = QVBoxLayout()
        
        self.engine_status = StatusIndicator("Engine: OK", "success")
        self.signal_status = StatusIndicator("Signal: OK", "success")
        self.brake_system_status = StatusIndicator("Brake System: OK", "success")
        
        failures_layout.addWidget(self.engine_status)
        failures_layout.addWidget(self.signal_status)
        failures_layout.addWidget(self.brake_system_status)
        
        failures_card.content_layout.addLayout(failures_layout)
        column_layout.addWidget(failures_card)
        
        # Environment Status
        env_status_card = ModernCard("Environment Controls")
        env_status_layout = QVBoxLayout()
        
        self.headlights_status = StatusIndicator("Headlights: OFF", "normal")
        self.interior_lights_status = StatusIndicator("Interior Lights: OFF", "normal")
        
        env_status_layout.addWidget(self.headlights_status)
        env_status_layout.addWidget(self.interior_lights_status)
        
        env_status_card.content_layout.addLayout(env_status_layout)
        column_layout.addWidget(env_status_card)
        
        # Connection Status
        connection_card = ModernCard("Hardware Connection")
        connection_layout = QVBoxLayout()
        
        self.connection_details = QLabel(f"""
            <div style='font-size: 14px; line-height: 1.5; color: #374151;'>
                <strong>Serial Port:</strong> {self.serial_port}<br>
                <strong>Baud Rate:</strong> {self.baud_rate}<br>
                <strong>GPIO Pins:</strong> 11 configured
            </div>
        """)
        self.connection_details.setStyleSheet("""
            QLabel {
                background-color: #F8FAFC;
                padding: 15px;
                border-radius: 8px;
                border: 1px solid #E2E8F0;
            }
        """)
        connection_layout.addWidget(self.connection_details)
        
        connection_card.content_layout.addLayout(connection_layout)
        column_layout.addWidget(connection_card)
        
        column_layout.addStretch()
        return column_widget
        
    def create_footer_section(self, layout):
        """Create the footer section with emergency controls and system summary"""
        footer_card = ModernCard()
        footer_layout = QHBoxLayout()
        footer_card.content_layout.addLayout(footer_layout)
        
        # Emergency brake - large and prominent
        emergency_section = QVBoxLayout()
        emergency_label = QLabel("EMERGENCY BRAKE SYSTEM")
        emergency_label.setStyleSheet("""
            font-size: 22px; 
            font-weight: bold; 
            color: #DC2626; 
            text-align: center;
            margin-bottom: 15px;
        """)
        emergency_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.emergency_brake_display = ModernButton("EMERGENCY BRAKE", "emergency")
        self.emergency_brake_display.setMinimumHeight(100)
        self.emergency_brake_display.setEnabled(False)  # Display only
        self.emergency_brake_display.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: white;
                border: 4px solid #B91C1C;
                border-radius: 16px;
                padding: 25px;
                font-weight: bold;
                font-size: 24px;
                outline: none;
            }
        """)
        
        gpio_emergency_note = QLabel("Controlled by GPIO PIN 21")
        gpio_emergency_note.setStyleSheet("""
            font-size: 14px; 
            color: #6B7280; 
            text-align: center;
            margin-top: 10px;
            font-weight: 600;
        """)
        gpio_emergency_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        emergency_section.addWidget(emergency_label)
        emergency_section.addWidget(self.emergency_brake_display)
        emergency_section.addWidget(gpio_emergency_note)
        footer_layout.addLayout(emergency_section)
        
        # System summary
        summary_section = QVBoxLayout()
        summary_label = QLabel("System Summary")
        summary_label.setStyleSheet("""
            font-size: 18px; 
            font-weight: 700; 
            color: #374151; 
            margin-bottom: 15px;
        """)
        
        self.system_summary = QLabel("""
            <div style='font-size: 16px; line-height: 1.6;'>
                <strong>Mode:</strong> AUTO<br>
                <strong>Speed:</strong> 0.0 mph<br>
                <strong>GPIO:</strong> DISCONNECTED<br>
                <strong>Status:</strong> READY
            </div>
        """)
        self.system_summary.setStyleSheet("""
            QLabel {
                background-color: #F3F4F6;
                padding: 20px;
                border-radius: 12px;
                border: 2px solid #E5E7EB;
            }
        """)
        
        summary_section.addWidget(summary_label)
        summary_section.addWidget(self.system_summary)
        summary_section.addStretch()
        footer_layout.addLayout(summary_section)
        
        layout.addWidget(footer_card)
        
    def apply_global_styles(self):
        """Apply global application styles"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F9FAFB;
            }
            QWidget {
                font-family: "Segoe UI", "San Francisco", "Helvetica Neue", Arial, sans-serif;
            }
            QGroupBox {
                font-weight: 600;
                padding-top: 15px;
                margin-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
            }
        """)
        
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
        
        # GPIO reading timer
        self.gpio_timer = QTimer()
        self.gpio_timer.timeout.connect(self.read_gpio_inputs)
        self.gpio_timer.start(100)  # 10 FPS
        
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
            print(f"Hardware Driver UI: Train ID set to {self.train_id}")
            
    def update_ui(self):
        """Main UI update function"""
        if self.train_controller:
            self.update_from_train_controller()
        self.update_gpio_status_display()
        self.update_system_summary()
        
    def update_from_train_controller(self):
        """Update UI from train controller data"""
        if not self.train_controller:
            return
            
        try:
            # Get controller output
            driver_output = self.train_controller.get_output_to_driver()
            
            # Update displays
            self.current_speed_display.set_value(f"{driver_output.actual_speed:.1f}")
            self.set_speed_display.set_value(f"{driver_output.input_speed:.1f}")
            self.speed_limit_display.set_value(f"{driver_output.speed_limit:.1f}")
            self.power_output_display.set_value(f"{driver_output.power_output:.1f}")
            self.authority_display.set_value(f"{driver_output.authority:.1f}")
            self.current_temp_display.set_value(f"{driver_output.current_cabin_temp:.0f}")
            
            # Update failures
            self.engine_status.set_status(
                "error" if driver_output.engine_failure else "success",
                "Engine: FAILED" if driver_output.engine_failure else "Engine: OK"
            )
            self.signal_status.set_status(
                "error" if driver_output.signal_failure else "success",
                "Signal: FAILED" if driver_output.signal_failure else "Signal: OK"
            )
            self.brake_system_status.set_status(
                "error" if driver_output.brake_failure else "success",
                "Brake System: FAILED" if driver_output.brake_failure else "Brake System: OK"
            )
            
            # Update PID status
            if driver_output.kp_ki_set:
                self.pid_status_display.set_status(
                    "success",
                    f"Controller Active\n(Kp: {driver_output.kp:.1f}, Ki: {driver_output.ki:.1f})"
                )
            else:
                self.pid_status_display.set_status("warning", "Waiting for Kp/Ki Parameters")
                
            # Update next station
            if driver_output.next_station and driver_output.station_side:
                station_text = f"{driver_output.next_station} (Platform: {driver_output.station_side.title()})"
                self.next_station_display.setText(station_text)
            else:
                self.next_station_display.setText("No Station Information")
                
        except Exception as e:
            print(f"Error updating from train controller: {e}")
            
    def update_gpio_status_display(self):
        """Update GPIO status displays"""
        # Update connection status
        connected = self.is_gpio_connected()
        self.gpio_status_widget.update_connection_status(connected)
        
        # Update mode status
        auto_mode = self.get_gpio_auto_mode()
        if auto_mode:
            self.mode_status.set_status("success", "AUTO MODE ACTIVE")
            self.gpio_status_widget.update_gpio_status("mode", "success", "Mode: AUTO")
        else:
            self.mode_status.set_status("info", "MANUAL MODE ACTIVE")
            self.gpio_status_widget.update_gpio_status("mode", "info", "Mode: MANUAL")
            
        # Update individual GPIO statuses
        self.gpio_status_widget.update_gpio_status(
            "headlights", 
            "warning" if self.gpio_inputs['headlights_on'] else "normal",
            f"Headlights: {'ON' if self.gpio_inputs['headlights_on'] else 'OFF'}"
        )
        
        self.gpio_status_widget.update_gpio_status(
            "interior", 
            "warning" if self.gpio_inputs['interior_lights_on'] else "normal",
            f"Interior: {'ON' if self.gpio_inputs['interior_lights_on'] else 'OFF'}"
        )
        
        self.gpio_status_widget.update_gpio_status(
            "emergency", 
            "error" if self.emergency_brake_active else "normal",
            f"Emergency: {'ON' if self.emergency_brake_active else 'OFF'}"
        )
        
        self.gpio_status_widget.update_gpio_status(
            "service_brake", 
            "warning" if self.service_brake_active else "normal",
            f"Service Brake: {'ON' if self.service_brake_active else 'OFF'}"
        )
        
        self.gpio_status_widget.update_gpio_status(
            "left_door", 
            "warning" if self.gpio_inputs['door_left_open'] else "normal",
            f"Left Door: {'OPEN' if self.gpio_inputs['door_left_open'] else 'CLOSED'}"
        )
        
        self.gpio_status_widget.update_gpio_status(
            "right_door", 
            "warning" if self.gpio_inputs['door_right_open'] else "normal",
            f"Right Door: {'OPEN' if self.gpio_inputs['door_right_open'] else 'CLOSED'}"
        )
        
        self.gpio_status_widget.update_gpio_status(
            "speed", 
            "info" if not auto_mode else "normal",
            f"Speed: {self.manual_set_speed:.1f} mph"
        )
        
        self.gpio_status_widget.update_gpio_status(
            "temperature", 
            "info" if not auto_mode else "normal",
            f"Temperature: {self.manual_set_temperature:.0f}°F"
        )
        
        # Update main status indicators
        self.headlights_status.set_status(
            "warning" if self.gpio_inputs['headlights_on'] else "normal",
            "Headlights: ON" if self.gpio_inputs['headlights_on'] else "Headlights: OFF"
        )
        
        self.interior_lights_status.set_status(
            "warning" if self.gpio_inputs['interior_lights_on'] else "normal",
            "Interior Lights: ON" if self.gpio_inputs['interior_lights_on'] else "Interior Lights: OFF"
        )
        
        self.left_door_status.set_status(
            "warning" if self.gpio_inputs['door_left_open'] else "normal",
            "Left Door: OPEN" if self.gpio_inputs['door_left_open'] else "Left Door: CLOSED"
        )
        
        self.right_door_status.set_status(
            "warning" if self.gpio_inputs['door_right_open'] else "normal",
            "Right Door: OPEN" if self.gpio_inputs['door_right_open'] else "Right Door: CLOSED"
        )
        
        # Update brake status
        self.emergency_brake_status.set_status(
            "error" if self.emergency_brake_active else "normal",
            "Emergency Brake: ON" if self.emergency_brake_active else "Emergency Brake: OFF"
        )
        
        self.service_brake_status.set_status(
            "warning" if self.service_brake_active else "normal",
            "Service Brake: ON" if self.service_brake_active else "Service Brake: OFF"
        )
        
        # Update manual setting displays
        self.speed_display.set_value(f"{self.manual_set_speed:.1f}")
        self.temp_display.set_value(f"{self.manual_set_temperature:.0f}")
        
        # Update emergency brake display
        if self.emergency_brake_active:
            self.emergency_brake_display.setText("EMERGENCY BRAKE ACTIVE")
            self.emergency_brake_display.setStyleSheet("""
                QPushButton {
                    background-color: #7F1D1D;
                    color: white;
                    border: 4px solid #991B1B;
                    border-radius: 16px;
                    padding: 25px;
                    font-weight: bold;
                    font-size: 24px;
                    outline: none;
                }
            """)
        else:
            self.emergency_brake_display.setText("EMERGENCY BRAKE")
            self.emergency_brake_display.setStyleSheet("""
                QPushButton {
                    background-color: #DC2626;
                    color: white;
                    border: 4px solid #B91C1C;
                    border-radius: 16px;
                    padding: 25px;
                    font-weight: bold;
                    font-size: 24px;
                    outline: none;
                }
            """)
            
    def update_system_summary(self):
        """Update the system summary display"""
        mode_text = "AUTO" if self.get_gpio_auto_mode() else "MANUAL"
        speed_text = "0.0"
        gpio_text = "CONNECTED" if self.is_gpio_connected() else "DISCONNECTED"
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
                
        self.system_summary.setText(f"""
            <div style='font-size: 16px; line-height: 1.6;'>
                <strong>Mode:</strong> {mode_text}<br>
                <strong>Speed:</strong> {speed_text} mph<br>
                <strong>GPIO:</strong> {gpio_text}<br>
                <strong>Status:</strong> {status_text}
            </div>
        """)
        
    def get_driver_input(self):
        """Return DriverInput object with current GPIO states"""
        if DriverInput:
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
        return None
        
    def set_next_station(self, station_text):
        """Update next station display"""
        self.next_station_display.setText(station_text)
        
    def cleanup_gpio(self):
        """Clean up GPIO emulator resources"""
        if hasattr(self, 'gpio_emulator') and self.gpio_emulator:
            self.gpio_emulator.stop()
            print("GPIO emulator cleanup completed")
            
    def closeEvent(self, event):
        """Handle window close event"""
        print("Professional Hardware Driver UI closing...")
        self.cleanup_gpio()
        event.accept()


def main():
    """Main function for standalone testing"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Professional Train Driver Interface - Hardware")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Train Control Systems")
    
    # Create and show the window
    window = ProfessionalHardwareDriverUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()