# ui/train_controller_engineer.py
import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QLabel, QSpinBox, QDoubleSpinBox, QPushButton, QVBoxLayout, 
    QHBoxLayout, QMessageBox, QGroupBox, QGridLayout
)
from PyQt5.QtCore import pyqtSignal, Qt

# Add path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Try different import approaches
try:
    from train_controller_hw.controller.data_types import EngineerInput
except ImportError:
    try:
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from controller.data_types import EngineerInput
    except ImportError:
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'controller')))
        from data_types import EngineerInput


class EngineerUI(QWidget):
    """
    GUI for train engineer to input Kp and Ki values.
    Emits kp_ki_submitted signal when Apply is clicked with valid values.
    """
    kp_ki_submitted = pyqtSignal(EngineerInput)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Train Controller - Engineer")
        self.train_controller = None  # Reference to train controller for speed checking
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the engineer UI with responsive layout"""
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Create group box for PID controls
        pid_group = QGroupBox("PID Controller Configuration")
        pid_layout = QGridLayout()
        pid_layout.setSpacing(10)
        
        # Header label
        header_label = QLabel("Configure the Proportional-Integral controller gains:")
        header_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        pid_layout.addWidget(header_label, 0, 0, 1, 3)
        
        # Kp controls
        kp_label = QLabel("Proportional Gain (Kp):")
        kp_label.setToolTip("Proportional gain in kW/(m/s)")
        self.kp_spinbox = QDoubleSpinBox()
        self.kp_spinbox.setRange(0.1, 100.0)  # Prevent negative values
        self.kp_spinbox.setDecimals(1)
        self.kp_spinbox.setSingleStep(0.5)
        self.kp_spinbox.setValue(12.0)  # Default value
        self.kp_spinbox.setSuffix(" kW/(m/s)")
        self.kp_spinbox.setMinimumWidth(150)
        
        kp_info = QLabel("ⓘ")
        kp_info.setToolTip("Controls how aggressively the system responds to speed errors")
        kp_info.setStyleSheet("color: blue; font-weight: bold;")
        
        pid_layout.addWidget(kp_label, 1, 0)
        pid_layout.addWidget(self.kp_spinbox, 1, 1)
        pid_layout.addWidget(kp_info, 1, 2)
        
        # Ki controls
        ki_label = QLabel("Integral Gain (Ki):")
        ki_label.setToolTip("Integral gain in kW/(m)")
        self.ki_spinbox = QDoubleSpinBox()
        self.ki_spinbox.setRange(0.0, 10.0)  # Allow 0 for Ki
        self.ki_spinbox.setDecimals(1)
        self.ki_spinbox.setSingleStep(0.1)
        self.ki_spinbox.setValue(1.2)  # Default value
        self.ki_spinbox.setSuffix(" kW/(m)")
        self.ki_spinbox.setMinimumWidth(150)
        
        ki_info = QLabel("ⓘ")
        ki_info.setToolTip("Controls how the system responds to accumulated errors over time")
        ki_info.setStyleSheet("color: blue; font-weight: bold;")
        
        pid_layout.addWidget(ki_label, 2, 0)
        pid_layout.addWidget(self.ki_spinbox, 2, 1)
        pid_layout.addWidget(ki_info, 2, 2)
        
        # Add some spacing
        pid_layout.setColumnStretch(1, 1)
        pid_group.setLayout(pid_layout)
        
        # Current values display
        current_group = QGroupBox("Current Controller Values")
        current_layout = QHBoxLayout()
        
        self.current_kp_label = QLabel("Kp: 12.0")
        self.current_ki_label = QLabel("Ki: 1.2")
        self.current_kp_label.setStyleSheet("font-size: 11px; padding: 5px;")
        self.current_ki_label.setStyleSheet("font-size: 11px; padding: 5px;")
        
        current_layout.addWidget(self.current_kp_label)
        current_layout.addWidget(self.current_ki_label)
        current_layout.addStretch()
        current_group.setLayout(current_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: palette(button);
                border: 1px solid palette(mid);
                border-radius: 3px;
                padding: 5px 15px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: palette(light);
            }
        """)
        self.reset_button.clicked.connect(self.reset_to_defaults)
        
        self.apply_button = QPushButton("Apply Changes")
        self.apply_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border: 1px solid #45a049;
                border-radius: 3px;
                padding: 5px 15px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.apply_button.clicked.connect(self.apply_clicked)
        
        button_layout.addStretch()
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.apply_button)
        
        # Add all to main layout
        main_layout.addWidget(pid_group)
        main_layout.addWidget(current_group)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # Set size constraints
        self.setMinimumWidth(400)
        self.setMaximumHeight(250)
    
    def set_train_controller(self, train_controller):
        """Set the train controller reference for speed checking"""
        self.train_controller = train_controller
    
    def reset_to_defaults(self):
        """Reset spinboxes to default values"""
        self.kp_spinbox.setValue(12.0)
        self.ki_spinbox.setValue(1.2)
    
    def apply_clicked(self):
        """Handle apply button click"""
        # Check if train is moving (prevent changes during movement)
        if self.train_controller is not None:
            if hasattr(self.train_controller, 'last_train_input') and self.train_controller.last_train_input:
                current_speed = self.train_controller.last_train_input.actual_speed
                if current_speed > 0.1:  # 0.1 mph threshold
                    QMessageBox.critical(self, "Train is Moving", 
                                       f"Cannot change Kp/Ki while train is moving!\n"
                                       f"Current speed: {current_speed:.1f} mph\n"
                                       f"Stop the train before changing controller gains.")
                    return
        
        kp = self.kp_spinbox.value()
        ki = self.ki_spinbox.value()
        
        # Validate values (already constrained by spinbox ranges)
        if kp <= 0:
            QMessageBox.warning(self, "Input Error", 
                              "Kp must be greater than 0.")
            return
        
        # Emit the engineer input
        engineer_input = EngineerInput(kp=kp, ki=ki)
        self.kp_ki_submitted.emit(engineer_input)
        
        # Update current values display
        self.current_kp_label.setText(f"Kp: {kp:.1f}")
        self.current_ki_label.setText(f"Ki: {ki:.1f}")
        
        # Show confirmation
        QMessageBox.information(self, "Success", 
                              f"Controller gains updated:\nKp = {kp:.1f}\nKi = {ki:.1f}")
    
    def update_current_values(self, kp: float, ki: float):
        """Update the current values display"""
        self.current_kp_label.setText(f"Kp: {kp:.1f}")
        self.current_ki_label.setText(f"Ki: {ki:.1f}")
        # Don't update spinboxes - let user control them


