#!/usr/bin/env python3
"""
Train Model Test Bench UI
Simulates the Train Model module for testing the Train Controller
This version is isolated and only communicates through main_test.py
"""

import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

# Add paths for imports
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from controller.data_types import TrainModelInput, TrainModelOutput


class TrainModelTestBench(QWidget):
    """Test bench UI for simulating Train Model inputs/outputs"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Train Model Test Bench")
        self.setGeometry(100, 100, 1200, 800)
        
        # Store pending values (edited in UI but not sent yet)
        self.pending_values = {
            'actual_speed': 0.0,
            'commanded_speed': 0.0,
            'speed_limit': 40.0,
            'authority': 1000.0,
            'cabin_temperature': 72.0,
            'next_station_number': 1,
            'engine_fault': False,
            'signal_fault': False,
            'brake_fault': False,
            'passenger_emergency_brake': False,
            'train_underground': False
        }
        
        # Store current values (actually being sent)
        self.current_train_input = TrainModelInput(
            fault_status={'signal': False, 'brake': False, 'engine': False},
            actual_speed=0.0,
            passenger_emergency_brake=False,
            cabin_temperature=72.0,
            next_station_number=1,
            authority_threshold=50.0,  # Default value, will be updated from UI
            add_new_block_info=False,  # Default to no new block info
            next_block_info={},  # Empty dict initially
            next_block_entered=False,  # Default to False
            update_next_block_info=False  # Default to False
        )
        
        # Store last received output
        self.last_output = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the test bench UI"""
        # Main horizontal layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Left side - Train Model Outputs (sends to Controller)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Title
        title_label = QLabel("Train Model → Train Controller")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title_label)
        
        # Scroll area for inputs
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        input_layout = QVBoxLayout(scroll_content)
        
        # Speed Controls Group
        speed_group = QGroupBox("Speed Controls")
        speed_layout = QGridLayout()
        
        # Actual Speed
        speed_layout.addWidget(QLabel("Actual Speed (mph):"), 0, 0)
        self.actual_speed_spin = QDoubleSpinBox()
        self.actual_speed_spin.setRange(0.0, 100.0)
        self.actual_speed_spin.setDecimals(1)
        self.actual_speed_spin.setValue(0.0)
        self.actual_speed_spin.setSuffix(" mph")
        speed_layout.addWidget(self.actual_speed_spin, 0, 1)
        
        # Commanded Speed - REMOVED: Now comes from next_block_info
        # speed_layout.addWidget(QLabel("Commanded Speed (mph):"), 1, 0)
        # self.commanded_speed_spin = QDoubleSpinBox()
        # self.commanded_speed_spin.setRange(0.0, 100.0)
        # self.commanded_speed_spin.setDecimals(1)
        # self.commanded_speed_spin.setValue(0.0)
        # self.commanded_speed_spin.setSuffix(" mph")
        # speed_layout.addWidget(self.commanded_speed_spin, 1, 1)
        
        # Speed Limit - REMOVED: Now comes from JSON track data
        # The train controller gets speed limit from the track JSON file
        # speed_layout.addWidget(QLabel("Speed Limit (mph):"), 2, 0)
        # self.speed_limit_spin = QDoubleSpinBox()
        # self.speed_limit_spin.setRange(0.0, 100.0)
        # self.speed_limit_spin.setDecimals(1)
        # self.speed_limit_spin.setValue(40.0)
        # self.speed_limit_spin.setSuffix(" mph")
        # speed_layout.addWidget(self.speed_limit_spin, 2, 1)
        
        speed_group.setLayout(speed_layout)
        input_layout.addWidget(speed_group)
        
        # Authority and Temperature Group
        auth_temp_group = QGroupBox("Authority & Temperature")
        auth_temp_layout = QGridLayout()
        
        # Authority - REMOVED: Now calculated by train controller from block data
        # auth_temp_layout.addWidget(QLabel("Authority (yards):"), 0, 0)
        # self.authority_spin = QDoubleSpinBox()
        # self.authority_spin.setRange(0.0, 10000.0)
        # self.authority_spin.setDecimals(1)
        # self.authority_spin.setValue(1000.0)
        # self.authority_spin.setSuffix(" yards")
        # auth_temp_layout.addWidget(self.authority_spin, 0, 1)
        
        # Authority Threshold
        auth_temp_layout.addWidget(QLabel("Authority Threshold (yards):"), 1, 0)
        self.authority_threshold_spin = QDoubleSpinBox()
        self.authority_threshold_spin.setRange(0.0, 1000.0)
        self.authority_threshold_spin.setDecimals(1)
        self.authority_threshold_spin.setValue(50.0)
        self.authority_threshold_spin.setSuffix(" yards")
        auth_temp_layout.addWidget(self.authority_threshold_spin, 1, 1)
        
        # Cabin Temperature
        auth_temp_layout.addWidget(QLabel("Cabin Temperature (°F):"), 2, 0)
        self.cabin_temp_spin = QDoubleSpinBox()
        self.cabin_temp_spin.setRange(32.0, 100.0)
        self.cabin_temp_spin.setDecimals(1)
        self.cabin_temp_spin.setValue(72.0)
        self.cabin_temp_spin.setSuffix(" °F")
        auth_temp_layout.addWidget(self.cabin_temp_spin, 2, 1)
        
        auth_temp_group.setLayout(auth_temp_layout)
        input_layout.addWidget(auth_temp_group)
        
        # Station Information Group
        station_group = QGroupBox("Station Information")
        station_layout = QGridLayout()
        
        # Next Station Number
        station_layout.addWidget(QLabel("Next Station Number:"), 0, 0)
        self.next_station_number_spin = QSpinBox()
        self.next_station_number_spin.setRange(0, 999)
        self.next_station_number_spin.setValue(1)
        self.next_station_number_spin.setSuffix("")
        station_layout.addWidget(self.next_station_number_spin, 0, 1)
        
        # Note about station lookup
        station_note = QLabel("Note: Station name and side will be looked up automatically from track data")
        station_note.setStyleSheet("font-style: italic; color: #666;")
        station_note.setWordWrap(True)
        station_layout.addWidget(station_note, 1, 0, 1, 2)
        
        station_group.setLayout(station_layout)
        input_layout.addWidget(station_group)
        
        # Train ID Management Group
        train_id_group = QGroupBox("Available Train IDs")
        train_id_layout = QVBoxLayout()
        
        # Text input for train IDs
        train_id_layout.addWidget(QLabel("Available Train IDs (comma-separated):"))
        self.train_ids_edit = QLineEdit("1,2,3,4,5")
        self.train_ids_edit.setPlaceholderText("e.g., 1,2,3,4,5,6")
        train_id_layout.addWidget(self.train_ids_edit)
        
        # Add/Remove buttons
        train_id_button_layout = QHBoxLayout()
        self.add_train_btn = QPushButton("Add Train")
        self.add_train_btn.clicked.connect(self.add_new_train)
        self.remove_train_btn = QPushButton("Remove Last Train")
        self.remove_train_btn.clicked.connect(self.remove_last_train)
        
        train_id_button_layout.addWidget(self.add_train_btn)
        train_id_button_layout.addWidget(self.remove_train_btn)
        train_id_layout.addLayout(train_id_button_layout)
        
        train_id_group.setLayout(train_id_layout)
        input_layout.addWidget(train_id_group)
        
        # Fault Status Group
        fault_group = QGroupBox("Fault Status")
        fault_layout = QVBoxLayout()
        
        self.engine_fault_check = QCheckBox("Engine Failure")
        self.signal_fault_check = QCheckBox("Signal Failure")
        self.brake_fault_check = QCheckBox("Brake Failure")
        
        fault_layout.addWidget(self.engine_fault_check)
        fault_layout.addWidget(self.signal_fault_check)
        fault_layout.addWidget(self.brake_fault_check)
        
        fault_group.setLayout(fault_layout)
        input_layout.addWidget(fault_group)
        
        # Emergency Brake
        emerg_group = QGroupBox("Emergency Systems")
        emerg_layout = QVBoxLayout()
        
        self.passenger_ebrake_check = QCheckBox("Passenger Emergency Brake")
        self.passenger_ebrake_check.setStyleSheet("""
            QCheckBox:checked {
                color: red;
                font-weight: bold;
            }
        """)
        emerg_layout.addWidget(self.passenger_ebrake_check)
        
        # Underground checkbox - REMOVED: Now determined from track data by train controller
        # self.underground_check = QCheckBox("Train Underground")
        # self.underground_check.setStyleSheet("""
        #     QCheckBox:checked {
        #         color: orange;
        #         font-weight: bold;
        #     }
        # """)
        # emerg_layout.addWidget(self.underground_check)
        
        emerg_group.setLayout(emerg_layout)
        input_layout.addWidget(emerg_group)
        
        # Block Information Group - NEW: Missing fields from train model
        block_group = QGroupBox("Block Information")
        block_layout = QGridLayout()
        
        # Add new block info toggle
        block_layout.addWidget(QLabel("Add New Block Info:"), 0, 0)
        self.add_new_block_check = QCheckBox("New block info available")
        block_layout.addWidget(self.add_new_block_check, 0, 1)
        
        # Update next block info toggle
        block_layout.addWidget(QLabel("Update Next Block Info:"), 1, 0)
        self.update_next_block_check = QCheckBox("Train model should update next block")
        block_layout.addWidget(self.update_next_block_check, 1, 1)
        
        # Next block entered toggle
        block_layout.addWidget(QLabel("Next Block Entered:"), 2, 0)
        self.next_block_entered_check = QCheckBox("Toggle when entering new block")
        block_layout.addWidget(self.next_block_entered_check, 2, 1)
        
        # Next block info fields
        block_layout.addWidget(QLabel("Next Block Number:"), 3, 0)
        self.next_block_number_spin = QSpinBox()
        self.next_block_number_spin.setRange(1, 999)
        self.next_block_number_spin.setValue(1)
        block_layout.addWidget(self.next_block_number_spin, 3, 1)
        
        block_layout.addWidget(QLabel("Next Block Commanded Speed:"), 4, 0)
        self.next_block_cmd_speed_spin = QSpinBox()
        self.next_block_cmd_speed_spin.setRange(0, 3)
        self.next_block_cmd_speed_spin.setValue(0)
        block_layout.addWidget(self.next_block_cmd_speed_spin, 4, 1)
        
        block_layout.addWidget(QLabel("Next Block Authorized:"), 5, 0)
        self.next_block_authorized_check = QCheckBox("Authorized to go")
        self.next_block_authorized_check.setChecked(True)
        block_layout.addWidget(self.next_block_authorized_check, 5, 1)
        
        block_group.setLayout(block_layout)
        input_layout.addWidget(block_group)
        
        # Add scroll content
        scroll.setWidget(scroll_content)
        left_layout.addWidget(scroll)
        
        # Save button
        self.save_button = QPushButton("SAVE AND SEND")
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.save_button.clicked.connect(self.save_values)
        left_layout.addWidget(self.save_button)
        
        # Current values being sent
        self.current_values_label = QLabel("Current values being sent:")
        self.current_values_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        left_layout.addWidget(self.current_values_label)
        
        self.current_values_display = QTextEdit()
        self.current_values_display.setReadOnly(True)
        self.current_values_display.setMaximumHeight(150)
        self.current_values_display.setStyleSheet("background-color: #f0f0f0;")
        left_layout.addWidget(self.current_values_display)
        
        # Right side - Train Controller Outputs (received from Controller)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Title
        title_label2 = QLabel("Train Controller → Train Model")
        title_label2.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        title_label2.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(title_label2)
        
        # Output display
        output_group = QGroupBox("Controller Outputs (Updated every 0.1s)")
        output_layout = QVBoxLayout()
        
        # Create output fields
        self.output_fields = {}
        output_items = [
            ("Train ID", "train_id", ""),
            ("Power Output", "power_kw", "kW"),
            ("Emergency Brake", "emergency_brake", ""),
            ("Service Brake", "service_brake", ""),
            ("Interior Lights", "interior_lights", ""),
            ("Headlights", "headlights", ""),
            ("Left Door", "left_door", ""),
            ("Right Door", "right_door", ""),
            ("Set Cabin Temp", "set_cabin_temp", "°F"),
            ("Station Stop Complete", "station_stop_complete", ""),
            ("Next Station Name", "next_station_name", ""),
            ("Next Station Side", "next_station_side", "")
        ]
        
        for label, field, unit in output_items:
            h_layout = QHBoxLayout()
            h_layout.addWidget(QLabel(f"{label}:"))
            h_layout.addStretch()
            
            value_label = QLabel("--")
            value_label.setStyleSheet("font-weight: bold; padding: 5px; background-color: white; border: 1px solid #ccc;")
            value_label.setMinimumWidth(100)
            value_label.setAlignment(Qt.AlignCenter)
            self.output_fields[field] = value_label
            
            h_layout.addWidget(value_label)
            if unit:
                h_layout.addWidget(QLabel(unit))
            
            output_layout.addLayout(h_layout)
        
        output_group.setLayout(output_layout)
        right_layout.addWidget(output_group)
        
        # Current Block Information
        current_block_group = QGroupBox("Current Block Information")
        current_block_layout = QVBoxLayout()
        
        self.current_block_label = QLabel("Block: N/A")
        self.current_block_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        current_block_layout.addWidget(self.current_block_label)
        
        self.block_details_label = QLabel("Details: N/A")
        self.block_details_label.setWordWrap(True)
        current_block_layout.addWidget(self.block_details_label)
        
        current_block_group.setLayout(current_block_layout)
        right_layout.addWidget(current_block_group)
        
        # Connection status
        self.status_label = QLabel("Status: Waiting for connection from main_test.py")
        self.status_label.setStyleSheet("padding: 10px; background-color: #ffffcc; border: 1px solid #cccc00;")
        self.status_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.status_label)
        
        right_layout.addStretch()
        
        # Add to main layout
        main_layout.addWidget(left_widget, 1)
        main_layout.addWidget(right_widget, 1)
        
        self.setLayout(main_layout)
        self.update_current_values_display()
        
    def save_values(self):
        """Save pending values as current values"""
        # Create next block info dict based on UI inputs
        # next_block_info is needed for both add_new_block_info AND update_next_block_info
        next_block_info = {}
        if self.add_new_block_check.isChecked() or self.update_next_block_check.isChecked():
            next_block_info = {
                'block_number': self.next_block_number_spin.value(),
                'commanded_speed': self.next_block_cmd_speed_spin.value(),
                'authorized_to_go_on_the_block': 1 if self.next_block_authorized_check.isChecked() else 0
            }
        
        # Create new TrainModelInput with values from UI
        self.current_train_input = TrainModelInput(
            fault_status={
                'engine': self.engine_fault_check.isChecked(),
                'signal': self.signal_fault_check.isChecked(),
                'brake': self.brake_fault_check.isChecked()
            },
            actual_speed=self.actual_speed_spin.value(),
            passenger_emergency_brake=self.passenger_ebrake_check.isChecked(),
            cabin_temperature=self.cabin_temp_spin.value(),
            next_station_number=self.next_station_number_spin.value(),
            available_train_ids=self.get_train_ids_from_ui(),
            authority_threshold=self.authority_threshold_spin.value(),
            add_new_block_info=self.add_new_block_check.isChecked(),
            next_block_info=next_block_info,
            next_block_entered=self.next_block_entered_check.isChecked(),
            update_next_block_info=self.update_next_block_check.isChecked()
        )
        
        self.update_current_values_display()
        
        # Flash save button
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
                border: none;
                border-radius: 5px;
            }
        """)
        QTimer.singleShot(200, lambda: self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """))
        
    def update_current_values_display(self):
        """Update the display showing current values being sent"""
        # Get commanded speed from next_block_info if available
        cmd_speed = "N/A"
        if self.current_train_input.next_block_info and 'commanded_speed' in self.current_train_input.next_block_info:
            cmd_speed = f"{self.current_train_input.next_block_info['commanded_speed']:.1f}"
        
        display_text = f"""Speed: {self.current_train_input.actual_speed:.1f} mph (Cmd: {cmd_speed})
Authority Threshold: {self.current_train_input.authority_threshold:.0f} yards
Cabin Temp: {self.current_train_input.cabin_temperature:.1f}°F
Next Station Number: {self.current_train_input.next_station_number}
Faults: Engine={self.current_train_input.fault_status.get('engine', False)}, 
        Signal={self.current_train_input.fault_status.get('signal', False)}, 
        Brake={self.current_train_input.fault_status.get('brake', False)}
Passenger E-Brake: {self.current_train_input.passenger_emergency_brake}
Block Info: Add New={self.current_train_input.add_new_block_info}, Update={self.current_train_input.update_next_block_info}, Next Entered={self.current_train_input.next_block_entered}
Next Block: {self.current_train_input.next_block_info.get('block_number', 'N/A')}, Auth={self.current_train_input.next_block_info.get('authorized_to_go_on_the_block', 'N/A')}"""
        self.current_values_display.setPlainText(display_text)
        
    def to_train_controller(self) -> TrainModelInput:
        """
        Called by main_test.py to get current train model data.
        Returns the current TrainModelInput that should be sent to the controller.
        """
        return self.current_train_input
        
    def update_current_block_info(self, block_number, block_data):
        """
        Update the current block information display.
        
        Args:
            block_number: Current block number
            block_data: Dictionary with block details from get_block_essentials
        """
        if block_data is None:
            self.current_block_label.setText(f"Block: {block_number} (No Data)")
            self.block_details_label.setText("Details: Block data not available")
            return
        
        # Update block label
        station_text = " 🚉 STATION" if block_data.get('is_station', False) else ""
        underground_text = " 🚇 UNDERGROUND" if block_data.get('underground', False) else ""
        self.current_block_label.setText(f"Block: {block_number}{station_text}{underground_text}")
        
        # Update details
        station_name = block_data.get('station_name', 'N/A') if block_data.get('is_station', False) else 'None'
        platform_side = block_data.get('platform_side', 'N/A') if block_data.get('is_station', False) else 'N/A'
        
        details_text = f"""Station: {station_name}
Platform Side: {platform_side}
Speed Limit: {block_data.get('speed_limit_mph', 'N/A')} mph
Length: {block_data.get('length_meters', 'N/A')} meters
Underground: {'Yes' if block_data.get('underground', False) else 'No'}"""
        
        self.block_details_label.setText(details_text)

    def from_train_controller(self, output: TrainModelOutput):
        """
        Called by main_test.py to provide controller output data.
        Updates the display with the received TrainModelOutput.
        """
        if output is None:
            return
            
        self.last_output = output
        
        # Update output display
        self.output_fields['train_id'].setText(f"{output.train_id}")
        self.output_fields['power_kw'].setText(f"{output.power_kw:.1f}")
        self.output_fields['emergency_brake'].setText("ON" if output.emergency_brake_status else "OFF")
        self.output_fields['service_brake'].setText("ON" if output.service_brake_status else "OFF")
        self.output_fields['interior_lights'].setText("ON" if output.interior_lights_status else "OFF")
        self.output_fields['headlights'].setText("ON" if output.headlights_status else "OFF")
        self.output_fields['left_door'].setText("OPEN" if output.door_left_status else "CLOSED")
        self.output_fields['right_door'].setText("OPEN" if output.door_right_status else "CLOSED")
        self.output_fields['set_cabin_temp'].setText(f"{output.set_cabin_temperature:.1f}")
        self.output_fields['station_stop_complete'].setText("YES" if output.station_stop_complete else "NO")
        self.output_fields['next_station_name'].setText(f"{output.next_station_name}")
        self.output_fields['next_station_side'].setText(f"{output.next_station_side}")
        
        # Update status
        self.status_label.setText("Status: Connected and receiving data")
        self.status_label.setStyleSheet("padding: 10px; background-color: #ccffcc; border: 1px solid #00ff00;")
        
        # Color code boolean values
        for field in ['emergency_brake', 'service_brake', 'interior_lights', 'headlights', 'left_door', 'right_door', 'station_stop_complete']:
            label = self.output_fields[field]
            if label.text() in ["ON", "OPEN", "YES"]:
                label.setStyleSheet("font-weight: bold; padding: 5px; background-color: #ffffcc; border: 1px solid #ffcc00;")
            else:
                label.setStyleSheet("font-weight: bold; padding: 5px; background-color: white; border: 1px solid #ccc;")
        
        # Special styling for station information fields
        station_fields = ['next_station_name', 'next_station_side']
        for field in station_fields:
            label = self.output_fields[field]
            if label.text() and label.text() != "No Information" and label.text() != "--":
                label.setStyleSheet("font-weight: bold; padding: 5px; background-color: #e6f3ff; border: 1px solid #0066cc; color: #0066cc;")
            else:
                label.setStyleSheet("font-weight: bold; padding: 5px; background-color: white; border: 1px solid #ccc; color: #999;")
                
        # Highlight emergency brake
        if output.emergency_brake_status:
            self.output_fields['emergency_brake'].setStyleSheet(
                "font-weight: bold; padding: 5px; background-color: #ffcccc; border: 2px solid #ff0000; color: #ff0000;"
            )
    
    def get_train_ids_from_ui(self):
        """Parse train IDs from the UI text field"""
        try:
            train_ids_text = self.train_ids_edit.text().strip()
            if not train_ids_text:
                return [1]  # Default if empty
            
            # Parse comma-separated values
            train_ids = []
            for item in train_ids_text.split(','):
                item = item.strip()
                if item:
                    train_ids.append(int(item))
            
            return sorted(list(set(train_ids)))  # Remove duplicates and sort
        except ValueError:
            # If parsing fails, return default
            return [1]
    
    def add_new_train(self):
        """Add a new train ID to the list"""
        current_ids = self.get_train_ids_from_ui()
        if current_ids:
            new_id = max(current_ids) + 1
        else:
            new_id = 1
        
        current_ids.append(new_id)
        current_ids.sort()
        
        # Update the text field
        self.train_ids_edit.setText(','.join(map(str, current_ids)))
        
        # Update the current train input if save is clicked
        print(f"Added new train ID: {new_id}")
    
    def remove_last_train(self):
        """Remove the highest train ID from the list"""
        current_ids = self.get_train_ids_from_ui()
        if len(current_ids) > 1:  # Keep at least one train
            current_ids.remove(max(current_ids))
            self.train_ids_edit.setText(','.join(map(str, current_ids)))
            print(f"Removed highest train ID. Remaining: {current_ids}")
        else:
            print("Cannot remove the last train - at least one train must remain")
            
    def closeEvent(self, event):
        """Handle window closing"""
        event.accept()


def main():
    """Run the test bench standalone for testing"""
    app = QApplication(sys.argv)
    
    # Create test bench
    test_bench = TrainModelTestBench()
    test_bench.show()
    
    # Print instructions
    print("\nTrain Model Test Bench (Standalone Mode)")
    print("="*50)
    print("This test bench is designed to work with main_test.py")
    print("To use it properly, run main_test.py instead.")
    print("\nIn standalone mode, you can only edit values.")
    print("No data will be sent or received.")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()