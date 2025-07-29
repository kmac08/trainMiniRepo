# train_dashboard_ui.py

import sys
from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QPushButton, QVBoxLayout,
    QWidget, QHBoxLayout, QGridLayout, QGroupBox, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, QTimer

class TrainDashboard(QMainWindow):
    def __init__(self, train_model):
        super().__init__()
        self.train_model = train_model
        self.setWindowTitle(f"Train Dashboard - {train_model.train_id}")
        self.setGeometry(200, 200, 1000, 600)
        self.init_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(200)

    def init_ui(self):
        container = QWidget()
        master_layout = QVBoxLayout()

        top_row = QHBoxLayout()
        bottom_row = QHBoxLayout()

        # Top-left: Next stop group (with header)
        next_stop_group = QGroupBox()
        next_stop_layout = QVBoxLayout()
        self.next_stop_label = QLabel("Next Stop: [Station Name]")
        self.next_stop_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.next_stop_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.station_image = QLabel()
        self.station_image.setPixmap(QPixmap())
        self.station_image.setScaledContents(True)
        self.station_image.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.station_image.setStyleSheet("border: 1px solid black;")
        next_stop_layout.addWidget(self.next_stop_label)
        next_stop_layout.addWidget(self.station_image)
        next_stop_group.setLayout(next_stop_layout)

        # Velocity Block split into 2 group boxes stacked
        velocity_column = QVBoxLayout()
        velocity_title_group = QGroupBox()
        velocity_title_layout = QVBoxLayout()
        velocity_title = QLabel("Current Velocity")
        velocity_title.setAlignment(Qt.AlignCenter)
        velocity_title.setFont(QFont("Arial", 24, QFont.Bold))
        velocity_title_layout.addWidget(velocity_title)
        velocity_title_group.setLayout(velocity_title_layout)

        velocity_value_group = QGroupBox()
        velocity_value_layout = QVBoxLayout()
        self.velocity_label = QLabel("0 mph")
        self.velocity_label.setAlignment(Qt.AlignCenter)
        self.velocity_label.setFont(QFont("Arial", 35, QFont.Bold))
        velocity_value_layout.addWidget(self.velocity_label)
        velocity_value_group.setLayout(velocity_value_layout)

        velocity_column.addWidget(velocity_title_group)
        velocity_column.addWidget(velocity_value_group)

        velocity_and_image = QHBoxLayout()
        velocity_and_image.addWidget(next_stop_group)
        velocity_and_image.addLayout(velocity_column)

        # Top-right: Logistics
        logistics_group = QGroupBox("Train Logistics")
        logistics_group.setFont(QFont("Arial", 16, QFont.Bold))
        logistics_layout = QGridLayout()
        self.power_label = QLabel("Train Power: -- W")
        self.elevation_label = QLabel("Terrain Elevation: -- m")
        self.speed_limit_label = QLabel("Speed Limit: -- mph")
        self.command_speed_label = QLabel("Commanded Speed: -- mph")
        self.accel_label = QLabel("Train Acceleration: -- ft/s²")
        self.train_weight_label = QLabel("Current Train Weight: -- lbs")
        self.crew_label = QLabel("Crew Count: --")
        self.passenger_label = QLabel("Passenger Count: --")
        self.train_length_label = QLabel("Train Length: 105.6 ft")
        self.train_width_label = QLabel("Train Width: 8.7 ft")
        self.train_height_label = QLabel("Train Length: 11.2 ft")
        self.distance_label = QLabel("Distance Traveled: -- ft")
        logistics_layout.addWidget(self.power_label, 0, 0)
        logistics_layout.addWidget(self.elevation_label, 1, 0)
        logistics_layout.addWidget(self.distance_label, 2, 0)
        logistics_layout.addWidget(self.train_weight_label, 3, 0)
        logistics_layout.addWidget(self.train_height_label, 4, 0)
        logistics_layout.addWidget(self.passenger_label, 5, 0)
        logistics_layout.addWidget(self.accel_label, 0, 1)
        logistics_layout.addWidget(self.speed_limit_label, 1, 1)
        logistics_layout.addWidget(self.command_speed_label, 2, 1)
        logistics_layout.addWidget(self.train_length_label, 3, 1)
        logistics_layout.addWidget(self.train_width_label, 4, 1)
        logistics_layout.addWidget(self.crew_label, 5, 1)
        logistics_group.setLayout(logistics_layout)
        logistics_group.setFixedWidth(617)

        top_row.addLayout(velocity_and_image)
        top_row.addWidget(logistics_group)

        # Bottom-left: Failure + Emergency Brake
        failure_column = QVBoxLayout()
        failure_group = QGroupBox("Train Failure Status")
        failure_group.setFont(QFont("Arial", 16, QFont.Bold))
        failure_layout = QHBoxLayout()

        def create_failure_indicator(image_path, text):
            container = QVBoxLayout()
            img = QLabel()
            img.setPixmap(QPixmap(image_path))
            img.setFixedSize(100, 100)
            img.setScaledContents(True)
            img.setAlignment(Qt.AlignCenter)
            label = QLabel(text)
            label.setAlignment(Qt.AlignCenter)
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
        self.emergency_button.setStyleSheet("background-color: red; color: white; font-weight: bold; font-size: 18px;")
        self.emergency_button.clicked.connect(self.handle_emergency_brake)
        self.emergency_button.setFixedHeight(150)
        # self.emergency_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        failure_column.addWidget(self.emergency_button)

        # Bottom-right: Physical Info + Sponsors (side-by-side)
        info_column = QHBoxLayout()

        physical_group = QGroupBox("Train Physical Info")
        physical_group.setFont(QFont("Arial", 16, QFont.Bold))
        physical_layout = QVBoxLayout()
        self.brake_status_label = QLabel("Main Brake: --")
        self.temp_label = QLabel("Cabin Temperature: -- °F")
        self.lights_label = QLabel("Interior Lights: --\nExterior Lights: --")
        self.doors_label = QLabel("Left Doors: --\nRight Doors: --")
        for label in [self.brake_status_label, self.temp_label, self.lights_label, self.doors_label]:
            physical_layout.addWidget(label)
        physical_group.setLayout(physical_layout)
        physical_group.setFixedWidth(300)

        sponsors_group = QGroupBox("Sponsors")
        sponsors_group.setFont(QFont("Arial", 16, QFont.Bold))
        sponsors_layout = QVBoxLayout()
        # self.pitt_logo = QLabel()
        # self.pitt_logo.setPixmap(QPixmap("Pitt_Logo.png"))
        # self.pitt_logo.setFixedSize(150,150)
        # self.pitt_logo.setAlignment(Qt.AlignCenter)
        self.laynes_logo = QLabel()
        self.laynes_logo.setPixmap(QPixmap("Laynes_Logo.png"))
        self.laynes_logo.setFixedSize(250,250)
        self.laynes_logo.setAlignment(Qt.AlignCenter)
        # sponsors_layout.addWidget(self.pitt_logo)
        sponsors_layout.addWidget(self.laynes_logo)
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
        self.train_model.engage_emergency_brake(True)
        self.emergency_button.setStyleSheet("background-color: darkred; color: white; font-weight: bold; font-size: 18px;")

    def update_display(self):
        self.velocity_label.setText(f"{self.train_model.velocity_mps * 2.237:.0f} mph")
        self.power_label.setText(f"Train Power: {self.train_model.power_watts:.0f} W")
        self.elevation_label.setText(f"Terrain Elevation: {self.train_model.elevation_m:.1f} m")
        self.speed_limit_label.setText(f"Speed Limit: {self.train_model.speed_limit_mps:.0f} mph")
        self.command_speed_label.setText(f"Commanded Speed: {self.train_model.command_speed_mps:.0f} mph")
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

        brake_pixmap = QPixmap("Siren_On.png" if self.train_model.brake_failure else "Siren_Off.png")
        signal_pixmap = QPixmap("Siren_On.png" if self.train_model.signal_failure else "Siren_Off.png")
        engine_pixmap = QPixmap("Siren_On.png" if self.train_model.engine_failure else "Siren_Off.png")

        self.brake_fail_light.setPixmap(brake_pixmap)
        self.signal_fail_light.setPixmap(signal_pixmap)
        self.engine_fail_light.setPixmap(engine_pixmap)

        # Emergency button visual reset
        if self.train_model.emergency_brake_engaged:
            self.emergency_button.setStyleSheet("background-color: darkred; color: white; font-weight: bold; font-size: 18px;")
        else:
            self.emergency_button.setStyleSheet("background-color: red; color: white; font-weight: bold; font-size: 18px;")

        # Update next stop
        if hasattr(self.train_model, 'next_stop'):
            self.next_stop_label.setText(f"Next Stop: {self.train_model.next_stop}")
            image_path = f"{self.train_model.next_stop.lower().replace(' ', '_')}.png"
            self.station_image.setPixmap(QPixmap(image_path))