# Standalone window version for backward compatibility
class EngineerWindow(QWidget):
    """
    Standalone window version of Engineer UI.
    Maintains compatibility with existing code.
    """
    kp_ki_submitted = pyqtSignal(EngineerInput)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Train Controller - Engineer")
        self.train_controller = None  # Reference to train controller for speed checking
        self.setup_ui()
        self.setFixedSize(500, 200)
    
    def set_train_controller(self, train_controller):
        """Set the train controller reference for speed checking"""
        self.train_controller = train_controller

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_label = QLabel("Please input numeric Kp and Ki values.")
        header_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header_label)

        # Kp Input
        kp_layout = QHBoxLayout()
        kp_label = QLabel("Kp value:")
        kp_label.setMinimumWidth(80)
        self.kp_spinbox = QDoubleSpinBox()
        self.kp_spinbox.setRange(0.1, 100.0)  # Prevent negative and zero
        self.kp_spinbox.setDecimals(1)
        self.kp_spinbox.setValue(10.0)
        self.kp_spinbox.setSuffix(" kW/(m/s)")
        kp_layout.addWidget(kp_label)
        kp_layout.addWidget(self.kp_spinbox)
        layout.addLayout(kp_layout)

        # Ki Input
        ki_layout = QHBoxLayout()
        ki_label = QLabel("Ki value:")
        ki_label.setMinimumWidth(80)
        self.ki_spinbox = QDoubleSpinBox()
        self.ki_spinbox.setRange(0.0, 10.0)  # Allow zero for Ki
        self.ki_spinbox.setDecimals(1)
        self.ki_spinbox.setValue(1.0)
        self.ki_spinbox.setSuffix(" kW/(m)")
        ki_layout.addWidget(ki_label)
        ki_layout.addWidget(self.ki_spinbox)
        layout.addLayout(ki_layout)

        # Save button
        save_button = QPushButton("Save")
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px;
                font-size: 14px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        save_button.clicked.connect(self.save_clicked)
        layout.addWidget(save_button)

        self.setLayout(layout)

    def save_clicked(self):
        # Check if train is moving (prevent changes during movement)
        if self.train_controller is not None:
            if hasattr(self.train_controller, 'last_train_input') and self.train_controller.last_train_input:
                current_speed = self.train_controller.last_train_input.actual_speed
                if current_speed > 0.1:  # 0.1 mph threshold
                    QMessageBox.critical(self, "Train is Moving", 
                                       f"Cannot change Kp/Ki while train is moving!\n"
                                       f"Current speed: {current_speed:.1f} mph\n"
                                       f"Stop the train before changing controller gains.")
                    return
        
        kp = self.kp_spinbox.value()
        ki = self.ki_spinbox.value()
        
        if kp <= 0:
            QMessageBox.warning(self, "Input Error", 
                              "Kp must be greater than 0.")
            return
            
        self.kp_ki_submitted.emit(EngineerInput(kp=kp, ki=ki))
        self.close()


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)

    # Test the standalone window
    window = EngineerWindow()
    window.kp_ki_submitted.connect(lambda x: print(f"Submitted: Kp={x.kp}, Ki={x.ki}"))
    window.show()

    sys.exit(app.exec_())