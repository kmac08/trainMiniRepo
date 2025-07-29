# train_test_ui.py

from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton, QLineEdit, QCheckBox, QComboBox, QApplication
)
from PyQt5.QtCore import Qt, QTimer
from train_dashboard_ui import TrainDashboard
from murphy_mode_ui import MurphyModeWindow

class TrainTestUI(QWidget):
    def __init__(self, train_models):
        super().__init__()
        self.train_models = train_models
        self.current_model = None
        self.dashboard_window = None
        self.murphy_window = None

        self.setWindowTitle("Train Test Interface")
        self.setGeometry(100, 100, 400, 500)
        self.init_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)
        self.timer.start(100)  # 10 Hz simulation

    def init_ui(self):
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Select Train ID"))
        self.train_selector = QComboBox()
        self.train_selector.addItems(self.train_models.keys())
        self.train_selector.currentIndexChanged.connect(self.switch_train)
        layout.addWidget(self.train_selector)

        open_dashboard_btn = QPushButton("Open Train Dashboard")
        open_dashboard_btn.clicked.connect(self.open_dashboard_and_murphy)
        layout.addWidget(open_dashboard_btn)

        self.power_input = QLineEdit()
        self.power_input.setPlaceholderText("Power in Watts")
        power_button = QPushButton("Set Power")
        power_button.clicked.connect(self.set_power)
        layout.addWidget(QLabel("Train Power (W)"))
        layout.addWidget(self.power_input)
        layout.addWidget(power_button)

        self.temp_input = QLineEdit()
        self.temp_input.setPlaceholderText("Temperature in °F")
        temp_button = QPushButton("Set Cabin Temperature")
        temp_button.clicked.connect(lambda: self.current_model.set_cabin_temperature(float(self.temp_input.text())))
        layout.addWidget(QLabel("Cabin Temperature (°F)"))
        layout.addWidget(self.temp_input)
        layout.addWidget(temp_button)

        self.speed_input = QLineEdit()
        self.speed_input.setPlaceholderText("Speed Limit (mph)")
        speed_button = QPushButton("Set Speed Limit")
        speed_button.clicked.connect(self.set_speed_limit)
        layout.addWidget(QLabel("Speed Limit (mph)"))
        layout.addWidget(self.speed_input)
        layout.addWidget(speed_button)

        self.grade_input = QLineEdit()
        self.grade_input.setPlaceholderText("Grade %")
        grade_button = QPushButton("Set Grade")
        grade_button.clicked.connect(self.set_grade)
        layout.addWidget(QLabel("Terrain Grade (%)"))
        layout.addWidget(self.grade_input)
        layout.addWidget(grade_button)

        self.authority_input = QLineEdit()
        self.authority_input.setPlaceholderText("Authority (m)")
        authority_button = QPushButton("Set Authority")
        authority_button.clicked.connect(self.set_authority)
        layout.addWidget(QLabel("Authority Distance (m)"))
        layout.addWidget(self.authority_input)
        layout.addWidget(authority_button)

        self.interior_light_check = QCheckBox("Interior Lights")
        self.exterior_light_check = QCheckBox("Exterior Lights")
        self.left_door_check = QCheckBox("Left Doors")
        self.right_door_check = QCheckBox("Right Doors")
        self.service_brake_check = QCheckBox("Service Brake")

        self.interior_light_check.stateChanged.connect(lambda state: self.current_model.set_interior_lights(state == Qt.Checked))
        self.exterior_light_check.stateChanged.connect(lambda state: self.current_model.set_exterior_lights(state == Qt.Checked))
        self.left_door_check.stateChanged.connect(lambda state: self.current_model.set_left_doors(state == Qt.Checked))
        self.right_door_check.stateChanged.connect(lambda state: self.current_model.set_right_doors(state == Qt.Checked))
        self.service_brake_check.stateChanged.connect(lambda state: self.current_model.set_service_brake(state == Qt.Checked))

        layout.addWidget(self.interior_light_check)
        layout.addWidget(self.exterior_light_check)
        layout.addWidget(self.left_door_check)
        layout.addWidget(self.right_door_check)
        layout.addWidget(self.service_brake_check)

        # Emergency Brake Reset Button
        self.reset_emergency_btn = QPushButton("Reset Emergency Brake")
        self.reset_emergency_btn.clicked.connect(self.reset_emergency_brake)
        layout.addWidget(self.reset_emergency_btn)

        # Next Stop Selector
        layout.addWidget(QLabel("Next Stop"))
        self.next_stop_selector = QComboBox()
        self.next_stop_selector.addItems(["Station B", "Station C", "Yard"])
        self.next_stop_selector.currentTextChanged.connect(self.set_next_stop)
        layout.addWidget(self.next_stop_selector)

        self.setLayout(layout)
        self.switch_train(0)

    def switch_train(self, index):
        train_id = self.train_selector.itemText(index)
        self.current_model = self.train_models[train_id]

    def open_dashboard_and_murphy(self):
        if self.dashboard_window:
            self.dashboard_window.close()
        if self.murphy_window:
            self.murphy_window.close()

        self.dashboard_window = TrainDashboard(self.current_model)
        self.dashboard_window.show()

        self.murphy_window = MurphyModeWindow(self.current_model)
        self.murphy_window.show()

    def update_simulation(self):
        if self.current_model:
            self.current_model.update_speed(0.1)  # 100ms timestep

    def set_power(self):
        try:
            power = float(self.power_input.text())
            self.current_model.set_power(power)
        except ValueError:
            # Invalid input - ignore silently
            return

    def set_speed_limit(self):
        try:
            speed_limit = float(self.speed_input.text())
            self.current_model.set_speed_limit(speed_limit)
        except ValueError:
            # Invalid input - ignore silently
            return

    def set_grade(self):
        try:
            grade = float(self.grade_input.text())
            self.current_model.grade_percent = grade
        except ValueError:
            # Invalid input - ignore silently
            return
    
    def set_authority(self):
        try:
            authority = float(self.authority_input.text())
            self.current_model.authority_m = authority
        except ValueError:
            # Invalid input - ignore silently
            return

    def reset_emergency_brake(self):
        if self.current_model and self.current_model.emergency_brake_engaged:
            self.current_model.engage_emergency_brake(False)

    def set_next_stop(self, station_name):
        if self.current_model:
            self.current_model.next_stop = station_name