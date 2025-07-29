# train_dashboard_ui.py

import sys
import os
from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QPushButton, QVBoxLayout,
    QWidget, QHBoxLayout, QGridLayout, QGroupBox
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, QTimer

class TrainDashboard(QMainWindow):
    def __init__(self, train_model):
        super().__init__()
        self.train_model = train_model
        self.setWindowTitle(f"Train Dashboard - {train_model.train_id}")
        self.setGeometry(200, 200, 1000, 600)
        
        # Get the directory where the Train Model images are located
        self.image_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.init_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(200)
    
    def get_image_path(self, filename):
        """Get the full path to an image file in the Train Model directory"""
        return os.path.join(self.image_dir, filename)

    def init_ui(self):
        # Font size variables for easy customization
        self.NEXT_STATION_FONT_SIZE = 30
        self.MAIN_DISPLAY_FONT_SIZE = 30  # Power and Speed displays
        self.GROUP_TITLE_FONT_SIZE = 20
        self.LOGISTICS_FONT_SIZE = 20  # NEW: For logistics labels
        self.PHYSICAL_INFO_FONT_SIZE = 20  # NEW: For physical info labels
        self.FAILURE_TEXT_FONT_SIZE = 20  # NEW: For failure indicator text
        self.EMERGENCY_BUTTON_FONT_SIZE = 50
        
        # Apply global styles to match Professional Driver UI
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QWidget {
                font-family: "Segoe UI", Arial, sans-serif;
                color: #333;
            }
            QFrame, QGroupBox {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 8px;
            }
            QGroupBox::title {
                color: #666;
                font-size: 12pt;
                font-weight: 600;
                padding: 0 8px;
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
            }
            QLabel {
                color: #333;
                border: none;
                background-color: transparent;
            }
            QPushButton {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 8px 16px;
                background-color: white;
                min-height: 30px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #e9e9e9;
                border-color: #999;
            }
            QPushButton:pressed {
                background-color: #ddd;
            }
        """)
        
        container = QWidget()
        master_layout = QVBoxLayout()
        master_layout.setContentsMargins(12, 12, 12, 12)
        master_layout.setSpacing(15)

        top_row = QHBoxLayout()
        top_row.setSpacing(15)
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(15)

        # Top-left: Next stop group (with header)
        next_stop_group = QGroupBox()
        next_stop_layout = QVBoxLayout()
        next_stop_layout.setContentsMargins(12, 20, 12, 12)
        self.next_stop_label = QLabel("Next Stop:\n[Station Name]\nOn: Both Side(s)")
        self.next_stop_label.setFont(QFont("Arial", self.NEXT_STATION_FONT_SIZE, QFont.Bold))
        self.next_stop_label.setAlignment(Qt.AlignCenter)
        next_stop_layout.addWidget(self.next_stop_label)
        next_stop_group.setLayout(next_stop_layout)


        # Power and Velocity side-by-side
        power_velocity_row = QHBoxLayout()
        power_velocity_row.setSpacing(15)

        # Power Group
        power_value_group = QGroupBox()
        power_value_layout = QVBoxLayout()
        power_value_layout.setContentsMargins(12, 20, 12, 12)
        self.power_label = QLabel("Train Power\n\n0 W")
        self.power_label.setAlignment(Qt.AlignCenter)
        self.power_label.setFont(QFont("Arial", self.MAIN_DISPLAY_FONT_SIZE, QFont.Bold))
        power_value_layout.addWidget(self.power_label)
        power_value_group.setLayout(power_value_layout)

        # Velocity Group
        velocity_title_group = QGroupBox()
        velocity_title_layout = QVBoxLayout()
        velocity_title_layout.setContentsMargins(12, 20, 12, 12)
        self.velocity_title = QLabel("Current Velocity\n0 mph")
        self.velocity_title.setAlignment(Qt.AlignCenter)
        self.velocity_title.setFont(QFont("Arial", self.MAIN_DISPLAY_FONT_SIZE, QFont.Bold))
        velocity_title_layout.addWidget(self.velocity_title)
        velocity_title_group.setLayout(velocity_title_layout)

        power_velocity_row.addWidget(power_value_group)
        power_velocity_row.addWidget(velocity_title_group)
        

        # Wrap next stop and the new row into a vertical stack
        left_column = QVBoxLayout()
        left_column.setSpacing(15)
        left_column.addWidget(next_stop_group)
        left_column.addLayout(power_velocity_row)

        # Top-right: Logistics
        logistics_group = QGroupBox("Train Logistics")
        logistics_group.setFont(QFont("Arial", self.GROUP_TITLE_FONT_SIZE, QFont.Bold))
        logistics_layout = QGridLayout()
        logistics_layout.setContentsMargins(12, 20, 12, 12)
        logistics_layout.setSpacing(8)
        self.authority_label = QLabel("Authority: -- yd")
        self.elevation_label = QLabel("Terrain Elevation: -- m")
        self.speed_limit_label = QLabel("Speed Limit: -- mph")
        self.command_speed_label = QLabel("Commanded Speed: -- mph")
        self.accel_label = QLabel("Train Acceleration: -- ft/s²")
        self.train_weight_label = QLabel("Current Train Weight: -- lbs")
        self.crew_label = QLabel("Crew Count: --")
        self.passenger_label = QLabel("Passenger Count: --")
        self.train_length_label = QLabel("Train Length: 105.6 ft")
        self.train_width_label = QLabel("Train Width: 8.7 ft")
        self.train_height_label = QLabel("Train Height: 11.2 ft")
        self.distance_label = QLabel("Distance Traveled: -- ft")
        
        # Apply larger font to all logistics labels
        logistics_labels = [self.authority_label, self.elevation_label, self.speed_limit_label, 
                           self.command_speed_label, self.accel_label, self.train_weight_label,
                           self.crew_label, self.passenger_label, self.train_length_label,
                           self.train_width_label, self.train_height_label, self.distance_label]
        for label in logistics_labels:
            label.setFont(QFont("Arial", self.LOGISTICS_FONT_SIZE, QFont.Bold))
        logistics_layout.addWidget(self.distance_label, 0, 0)
        logistics_layout.addWidget(self.authority_label, 1, 0)
        logistics_layout.addWidget(self.elevation_label, 2, 0)
        logistics_layout.addWidget(self.passenger_label, 3, 0)
        logistics_layout.addWidget(self.train_weight_label, 4, 0)
        logistics_layout.addWidget(self.train_height_label, 5, 0)
        logistics_layout.addWidget(self.accel_label, 0, 1)
        logistics_layout.addWidget(self.speed_limit_label, 1, 1)
        logistics_layout.addWidget(self.command_speed_label, 2, 1)
        logistics_layout.addWidget(self.crew_label, 3, 1)
        logistics_layout.addWidget(self.train_length_label, 4, 1)
        logistics_layout.addWidget(self.train_width_label, 5, 1)
        logistics_group.setLayout(logistics_layout)
        logistics_group.setFixedWidth(673)

        top_row.addLayout(left_column)
        top_row.addWidget(logistics_group)

        # Bottom-left: Failure + Emergency Brake
        failure_column = QVBoxLayout()
        failure_column.setSpacing(15)
        failure_group = QGroupBox("Train Failure Status")
        failure_group.setFont(QFont("Arial", self.GROUP_TITLE_FONT_SIZE, QFont.Bold))
        failure_layout = QHBoxLayout()
        failure_layout.setContentsMargins(12, 20, 12, 12)
        failure_layout.setSpacing(15)

        def create_failure_indicator(image_path, text):
            container = QVBoxLayout()
            img = QLabel()
            img.setPixmap(QPixmap(self.get_image_path(image_path)))
            img.setFixedSize(100, 100)
            img.setScaledContents(True)
            img.setAlignment(Qt.AlignCenter)
            label = QLabel(text)
            label.setAlignment(Qt.AlignCenter)
            label.setFont(QFont("Arial", self.FAILURE_TEXT_FONT_SIZE, QFont.Bold))  # Apply larger font
            container_widget = QWidget()
            container_layout = QVBoxLayout()
            container_layout.setAlignment(Qt.AlignCenter)
            container_layout.addWidget(img)
            container_layout.addWidget(label)
            container_widget.setLayout(container_layout)
            return img, container_widget
        
        self.brake_fail_light, brake_widget = create_failure_indicator("Siren_Off.png", "BRAKE\nFAILURE")
        self.signal_fail_light, signal_widget = create_failure_indicator("Siren_Off.png", "SIGNAL\nFAILURE")
        self.engine_fail_light, engine_widget = create_failure_indicator("Siren_Off.png", "ENGINE\nFAILURE")

        failure_layout.addWidget(brake_widget)
        failure_layout.addWidget(signal_widget)
        failure_layout.addWidget(engine_widget)
        failure_group.setLayout(failure_layout)
        failure_column.addWidget(failure_group)

        self.emergency_button = QPushButton("EMERGENCY BRAKE")
        self.emergency_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #CC0000;
                color: white;
                font-weight: bold;
                font-size: {self.EMERGENCY_BUTTON_FONT_SIZE}px;
                border: 2px solid #990000;
                border-radius: 8px;
                padding: 15px;
            }}
            
            QPushButton:hover {{
                    background-color: #DD0000;
                    border-color: #AA0000;
            }}
            QPushButton:pressed {{
                    background-color: #990000;
            }}
        """)

        self.emergency_button.clicked.connect(self.handle_emergency_brake)
        self.emergency_button.setFixedHeight(150)
        failure_column.addWidget(self.emergency_button)

        # Bottom-right: Physical Info + Sponsors (side-by-side)
        info_column = QHBoxLayout()
        info_column.setSpacing(15)

        physical_group = QGroupBox("Train Physical Info")
        physical_group.setFont(QFont("Arial", self.GROUP_TITLE_FONT_SIZE, QFont.Bold))
        physical_layout = QVBoxLayout()
        physical_layout.setContentsMargins(12, 20, 12, 12)
        physical_layout.setSpacing(8)
        self.brake_status_label = QLabel("Main Brake: --")
        self.temp_label = QLabel("Cabin Temperature: -- °F")
        self.lights_label = QLabel("Interior Lights: --\nExterior Lights: --")
        self.doors_label = QLabel("Left Doors: --\nRight Doors: --")
        
        # Apply larger font to all physical info labels
        physical_labels = [self.brake_status_label, self.temp_label, self.lights_label, self.doors_label]
        for label in physical_labels:
            label.setFont(QFont("Arial", self.PHYSICAL_INFO_FONT_SIZE, QFont.Bold))
            physical_layout.addWidget(label)
        physical_group.setLayout(physical_layout)
        physical_group.setFixedWidth(357)

        sponsors_group = QGroupBox("Train Sponsored By:")
        sponsors_group.setFont(QFont("Arial", self.GROUP_TITLE_FONT_SIZE, QFont.Bold))
        sponsors_layout = QVBoxLayout()
        sponsors_layout.setContentsMargins(12, 20, 12, 12)
        self.claude_logo = QLabel()
        self.claude_logo.setPixmap(QPixmap(self.get_image_path("Claude_Logo.png")))
        self.claude_logo.setFixedSize(267,300)
        self.claude_logo.setAlignment(Qt.AlignCenter)
        sponsors_layout.addWidget(self.claude_logo)
        sponsors_group.setLayout(sponsors_layout)
        sponsors_group.setFixedWidth(300)

        info_column.addWidget(physical_group)
        info_column.addWidget(sponsors_group)

        bottom_row.addLayout(failure_column)
        bottom_row.addLayout(info_column)

        master_layout.addLayout(top_row)
        master_layout.addLayout(bottom_row)
        container.setLayout(master_layout)
        self.setCentralWidget(container)

    def handle_emergency_brake(self):
        self.train_model.set_passenger_emergency_brake(True)
        self.emergency_button.setStyleSheet("background-color: darkred; color: white; font-weight: bold; font-size: 50px;")

    def update_display(self):
        self.velocity_title.setText(f"Current Velocity\n\n{self.train_model.velocity_mps * 2.237:.0f} mph")
        self.power_label.setText(f"Train Power\n\n {self.train_model.power_watts:.0f} W")
        self.authority_label.setText(f"Authority: {self.train_model.authority_m:.0f} yd")
        self.elevation_label.setText(f"Terrain Elevation: {self.train_model.elevation_m:.1f} m")
        self.speed_limit_label.setText(f"Speed Limit: {self.train_model.speed_limit_mps:.0f} mph")
        self.command_speed_label.setText(f"Commanded Speed Signal: {self.train_model.command_speed_signal}")
        self.accel_label.setText(f"Train Acceleration: {self.train_model.acceleration_mps2 * 3.281:.2f} ft/s²")
        self.train_weight_label.setText(f"Current Train Weight: {self.train_model.mass_kg * 2.205:.0f} lbs")
        self.crew_label.setText(f"Crew Count: {self.train_model.crew_count}")
        self.distance_label.setText(f"Distance Traveled: {self.train_model.total_distance_m * 3.328:.2f} ft")
        self.passenger_label.setText(f"Passenger Count: {self.train_model.passenger_count}")
        self.temp_label.setText(f"Cabin Temperature: {self.train_model.cabin_temperature:.1f}°F")
        self.lights_label.setText(f"Interior Lights: {'ON' if self.train_model.interior_lights_on else 'OFF'}\n"
                                  f"Exterior Lights: {'ON' if self.train_model.exterior_lights_on else 'OFF'}")
        self.doors_label.setText(f"Left Doors: {'OPEN' if self.train_model.left_doors_open else 'CLOSED'}\n"
                                 f"Right Doors: {'OPEN' if self.train_model.right_doors_open else 'CLOSED'}")
        self.brake_status_label.setText(f"Main Brake: {'Engaged' if self.train_model.service_brake_engaged else 'Disengaged'}")

        brake_pixmap = QPixmap(self.get_image_path("Siren_On.png" if self.train_model.brake_failure else "Siren_Off.png"))
        signal_pixmap = QPixmap(self.get_image_path("Siren_On.png" if self.train_model.signal_failure else "Siren_Off.png"))
        engine_pixmap = QPixmap(self.get_image_path("Siren_On.png" if self.train_model.engine_failure else "Siren_Off.png"))

        self.brake_fail_light.setPixmap(brake_pixmap)
        self.signal_fail_light.setPixmap(signal_pixmap)
        self.engine_fail_light.setPixmap(engine_pixmap)

        # Emergency button visual reset - show active if EITHER emergency brake is engaged
        if self.train_model.emergency_brake_engaged or self.train_model.passenger_emergency_brake:
            self.emergency_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: #660000;
                    color: white;
                    font-weight: bold;
                    font-size: {self.EMERGENCY_BUTTON_FONT_SIZE}px;
                    border: 2px solid #440000;
                    border-radius: 8px;
                    padding: 15px;
                }}
            """)
            self.emergency_button.setText("EMERGENCY BRAKE")
        else:
            self.emergency_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: #CC0000;
                    color: white;
                    font-weight: bold;
                    font-size: {self.EMERGENCY_BUTTON_FONT_SIZE}px;
                    border: 2px solid #990000;
                    border-radius: 8px;
                    padding: 15px;
                }}
                QPushButton:hover {{
                    background-color: #DD0000;
                    border-color: #AA0000;
                }}
                QPushButton:pressed {{
                    background-color: #990000;
                }}
            """)
            self.emergency_button.setText("EMERGENCY BRAKE")

        # Update next stop
        if hasattr(self.train_model, 'next_stop'):
            self.next_stop_label.setText(f"Next Stop: {self.train_model.next_stop}\n On: {self.train_model.next_stop_side} Side(s)")
