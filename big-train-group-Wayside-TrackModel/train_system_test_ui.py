# =============================================================================
#  train_system_test_ui.py
# =============================================================================
"""
Test UI for simulating initial block data being passed directly to the 
IntegratedTrainSystem constructor instead of through the train controller
initialization UI.

This simulates how the system would be called from an external module
with pre-configured TrainControllerInit data.
"""

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
    QLabel, QPushButton, QComboBox, QSpinBox, QGroupBox, QGridLayout,
    QLineEdit, QCheckBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'train_controller_sw'))
sys.path.append(os.path.join(current_dir, 'train_controller_sw', 'controller'))

# Import data types and main system
from controller.data_types import TrainControllerInit, BlockInfo
from train_system_main import TrainSystemSW


class TrainSystemTestUI(QMainWindow):
    """
    Test UI that allows configuring initial block data and launching
    the IntegratedTrainSystem with that data directly.
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Train System Test Launcher")
        self.setGeometry(100, 100, 600, 500)
        
        self.init_ui()
        
        # Store reference to launched system
        self.launched_system = None
    
    def init_ui(self):
        """Initialize the test UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("Train System Test Launcher")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Configure initial block data and launch IntegratedTrainSystem directly")
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Basic Configuration Group
        basic_group = QGroupBox("Basic Configuration")
        basic_layout = QGridLayout(basic_group)
        
        # Track Color
        basic_layout.addWidget(QLabel("Track Color:"), 0, 0)
        self.track_color_combo = QComboBox()
        self.track_color_combo.addItems(["Red", "Green"])
        basic_layout.addWidget(self.track_color_combo, 0, 1)
        
        # Current Block
        basic_layout.addWidget(QLabel("Current Block:"), 1, 0)
        self.current_block_spin = QSpinBox()
        self.current_block_spin.setRange(1, 150)
        self.current_block_spin.setValue(1)
        basic_layout.addWidget(self.current_block_spin, 1, 1)
        
        # Train ID
        basic_layout.addWidget(QLabel("Train ID:"), 2, 0)
        self.train_id_spin = QSpinBox()
        self.train_id_spin.setRange(1, 999)
        self.train_id_spin.setValue(63)
        basic_layout.addWidget(self.train_id_spin, 2, 1)
        
        # Current Commanded Speed
        basic_layout.addWidget(QLabel("Current Commanded Speed:"), 3, 0)
        self.commanded_speed_spin = QSpinBox()
        self.commanded_speed_spin.setRange(0, 3)
        self.commanded_speed_spin.setValue(1)
        basic_layout.addWidget(self.commanded_speed_spin, 3, 1)
        
        # Authorization
        basic_layout.addWidget(QLabel("Authorized Current Block:"), 4, 0)
        self.authorized_check = QCheckBox()
        self.authorized_check.setChecked(True)
        basic_layout.addWidget(self.authorized_check, 4, 1)
        
        # Next Station Number
        basic_layout.addWidget(QLabel("Next Station Number:"), 5, 0)
        self.next_station_spin = QSpinBox()
        self.next_station_spin.setRange(0, 31)
        self.next_station_spin.setValue(5)
        basic_layout.addWidget(self.next_station_spin, 5, 1)
        
        layout.addWidget(basic_group)
        
        # Next Four Blocks Group
        blocks_group = QGroupBox("Next Four Blocks Configuration")
        blocks_layout = QGridLayout(blocks_group)
        
        # Headers
        blocks_layout.addWidget(QLabel("Block #"), 0, 0)
        blocks_layout.addWidget(QLabel("Commanded Speed"), 0, 1)
        blocks_layout.addWidget(QLabel("Authorized"), 0, 2)
        
        # Create input fields for 4 blocks
        self.block_inputs = []
        for i in range(4):
            row = i + 1
            
            # Block number
            block_num = QSpinBox()
            block_num.setRange(1, 150)
            block_num.setValue(self.current_block_spin.value() + i + 1)
            blocks_layout.addWidget(block_num, row, 0)
            
            # Commanded speed
            commanded_speed = QSpinBox()
            commanded_speed.setRange(0, 3)
            commanded_speed.setValue(1)
            blocks_layout.addWidget(commanded_speed, row, 1)
            
            # Authorized
            authorized = QCheckBox()
            authorized.setChecked(True)
            blocks_layout.addWidget(authorized, row, 2)
            
            self.block_inputs.append({
                'block_number': block_num,
                'commanded_speed': commanded_speed,
                'authorized': authorized
            })
        
        layout.addWidget(blocks_group)
        
        # Control Buttons
        button_layout = QHBoxLayout()
        
        # Auto-increment blocks button
        auto_increment_btn = QPushButton("Auto-Increment Block Numbers")
        auto_increment_btn.clicked.connect(self.auto_increment_blocks)
        button_layout.addWidget(auto_increment_btn)
        
        # Launch button
        launch_btn = QPushButton("Launch Train System")
        launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        launch_btn.clicked.connect(self.launch_train_system)
        button_layout.addWidget(launch_btn)
        
        layout.addLayout(button_layout)
        
        # Status label
        self.status_label = QLabel("Ready to launch")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.status_label)
        
        # Connect current block changes to auto-increment
        self.current_block_spin.valueChanged.connect(self.auto_increment_blocks)
    
    def auto_increment_blocks(self):
        """Auto-increment the next four blocks based on current block"""
        current_block = self.current_block_spin.value()
        for i, block_input in enumerate(self.block_inputs):
            block_input['block_number'].setValue(current_block + i + 1)
    
    def launch_train_system(self):
        """Launch the IntegratedTrainSystem with configured data"""
        try:
            self.status_label.setText("Preparing initialization data...")
            self.status_label.setStyleSheet("color: orange; font-style: italic;")
            
            # Build TrainControllerInit data
            init_data = self.build_train_controller_init()
            next_station_number = self.next_station_spin.value()
            
            self.status_label.setText("Launching Train System...")
            
            # Launch the integrated train system
            self.launched_system = TrainSystemSW(init_data, next_station_number)
            
            self.status_label.setText("Train System launched successfully!")
            self.status_label.setStyleSheet("color: green; font-style: italic;")
            
            print("=" * 50)
            print("TRAIN SYSTEM LAUNCHED WITH TEST DATA:")
            print(f"Track: {init_data.track_color}")
            print(f"Current Block: {init_data.current_block}")
            print(f"Train ID: {init_data.train_id}")
            print(f"Next Station: {next_station_number}")
            print(f"Next Four Blocks: {[block.block_number for block in init_data.next_four_blocks]}")
            print("=" * 50)
            
        except Exception as e:
            self.status_label.setText(f"Launch failed: {str(e)}")
            self.status_label.setStyleSheet("color: red; font-style: italic;")
            print(f"Error launching train system: {e}")
            import traceback
            traceback.print_exc()
    
    def build_train_controller_init(self) -> TrainControllerInit:
        """Build TrainControllerInit data from UI inputs"""
        
        # Build next four blocks
        next_four_blocks = []
        for block_input in self.block_inputs:
            block_info = BlockInfo(
                block_number=block_input['block_number'].value(),
                length_meters=100.0,  # Default value - controller will get actual from JSON
                speed_limit_mph=40.0,  # Default value - controller will get actual from JSON
                underground=False,  # Default value - controller will get actual from JSON
                authorized_to_go=block_input['authorized'].isChecked(),
                commanded_speed=block_input['commanded_speed'].value()
            )
            next_four_blocks.append(block_info)
        
        # Create TrainControllerInit
        init_data = TrainControllerInit(
            track_color=self.track_color_combo.currentText(),
            current_block=self.current_block_spin.value(),
            current_commanded_speed=self.commanded_speed_spin.value(),
            authorized_current_block=self.authorized_check.isChecked(),
            next_four_blocks=next_four_blocks,
            train_id=str(self.train_id_spin.value()),
            next_station_number=1  # Default value for test UI
        )
        
        return init_data


def main():
    """Main entry point for the test UI"""
    print("=" * 50)
    print("TRAIN SYSTEM TEST LAUNCHER")
    print("=" * 50)
    
    app = QApplication(sys.argv)
    
    try:
        test_ui = TrainSystemTestUI()
        test_ui.show()
        
        print("Test UI ready. Configure parameters and click 'Launch Train System'")
        print("This will pass TrainControllerInit data directly to the system constructor.")
        
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"TEST UI STARTUP FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()