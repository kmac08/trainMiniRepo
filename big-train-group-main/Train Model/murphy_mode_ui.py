# murphy_mode_ui.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt

class MurphyModeWindow(QWidget):
    def __init__(self, train_model):
        super().__init__()
        self.train_model = train_model

        self.setWindowTitle(f"Murphy Mode - {train_model.train_id}")
        self.setGeometry(200, 200, 300, 200)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Murphy Mode (Toggle Failures)", alignment=Qt.AlignCenter))

        # Signal Failure Toggle
        self.signal_button = QPushButton()
        self.signal_button.setCheckable(True)
        self.signal_button.clicked.connect(self.toggle_signal_failure)
        layout.addWidget(self.signal_button)

        # Brake Failure Toggle
        self.brake_button = QPushButton()
        self.brake_button.setCheckable(True)
        self.brake_button.clicked.connect(self.toggle_brake_failure)
        layout.addWidget(self.brake_button)

        # Engine Failure Toggle
        self.engine_button = QPushButton()
        self.engine_button.setCheckable(True)
        self.engine_button.clicked.connect(self.toggle_engine_failure)
        layout.addWidget(self.engine_button)

        self.setLayout(layout)
        self.sync_with_model()

    def toggle_signal_failure(self):
        self.train_model.signal_failure = self.signal_button.isChecked()
        self.signal_button.setText(
            "Disengage Signal Failure" if self.signal_button.isChecked() else "Engage Signal Failure"
        )

    def toggle_brake_failure(self):
        self.train_model.brake_failure = self.brake_button.isChecked()
        self.brake_button.setText(
            "Disengage Brake Failure" if self.brake_button.isChecked() else "Engage Brake Failure"
        )

    def toggle_engine_failure(self):
        self.train_model.engine_failure = self.engine_button.isChecked()
        self.engine_button.setText(
            "Disengage Engine Failure" if self.engine_button.isChecked() else "Engage Engine Failure"
        )

    def sync_with_model(self):
        self.signal_button.setChecked(self.train_model.signal_failure)
        self.signal_button.setText(
            "Disengage Signal Failure" if self.train_model.signal_failure else "Engage Signal Failure"
        )

        self.brake_button.setChecked(self.train_model.brake_failure)
        self.brake_button.setText(
            "Disengage Brake Failure" if self.train_model.brake_failure else "Engage Brake Failure"
        )

        self.engine_button.setChecked(self.train_model.engine_failure)
        self.engine_button.setText(
            "Disengage Engine Failure" if self.train_model.engine_failure else "Engage Engine Failure"
        )
