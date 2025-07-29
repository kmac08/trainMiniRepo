"""
Track Circuit Test UI
Provides interface to send 18-bit track circuit data packets to the train system
"""

import sys
import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QLineEdit, QPushButton, QLabel, QGroupBox, 
                            QTextEdit, QFrame, QRadioButton, QButtonGroup, QCheckBox)
from PyQt5.QtCore import pyqtSignal, QTimer, Qt
from PyQt5.QtGui import QFont


class TrackCircuitTestUI(QMainWindow):
    # Signal to send 18-bit track circuit data to train system
    track_circuit_data_signal = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Track Circuit Test UI")
        self.setGeometry(100, 100, 600, 900)
        
        # Track sent packets for display
        self.last_packet = None
        self.packet_count = 0
        
        # Automatic testing variables
        self.auto_mode = False
        self.automatic_testing_data = {}
        self.current_block_pointer = 68  # Starting block from JSON
        self.train_model = None  # Reference to train model (will be set by train system)
        self.last_edge_state = False
        
        # Load JSON data for automatic testing
        self.load_automatic_testing_data()
        
        self.init_ui()
        
        # Timer for updating display
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(100)  # Update every 100ms
        
    def load_automatic_testing_data(self):
        """Load automatic testing data from JSON file"""
        try:
            json_path = os.path.join(os.path.dirname(__file__), 'automatic_testing_for_train_system.json')
            with open(json_path, 'r') as f:
                self.automatic_testing_data = json.load(f)
            print(f"Loaded automatic testing data for {len(self.automatic_testing_data)} blocks")
        except FileNotFoundError:
            print("WARNING: automatic_testing_for_train_system.json not found")
            self.automatic_testing_data = {}
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in automatic_testing_for_train_system.json: {e}")
            self.automatic_testing_data = {}
    
    def set_train_model(self, train_model):
        """Set reference to train model for automatic testing"""
        self.train_model = train_model
        
    def init_ui(self):
        """Initialize the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Set consistent styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
            }
            QPushButton {
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                opacity: 0.8;
            }
        """)
        
        # Title
        title_label = QLabel("Track Circuit Test Interface")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        main_layout.addWidget(title_label)
        
        # Mode Selection
        mode_group = QGroupBox("Operating Mode")
        mode_layout = QHBoxLayout(mode_group)
        
        self.manual_radio = QRadioButton("Manual Mode")
        self.auto_radio = QRadioButton("Automatic Mode")
        self.manual_radio.setChecked(True)  # Default to manual
        
        # Button group for radio buttons
        self.mode_button_group = QButtonGroup()
        self.mode_button_group.addButton(self.manual_radio)
        self.mode_button_group.addButton(self.auto_radio)
        
        # Connect radio button changes
        self.manual_radio.toggled.connect(self.on_mode_changed)
        self.auto_radio.toggled.connect(self.on_mode_changed)
        
        mode_layout.addWidget(self.manual_radio)
        mode_layout.addWidget(self.auto_radio)
        
        # Auto mode status
        self.auto_status_label = QLabel("Auto Status: Disabled")
        self.auto_status_label.setFont(QFont("Arial", 10))
        mode_layout.addWidget(self.auto_status_label)
        
        main_layout.addWidget(mode_group)
        
        # Input Section
        input_group = QGroupBox("Track Circuit Data Input (Decimal)")
        input_layout = QVBoxLayout(input_group)
        
        # Block Number (7 bits, max 127)
        block_row = QHBoxLayout()
        block_label = QLabel("Block Number (0-127):")
        block_label.setFont(QFont("Arial", 10))
        block_label.setMinimumWidth(150)
        self.block_number_input = QLineEdit()
        self.block_number_input.setPlaceholderText("0-127")
        self.block_number_input.textChanged.connect(self.validate_input)
        block_row.addWidget(block_label)
        block_row.addWidget(self.block_number_input)
        input_layout.addLayout(block_row)
        
        # Commanded Speed (2 bits, max 3)
        speed_row = QHBoxLayout()
        speed_label = QLabel("Commanded Speed (0-3):")
        speed_label.setFont(QFont("Arial", 10))
        speed_label.setMinimumWidth(150)
        self.commanded_speed_input = QLineEdit()
        self.commanded_speed_input.setPlaceholderText("0-3")
        self.commanded_speed_input.textChanged.connect(self.validate_input)
        speed_row.addWidget(speed_label)
        speed_row.addWidget(self.commanded_speed_input)
        input_layout.addLayout(speed_row)
        
        # Authority (1 bit, max 1)
        auth_row = QHBoxLayout()
        auth_label = QLabel("Authority (0-1):")
        auth_label.setFont(QFont("Arial", 10))
        auth_label.setMinimumWidth(150)
        self.authority_input = QLineEdit()
        self.authority_input.setPlaceholderText("0-1")
        self.authority_input.textChanged.connect(self.validate_input)
        auth_row.addWidget(auth_label)
        auth_row.addWidget(self.authority_input)
        input_layout.addLayout(auth_row)
        
        # New Block Flag (1 bit, max 1)
        new_block_row = QHBoxLayout()
        new_block_label = QLabel("New Block Flag (0-1):")
        new_block_label.setFont(QFont("Arial", 10))
        new_block_label.setMinimumWidth(150)
        self.new_block_flag_input = QLineEdit()
        self.new_block_flag_input.setPlaceholderText("0-1")
        self.new_block_flag_input.textChanged.connect(self.validate_input)
        new_block_row.addWidget(new_block_label)
        new_block_row.addWidget(self.new_block_flag_input)
        input_layout.addLayout(new_block_row)
        
        # Next Block Entered (1 bit, max 1)
        next_block_row = QHBoxLayout()
        next_block_label = QLabel("Next Block Entered (0-1):")
        next_block_label.setFont(QFont("Arial", 10))
        next_block_label.setMinimumWidth(150)
        self.next_block_entered_input = QLineEdit()
        self.next_block_entered_input.setPlaceholderText("0-1")
        self.next_block_entered_input.textChanged.connect(self.validate_input)
        next_block_row.addWidget(next_block_label)
        next_block_row.addWidget(self.next_block_entered_input)
        input_layout.addLayout(next_block_row)
        
        # Update Block in Queue (1 bit, max 1)
        update_queue_row = QHBoxLayout()
        update_queue_label = QLabel("Update Block in Queue (0-1):")
        update_queue_label.setFont(QFont("Arial", 10))
        update_queue_label.setMinimumWidth(150)
        self.update_block_queue_input = QLineEdit()
        self.update_block_queue_input.setPlaceholderText("0-1")
        self.update_block_queue_input.textChanged.connect(self.validate_input)
        update_queue_row.addWidget(update_queue_label)
        update_queue_row.addWidget(self.update_block_queue_input)
        input_layout.addLayout(update_queue_row)
        
        # Station Number (5 bits, max 31)
        station_row = QHBoxLayout()
        station_label = QLabel("Station Number (0-31):")
        station_label.setFont(QFont("Arial", 10))
        station_label.setMinimumWidth(150)
        self.station_number_input = QLineEdit()
        self.station_number_input.setPlaceholderText("0-31")
        self.station_number_input.textChanged.connect(self.validate_input)
        station_row.addWidget(station_label)
        station_row.addWidget(self.station_number_input)
        input_layout.addLayout(station_row)
        
        # Send button
        self.send_button = QPushButton("Send to Train System")
        self.send_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.send_button.clicked.connect(self.send_track_circuit_data)
        self.send_button.setEnabled(False)
        input_layout.addWidget(self.send_button)
        
        # Validation message
        self.validation_label = QLabel("")
        self.validation_label.setFont(QFont("Arial", 9))
        input_layout.addWidget(self.validation_label)
        
        main_layout.addWidget(input_group)
        
        # Generated Output Section
        output_group = QGroupBox("Generated Packet Preview")
        output_layout = QVBoxLayout(output_group)
        
        self.generated_binary_label = QLabel("Binary (18-bit): None")
        self.generated_binary_label.setFont(QFont("Courier New", 10))
        self.generated_binary_label.setWordWrap(True)
        output_layout.addWidget(self.generated_binary_label)
        
        self.generated_decimal_label = QLabel("Decimal: None")
        self.generated_decimal_label.setFont(QFont("Arial", 10))
        output_layout.addWidget(self.generated_decimal_label)
        
        main_layout.addWidget(output_group)
        
        # Status Section
        status_group = QGroupBox("System Status")
        status_layout = QVBoxLayout(status_group)
        
        self.connection_status = QLabel("Connection: Ready")
        self.connection_status.setFont(QFont("Arial", 10))
        status_layout.addWidget(self.connection_status)
        
        self.packet_count_label = QLabel("Packets Sent: 0")
        self.packet_count_label.setFont(QFont("Arial", 10))
        status_layout.addWidget(self.packet_count_label)
        
        main_layout.addWidget(status_group)
        
        # Last Packet Info Section
        packet_group = QGroupBox("Last Packet Information")
        packet_layout = QVBoxLayout(packet_group)
        
        self.last_packet_binary = QLabel("Binary: None")
        self.last_packet_binary.setFont(QFont("Courier New", 10))
        packet_layout.addWidget(self.last_packet_binary)
        
        self.last_packet_decimal = QLabel("Decimal: None")
        self.last_packet_decimal.setFont(QFont("Arial", 10))
        packet_layout.addWidget(self.last_packet_decimal)
        
        # Parsed components
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        packet_layout.addWidget(separator)
        
        parsed_label = QLabel("Parsed Components:")
        parsed_label.setFont(QFont("Arial", 10, QFont.Bold))
        packet_layout.addWidget(parsed_label)
        
        self.block_number_label = QLabel("Block Number: None")
        self.commanded_signal_label = QLabel("Commanded Signal: None")
        self.authority_bit_label = QLabel("Authority Bit: None")
        self.new_block_flag_label = QLabel("New Block Flag: None")
        self.next_block_entered_flag_label = QLabel("Next Block Entered Flag: None")
        self.update_block_in_queue_label = QLabel("Update Block in Queue: None")
        self.station_number_label = QLabel("Station Number: None")
        
        for label in [self.block_number_label, self.commanded_signal_label, 
                     self.authority_bit_label, self.new_block_flag_label, 
                     self.next_block_entered_flag_label, self.update_block_in_queue_label,
                     self.station_number_label]:
            label.setFont(QFont("Arial", 9))
            packet_layout.addWidget(label)
        
        main_layout.addWidget(packet_group)
        
        # Log Section
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_display = QTextEdit()
        self.log_display.setMaximumHeight(150)
        self.log_display.setFont(QFont("Courier New", 9))
        self.log_display.setReadOnly(True)
        log_layout.addWidget(self.log_display)
        
        main_layout.addWidget(log_group)
        
        # Add initial log entry
        self.add_log_entry("Track Circuit Test UI initialized")
        
    def on_mode_changed(self):
        """Handle mode change between manual and automatic"""
        if self.auto_radio.isChecked():
            self.auto_mode = True
            self.auto_status_label.setText("Auto Status: Enabled - Monitoring train")
            self.auto_status_label.setStyleSheet("color: green;")
            
            # Disable manual input fields
            self.block_number_input.setEnabled(False)
            self.commanded_speed_input.setEnabled(False)
            self.authority_input.setEnabled(False)
            self.new_block_flag_input.setEnabled(False)
            self.next_block_entered_input.setEnabled(False)
            self.update_block_queue_input.setEnabled(False)
            self.station_number_input.setEnabled(False)
            self.send_button.setEnabled(False)
            
            self.add_log_entry("Switched to AUTOMATIC mode - monitoring train for edge detection")
        else:
            self.auto_mode = False
            self.auto_status_label.setText("Auto Status: Disabled")
            self.auto_status_label.setStyleSheet("color: red;")
            
            # Enable manual input fields
            self.block_number_input.setEnabled(True)
            self.commanded_speed_input.setEnabled(True)
            self.authority_input.setEnabled(True)
            self.new_block_flag_input.setEnabled(True)
            self.next_block_entered_input.setEnabled(True)
            self.update_block_queue_input.setEnabled(True)
            self.station_number_input.setEnabled(True)
            
            # Re-validate inputs to enable send button if appropriate
            self.validate_input()
            
            self.add_log_entry("Switched to MANUAL mode - ready for manual input")
        
    def validate_input(self):
        """Validate the decimal inputs and update UI accordingly"""
        inputs = [
            (self.block_number_input.text(), 0, 127, "Block Number"),
            (self.commanded_speed_input.text(), 0, 3, "Commanded Speed"),
            (self.authority_input.text(), 0, 1, "Authority"),
            (self.new_block_flag_input.text(), 0, 1, "New Block Flag"),
            (self.next_block_entered_input.text(), 0, 1, "Next Block Entered"),
            (self.update_block_queue_input.text(), 0, 1, "Update Block in Queue"),
            (self.station_number_input.text(), 0, 31, "Station Number")
        ]
        
        errors = []
        all_filled = True
        
        for text, min_val, max_val, field_name in inputs:
            if not text:
                all_filled = False
                continue
                
            # Check if it's a valid integer
            try:
                value = int(text)
            except ValueError:
                errors.append(f"{field_name} must be an integer")
                continue
                
            # Check range
            if value < min_val or value > max_val:
                errors.append(f"{field_name} must be between {min_val} and {max_val}")
        
        # Update validation display
        if errors:
            self.validation_label.setText("❌ " + "; ".join(errors))
            self.validation_label.setStyleSheet("color: red;")
            self.send_button.setEnabled(False)
            self.generated_binary_label.setText("Binary (18-bit): None")
            self.generated_decimal_label.setText("Decimal: None")
        elif not all_filled:
            self.validation_label.setText("Please fill all fields")
            self.validation_label.setStyleSheet("color: orange;")
            self.send_button.setEnabled(False)
            self.generated_binary_label.setText("Binary (18-bit): None")
            self.generated_decimal_label.setText("Decimal: None")
        else:
            self.validation_label.setText("✓ All inputs valid")
            self.validation_label.setStyleSheet("color: green;")
            self.send_button.setEnabled(True)
            
            # Generate preview
            try:
                block_number = int(self.block_number_input.text())
                commanded_signal = int(self.commanded_speed_input.text())
                authority_bit = int(self.authority_input.text())
                new_block_flag = int(self.new_block_flag_input.text())
                next_block_entered_flag = int(self.next_block_entered_input.text())
                update_block_in_queue = int(self.update_block_queue_input.text())
                station_number = int(self.station_number_input.text())
                
                # Convert to binary representation and combine into 18-bit packet
                data_packet = (
                    (block_number & 0b1111111) << 11 |
                    (commanded_signal & 0b11) << 9 |
                    (authority_bit & 0b1) << 8 |
                    (new_block_flag & 0b1) << 7 |
                    (next_block_entered_flag & 0b1) << 6 |
                    (update_block_in_queue & 0b1) << 5 |
                    (station_number & 0b11111)
                )
                
                binary_str = format(data_packet, '018b')
                self.generated_binary_label.setText(f"Binary (18-bit): {binary_str}")
                self.generated_decimal_label.setText(f"Decimal: {data_packet}")
            except ValueError:
                self.generated_binary_label.setText("Binary (18-bit): None")
                self.generated_decimal_label.setText("Decimal: None")
        
    def send_track_circuit_data(self):
        """Send the track circuit data to the train system"""
        try:
            # Get decimal values from inputs
            block_number = int(self.block_number_input.text())
            commanded_signal = int(self.commanded_speed_input.text())
            authority_bit = int(self.authority_input.text())
            new_block_flag = int(self.new_block_flag_input.text())
            next_block_entered_flag = int(self.next_block_entered_input.text())
            update_block_in_queue = int(self.update_block_queue_input.text())
            station_number = int(self.station_number_input.text())
            
            # Convert to binary representation and combine into 18-bit packet
            # Bit layout: [Block Number (7)] [Commanded Signal (2)] [Authority (1)] [New Block Flag (1)] [Next Block Entered (1)] [Update Block Queue (1)] [Station Number (5)]
            data_packet = (
                (block_number & 0b1111111) << 11 |
                (commanded_signal & 0b11) << 9 |
                (authority_bit & 0b1) << 8 |
                (new_block_flag & 0b1) << 7 |
                (next_block_entered_flag & 0b1) << 6 |
                (update_block_in_queue & 0b1) << 5 |
                (station_number & 0b11111)
            )
            
            # Convert to binary string for display
            binary_str = format(data_packet, '018b')
            
            # Store packet info
            self.last_packet = {
                'binary': binary_str,
                'decimal': data_packet,
                'block_number': block_number,
                'commanded_signal': commanded_signal,
                'authority_bit': authority_bit,
                'new_block_flag': new_block_flag,
                'next_block_entered_flag': next_block_entered_flag,
                'update_block_in_queue': update_block_in_queue,
                'station_number': station_number
            }
            
            # Emit signal to train system
            self.track_circuit_data_signal.emit(data_packet)
            
            # Update counters
            self.packet_count += 1
            
            # Add to log
            self.add_log_entry(f"Sent packet {self.packet_count}: {binary_str} (decimal: {data_packet})")
            self.add_log_entry(f"  → Block: {block_number}, Speed: {commanded_signal}, Auth: {authority_bit}")
            
            # Clear inputs for next packet
            self.block_number_input.clear()
            self.commanded_speed_input.clear()
            self.authority_input.clear()
            self.new_block_flag_input.clear()
            self.next_block_entered_input.clear()
            self.update_block_queue_input.clear()
            self.station_number_input.clear()
            
        except ValueError as e:
            self.add_log_entry(f"Error: Invalid input values - {str(e)}")
            
    def add_log_entry(self, message):
        """Add an entry to the activity log"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_display.append(f"[{timestamp}] {message}")
        
        # Auto-scroll to bottom
        cursor = self.log_display.textCursor()
        cursor.movePosition(cursor.End)
        self.log_display.setTextCursor(cursor)
        
    def update_display(self):
        """Update the display with current information"""
        # Update packet count
        self.packet_count_label.setText(f"Packets Sent: {self.packet_count}")
        
        # Handle automatic testing if enabled
        if self.auto_mode:
            self.check_automatic_testing()
        
        # Update last packet info
        if self.last_packet:
            self.last_packet_binary.setText(f"Binary: {self.last_packet['binary']}")
            self.last_packet_decimal.setText(f"Decimal: {self.last_packet['decimal']}")
            
            self.block_number_label.setText(f"Block Number: {self.last_packet['block_number']} (7 bits)")
            self.commanded_signal_label.setText(f"Commanded Signal: {self.last_packet['commanded_signal']} (2 bits)")
            self.authority_bit_label.setText(f"Authority Bit: {self.last_packet['authority_bit']} (1 bit)")
            self.new_block_flag_label.setText(f"New Block Flag: {self.last_packet['new_block_flag']} (1 bit)")
            self.next_block_entered_flag_label.setText(f"Next Block Entered Flag: {self.last_packet['next_block_entered_flag']} (1 bit)")
            self.update_block_in_queue_label.setText(f"Update Block in Queue: {self.last_packet['update_block_in_queue']} (1 bit)")
            self.station_number_label.setText(f"Station Number: {self.last_packet['station_number']} (5 bits)")
    
    def check_automatic_testing(self):
        """Check if automatic testing should send data based on train state"""
        if not self.train_model or not self.automatic_testing_data:
            return
            
        # Check if train is at edge of current block
        current_edge_state = getattr(self.train_model, 'edge_of_current_block', False)
        
        # Only send when edge state changes from False to True
        if current_edge_state and not self.last_edge_state:
            self.send_automatic_data()
            
        self.last_edge_state = current_edge_state
        
        # Update auto status display
        if current_edge_state:
            self.auto_status_label.setText("Auto Status: Train at edge - sending data")
            self.auto_status_label.setStyleSheet("color: orange;")
        else:
            self.auto_status_label.setText("Auto Status: Monitoring train")
            self.auto_status_label.setStyleSheet("color: green;")
    
    def send_automatic_data(self):
        """Send automatic track circuit data from JSON file"""
        try:
            # Get data for current block
            block_key = str(self.current_block_pointer)
            if block_key not in self.automatic_testing_data:
                self.add_log_entry(f"AUTO: No data found for block {self.current_block_pointer}")
                return
            
            data = self.automatic_testing_data[block_key]
            
            # Extract values from JSON data
            block_number = data['block_number']
            commanded_speed = data['commanded_speed']
            authority = data['authority']
            new_block_flag = data['new_block_flag']
            next_block_entered = data['next_block_entered']
            update_block_in_queue = data['update_block_in_queue']
            station_number = data['station_number']
            
            # Update UI to show what's being sent
            self.block_number_input.setText(str(block_number))
            self.commanded_speed_input.setText(str(commanded_speed))
            self.authority_input.setText(str(authority))
            self.new_block_flag_input.setText(str(new_block_flag))
            self.next_block_entered_input.setText(str(next_block_entered))
            self.update_block_queue_input.setText(str(update_block_in_queue))
            self.station_number_input.setText(str(station_number))
            
            # Convert to binary and send
            data_packet = (
                (block_number & 0b1111111) << 11 |
                (commanded_speed & 0b11) << 9 |
                (authority & 0b1) << 8 |
                (new_block_flag & 0b1) << 7 |
                (next_block_entered & 0b1) << 6 |
                (update_block_in_queue & 0b1) << 5 |
                (station_number & 0b11111)
            )
            
            binary_str = format(data_packet, '018b')
            
            # Store packet info
            self.last_packet = {
                'binary': binary_str,
                'decimal': data_packet,
                'block_number': block_number,
                'commanded_signal': commanded_speed,
                'authority_bit': authority,
                'new_block_flag': new_block_flag,
                'next_block_entered_flag': next_block_entered,
                'update_block_in_queue': update_block_in_queue,
                'station_number': station_number
            }
            
            # Send the packet
            self.track_circuit_data_signal.emit(data_packet)
            self.packet_count += 1
            
            # Log the automatic send
            self.add_log_entry(f"AUTO: Sent block {block_number} data: {binary_str} (decimal: {data_packet})")
            self.add_log_entry(f"AUTO: Speed: {commanded_speed}, Auth: {authority}, Station: {station_number}")
            
            # Move to next block
            self.current_block_pointer += 1
            if str(self.current_block_pointer) not in self.automatic_testing_data:
                # Wrap around or stop
                self.current_block_pointer = 68  # Reset to start
                self.add_log_entry(f"AUTO: Reached end of data, restarting from block 68")
                
        except Exception as e:
            self.add_log_entry(f"AUTO ERROR: {str(e)}")

def main():
    """Main function to run the Track Circuit Test UI standalone"""
    app = QApplication(sys.argv)
    window = TrackCircuitTestUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
