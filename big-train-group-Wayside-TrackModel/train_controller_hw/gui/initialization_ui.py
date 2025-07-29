"""
Initialization UI for Train Controller
=====================================
This UI appears first when main_test.py is run, allowing the user to input
initialization data including track color, current block, and next 4 blocks
information before the train controller is created.
"""

import sys
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
                             QSpinBox, QCheckBox, QPushButton, QGroupBox, QGridLayout,
                             QDoubleSpinBox, QMessageBox, QApplication, QLineEdit)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont

# Add paths for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from controller.data_types import TrainControllerInit, BlockInfo


class InitializationUI(QWidget):
    """
    UI for entering train controller initialization data.
    Emits initialization_complete signal when all data is entered and validated.
    """
    
    initialization_complete = pyqtSignal(object)  # Emits TrainControllerInit object
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the initialization UI"""
        self.setWindowTitle("Train Controller Initialization")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 10px;
                margin: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Train Controller Initialization")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: #333333; margin: 20px;")
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel("Please enter the initialization data for the train controller.\n"
                             "All fields are required to proceed.")
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setStyleSheet("color: #666666; margin: 10px;")
        layout.addWidget(instructions)
        
        # Track Color Group
        color_group = QGroupBox("Track Color")
        color_layout = QHBoxLayout()
        
        color_layout.addWidget(QLabel("Select Track Color:"))
        self.track_color_combo = QComboBox()
        self.track_color_combo.addItems(["Red", "Green"])
        color_layout.addWidget(self.track_color_combo)
        color_layout.addStretch()
        
        color_group.setLayout(color_layout)
        layout.addWidget(color_group)
        
        # Train Information Group
        train_info_group = QGroupBox("Train Information")
        train_info_layout = QGridLayout()
        
        train_info_layout.addWidget(QLabel("Train ID:"), 0, 0)
        self.train_id_input = QLineEdit()
        self.train_id_input.setPlaceholderText("Enter train ID (e.g., '1', '2', '3')")
        self.train_id_input.setText("1")  # Default value
        train_info_layout.addWidget(self.train_id_input, 0, 1)
        
        train_info_layout.addWidget(QLabel("Next Station Number:"), 0, 2)
        self.next_station_spin = QSpinBox()
        self.next_station_spin.setMinimum(1)
        self.next_station_spin.setMaximum(1000)
        self.next_station_spin.setValue(1)  # Default value
        train_info_layout.addWidget(self.next_station_spin, 0, 3)
        
        train_info_group.setLayout(train_info_layout)
        layout.addWidget(train_info_group)
        
        # Current Block Group
        current_block_group = QGroupBox("Current Block Information")
        current_layout = QGridLayout()
        
        current_layout.addWidget(QLabel("Block Number:"), 0, 0)
        self.current_block_spin = QSpinBox()
        self.current_block_spin.setMinimum(1)
        self.current_block_spin.setMaximum(1000)
        self.current_block_spin.setValue(1)
        current_layout.addWidget(self.current_block_spin, 0, 1)
        
        current_layout.addWidget(QLabel("Commanded Speed:"), 0, 2)
        self.current_speed_combo = QComboBox()
        self.current_speed_combo.addItems(["0", "1", "2", "3"])
        current_layout.addWidget(self.current_speed_combo, 0, 3)
        
        current_layout.addWidget(QLabel("Authorized:"), 1, 0)
        self.current_authorized_check = QCheckBox()
        self.current_authorized_check.setChecked(True)
        current_layout.addWidget(self.current_authorized_check, 1, 1)
        
        current_block_group.setLayout(current_layout)
        layout.addWidget(current_block_group)
        
        # Next 4 Blocks Group
        next_blocks_group = QGroupBox("Next 4 Blocks Information")
        next_layout = QGridLayout()
        
        # Headers - block number, commanded speed, and authorization (length, speed limit, underground come from JSON)
        next_layout.addWidget(QLabel("Block #"), 0, 0)
        next_layout.addWidget(QLabel("Commanded Speed"), 0, 1)
        next_layout.addWidget(QLabel("Authorized"), 0, 2)
        next_layout.addWidget(QLabel("(Length, Speed Limit, Underground from JSON)"), 0, 3)
        
        # Create input fields for 4 blocks
        self.next_block_inputs = []
        for i in range(4):
            row = i + 1
            
            # Block number
            block_num_spin = QSpinBox()
            block_num_spin.setMinimum(1)
            block_num_spin.setMaximum(1000)
            block_num_spin.setValue(i + 2)  # Default to sequential blocks
            next_layout.addWidget(block_num_spin, row, 0)
            
            # Commanded Speed (0, 1, 2, 3)
            commanded_speed_combo = QComboBox()
            commanded_speed_combo.addItems(["0", "1", "2", "3"])
            commanded_speed_combo.setCurrentText("2")  # Default to speed level 2
            next_layout.addWidget(commanded_speed_combo, row, 1)
            
            # Authorized
            authorized_check = QCheckBox()
            authorized_check.setChecked(True)
            next_layout.addWidget(authorized_check, row, 2)
            
            # Info label showing this comes from JSON
            info_label = QLabel("Auto-populated from track data")
            info_label.setStyleSheet("color: #666666; font-style: italic;")
            next_layout.addWidget(info_label, row, 3)
            
            self.next_block_inputs.append({
                'block_num': block_num_spin,
                'commanded_speed': commanded_speed_combo,
                'authorized': authorized_check
            })
        
        next_blocks_group.setLayout(next_layout)
        layout.addWidget(next_blocks_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.validate_btn = QPushButton("Validate Data")
        self.validate_btn.clicked.connect(self.validate_data)
        button_layout.addWidget(self.validate_btn)
        
        self.initialize_btn = QPushButton("Initialize Train Controller")
        self.initialize_btn.clicked.connect(self.initialize_controller)
        self.initialize_btn.setEnabled(False)
        button_layout.addWidget(self.initialize_btn)
        
        layout.addLayout(button_layout)
        
        # Status label
        self.status_label = QLabel("Status: Ready for input")
        self.status_label.setStyleSheet("color: #666666; margin: 10px;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def validate_data(self):
        """Validate all input data"""
        try:
            # Validate train ID
            train_id = self.train_id_input.text().strip()
            if not train_id:
                raise ValueError("Train ID cannot be empty")
            
            # Validate current block
            current_block = self.current_block_spin.value()
            if current_block <= 0:
                raise ValueError("Current block must be positive")
            
            # Validate next 4 blocks
            for i, input_set in enumerate(self.next_block_inputs):
                block_num = input_set['block_num'].value()
                
                if block_num <= 0:
                    raise ValueError(f"Block {i+1} number must be positive")
            
            # Check for duplicate block numbers
            all_blocks = [current_block] + [inp['block_num'].value() for inp in self.next_block_inputs]
            if len(set(all_blocks)) != len(all_blocks):
                raise ValueError("Duplicate block numbers found")
            
            self.status_label.setText("Status: Data validation successful")
            self.status_label.setStyleSheet("color: #4CAF50; margin: 10px;")
            self.initialize_btn.setEnabled(True)
            
        except ValueError as e:
            QMessageBox.warning(self, "Validation Error", str(e))
            self.status_label.setText(f"Status: Validation failed - {str(e)}")
            self.status_label.setStyleSheet("color: #FF6B6B; margin: 10px;")
            self.initialize_btn.setEnabled(False)
    
    def initialize_controller(self):
        """Create TrainControllerInit object and emit signal"""
        try:
            # Create BlockInfo objects for next 4 blocks
            # Note: This UI represents the train model side, so we only provide the data
            # that the train model would know (block number, commanded speed, authorization)
            # The train controller will fill in track data (length, speed limit, underground) from JSON
            next_four_blocks = []
            
            for input_set in self.next_block_inputs:
                block_number = input_set['block_num'].value()
                commanded_speed = int(input_set['commanded_speed'].currentText())
                authorized = input_set['authorized'].isChecked()
                
                # Train model side only provides these fields - controller fills the rest from track data
                block_info = BlockInfo(
                    block_number=block_number,
                    length_meters=0.0,  # Will be filled by controller from track data
                    speed_limit_mph=0.0,  # Will be filled by controller from track data
                    underground=False,  # Will be filled by controller from track data
                    authorized_to_go=authorized,
                    commanded_speed=commanded_speed
                )
                next_four_blocks.append(block_info)
            
            # Create TrainControllerInit object
            init_data = TrainControllerInit(
                track_color=self.track_color_combo.currentText().lower(),
                current_block=self.current_block_spin.value(),
                current_commanded_speed=int(self.current_speed_combo.currentText()),
                authorized_current_block=self.current_authorized_check.isChecked(),
                next_four_blocks=next_four_blocks,
                train_id=self.train_id_input.text().strip(),
                next_station_number=self.next_station_spin.value()
            )
            
            # Emit the signal
            self.initialization_complete.emit(init_data)
            
            self.status_label.setText("Status: Initialization complete - starting train controller...")
            self.status_label.setStyleSheet("color: #4CAF50; margin: 10px;")
            
            # Hide this window
            self.hide()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to initialize controller: {str(e)}")
            self.status_label.setText(f"Status: Initialization failed - {str(e)}")
            self.status_label.setStyleSheet("color: #FF6B6B; margin: 10px;")


def main():
    """Test the initialization UI"""
    app = QApplication(sys.argv)
    
    def on_initialization_complete(init_data):
        print("Initialization complete!")
        print(f"Track Color: {init_data.track_color}")
        print(f"Current Block: {init_data.current_block}")
        print(f"Current Speed: {init_data.current_commanded_speed}")
        print(f"Authorized: {init_data.authorized_current_block}")
        print("Next 4 blocks:")
        for i, block in enumerate(init_data.next_four_blocks):
            print(f"  Block {i+1}: {block}")
    
    ui = InitializationUI()
    ui.initialization_complete.connect(on_initialization_complete)
    ui.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()