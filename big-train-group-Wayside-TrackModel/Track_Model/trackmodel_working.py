import sys
import os
import threading
import time  # Keep for performance timing only
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QFileDialog, QPushButton, QComboBox, QTextEdit, QSizePolicy,
    QLineEdit, QMessageBox, QScrollArea, QTabWidget
)
from PyQt5.QtCore import Qt, QTimer
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from Track_Reader.track_reader import TrackLayoutReader, TrackBlock
from Inputs import TrackModelInputs
from Outputs import get_16bit_track_model_output  # Import from Outputs.py

# Master Interface Time Integration
try:
    from Master_Interface.master_control import get_time
    MASTER_TIME_AVAILABLE = True
except ImportError:
    MASTER_TIME_AVAILABLE = False
    # Fallback function if Master Interface not available
    def get_time():
        return datetime.now()

# Train System Integration
try:
    from train_system_main_sw import TrainSystemSW
    from train_system_main_hw import TrainSystemHW
    from train_controller_sw.controller.data_types import TrainControllerInit, BlockInfo
    TRAIN_SYSTEMS_AVAILABLE = True
except ImportError:
    TRAIN_SYSTEMS_AVAILABLE = False

# --- Debug Terminal Singleton ---
class DebugTerminal(QTextEdit):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DebugTerminal, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self.setReadOnly(True)
        self.setStyleSheet("font-family: Consolas; font-size: 11pt;")
        self.setLineWrapMode(QTextEdit.NoWrap)
        self._initialized = True

    @staticmethod
    def log(message):
        instance = DebugTerminal._instance or DebugTerminal()
        timestamp = get_time().strftime("%H:%M:%S")
        instance.append(f"{timestamp} {message}")

# Log train system availability after DebugTerminal is defined
if not TRAIN_SYSTEMS_AVAILABLE:
    DebugTerminal.log("Warning: Train system modules not available")

# --- Tests Tab Widget ---
class TestsTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.all_tests_running = False
        self.current_test_index = 0
        self.test_functions = [
            ("Create Train", self.test_create_train),
            ("Basic Movement", self.test_wayside_sim),
            ("Movement - Stations", self.test_movement_stations),
            ("Hardcoded Packets", self.test_hardcoded_packets)
        ]
        
        # Set up UI with two columns
        main_layout = QVBoxLayout()
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(8, 8, 8, 8)
        
        # Create grid layout for two columns
        from PyQt5.QtWidgets import QGridLayout
        grid_layout = QGridLayout()
        grid_layout.setSpacing(4)
        
        # Individual test buttons in two columns
        for i, (test_name, test_func) in enumerate(self.test_functions):
            button = QPushButton(test_name)
            button.setStyleSheet("font-size: 10pt; font-family: Arial; padding: 6px;")  # Smaller text
            button.clicked.connect(test_func)
            setattr(self, f"btn_{test_name.lower().replace(' ', '_').replace('->', '_to_')}", button)
            
            # Place in grid: row = i // 2, column = i % 2
            row = i // 2
            col = i % 2
            grid_layout.addWidget(button, row, col)
        
        main_layout.addLayout(grid_layout)
        
        # All tests button with progress counter (spans both columns)
        self.all_tests_button = QPushButton("All Tests")
        self.all_tests_button.setStyleSheet("font-size: 11pt; font-family: Arial; padding: 6px; font-weight: bold;")
        self.all_tests_button.clicked.connect(self.run_all_tests)
        main_layout.addWidget(self.all_tests_button)
        
        main_layout.addStretch()
        self.setLayout(main_layout)
    
    def set_buttons_enabled(self, enabled):
        """Enable/disable all test buttons"""
        for test_name, _ in self.test_functions:
            button = getattr(self, f"btn_{test_name.lower().replace(' ', '_').replace('->', '_to_')}")
            button.setEnabled(enabled)
    
    def run_all_tests(self):
        """Run all tests sequentially with progress tracking"""
        if self.all_tests_running:
            return
            
        self.all_tests_running = True
        self.current_test_index = 0
        self.set_buttons_enabled(False)
        
        DebugTerminal.log("=== Starting All Tests ===")
        self.run_next_test()
    
    def run_next_test(self):
        """Run the next test in sequence"""
        if self.current_test_index >= len(self.test_functions):
            # All tests complete
            self.all_tests_running = False
            self.set_buttons_enabled(True)
            self.all_tests_button.setText("All Tests")
            DebugTerminal.log("=== All Tests Complete ===")
            return
        
        # Update progress counter
        progress_text = f"All Tests [{self.current_test_index + 1}/{len(self.test_functions)}]"
        self.all_tests_button.setText(progress_text)
        
        # Run current test
        test_name, test_func = self.test_functions[self.current_test_index]
        DebugTerminal.log(f"Running test: {test_name}")
        
        try:
            test_func()
        except Exception as e:
            DebugTerminal.log(f"Test {test_name} failed: {str(e)}")
        
        # Move to next test
        self.current_test_index += 1
        
        # Schedule next test with a small delay for UI responsiveness
        QTimer.singleShot(500, self.run_next_test)
    
    # Test function implementations
    def test_create_train(self):
        """Create a train manually"""
        if not self.main_window.train_manager:
            DebugTerminal.log("No train manager available")
            return
        
        train_id = self.main_window.train_manager.create_train_manual()
        if train_id:
            self.main_window.update_train_count()
            DebugTerminal.log(f"Created train {train_id}")
        else:
            DebugTerminal.log("Failed to create train")
    
    def test_wayside_sim(self):
        """Run progressive wayside simulation: G0->G63->G64 over 30 seconds"""
        # First run the yard buffer simulation to create train
        success = self.main_window.simulate_wayside_yard_sequence()
        if not success:
            DebugTerminal.log("Wayside simulation failed")
            return
            
        if not self.main_window.train_manager:
            DebugTerminal.log("ERROR: No train manager available")
            return
            
        train_manager = self.main_window.train_manager
        
        # Use QTimer to wait for train creation to complete (Master Interface aware)
        def check_train_creation():
            if len(train_manager.active_trains) == 0:
                DebugTerminal.log("ERROR: No active trains found after wayside simulation")
                return
                
            train_id = list(train_manager.active_trains.keys())[0]
            train_system = train_manager.active_trains[train_id]
            
            DebugTerminal.log(f"=== Progressive Test: {train_id} G0->G63->G64 (30s) ===")
            self.continue_wayside_test(train_id, train_system, train_manager)
        
        # Delay using QTimer instead of blocking sleep
        QTimer.singleShot(500, check_train_creation)
    
    def continue_wayside_test(self, train_id, train_system, train_manager):
        
        # Define packet sequence for 30-second journey
        packet_sequence = [
            # Phase 1: G0->G63 (0-14 seconds)
            {"time": 0, "block": 67, "phase": "G0->G63", "next_entered": 0},
            {"time": 2, "block": 67, "phase": "G0->G63", "next_entered": 0},
            {"time": 4, "block": 67, "phase": "G0->G63", "next_entered": 0}, 
            {"time": 6, "block": 67, "phase": "G0->G63", "next_entered": 0},
            {"time": 8, "block": 67, "phase": "G0->G63", "next_entered": 0},
            {"time": 10, "block": 67, "phase": "G0->G63", "next_entered": 0},
            {"time": 12, "block": 67, "phase": "G0->G63", "next_entered": 0},
            {"time": 14, "block": 67, "phase": "Enter G63", "next_entered": 1},
            
            # Phase 2: G63->G64 (16-30 seconds)
            {"time": 16, "block": 68, "phase": "G63->G64", "next_entered": 0},
            {"time": 18, "block": 68, "phase": "G63->G64", "next_entered": 0},
            {"time": 20, "block": 68, "phase": "G63->G64", "next_entered": 0},
            {"time": 22, "block": 68, "phase": "G63->G64", "next_entered": 0},
            {"time": 24, "block": 68, "phase": "G63->G64", "next_entered": 0},
            {"time": 26, "block": 68, "phase": "G63->G64", "next_entered": 0},
            {"time": 28, "block": 68, "phase": "G63->G64", "next_entered": 0},
            {"time": 30, "block": 69, "phase": "Enter G64", "next_entered": 1}
        ]
        
        # Enable test mode to disable automatic packet sending
        train_manager.test_mode_active = True
        DebugTerminal.log("Test mode activated")
        
        # Initialize packet stepping
        self.packet_index = 0
        self.packet_sequence = packet_sequence
        self.test_train_id = train_id
        self.test_start_time = get_time()
        
        # Create timer for packet stepping
        from PyQt5.QtCore import QTimer
        self.packet_step_timer = QTimer()
        self.packet_step_timer.timeout.connect(self.step_packet_sequence)
        self.packet_step_timer.start(2000)  # Every 2 seconds
        
        self.step_packet_sequence()  # Send first packet immediately
        
    def step_packet_sequence(self):
        """Step through the progressive packet sequence"""
        if not hasattr(self, 'packet_sequence') or self.packet_index >= len(self.packet_sequence):
            # Sequence complete
            self.packet_step_timer.stop()
            DebugTerminal.log("=== Progressive packet sequence completed ===")
            
            # Disable test mode to re-enable automatic packet sending
            train_manager = self.main_window.train_manager
            train_manager.test_mode_active = False
            DebugTerminal.log("Test mode deactivated")
            return
        
        # Get current packet data
        packet_data = self.packet_sequence[self.packet_index]
        elapsed_time = (get_time() - self.test_start_time).total_seconds()
        
        DebugTerminal.log(f"Time: {elapsed_time:.1f}s - {packet_data['phase']} - Sending Block {packet_data['block']}")
        
        # Create and send packet
        packet = TrackCircuitInterface.create_packet(
            block_number=packet_data['block'],
            speed_command=2,  # Medium speed
            authorized=True,
            new_block=(packet_data['next_entered'] == 0),  # New block when not entering
            next_block_entered=(packet_data['next_entered'] == 1),
            update_queue=False,
            station_number=19  # POPLAR station
        )
        
        # Send packet to train
        train_manager = self.main_window.train_manager
        train_system = train_manager.active_trains[self.test_train_id]
        success = TrackCircuitInterface.send_to_train(train_system, packet, self.test_train_id)
        
        if success:
            # Update train packet tracking
            packet_binary = format(packet, '018b')
            packet_hex = format(packet, '05X')
            train_manager.train_last_packets[self.test_train_id] = {
                'binary': packet_binary,
                'hex': packet_hex,
                'decimal': packet
            }
            
            # Update train position based on distance traveled
            self.update_train_position_from_distance()
            
            DebugTerminal.log(f"  Packet sent: 0x{packet_hex} = {packet_binary}")
        else:
            DebugTerminal.log(f"  ERROR: Failed to send packet")
        
        self.packet_index += 1
        
    def update_train_position_from_distance(self):
        """Update train position on GUI based on distance traveled"""
        if not hasattr(self, 'test_train_id'):
            return
            
        train_manager = self.main_window.train_manager
        train_system = train_manager.active_trains.get(self.test_train_id)
        
        if not train_system:
            return
            
        try:
            # Get current distance traveled from train
            distance_traveled = train_system.get_train_distance_traveled()
            
            # Calculate current block based on distance and track layout
            current_block = self.calculate_current_block_from_distance(distance_traveled)
            
            if current_block:
                # Update GUI occupancy
                train_manager._update_gui_train_occupancy(self.test_train_id, current_block)
                DebugTerminal.log(f"  Train position: {current_block} (distance: {distance_traveled:.1f}m)")
            
        except Exception as e:
            DebugTerminal.log(f"  Position update error: {e}")
            
    def calculate_current_block_from_distance(self, distance_traveled):
        """Calculate current block from distance traveled using track layout"""
        # Simplified calculation for G0->G63->G64 route
        # This should use actual track layout block lengths in full implementation
        
        if distance_traveled < 100:  # First 100m = still in yard (G0)
            return "G0"
        elif distance_traveled < 200:  # Next 100m = G63
            return "G63"
        elif distance_traveled < 300:  # Next 100m = G64
            return "G64"
        else:
            return "G64"  # Stay at G64 for this test
    
    def test_hardcoded_packets(self):
        """Test single hardcoded packet: Block 63, Fast speed, Authorized"""
        if not self.main_window or not self.main_window.train_manager:
            DebugTerminal.log("ERROR: No train manager available")
            return
            
        train_manager = self.main_window.train_manager
        
        # Create train if needed
        if len(train_manager.active_trains) == 0:
            train_id = train_manager.create_train_manual()
            if not train_id:
                DebugTerminal.log("ERROR: Failed to create train")
                return
            self.main_window.update_train_count()
            DebugTerminal.log(f"Created train {train_id}")
        else:
            train_id = list(train_manager.active_trains.keys())[0]
            DebugTerminal.log(f"Using existing train {train_id}")
            
        train_system = train_manager.active_trains[train_id]
        
        # Send single packet: Block 63, Fast speed, Authorized
        DebugTerminal.log("=== Sending Single Test Packet ===")
        DebugTerminal.log("Packet: Block 63, Speed 3 (Fast), Authorized")
        
        packet = TrackCircuitInterface.create_packet(
            block_number=63,
            speed_command=3,  # Fast
            authorized=True,
            new_block=True,
            station_number=0
        )
        
        success = TrackCircuitInterface.send_to_train(train_system, packet, train_id)
        if success:
            # Store the test packet data for train info panel
            try:
                packet_binary = format(packet, '018b')
                packet_hex = format(packet, '05X')
                train_manager.train_last_packets[train_id] = {
                    'binary': packet_binary,
                    'hex': packet_hex,
                    'decimal': packet
                }
                DebugTerminal.log("✓ Test packet sent successfully")
                DebugTerminal.log("Expected packet: Block=63, Speed=3, Auth=1")
                DebugTerminal.log("Watch for train distance updates in Train Info panel")
            except Exception as e:
                DebugTerminal.log(f"Failed to store test packet data: {e}")
        else:
            DebugTerminal.log("✗ Failed to send test packet")
    
    def test_movement_stations(self):
        """Test progressive train movement through stations: G0→G65(GLENBURY)→G73(DORMONT)"""
        if not self.main_window or not self.main_window.train_manager:
            DebugTerminal.log("ERROR: No train manager available")
            return
            
        train_manager = self.main_window.train_manager
        
        # Clear all trains to ensure 0 trains at start
        train_manager.destroy_all_trains()
        self.main_window.update_train_count()
        DebugTerminal.log("=== Movement - Stations Test Started ===")
        DebugTerminal.log("All trains cleared - starting with 0 trains")
        
        # Create single train for testing
        train_id = train_manager.create_train_manual()
        if not train_id:
            DebugTerminal.log("ERROR: Failed to create train")
            return
        self.main_window.update_train_count()
        DebugTerminal.log(f"Created test train {train_id}")
        
        # Set test mode to prevent automatic packet conflicts
        train_manager.test_mode_active = True
        DebugTerminal.log("Test mode activated - automatic packets disabled")
        
        # Start progressive station packet sequence
        self.station_packet_step = 0
        self.station_test_train_id = train_id
        self.station_packet_timer = QTimer()
        self.station_packet_timer.timeout.connect(self.step_station_packet_sequence)
        self.station_packet_timer.start(2000)  # 2-second intervals
        
        DebugTerminal.log("Progressive station packet sequence started")
        DebugTerminal.log("Route: G0 → G65(GLENBURY) → G73(DORMONT)")
        DebugTerminal.log("Speed pattern: Fast(3) → Slow(1) at stations")
    
    def step_station_packet_sequence(self):
        """Step through station movement packet sequence"""
        if not hasattr(self, 'station_test_train_id') or not self.main_window:
            return
            
        train_manager = self.main_window.train_manager
        train_id = self.station_test_train_id
        
        if train_id not in train_manager.active_trains:
            DebugTerminal.log("ERROR: Test train no longer exists")
            self.station_packet_timer.stop()
            return
            
        train_system = train_manager.active_trains[train_id]
        
        # Station movement sequence: G0→G65(GLENBURY)→G73(DORMONT)
        # GLENBURY = station 16, DORMONT = station 17
        packet_sequence = [
            # Phase 1: G0→G65 (GLENBURY approach) - 0-20 seconds
            (0, 67, 3, True, 16, "G0→G65: Fast approach to GLENBURY"),
            (2, 67, 3, True, 16, "G0→G65: Fast approach to GLENBURY"),
            (4, 67, 3, True, 16, "G0→G65: Fast approach to GLENBURY"),
            (6, 67, 3, True, 16, "G0→G65: Fast approach to GLENBURY"),
            (8, 67, 1, True, 16, "G0→G65: Slow for GLENBURY station"),
            (10, 67, 1, True, 16, "G0→G65: Slow for GLENBURY station"),
            (12, 68, 1, True, 16, "G65: At GLENBURY station"),
            (14, 68, 1, True, 16, "G65: At GLENBURY station"),
            (16, 69, 3, True, 17, "G65→G73: Fast approach to DORMONT"),
            (18, 69, 3, True, 17, "G65→G73: Fast approach to DORMONT"),
            (20, 77, 3, True, 17, "G65→G73: Fast approach to DORMONT"),
            # Phase 2: G65→G73 (DORMONT approach) - 22-40 seconds
            (22, 77, 3, True, 17, "G65→G73: Fast approach to DORMONT"),
            (24, 77, 1, True, 17, "G65→G73: Slow for DORMONT station"),
            (26, 77, 1, True, 17, "G65→G73: Slow for DORMONT station"),
            (28, 77, 1, True, 17, "G73: At DORMONT station"),
            (30, 77, 1, True, 17, "G73: At DORMONT station"),
            (32, 77, 1, True, 17, "G73: Holding at DORMONT"),
            (34, 77, 1, True, 17, "G73: Holding at DORMONT"),
            (36, 77, 1, True, 17, "G73: Holding at DORMONT"),
            (38, 77, 1, True, 17, "Test complete - holding final packet")
        ]
        
        if self.station_packet_step >= len(packet_sequence):
            DebugTerminal.log("=== Movement - Stations Test Complete ===")
            DebugTerminal.log("Train held at final position - test mode remains active")
            DebugTerminal.log("Final status: Train at DORMONT station (G73)")
            self.station_packet_timer.stop()
            # Keep test mode active to hold final packet as requested
            return
            
        # Get current packet data
        step_time, block_num, speed, auth, station, description = packet_sequence[self.station_packet_step]
        
        DebugTerminal.log(f"Step {self.station_packet_step + 1}/{len(packet_sequence)}: {description}")
        
        # Create and send packet
        packet = TrackCircuitInterface.create_packet(
            block_number=block_num,
            speed_command=speed,
            authorized=auth,
            new_block=True,
            station_number=station
        )
        
        success = TrackCircuitInterface.send_to_train(train_system, packet, train_id)
        if success:
            # Store packet data for train info panel
            try:
                packet_binary = format(packet, '018b')
                packet_hex = format(packet, '05X')
                train_manager.train_last_packets[train_id] = {
                    'binary': packet_binary,
                    'hex': packet_hex,
                    'decimal': packet
                }
                
                # Update train position for GUI
                self.update_station_train_position(train_id, block_num, speed, station)
                
                speed_desc = {1: "Slow", 2: "Medium", 3: "Fast"}.get(speed, "Stop")
                station_desc = {16: "GLENBURY", 17: "DORMONT"}.get(station, f"Station{station}")
                DebugTerminal.log(f"✓ Packet sent: Block={block_num}, Speed={speed_desc}, Station={station_desc}")
                
            except Exception as e:
                DebugTerminal.log(f"Failed to store station packet data: {e}")
        else:
            DebugTerminal.log(f"✗ Failed to send station packet for step {self.station_packet_step + 1}")
            
        self.station_packet_step += 1
    
    def update_station_train_position(self, train_id, block_num, speed, station):
        """Update train position for station testing GUI display"""
        try:
            train_manager = self.main_window.train_manager
            if train_id in train_manager.train_trackers:
                # Calculate approximate distance based on block number
                # This is a simplified calculation for testing purposes
                distance = self.calculate_station_block_from_distance(block_num)
                train_manager.train_trackers[train_id].update_position(distance)
                
                # Update GUI block coloring
                current_block_id = train_manager.train_trackers[train_id].get_current_block()
                if current_block_id in train_manager.block_info_objects:
                    train_manager.block_info_objects[current_block_id].set_train_occupancy(train_id)
                    
                DebugTerminal.log(f"Train {train_id} position updated: {current_block_id}")
                
        except Exception as e:
            DebugTerminal.log(f"Failed to update station train position: {e}")
    
    def calculate_station_block_from_distance(self, block_num):
        """Calculate distance for station block positioning (simplified for testing)"""
        # Simplified distance calculation: each block = ~300m
        # This is for testing visualization only
        base_distance = block_num * 300
        return base_distance

# --- Debug Window ---
class DebugWindow(QWidget):
    def __init__(self, inputs: TrackModelInputs):
        super().__init__()
        self.inputs = inputs
        self.selected_block_id = None  # Track currently selected block
        self.setVisible(False)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Inputs panel with scroll area
        self.inputs_label = QLabel(self.generate_inputs_text())
        self.inputs_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.inputs_label.setStyleSheet("font-family: Arial; font-size: 11pt;")
        self.inputs_label.setMinimumWidth(280)
        self.inputs_label.setWordWrap(True)
        
        # Wrap inputs label in scroll area
        self.inputs_scroll = QScrollArea()
        self.inputs_scroll.setWidget(self.inputs_label)
        self.inputs_scroll.setWidgetResizable(True)
        self.inputs_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.inputs_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.inputs_scroll.setMinimumHeight(200)
        self.inputs_scroll.setMaximumHeight(400)

        # Outputs panel
        self.outputs_label = QLabel(self.generate_outputs_text())
        self.outputs_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.outputs_label.setStyleSheet("font-family: Arial; font-size: 11pt;")
        self.outputs_label.setMinimumWidth(280)
        self.outputs_label.setWordWrap(True)

        # --- Bit structure display and button under Outputs ---
        self.bits_display = QLabel("Output Bits: ")
        self.bits_display.setAlignment(Qt.AlignLeft)
        self.bits_display.setStyleSheet("font-family: Consolas; font-size: 12pt; color: #333333;")
        self.bits_display.setWordWrap(True)

        self.gen_bits_button = QPushButton("Generate bit structure")
        self.gen_bits_button.setStyleSheet("font-size: 11pt; font-family: Arial;")
        self.gen_bits_button.clicked.connect(self.display_bits)

        # Terminal panel (center)
        self.terminal = DebugTerminal()

        # Layouts
        left = QVBoxLayout()
        left.addWidget(QLabel("<b>Inputs</b>"))
        left.addWidget(self.inputs_scroll)

        center = QVBoxLayout()
        center.addWidget(QLabel("<b>Debug Terminal</b>"))
        center.addWidget(self.terminal)

        # Right panel with tabs
        right_tabs = QTabWidget()
        
        # Outputs tab (existing functionality)
        outputs_widget = QWidget()
        outputs_layout = QVBoxLayout()
        outputs_layout.addWidget(self.bits_display)
        outputs_layout.addWidget(self.gen_bits_button)
        outputs_layout.addWidget(self.outputs_label)
        outputs_layout.addStretch()
        outputs_widget.setLayout(outputs_layout)
        right_tabs.addTab(outputs_widget, "Outputs")
        
        # Tests tab (new functionality)
        self.tests_tab = TestsTab(None)  # Will set main_window reference later
        right_tabs.addTab(self.tests_tab, "Tests")

        layout = QHBoxLayout()
        layout.addLayout(left, 1)
        layout.addLayout(center, 2)
        layout.addWidget(right_tabs, 1)
        self.setLayout(layout)

        # Start background update thread for inputs/outputs texts
        threading.Thread(target=self.update_loop, daemon=True).start()

    def set_main_window(self, main_window):
        """Set the main window reference for the tests tab"""
        self.tests_tab.main_window = main_window

    def display_bits(self):
        bits = get_16bit_track_model_output()
        self.bits_display.setText(f"Output Bits: {bits}")

    def update_loop(self):
        # Convert to QTimer-based updates instead of blocking thread
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(2000)  # Update every 2 seconds
    
    def update_display(self):
        """Update display labels - called by QTimer"""
        self.inputs_label.setText(self.generate_inputs_text(self.selected_block_id))
        self.outputs_label.setText(self.generate_outputs_text())

    def update_for_block(self, block_id):
        """Update debug window immediately for a specific block"""
        self.selected_block_id = block_id
        self.inputs_label.setText(self.generate_inputs_text(block_id))
        self.outputs_label.setText(self.generate_outputs_text())

    def generate_inputs_text(self, selected_block_id=None):
        # Summarize block failures as a comma-separated list of block IDs with active failures
        def summarize_map(data_map):
            active = [str(k) for k, v in data_map.items() if v]
            return ", ".join(active) if active else "None"

        # Use selected block if provided, otherwise show sample blocks
        if selected_block_id and selected_block_id in self.inputs._wayside_authority:
            # Show detailed data for the selected block
            block_id = selected_block_id
            auth = self.inputs.get_wayside_authority(block_id)
            speed = self.inputs.get_wayside_commanded_speed(block_id)
            next_blk = self.inputs.get_next_block_number(block_id)
            next_station = self.inputs.get_next_station_number(block_id)
            update_queue = self.inputs.get_update_block_in_queue(block_id)
            switch = self.inputs.get_switch_state(block_id)
            traffic = self.inputs.get_traffic_light_state(block_id)
            crossing = self.inputs.get_crossing_state(block_id)
            covered = self.inputs.get_wayside_blocks_covered(block_id)
            
            # Debug: Confirm debug window is getting correct wayside data
            DebugWindow.print_to_terminal(f"Debug inputs for {block_id}: Auth={auth}, Speed={speed}, NextBlk={next_blk}")
            
            wayside_data = (
                f"\n--- SELECTED BLOCK {block_id} WAYSIDE DATA ---\n"
                f"Authority\t{auth}\n"
                f"Commanded Speed\t{speed}\n"
                f"Next Block Number\t{next_blk} (Block {int(next_blk, 2)})\n"
                f"Next Station Number\t{next_station} (Station {int(next_station, 2)})\n"
                f"Update Block in Queue\t{update_queue}\n"
                f"Switch State\t{switch}\n"
                f"Traffic Light State\t{traffic}\n"
                f"Crossing State\t{crossing}\n"
                f"Wayside Blocks Covered\t{covered}\n"
            )
        else:
            # Show sample blocks for demonstration
            sample_blocks = ["G0", "G20", "G40", "G60"]
            wayside_summary = ""
            for block_id in sample_blocks:
                if block_id in self.inputs._wayside_authority:
                    auth = self.inputs.get_wayside_authority(block_id)
                    speed = self.inputs.get_wayside_commanded_speed(block_id)
                    next_blk = self.inputs.get_next_block_number(block_id)
                    wayside_summary += f"{block_id}(A:{auth} S:{speed} N:{int(next_blk, 2):03d}) "
            
            wayside_data = (
                f"\n--- WAYSIDE CONTROLLER DATA ---\n"
                f"Sample Blocks\t{wayside_summary.strip()}\n"
                f"Block G0 Authority\t{self.inputs.get_wayside_authority('G0')}\n"
                f"Block G0 Cmd Speed\t{self.inputs.get_wayside_commanded_speed('G0')}\n"
                f"Block G20 Next Block\t{self.inputs.get_next_block_number('G20')}\n"
                f"Block G20 Next Station\t{self.inputs.get_next_station_number('G20')}\n"
                f"Switch States\t{self.inputs.get_switch_state('G15')} (G15), {self.inputs.get_switch_state('G30')} (G30)\n"
                f"Traffic Lights\t{self.inputs.get_traffic_light_state('G25')} (G25), {self.inputs.get_traffic_light_state('G50')} (G50)\n"
                f"Crossings\t{self.inputs.get_crossing_state('G25')} (G25), {self.inputs.get_crossing_state('G75')} (G75)\n"
            )

        return (
            f"Train Layout\t{str(self.inputs.get_train_layout()) if self.inputs.get_train_layout() else 'None'}\n"
            f"Temperature\t{self.inputs.get_temperature()}°F\n"
            f"Broken Rail Failure\t{summarize_map(self.inputs._broken_rail_failure)}\n"
            f"Track Circuit Failure\t{summarize_map(self.inputs._track_circuit_failure)}\n"
            f"Power Failure\t{summarize_map(self.inputs._power_failure)}\n"
            + wayside_data
        )

    def generate_outputs_text(self):
        return (
            f"Authority\n"
            f"Commanded Speed\n"
            f"Next Block #s\n"
            f"Update Previous Bit\n"
            f"Next Station #\n"
        )

    @staticmethod
    def print_to_terminal(message):
        DebugTerminal.log(message)

# --- Info Panel ---
class InfoPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.label = QLabel("Select a block")
        self.label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.label.setWordWrap(True)
        self.label.setStyleSheet("font-size: 14pt; font-family: Arial;")
        self.temp_edit = QLineEdit()
        self.temp_edit.setFixedWidth(120)
        self.temp_edit.setStyleSheet("font-size: 13pt; font-family: Arial;")
        self.temp_edit.setAlignment(Qt.AlignLeft)
        self.temp_edit.setPlaceholderText("Temperature (°F)")
        self.temp_edit.returnPressed.connect(self._try_set_temperature)
        self.temp_edit.editingFinished.connect(self._try_set_temperature)
        self.inputs = None  # Will be set in update_info

        # Simulation clock
        self.clock_label = QLabel("Elapsed Time: 00:00:00")
        self.clock_label.setStyleSheet("font-size: 13pt; font-family: Arial;")
        self.sim_start_time = get_time()

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addStretch()
        layout.addWidget(self.clock_label)
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Temperature:"))
        temp_layout.addWidget(self.temp_edit)
        temp_layout.addWidget(QLabel("°F"))
        temp_layout.addStretch()
        layout.addLayout(temp_layout)
        self.setLayout(layout)

    def _clock_update_loop(self):
        # Convert to QTimer-based updates instead of blocking thread
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock_display)
        self.clock_timer.start(2000)  # Update every 2 seconds
    
    def update_clock_display(self):
        """Update clock display - called by QTimer"""
        elapsed = int((get_time() - self.sim_start_time).total_seconds())
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        seconds = elapsed % 60
        self.clock_label.setText(f"Elapsed Time: {hours:02}:{minutes:02}:{seconds:02}")

    def update_info(self, block: TrackBlock, inputs: TrackModelInputs = None):
        self.inputs = inputs
        
        # Special handling for yard block (G0)
        if block.block_number == 0:
            info = self._generate_yard_info(block, inputs)
        else:
            info = self._generate_regular_block_info(block, inputs)
            
        self.label.setText(info)
        
    def _generate_yard_info(self, block: TrackBlock, inputs: TrackModelInputs = None):
        """Generate special yard information display"""
        info = f"<b>YARD - BLOCK G0</b><br><br>"
        info += f"<b>Facility Type:</b> Train Staging Yard<br>"
        info += f"<b>Block Length (m):</b> {block.length_m}<br>"
        info += f"<b>Speed Limit:</b> 0 km/h (Staging Only)<br><br>"
        
        # Yard buffer status
        if inputs and hasattr(inputs, 'train_manager') and inputs.train_manager:
            yard_buffer = inputs.train_manager.yard_buffer
            buffer_status = yard_buffer.current_buffer if yard_buffer else []
            is_complete = yard_buffer.is_complete if yard_buffer else False
            
            info += f"<b>YARD BUFFER STATUS</b><br>"
            if buffer_status:
                sequence_str = " → ".join([f"G{b}" for b in buffer_status])
                info += f"Current Sequence: {sequence_str}<br>"
                if is_complete:
                    info += f"<span style='color: green;'>Complete - Ready for dispatch</span><br>"
                else:
                    needed = [63, 64, 65, 66][len(buffer_status):]
                    needed_str = " → ".join([f"G{b}" for b in needed])
                    info += f"<span style='color: orange;'>Waiting: {needed_str}</span><br>"
            else:
                info += f"<span style='color: #666;'>Empty - Awaiting CTC sequence</span><br>"
            
            info += f"Expected Sequence: G63 → G64 → G65 → G66<br><br>"
            
            # Trains in yard
            trains_in_yard = getattr(inputs.train_manager, 'trains_in_yard', [])
            info += f"<b>TRAINS IN YARD</b><br>"
            if trains_in_yard:
                info += f"Staged Trains: {', '.join(trains_in_yard)}<br>"
            else:
                info += f"<span style='color: #666;'>No trains staged</span><br>"
            
            info += f"Active Trains: {inputs.train_manager.get_train_count()}/25<br><br>"
        
        # Wayside debugging
        if inputs:
            info += f"<b>WAYSIDE DEBUG</b><br>"
            block_id = "G0"
            auth = inputs.get_wayside_authority(block_id)
            speed = inputs.get_wayside_commanded_speed(block_id)
            next_block = inputs.get_next_block_number(block_id)
            next_block_num = int(next_block, 2) if next_block else 0
            
            info += f"Authority: {'Authorized' if auth == '1' else 'Not Authorized'}<br>"
            info += f"Speed Command: {speed} ({'Stop' if speed=='00' else 'Slow' if speed=='01' else 'Medium' if speed=='10' else 'Fast'})<br>"
            info += f"Next Block: G{next_block_num}<br>"
            
            # Set the temperature box to the current value
            temp_val = inputs.get_temperature()
            self.temp_edit.setText(f"{temp_val:.1f}")
        
        return info
        
    def _generate_regular_block_info(self, block: TrackBlock, inputs: TrackModelInputs = None):
        """Generate regular block information display"""
        info = f"<b>Line:</b> {block.line}<br><b>Section:</b> {block.section}<br>"
        info += f"<b>Block Number:</b> {block.block_number}<br>"
        info += f"<b>Block Length (m):</b> {block.length_m}<br>"
        info += f"<b>Block Grade (%):</b> {block.grade_percent}<br>"
        info += f"<b>Speed Limit (km/h):</b> {block.speed_limit_kmh}<br>"
        info += f"<b>Elevation (m):</b> {block.elevation_m}<br>"
        info += f"<b>Direction:</b> {block.get_direction_description()}<br>"
        info += f"<b>Infrastructure:</b><div style='white-space: pre-wrap; max-width: 380px;'>{block.get_infrastructure_description()}</div><br>"
        
        # Station Heater status for station blocks
        if block.has_station and inputs:
            temp_val = inputs.get_temperature()
            heater_status = "On" if temp_val < 37.0 else "Off"
            info += f"<b>Station Heater:</b> {heater_status}<br>"
        
        # Train information for regular blocks
        if inputs and hasattr(inputs, 'train_manager') and inputs.train_manager:
            bid = f"{block.line[0].upper()}{block.block_number}"
            trains_on_block = []
            for train_id, tracker in inputs.train_manager.train_trackers.items():
                if tracker.get_current_block() == bid:
                    trains_on_block.append(train_id)
            
            if trains_on_block:
                info += f"<b>Trains on Block:</b> {', '.join(trains_on_block)}<br>"
            
            info += f"<b>Active Trains:</b> {inputs.train_manager.get_train_count()}/25<br>"
        
        if inputs:
            bid = f"{block.line[0].upper()}{block.block_number}"
            
            # Wayside Controller Data
            authority = inputs.get_wayside_authority(bid)
            cmd_speed = inputs.get_wayside_commanded_speed(bid)
            info += f"<br><b>Authority:</b> {authority}<br>"
            info += f"<b>Commanded Speed:</b> {cmd_speed}<br><sbr>"
            
            # Debug: Confirm InfoPanel is displaying correct data from Inputs
            DebugWindow.print_to_terminal(f"InfoPanel displaying {bid}: Auth={authority}, CmdSpeed={cmd_speed}")
            
            # Murphy Failures
            info += f"<b>Broken Rail Failure:</b> {'Active' if inputs.get_broken_rail_failure(bid) else 'None'}<br>"
            info += f"<b>Track Circuit Failure:</b> {'Active' if inputs.get_track_circuit_failure(bid) else 'None'}<br>"
            info += f"<b>Power Failure:</b> {'Active' if inputs.get_power_failure(bid) else 'None'}<br>"
            # Set the temperature box to the current value
            temp_val = inputs.get_temperature()
            self.temp_edit.setText(f"{temp_val:.1f}")
        
        return info

    def _try_set_temperature(self):
        if self.inputs is None:
            return
        text = self.temp_edit.text().strip().replace("°F", "")
        try:
            value = float(text)
            if not (-25.0 <= value <= 105.0):
                raise ValueError
        except Exception:
            # Only show the popup and reset once
            if self.temp_edit.hasFocus():
                self._show_temp_error()
            self.temp_edit.setText(f"{self.inputs.get_temperature():.1f}")
            return
        # Only update and print if the value is actually different
        if value != self.inputs.get_temperature():
            self.inputs.set_temperature(value)
            self.temp_edit.setText(f"{value:.1f}")
            DebugWindow.print_to_terminal(f"Temperature set to {value:.1f}°F")

    def _show_temp_error(self):
        QMessageBox.warning(self, "Invalid Temperature", "Please only enter numerical values between -25.0 and 105.0")

# --- Train Info Panel ---
class TrainInfoPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_train_id = None
        self.main_window = None  # Will be set by MainWindow
        self.last_distance = 0.0  # Track distance changes
        
        # Create scrollable area for train data
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Create label inside scroll area
        self.label = QLabel("Select a train to see train data")
        self.label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.label.setWordWrap(True)
        self.label.setStyleSheet("font-size: 14pt; font-family: Arial; padding: 10px;")
        self.label.setMinimumWidth(200)  # Ensure minimum width for readability
        
        # Set label as scroll area widget
        self.scroll_area.setWidget(self.label)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins for full scroll area
        layout.addWidget(self.scroll_area)
        self.setLayout(layout)
        
        # Start update timer for continuous data refresh
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_train_info)
        self.update_timer.start(500)  # Update every 500ms for smooth data flow
        
    def set_selected_train(self, train_id):
        """Set the currently selected train for display"""
        self.selected_train_id = train_id
        self.update_train_info()
        
    def update_train_info(self):
        """Update train information display"""
        if not self.selected_train_id or not self.main_window or not self.main_window.train_manager:
            self.label.setText("Select a train to see train data")
            return
            
        train_manager = self.main_window.train_manager
        
        # Check if train is still active
        if self.selected_train_id not in train_manager.active_trains:
            self.label.setText(f"Train {self.selected_train_id} is no longer active")
            return
            
        try:
            # Get train system and tracker
            train_system = train_manager.active_trains[self.selected_train_id]
            train_tracker = train_manager.train_trackers.get(self.selected_train_id)
            
            if not train_tracker:
                self.label.setText(f"No tracker found for train {self.selected_train_id}")
                return
                
            # Get train creation time
            creation_time = train_manager.train_creation_times.get(self.selected_train_id, "Unknown")
            
            # Get current position
            current_block = train_tracker.get_current_block()
            distance_traveled = train_system.get_train_distance_traveled()
            
            # Get next four blocks from last packet sent
            next_four_blocks = train_manager.train_next_blocks.get(self.selected_train_id, ["N/A", "N/A", "N/A", "N/A"])
            
            # Get last packet sent to train
            last_packet_data = train_manager.train_last_packets.get(self.selected_train_id, None)
            
            # Decode 18-bit packet if available
            if last_packet_data and isinstance(last_packet_data, dict):
                packet_binary = last_packet_data['binary']
                packet_hex = last_packet_data['hex']
                packet_decimal = last_packet_data['decimal']
                
                # Decode 18-bit track circuit packet
                # Format: Block(7) | Speed(2) | Auth(1) | NewBlock(1) | NextEntered(1) | UpdateQueue(1) | Station(5)
                block_bits = packet_binary[0:7]
                speed_bits = packet_binary[7:9]
                auth_bit = packet_binary[9]
                new_block_bit = packet_binary[10]
                next_entered_bit = packet_binary[11]
                update_queue_bit = packet_binary[12]
                station_bits = packet_binary[13:18]
                
                speed_names = ["Stop", "Slow", "Medium", "Fast"]
                block_num = int(block_bits, 2)
                speed_num = int(speed_bits, 2)
                speed_name = speed_names[speed_num] if speed_num < len(speed_names) else "Unknown"
                station_num = int(station_bits, 2)
                
                decoded = f"Block: G{block_num} | Speed: {speed_name} | Auth: {auth_bit} | NewBlk: {new_block_bit} | Update: {update_queue_bit} | Station: {station_num}"
                packet_display = f"0x{packet_hex} = {packet_binary}"
            else:
                decoded = "No packet data available"
                packet_display = "No packet sent yet"
            
            # Build clean info display
            info = f"<b>Train {self.selected_train_id}</b><br>"
            info += f"<b>Position:</b> {current_block} ({distance_traveled:.1f}m)<br>"
            info += f"<b>Created:</b> {creation_time}<br><br>"
            
            info += f"<b>Current Packet:</b><br>"
            info += f"{packet_display}<br>"
            info += f"{decoded}<br><br>"
            
            info += f"<b>Route Ahead:</b><br>"
            for i, block in enumerate(next_four_blocks[:2]):  # Show only next 2 blocks
                info += f"  {i+1}. {block}<br>"
            
            self.label.setText(info)
            
        except Exception as e:
            self.label.setText(f"Error updating train {self.selected_train_id}: {str(e)}")

# --- Clickable Block ---
class ClickableBox(QFrame):
    def __init__(self, block: TrackBlock, info_panel: QWidget, main_window, inputs: TrackModelInputs):
        super().__init__()
        self.block = block
        self.info_panel = info_panel
        self.main_window = main_window
        self.inputs = inputs
        self.block_id_str = f"{self.block.line[0].upper()}{self.block.block_number}"
        self.setFixedSize(30, 30)
        # Only display the block number (no R/G) for visibility
        self.label = QLabel(str(self.block.block_number))
        self.label.setAlignment(Qt.AlignCenter)
        # Smaller, bold, black text with subtle white shadow for contrast
        self.label.setStyleSheet(
            "font-size: 9pt; font-family: Arial; font-weight: bold; color: #000000;"
        )
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.setFrameShape(QFrame.StyledPanel)
        self.set_failure_color()

    def mousePressEvent(self, event):
        self.info_panel.update_info(self.block, self.inputs)
        self.main_window.set_selected_block(self)
        # Update debug window immediately for the selected block
        self.main_window.debug_window.update_for_block(self.block_id_str)
        
        # Debug: Confirm GUI is getting correct block data
        DebugWindow.print_to_terminal(f"Block {self.block_id_str} selected - Loading wayside data...")
        auth = self.inputs.get_wayside_authority(self.block_id_str)
        speed = self.inputs.get_wayside_commanded_speed(self.block_id_str)
        DebugWindow.print_to_terminal(f"Block {self.block_id_str}: Authority={auth}, Speed={speed}")

    def set_failure(self, failure_type, failed):
        bid = self.block_id_str
        if failure_type == 'power':
            self.inputs.set_power_failure(bid, failed)
        elif failure_type == 'broken_rail':
            self.inputs.set_broken_rail_failure(bid, failed)
        elif failure_type == 'track_circuit':
            self.inputs.set_track_circuit_failure(bid, failed)
        self.set_failure_color()

    def set_failure_color(self):
        bid = self.block_id_str
        
        # Special handling for yard block (G0)
        if self.block.block_number == 0:
            self._set_yard_color()
            return
        
        # Check for train occupancy first
        train_occupied = False
        if hasattr(self.main_window, 'train_manager') and self.main_window.train_manager:
            if bid in self.main_window.train_manager.block_info_objects:
                block_info = self.main_window.train_manager.block_info_objects[bid]
                if block_info.current_train_id:
                    train_occupied = True
        
        # Set color based on status
        if train_occupied:
            color = "#808080"  # Grey for train occupancy
        elif self.inputs.get_power_failure(bid):
            color = "#FB8C00"  # Orange for power failure
        elif self.inputs.get_broken_rail_failure(bid):
            color = "#FFA726"  # Light orange for broken rail
        elif self.inputs.get_track_circuit_failure(bid):
            color = "#FF9800"  # Amber for track circuit failure
        else:
            # Default line colors
            color = "#4CAF50" if self.block.line.lower() == "green" else "#f44336" if self.block.line.lower() == "red" else "salmon"
            
        self.setStyleSheet(
            f"background-color: {color}; border: 0.5px solid #222; "
            "border-radius: 4px; "
        )
        
    def _set_yard_color(self):
        """Set special yard block coloring"""
        bid = self.block_id_str
        
        # Check for trains staged in yard
        trains_in_yard = 0
        yard_buffer_active = False
        
        if hasattr(self.main_window, 'train_manager') and self.main_window.train_manager:
            trains_in_yard = len(getattr(self.main_window.train_manager, 'trains_in_yard', []))
            
            # Check yard buffer status
            yard_buffer = self.main_window.train_manager.yard_buffer
            if yard_buffer and (yard_buffer.current_buffer or yard_buffer.is_complete):
                yard_buffer_active = True
        
        # Yard color logic: buffer activity > train staging > failures > default
        if yard_buffer_active:
            color = "#FFD700"  # Gold for active yard buffer
        elif trains_in_yard > 0:
            color = "#87CEEB"  # Sky blue for staged trains
        elif self.inputs.get_power_failure(bid):
            color = "#FB8C00"  # Orange for power failure
        elif self.inputs.get_broken_rail_failure(bid):
            color = "#FFA726"  # Light orange for broken rail
        elif self.inputs.get_track_circuit_failure(bid):
            color = "#FF9800"  # Amber for track circuit failure
        else:
            color = "#E0E0E0"  # Light grey for empty yard
            
        # Special yard styling with bold border
        self.setStyleSheet(
            f"background-color: {color}; border: 2px solid #333; "
            "border-radius: 6px; font-weight: bold;"
        )
        # Only show the block number (no R/G) for clarity  
        self.label.setText(str(self.block.block_number))

# --- Train Integration Classes ---
class YardTrackBlock:
    """Synthetic TrackBlock for the yard (Block 0)"""
    
    def __init__(self):
        self.block_number = 0
        self.line = "Green"
        self.section = "Yard"
        self.length_m = 50.0  # Short yard block
        self.grade_percent = 0.0
        self.speed_limit_kmh = 0.0  # Yard speed is 0
        self.elevation_m = 0.0
        self.is_underground = False
        self.has_station = False
        self.has_switch = False
        self.has_crossing = False
        self.has_beacon = False
        
    def get_direction_description(self):
        return "Yard Storage"
        
    def get_infrastructure_description(self):
        return "Yard Facility"

class BlockInfo:
    """Wraps TrackBlock with wayside data for train system integration"""
    
    def __init__(self, track_block: 'TrackBlock', wayside_inputs: TrackModelInputs):
        self.block_number = track_block.block_number
        self.length_meters = track_block.length_m
        self.speed_limit_mph = track_block.speed_limit_kmh * 0.621371  # Convert km/h to mph
        self.underground = track_block.is_underground
        
        # Update from wayside data
        block_id = f"{track_block.line[0].upper()}{track_block.block_number}"
        self.authorized_to_go = wayside_inputs.get_wayside_authority(block_id) == "1"
        speed_bits = wayside_inputs.get_wayside_commanded_speed(block_id)
        self.commanded_speed = int(speed_bits, 2) if speed_bits and len(speed_bits) == 2 else 0
        
        # Store reference for updates
        self.track_block = track_block
        self.wayside_inputs = wayside_inputs
        self.current_train_id = None  # Track which train is on this block
        
    def update_from_wayside(self):
        """Update BlockInfo from current wayside data"""
        block_id = f"{self.track_block.line[0].upper()}{self.track_block.block_number}"
        self.authorized_to_go = self.wayside_inputs.get_wayside_authority(block_id) == "1"
        speed_bits = self.wayside_inputs.get_wayside_commanded_speed(block_id)
        self.commanded_speed = int(speed_bits, 2) if speed_bits and len(speed_bits) == 2 else 0
        
    def set_train_occupancy(self, train_id: str = None):
        """Set which train is currently on this block"""
        self.current_train_id = train_id

class YardBuffer:
    """Manages train dispatch sequencing from CTC through wayside to Track Model"""
    
    def __init__(self):
        self.current_buffer = []  # Stores sequence: 63, 64, 65, 66
        self.is_complete = False
        
    def add_next_block(self, block_number: int):
        """Add next block number from wayside. Returns True if buffer is complete."""
        if not self.is_complete:
            self.current_buffer.append(block_number)
            if len(self.current_buffer) == 4 and self.current_buffer == [63, 64, 65, 66]:
                self.is_complete = True
                DebugTerminal.log(f"Yard buffer complete: {self.current_buffer}")
                return True
        return False
        
    def get_buffer_and_clear(self):
        """Get complete buffer and reset for next train"""
        if self.is_complete:
            buffer = self.current_buffer.copy()
            self.current_buffer = []
            self.is_complete = False
            return buffer
        return None

class TrainPathTracker:
    """Tracks train position using distance-based calculation"""
    
    def __init__(self, train_id: str, track_layout: TrackLayoutReader):
        self.train_id = train_id
        self.track_layout = track_layout
        self.current_block = "G0"
        self.total_distance_traveled = 0.0
        self.block_distances = self._calculate_block_distances()
        
    def _calculate_block_distances(self):
        """Calculate cumulative distances for each block in sequence"""
        distances = {"G0": 0.0}  # Yard starts at 0
        cumulative = 0.0
        
        # Get Green Line blocks using correct .lines access pattern
        if self.track_layout:
            green_blocks = self.track_layout.lines.get("Green", [])
            
            # Create a lookup dictionary for quick access
            block_lookup = {f"G{block.block_number}": block for block in green_blocks}
            
            # G0 -> G63 (from track layout)
            if "G63" in block_lookup:
                cumulative += block_lookup["G63"].length_m
                distances["G63"] = cumulative
                
                # Continue sequential path G63 -> G64 -> G65 -> ...
                for i in range(64, 151):
                    block_id = f"G{i}"
                    if block_id in block_lookup:
                        cumulative += block_lookup[block_id].length_m
                        distances[block_id] = cumulative
        
        return distances
        
    def update_position(self, distance_traveled: float):
        """Update train position based on total distance traveled"""
        self.total_distance_traveled = distance_traveled
        
        # Find current block based on distance
        for block_id in ["G0", "G63"] + [f"G{i}" for i in range(64, 151)]:
            if block_id in self.block_distances:
                if distance_traveled <= self.block_distances[block_id]:
                    if self.current_block != block_id:
                        DebugTerminal.log(f"Train {self.train_id} entered block {block_id}")
                    self.current_block = block_id
                    break
                    
    def get_current_block(self):
        return self.current_block

class TrackCircuitInterface:
    """Handles 18-bit track circuit packet communication"""
    
    @staticmethod
    def create_packet(block_number: int, speed_command: int, authorized: bool = True, 
                     new_block: bool = True, next_block_entered: bool = False,
                     update_queue: bool = False, station_number: int = 0):
        """
        Create 18-bit track circuit packet
        
        Format (bits 17-0):
        - 17-11: Block Number (7 bits) - 4th block ahead of train's current position
        - 10-9: Speed Command (2 bits) 
        - 8: Authority (1 bit)
        - 7: New Block Flag (1 bit)
        - 6: Next Block Entered (1 bit)
        - 5: Update Queue (1 bit)
        - 4-0: Station Number (5 bits)
        """
        # Ensure new_block_flag is never 1 when update_queue is 1
        if update_queue and new_block:
            new_block = False
            DebugTerminal.log("Track circuit: new_block forced to 0 when update_queue=1")
        
        # Debug: Log the input values
        DebugTerminal.log(f"create_packet inputs: block={block_number}, speed={speed_command}, auth={authorized}, new_block={new_block}, station={station_number}")
        
        packet = (
            (block_number & 0b1111111) << 11 |
            (speed_command & 0b11) << 9 |
            (1 if authorized else 0) << 8 |
            (1 if new_block else 0) << 7 |
            (1 if next_block_entered else 0) << 6 |
            (1 if update_queue else 0) << 5 |
            (station_number & 0b11111)
        )
        
        # Debug: Log the packet construction
        final_packet = packet & 0x3FFFF
        DebugTerminal.log(f"create_packet result: 0x{final_packet:05X} = {final_packet:018b}")
        return final_packet
        
    @staticmethod
    def send_to_train(train_system, packet: int, train_id: str = None):
        """Send packet to train system"""
        try:
            success = train_system.send_track_circuit_data(packet)
            # Convert to 18-bit binary string for display
            binary_packet = format(packet, '018b')
            
            if success:
                if train_id:
                    DebugTerminal.log(f"Train {train_id} received data packet: {binary_packet}")
                else:
                    DebugTerminal.log(f"Track circuit packet sent: {binary_packet}")
            else:
                DebugTerminal.log(f"Track circuit send failed for packet: {binary_packet} (Train {train_id})")
            return success
        except Exception as e:
            DebugTerminal.log(f"Track circuit send exception: {e}")
            return False

# --- Switch State Handler ---
class SwitchStateHandler:
    def __init__(self, inputs, track_layout):
        self.inputs = inputs
        self.track_layout = track_layout
    
    def get_next_block(self, current_block: int) -> int:
        """
        Get the next block considering switch states.
        Returns the correct next block based on current switch position.
        """
        block_id = f"G{current_block}"
        
        # Check if this block has a switch
        if not self.track_layout.is_block_switch(current_block, "Green"):
            # No switch, return sequential next block
            return current_block + 1
        
        # Get switch information
        switch_info = self.track_layout.get_switch_by_block(current_block, "Green")
        if not switch_info:
            return current_block + 1
        
        # Get current switch state from wayside
        switch_state = self.inputs.get_switch_state(block_id)
        state_value = int(switch_state) if switch_state in ['0', '1'] else 0
        
        # Find the correct destination based on switch state
        connections = switch_info['connections']
        destinations = []
        
        for conn in connections:
            if conn['from_block'] == current_block:
                destinations.append(conn['to_block'])
        
        # Sort destinations to ensure consistent ordering (lower first, higher second)
        destinations = sorted([d for d in destinations if isinstance(d, int)])
        
        if len(destinations) >= 2:
            # State 0 = lower block, State 1 = higher block
            return destinations[0] if state_value == 0 else destinations[1]
        elif len(destinations) == 1:
            return destinations[0]
        else:
            # Fallback to sequential
            return current_block + 1

class TrainManager:
    """Manages up to 25 trains on Green Line"""
    
    def __init__(self, track_layout: TrackLayoutReader, inputs: TrackModelInputs):
        self.track_layout = track_layout
        self.inputs = inputs
        self.active_trains = {}  # {train_id: train_system}
        self.train_trackers = {}  # {train_id: TrainPathTracker}
        self.yard_buffer = YardBuffer()
        self.next_train_number = 1
        self.MAX_TRAINS = 25
        self.packet_timer = None
        self.block_info_objects = {}  # {block_id: BlockInfo}
        self.trains_in_yard = []  # List of trains staged in yard
        
        # Train tracking data for info panel
        self.train_creation_times = {}  # {train_id: timestamp}
        self.train_next_blocks = {}  # {train_id: [block1, block2, block3, block4]}
        self.train_last_packets = {}  # {train_id: bitstring}
        
        # Switch state handler for routing decisions
        self.switch_handler = SwitchStateHandler(inputs, track_layout)
        
        # Test mode flag to disable automatic packet sending during tests
        self.test_mode_active = False
        
        self._create_block_info_objects()
        
    def _create_block_info_objects(self):
        """Create BlockInfo objects for all blocks in track layout"""
        # Create yard block (G0) first
        yard_track_block = YardTrackBlock()
        self.block_info_objects["G0"] = BlockInfo(yard_track_block, self.inputs)
        
        # Create regular track blocks
        if self.track_layout:
            green_blocks = self.track_layout.lines.get("Green", [])
            for track_block in green_blocks:
                block_id = f"G{track_block.block_number}"
                self.block_info_objects[block_id] = BlockInfo(track_block, self.inputs)
        
        DebugTerminal.log(f"Created {len(self.block_info_objects)} BlockInfo objects (including yard G0)")
        
    def update_block_info_from_wayside(self):
        """Update all BlockInfo objects from current wayside data"""
        for block_info in self.block_info_objects.values():
            block_info.update_from_wayside()
            
    def get_next_four_blocks_from_wayside(self, starting_block: int):
        """Get next 4 blocks from wayside data for train initialization"""
        next_blocks = []
        current_block = starting_block
        
        for i in range(4):
            # Get next block number from wayside data
            block_id = f"G{current_block}"
            next_block_bits = self.inputs.get_next_block_number(block_id)
            
            try:
                # Convert 7-bit string to integer
                next_block_num = int(next_block_bits, 2) if next_block_bits else current_block + 1
            except ValueError:
                # Fallback to sequential if wayside data is invalid
                next_block_num = current_block + 1
                DebugTerminal.log(f"Invalid wayside next block data for {block_id}, using {next_block_num}")
            
            # Get TrackBlock from track layout using correct .lines access pattern
            track_block = None
            if self.track_layout:
                green_blocks = self.track_layout.lines.get("Green", [])
                for block in green_blocks:
                    if block.block_number == next_block_num:
                        track_block = block
                        break
            
            if track_block and TRAIN_SYSTEMS_AVAILABLE:
                # Create BlockInfo compatible with TrainControllerInit
                from train_controller_sw.controller.data_types import BlockInfo as TrainBlockInfo
                next_blocks.append(TrainBlockInfo(
                    block_number=track_block.block_number,
                    length_meters=track_block.length_m,
                    speed_limit_mph=int(track_block.speed_limit_kmh * 0.621371),
                    underground=track_block.is_underground,
                    authorized_to_go=True,
                    commanded_speed=2
                ))
            else:
                # Create fallback BlockInfo if track block not found
                if TRAIN_SYSTEMS_AVAILABLE:
                    from train_controller_sw.controller.data_types import BlockInfo as TrainBlockInfo
                    next_blocks.append(TrainBlockInfo(
                        block_number=next_block_num,
                        length_meters=100.0,  # Default length
                        speed_limit_mph=25,   # Default speed
                        underground=False,
                        authorized_to_go=True,
                        commanded_speed=2
                    ))
                    DebugTerminal.log(f"Using fallback BlockInfo for block {next_block_num}")
            
            current_block = next_block_num
            
        return next_blocks
    
    def process_yard_buffer_data(self, block_number: int):
        """Process next block data from wayside for yard buffer"""
        DebugTerminal.log(f"[WAYSIDE FLOW] TrainManager received block {block_number} for yard buffer")
        
        # Show current buffer state before adding
        current_buffer = self.yard_buffer.current_buffer.copy() if self.yard_buffer.current_buffer else []
        DebugTerminal.log(f"[WAYSIDE FLOW] Current buffer before: {current_buffer}")
        
        buffer_complete = self.yard_buffer.add_next_block(block_number)
        
        # Show buffer state after adding
        new_buffer = self.yard_buffer.current_buffer.copy() if self.yard_buffer.current_buffer else []
        DebugTerminal.log(f"[WAYSIDE FLOW] Buffer after adding {block_number}: {new_buffer}")
        DebugTerminal.log(f"[WAYSIDE FLOW] Buffer complete: {buffer_complete}")
        
        if buffer_complete:
            DebugTerminal.log(f"[WAYSIDE FLOW] Yard buffer sequence complete! Creating train...")
            if len(self.active_trains) < self.MAX_TRAINS:
                created_train = self.create_train()
                if created_train:
                    DebugTerminal.log(f"[WAYSIDE FLOW] SUCCESS: Train {created_train} created and deployed!")
                else:
                    DebugTerminal.log(f"[WAYSIDE FLOW] ERROR: Train creation failed")
            else:
                DebugTerminal.log("[WAYSIDE FLOW] ERROR: Cannot create train - Maximum 25 trains reached")
                
    def create_train(self):
        """Create new train from yard buffer starting at block 0 (yard)"""
        DebugTerminal.log(f"[WAYSIDE FLOW] Starting train creation process...")
        
        buffer = self.yard_buffer.get_buffer_and_clear()
        DebugTerminal.log(f"[WAYSIDE FLOW] Retrieved yard buffer: {buffer}")
        
        if not buffer:
            DebugTerminal.log(f"[WAYSIDE FLOW] ERROR: No buffer data available for train creation")
            return None
            
        if not TRAIN_SYSTEMS_AVAILABLE:
            DebugTerminal.log(f"[WAYSIDE FLOW] ERROR: Train systems not available")
            return None
            
        train_id = f"G{self.next_train_number:02d}"
        self.next_train_number += 1
        
        # Record creation time
        creation_timestamp = get_time().strftime("%H:%M:%S")
        self.train_creation_times[train_id] = creation_timestamp
        
        # Train starts at block 63 (first operational block after yard staging)
        starting_block = 63  # First operational block
        next_four_blocks = self.get_next_four_blocks_from_wayside(starting_block)
        
        if not next_four_blocks:
            DebugTerminal.log(f"Could not get next 4 blocks for train {train_id}")
            return None
            
        # Store next four blocks for info panel
        block_names = [f"G{block}" for block in next_four_blocks]
        self.train_next_blocks[train_id] = block_names
        
        # Create train initialization data 
        try:
            init_data = TrainControllerInit(
                track_color="green",
                current_block=starting_block,  # Start at block 63 (operational)
                current_commanded_speed=0,     # Start stopped
                authorized_current_block=True,
                next_four_blocks=next_four_blocks,
                train_id=train_id,
                next_station_number=0
            )
            
            # Create software train system
            train_system = TrainSystemSW(init_data, next_station_number=0)
            self.active_trains[train_id] = train_system
            self.train_trackers[train_id] = TrainPathTracker(train_id, self.track_layout)
            
            # Train is immediately operational after yard buffer sequence completion
            DebugTerminal.log(f"Created train {train_id} operational on track, starting at block {starting_block}")
            
            # Start packet timer if this is the first train
            if len(self.active_trains) == 1:
                self.start_packet_timer()
                
            return train_id
        except Exception as e:
            DebugTerminal.log(f"Failed to create train {train_id}: {e}")
            return None
    
    def destroy_all_trains(self):
        """Destroy all active trains and reset system"""
        if self.packet_timer and self.packet_timer.isActive():
            self.packet_timer.stop()
            
        self.active_trains.clear()
        self.train_trackers.clear()
        self.train_creation_times.clear()
        self.train_next_blocks.clear()
        self.train_last_packets.clear()
        
        # Clear GUI occupancy
        for block_info in self.block_info_objects.values():
            block_info.set_train_occupancy(None)
            
        DebugTerminal.log(f"All trains destroyed - system reset")
            
    def start_packet_timer(self):
        """Start 2-second timer for track circuit packets"""
        self.packet_timer = QTimer()
        self.packet_timer.timeout.connect(self.send_packets_to_trains)
        self.packet_timer.start(2000)  # 2 seconds
        
    def send_packets_to_trains(self):
        """Send track circuit packets to all active trains"""
        # Skip automatic packet sending if test mode is active
        if self.test_mode_active:
            DebugTerminal.log("Automatic packet sending disabled - test mode active")
            return
            
        # Update all BlockInfo from wayside data first
        self.update_block_info_from_wayside()
        
        for train_id, train_system in self.active_trains.items():
            try:
                # Get train position using get_train_distance_traveled()
                distance = train_system.get_train_distance_traveled()
                DebugTerminal.log(f"Train {train_id} distance_traveled: {distance}")
                self.train_trackers[train_id].update_position(distance)
                current_block_id = self.train_trackers[train_id].get_current_block()
                DebugTerminal.log(f"Train {train_id} current_block: {current_block_id}")
                
                # Extract block number from current block
                current_block_num = int(current_block_id[1:]) if current_block_id != "G0" else 0
                
                # Get 4th block ahead from wayside next block data
                fourth_block_ahead = self._get_fourth_block_ahead(current_block_num)
                
                # Get wayside data for train's current position
                authority = self.inputs.get_wayside_authority(current_block_id) == "1"
                speed_bits = self.inputs.get_wayside_commanded_speed(current_block_id)
                speed_cmd = int(speed_bits, 2) if speed_bits and len(speed_bits) == 2 else 0
                
                # Debug: Log packet details
                DebugTerminal.log(f"Train {train_id} at {current_block_id}: 4th_ahead={fourth_block_ahead}, speed_bits={speed_bits}, speed_cmd={speed_cmd}, auth={authority}")
                
                # Get station info
                station_bits = self.inputs.get_next_station_number(current_block_id)
                station_num = int(station_bits, 2) if station_bits and len(station_bits) == 5 else 0
                
                # Create and send packet with 4th block ahead
                DebugTerminal.log(f"Creating packet: block_ahead={fourth_block_ahead}, speed_cmd={speed_cmd}, auth={authority}, station={station_num}")
                packet = TrackCircuitInterface.create_packet(
                    block_number=fourth_block_ahead,  # 4th block ahead
                    speed_command=speed_cmd,
                    authorized=authority,
                    new_block=True,
                    station_number=station_num
                )
                
                success = TrackCircuitInterface.send_to_train(train_system, packet, train_id)
                if not success:
                    DebugTerminal.log(f"Packet send failed for train {train_id}")
                else:
                    # Store the actual 18-bit packet sent to train (not 16-bit simulation)
                    try:
                        # Convert 18-bit packet to binary string for display
                        packet_binary = format(packet, '018b')
                        packet_hex = format(packet, '05X')
                        self.train_last_packets[train_id] = {
                            'binary': packet_binary,
                            'hex': packet_hex,
                            'decimal': packet
                        }
                        
                        # Update next four blocks for this train
                        next_four = self.get_next_four_blocks_from_wayside(current_block_num)
                        if next_four:
                            self.train_next_blocks[train_id] = [f"G{block}" for block in next_four]
                    except Exception as e:
                        DebugTerminal.log(f"Failed to update train {train_id} tracking data: {e}")
                
                # Update GUI colors for train occupancy
                self._update_gui_train_occupancy(train_id, current_block_id)
                
                # Trigger GUI update for block colors
                if hasattr(self, 'main_window'):
                    self.main_window.update_train_count()
                    
            except Exception as e:
                DebugTerminal.log(f"Communication failed with train {train_id}: {e}")
                self.show_train_communication_error(train_id)
                
    def _get_fourth_block_ahead(self, current_block: int):
        """Get the 4th block ahead using wayside next block data"""
        block_num = current_block
        DebugTerminal.log(f"_get_fourth_block_ahead starting from block {current_block}")
        
        # Special case: G0 (yard) always routes to G63 first
        if block_num == 0:
            block_num = 63
            DebugTerminal.log(f"  Special case: G0 -> G63 (yard exit)")
            # Continue from G63 for remaining steps
            remaining_steps = 3
        else:
            remaining_steps = 4
        
        for i in range(remaining_steps):
            # Use switch handler to get correct next block
            next_block_num = self.switch_handler.get_next_block(block_num)
            DebugTerminal.log(f"  Step {i+1}: G{block_num} -> G{next_block_num} (switch-aware)")
            block_num = next_block_num
        
        DebugTerminal.log(f"_get_fourth_block_ahead result: G{block_num}")
        return block_num
        
    def _update_gui_train_occupancy(self, train_id: str, current_block_id: str):
        """Update GUI to show train occupancy on blocks"""
        # Clear previous occupancy for this train
        for block_info in self.block_info_objects.values():
            if block_info.current_train_id == train_id:
                block_info.set_train_occupancy(None)
        
        # Set current occupancy
        if current_block_id in self.block_info_objects:
            self.block_info_objects[current_block_id].set_train_occupancy(train_id)
                
    def show_train_communication_error(self, train_id: str):
        """Show error popup and close GUI"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Train Communication Error")
        msg.setText(f"Train {train_id} failed to communicate")
        msg.setInformativeText("The Track Model GUI will now close due to train communication failure.")
        msg.exec_()
        QApplication.instance().quit()
        
    def get_train_count(self):
        return len(self.active_trains)
        
    def create_train_manual(self):
        """Manually create a train for testing (bypasses yard buffer)"""
        if len(self.active_trains) >= self.MAX_TRAINS:
            DebugTerminal.log("Cannot create train: Maximum 25 trains reached")
            return None
            
        if not TRAIN_SYSTEMS_AVAILABLE:
            DebugTerminal.log("Train systems not available")
            return None
            
        # Simulate yard buffer completion
        self.yard_buffer.current_buffer = [63, 64, 65, 66]
        self.yard_buffer.is_complete = True
        
        return self.create_train()

# --- Main Window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Track Grid Display")
        self.setGeometry(100, 100, 1400, 800)  # Wider window for better panel proportions

        self.inputs = TrackModelInputs()
        self.debug_window = DebugWindow(self.inputs)
        self.debug_window.set_main_window(self)  # Set reference for tests tab
        self.info_panel = InfoPanel()
        self.train_info_panel = TrainInfoPanel()
        self.train_info_panel.main_window = self  # Set reference for data access
        self.grid_container = QWidget()
        self.grid_container.setMinimumSize(800, 700)
        self.grid_container.setStyleSheet("background-color: white;")
        self.selected_block = None
        
        # Train management system
        self.track_layout = None
        self.train_manager = None
        # Yard is now integrated as Block 0 in the main track grid

        self.load_button = QPushButton("Load Track Layout")
        self.power_button = QPushButton("Power Failure")
        self.track_button = QPushButton("Track Circuit Failure")
        self.rail_button = QPushButton("Broken Rail Failure")
        self.train_dropdown = QComboBox()
        self.train_dropdown.addItem("Select Train")  # Default option
        self.train_count_label = QLabel("0/25")  # Keep count but make it shorter
        self.toggle_debug_button = QPushButton(">_")
        self.line_selector = QComboBox()
        self.line_selector.addItems(["Green", "Red"])

        for btn in [self.load_button, self.power_button, self.track_button, self.rail_button, self.toggle_debug_button]:
            btn.setStyleSheet("font-size: 13pt; font-family: Arial;")

        hdr = QHBoxLayout()
        hdr.addWidget(self.load_button)
        hdr.addWidget(self.power_button)
        hdr.addWidget(self.track_button)
        hdr.addWidget(self.rail_button)
        hdr.addWidget(self.train_dropdown)
        hdr.addWidget(self.train_count_label)
        hdr.addWidget(QLabel("Line:"))
        hdr.addWidget(self.line_selector)
        hdr.addStretch()
        hdr.addWidget(self.toggle_debug_button)

        # Create layout (yard is now integrated into main track grid as Block 0)
        row = QHBoxLayout()
        row.addWidget(self.grid_container)
        
        # Add info panel with 3/5 ratio
        row.addWidget(self.info_panel, 3)  # 3 parts
        
        # Add train info panel with 2/5 ratio  
        row.addWidget(self.train_info_panel, 2)  # 2 parts

        main = QVBoxLayout()
        main.addLayout(hdr)
        main.addLayout(row)
        main.addWidget(self.debug_window, stretch=0)

        root = QWidget()
        root.setLayout(main)
        self.setCentralWidget(root)

        self.load_button.clicked.connect(self.load_track_data)
        self.toggle_debug_button.clicked.connect(self.toggle_debug_window)
        self.power_button.clicked.connect(lambda: self.toggle_failure('power'))
        self.track_button.clicked.connect(lambda: self.toggle_failure('track_circuit'))
        self.rail_button.clicked.connect(lambda: self.toggle_failure('broken_rail'))
        self.train_dropdown.currentTextChanged.connect(self.on_train_selected)
        self.line_selector.currentTextChanged.connect(self.display_selected_line)
        self.reader = None

        # Hide debug window by default
        self.debug_window.setVisible(False)
        self.debug_window.setMaximumHeight(int(self.height() * 0.3))

        # --- Polling for clock in main event loop ---
        self.last_clock_update = 0

        # Start polling timer
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_events)
        self.poll_timer.start(50)  # Poll 20 times per second for higher responsiveness

    def poll_events(self):
        # Update the InfoPanel clock every 0.1 seconds
        now = time.time()
        if now - self.last_clock_update > 0.1:
            self.last_clock_update = now
            self.update_info_panel_clock()

    def update_info_panel_clock(self):
        elapsed = int((get_time() - self.info_panel.sim_start_time).total_seconds())
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        seconds = elapsed % 60
        self.info_panel.clock_label.setText(f"Elapsed Time: {hours:02}:{minutes:02}:{seconds:02}")

    def resizeEvent(self, event):
        # Keep debug window at ~30% of window height
        self.debug_window.setMaximumHeight(int(self.height() * 0.3))
        super().resizeEvent(event)

    def toggle_debug_window(self):
        vis = not self.debug_window.isVisible()
        self.debug_window.setVisible(vis)

    def load_track_data(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Track Layout Excel", "", "Excel Files (*.xlsx)")
        if not path:
            return
        try:
            self.reader = TrackLayoutReader(path, selected_lines=["Green", "Red"])
            self.track_layout = self.reader
            
            # Initialize train management system
            if TRAIN_SYSTEMS_AVAILABLE:
                self.train_manager = TrainManager(self.reader, self.inputs)
                self.train_manager.main_window = self  # Set reference for GUI updates
                self.inputs.set_train_manager(self.train_manager)
                DebugWindow.print_to_terminal("Train management system initialized")
            
            self.display_selected_line()
            DebugWindow.print_to_terminal(f"Loaded: {os.path.basename(path)}")
        except Exception as e:
            DebugWindow.print_to_terminal(f"Error: {e}")

    def display_selected_line(self):
        if not self.reader:
            return
        line = self.line_selector.currentText()
        blocks = self.reader.lines.get(line, [])
        for child in self.grid_container.findChildren(QWidget):
            child.deleteLater()
        spacing = 40
        cols = 10
        
        # Create yard block (G0) first if Green line is selected
        display_blocks = []
        if line == "Green":
            yard_block = YardTrackBlock()
            display_blocks.append(yard_block)
        
        # Add regular track blocks
        display_blocks.extend(blocks)
        
        for i, blk in enumerate(display_blocks):
            box = ClickableBox(blk, self.info_panel, main_window=self, inputs=self.inputs)
            box.setParent(self.grid_container)
            row = i // cols
            col = i % cols
            box.move(10 + col * spacing, 10 + row * spacing)
            box.show()
        self.selected_block = None

    def set_selected_block(self, box):
        self.selected_block = box

    def toggle_failure(self, failure_type):
        if self.selected_block:
            bid = self.selected_block.block_id_str
            get = {
                'power': self.inputs.get_power_failure,
                'broken_rail': self.inputs.get_broken_rail_failure,
                'track_circuit': self.inputs.get_track_circuit_failure
            }[failure_type]
            val = get(bid)
            self.selected_block.set_failure(failure_type, not val)
            DebugWindow.print_to_terminal(f"{failure_type.replace('_', ' ').title()} toggled for {bid}")
            
    def simulate_wayside_yard_sequence(self):
        """Simulate a complete wayside yard buffer sequence for external testing"""
        if not self.train_manager:
            return False
            
        initial_train_count = len(self.train_manager.active_trains)
        
        # Simulate CTC sending yard buffer sequence through wayside
        for block_num in [63, 64, 65, 66]:
            self.inputs.process_next_block_for_yard(block_num)
        
        # Check if a new train was created
        final_train_count = len(self.train_manager.active_trains)
        if final_train_count > initial_train_count:
            self.update_train_count()  # Update GUI
            return True
        
        return False

    def manual_create_train(self):
        """Manually create a train for testing purposes"""
        if self.train_manager:
            # Simulate yard buffer completion by calling train creation directly
            train_id = self.train_manager.create_train_manual()
            if train_id:
                # Train creation handled by train manager, GUI will update automatically
                self.update_train_count()
                DebugWindow.print_to_terminal(f"Manually created train {train_id} - immediately operational")
            else:
                DebugWindow.print_to_terminal("Failed to create train manually")
                
    def update_train_count(self):
        """Update train count display and dropdown"""
        if self.train_manager:
            count = self.train_manager.get_train_count()
            self.train_count_label.setText(f"{count}/25")
            
            # Update train dropdown with active trains (exclude yard staged trains)
            self.update_train_dropdown()
            
            # Update GUI colors for all blocks
            for child in self.grid_container.findChildren(ClickableBox):
                child.set_failure_color()
                
    def update_train_dropdown(self):
        """Update the train selection dropdown with active trains"""
        if not self.train_manager:
            return
            
        # Get current selection to maintain it if possible
        current_selection = self.train_dropdown.currentText()
        
        # Clear and rebuild dropdown
        self.train_dropdown.clear()
        self.train_dropdown.addItem("Select Train")
        
        # Add all active trains (no yard staging exclusion)
        active_train_ids = list(self.train_manager.active_trains.keys())
                
        # Sort train IDs for consistent ordering
        active_train_ids.sort()
        
        for train_id in active_train_ids:
            self.train_dropdown.addItem(train_id)
            
        # Restore previous selection if it still exists
        if current_selection in active_train_ids:
            index = self.train_dropdown.findText(current_selection)
            if index >= 0:
                self.train_dropdown.setCurrentIndex(index)
                
    def on_train_selected(self, train_id):
        """Handle train selection from dropdown"""
        if train_id == "Select Train" or not train_id:
            self.train_info_panel.set_selected_train(None)
        else:
            self.train_info_panel.set_selected_train(train_id)
                
    def deploy_train_from_yard(self, train_id):
        """Move train from yard staging to operational track"""
        if self.train_manager and train_id in self.train_manager.trains_in_yard:
            # Remove from yard
            self.train_manager.trains_in_yard.remove(train_id)
            
            # Set train on operational track (block 63)
            if f"G63" in self.train_manager.block_info_objects:
                self.train_manager.block_info_objects["G63"].set_train_occupancy(train_id)
                DebugWindow.print_to_terminal(f"Train {train_id} deployed to block 63")
                
                # Update GUI
                self.update_train_count()

class CommunicationObject:
    """
    Communication interface for Track Model to interact with individual Wayside Controllers.
    Each wayside has its own CommunicationObject instance that manages data for blocks it covers.
    
    Array Structure: Index 0 = G0 (Yard), Index 1 = G1, ..., Index 150 = G150 (151 total elements)
    """
    
    def __init__(self, wayside_id: str, wayside_line: str = "Green"):
        """
        Initialize CommunicationObject for a specific wayside.
        
        Args:
            wayside_id: Identifier for this wayside (e.g., "1", "2", "3")
            wayside_line: Track line this wayside manages (default "Green")
        """
        self.wayside_id = wayside_id
        self.wayside_line = wayside_line
        
        # Initialize all data arrays with default values (151 elements: G0-G150)
        self._wayside_blocks_covered = ["0"] * 151      # 1-bit: determines which blocks this wayside manages
        self._next_block_numbers = ["0000000"] * 151    # 7-bit: next block numbers
        self._next_station_numbers = ["00000"] * 151    # 5-bit: next station numbers  
        self._update_block_in_queue = ["0"] * 151       # 1-bit: update block in queue
        self._wayside_authority = ["0"] * 151           # 1-bit: authority for each block
        self._wayside_commanded_speed = ["00"] * 151    # 2-bit: commanded speed
        self._switch_states = ["0"] * 151               # 1-bit: switch states
        self._traffic_light_states = ["0"] * 151        # 1-bit: traffic light states
        self._crossing_states = ["0"] * 151             # 1-bit: crossing states
        
        # Track which blocks this wayside is responsible for
        self._covered_blocks = set()
        
    def _validate_array_length(self, data_array, expected_length=151, param_name="parameter"):
        """Validate that input array has correct length"""
        if len(data_array) != expected_length:
            raise ValueError(f"{param_name} array must have {expected_length} elements, got {len(data_array)}")
    
    def _validate_bit_string(self, value, expected_length, param_name="parameter"):
        """Validate that value is a proper bit string"""
        if not isinstance(value, str):
            raise ValueError(f"{param_name} must be a string, got {type(value)}")
        if len(value) != expected_length:
            raise ValueError(f"{param_name} must be {expected_length} bits, got {len(value)}")
        if not all(c in '01' for c in value):
            raise ValueError(f"{param_name} must contain only '0' and '1', got '{value}'")
    
    def _update_covered_blocks(self):
        """Update the set of blocks this wayside covers based on wayside_blocks_covered"""
        self._covered_blocks.clear()
        for i, covered in enumerate(self._wayside_blocks_covered):
            if covered == "1":
                self._covered_blocks.add(i)
    
    # === WAYSIDE BLOCKS COVERED (Critical - determines which data to use) ===
    
    def setWaysideBlocksCovered(self, blocks_covered_list):
        """
        Set which blocks this wayside covers. This determines which other data is valid.
        
        Args:
            blocks_covered_list: List of 151 strings, each "0" or "1"
        """
        self._validate_array_length(blocks_covered_list, 151, "WaysideBlocksCovered")
        
        # Validate each element is "0" or "1"
        for i, value in enumerate(blocks_covered_list):
            if value not in ["0", "1"]:
                raise ValueError(f"WaysideBlocksCovered[{i}] must be '0' or '1', got '{value}'")
        
        self._wayside_blocks_covered = blocks_covered_list.copy()
        self._update_covered_blocks()
        DebugWindow.print_to_terminal(f"Wayside {self.wayside_id}: Updated block coverage, managing {len(self._covered_blocks)} blocks")
    
    def getWaysideBlocksCovered(self):
        """Return list of 151 strings indicating which blocks this wayside covers"""
        return self._wayside_blocks_covered.copy()
    
    # === AUTHORITY ===
    
    def setAuthorities(self, authorities_list):
        """
        Set authority values for all blocks. Only updates blocks this wayside covers.
        
        Args:
            authorities_list: List of 151 strings, each "0" or "1"
        """
        self._validate_array_length(authorities_list, 151, "Authorities")
        
        updated_count = 0
        for i, value in enumerate(authorities_list):
            self._validate_bit_string(value, 1, f"Authority[{i}]")
            
            # Only update if this wayside covers this block
            if i in self._covered_blocks:
                self._wayside_authority[i] = value
                updated_count += 1
        
        DebugWindow.print_to_terminal(f"Wayside {self.wayside_id}: Updated authority for {updated_count} covered blocks")
    
    def getWaysideAuthority(self):
        """Return complete list of 151 authority values"""
        return self._wayside_authority.copy()
    
    # === COMMANDED SPEED ===
    
    def setCommandedSpeeds(self, speeds_list):
        """
        Set commanded speed values for all blocks. Only updates blocks this wayside covers.
        
        Args:
            speeds_list: List of 151 strings, each 2-bit ("00", "01", "10", "11")
        """
        self._validate_array_length(speeds_list, 151, "CommandedSpeeds")
        
        updated_count = 0
        for i, value in enumerate(speeds_list):
            self._validate_bit_string(value, 2, f"CommandedSpeed[{i}]")
            
            if i in self._covered_blocks:
                self._wayside_commanded_speed[i] = value
                updated_count += 1
        
        DebugWindow.print_to_terminal(f"Wayside {self.wayside_id}: Updated commanded speed for {updated_count} covered blocks")
    
    def getWaysideCommandedSpeed(self):
        """Return complete list of 151 commanded speed values"""
        return self._wayside_commanded_speed.copy()
    
    # === NEXT BLOCK NUMBERS ===
    
    def setNextBlockNumbers(self, next_blocks_list):
        """
        Set next block numbers for all blocks. Only updates blocks this wayside covers.
        
        Args:
            next_blocks_list: List of 151 strings, each 7-bit
        """
        self._validate_array_length(next_blocks_list, 151, "NextBlockNumbers")
        
        updated_count = 0
        for i, value in enumerate(next_blocks_list):
            self._validate_bit_string(value, 7, f"NextBlockNumber[{i}]")
            
            if i in self._covered_blocks:
                self._next_block_numbers[i] = value
                updated_count += 1
        
        DebugWindow.print_to_terminal(f"Wayside {self.wayside_id}: Updated next block numbers for {updated_count} covered blocks")
    
    def getNextBlockNumbers(self):
        """Return complete list of 151 next block number values"""
        return self._next_block_numbers.copy()
    
    # === NEXT STATION NUMBERS ===
    
    def setNextStationNumbers(self, next_stations_list):
        """
        Set next station numbers for all blocks. Only updates blocks this wayside covers.
        
        Args:
            next_stations_list: List of 151 strings, each 5-bit
        """
        self._validate_array_length(next_stations_list, 151, "NextStationNumbers")
        
        updated_count = 0
        for i, value in enumerate(next_stations_list):
            self._validate_bit_string(value, 5, f"NextStationNumber[{i}]")
            
            if i in self._covered_blocks:
                self._next_station_numbers[i] = value
                updated_count += 1
        
        DebugWindow.print_to_terminal(f"Wayside {self.wayside_id}: Updated next station numbers for {updated_count} covered blocks")
    
    def getNextStationNumbers(self):
        """Return complete list of 151 next station number values"""
        return self._next_station_numbers.copy()
    
    # === UPDATE BLOCK IN QUEUE ===
    
    def setUpdateBlockInQueue(self, update_queue_list):
        """
        Set update block in queue values for all blocks. Only updates blocks this wayside covers.
        
        Args:
            update_queue_list: List of 151 strings, each "0" or "1"
        """
        self._validate_array_length(update_queue_list, 151, "UpdateBlockInQueue")
        
        updated_count = 0
        for i, value in enumerate(update_queue_list):
            self._validate_bit_string(value, 1, f"UpdateBlockInQueue[{i}]")
            
            if i in self._covered_blocks:
                self._update_block_in_queue[i] = value
                updated_count += 1
        
        DebugWindow.print_to_terminal(f"Wayside {self.wayside_id}: Updated update block in queue for {updated_count} covered blocks")
    
    def getUpdateBlockInQueue(self):
        """Return complete list of 151 update block in queue values"""
        return self._update_block_in_queue.copy()
    
    # === SWITCH STATES ===
    
    def setSwitchStates(self, switch_states_list):
        """
        Set switch states for all blocks. Only updates blocks this wayside covers.
        
        Args:
            switch_states_list: List of 151 strings, each "0" or "1"
        """
        self._validate_array_length(switch_states_list, 151, "SwitchStates")
        
        updated_count = 0
        for i, value in enumerate(switch_states_list):
            self._validate_bit_string(value, 1, f"SwitchState[{i}]")
            
            if i in self._covered_blocks:
                self._switch_states[i] = value
                updated_count += 1
        
        DebugWindow.print_to_terminal(f"Wayside {self.wayside_id}: Updated switch states for {updated_count} covered blocks")
    
    def getSwitchStates(self):
        """Return complete list of 151 switch state values"""
        return self._switch_states.copy()
    
    # === TRAFFIC LIGHT STATES ===
    
    def setTrafficLightStates(self, traffic_light_list):
        """
        Set traffic light states for all blocks. Only updates blocks this wayside covers.
        
        Args:
            traffic_light_list: List of 151 strings, each "0" or "1"
        """
        self._validate_array_length(traffic_light_list, 151, "TrafficLightStates")
        
        updated_count = 0
        for i, value in enumerate(traffic_light_list):
            self._validate_bit_string(value, 1, f"TrafficLightState[{i}]")
            
            if i in self._covered_blocks:
                self._traffic_light_states[i] = value
                updated_count += 1
        
        DebugWindow.print_to_terminal(f"Wayside {self.wayside_id}: Updated traffic light states for {updated_count} covered blocks")
    
    def getTrafficLightStates(self):
        """Return complete list of 151 traffic light state values"""
        return self._traffic_light_states.copy()
    
    # === CROSSING STATES ===
    
    def setCrossingStates(self, crossing_states_list):
        """
        Set crossing states for all blocks. Only updates blocks this wayside covers.
        
        Args:
            crossing_states_list: List of 151 strings, each "0" or "1"
        """
        self._validate_array_length(crossing_states_list, 151, "CrossingStates")
        
        updated_count = 0
        for i, value in enumerate(crossing_states_list):
            self._validate_bit_string(value, 1, f"CrossingState[{i}]")
            
            if i in self._covered_blocks:
                self._crossing_states[i] = value
                updated_count += 1
        
        DebugWindow.print_to_terminal(f"Wayside {self.wayside_id}: Updated crossing states for {updated_count} covered blocks")
    
    def getCrossingStates(self):
        """Return complete list of 151 crossing state values"""
        return self._crossing_states.copy()
    
    # === UTILITY METHODS ===
    
    def getWaysideInfo(self):
        """Return wayside identification information"""
        return {
            'wayside_id': self.wayside_id,
            'wayside_line': self.wayside_line,
            'blocks_covered': len(self._covered_blocks),
            'covered_block_indices': sorted(list(self._covered_blocks))
        }
    
    def getCoveredBlockCount(self):
        """Return number of blocks this wayside covers"""
        return len(self._covered_blocks)
    
    def isBlockCovered(self, block_index):
        """Check if this wayside covers a specific block index (0-150)"""
        return block_index in self._covered_blocks
    
    def getDataSummary(self, block_index):
        """Get all wayside data for a specific block index"""
        if block_index < 0 or block_index >= 151:
            raise ValueError(f"Block index must be 0-150, got {block_index}")
        
        return {
            'block_index': block_index,
            'block_id': f"G{block_index}",
            'covered': self.isBlockCovered(block_index),
            'next_block_number': self._next_block_numbers[block_index],
            'next_station_number': self._next_station_numbers[block_index],
            'update_block_in_queue': self._update_block_in_queue[block_index],
            'authority': self._wayside_authority[block_index],
            'commanded_speed': self._wayside_commanded_speed[block_index],
            'switch_state': self._switch_states[block_index],
            'traffic_light_state': self._traffic_light_states[block_index],
            'crossing_state': self._crossing_states[block_index]
        }


# Master Interface Integration Class
class TrackModelInterface(QMainWindow):
    """
    Master Interface compatible wrapper for Track Model system.
    Provides integration with Master Control Interface time and line selection.
    """
    
    def __init__(self, track_file="Track Layout & Vehicle Data vF2.xlsx", selected_lines=None):
        """
        Initialize Track Model Interface for Master Control integration.
        
        Args:
            track_file (str): Path to track layout Excel file
            selected_lines (list): List of selected lines ['Blue', 'Red', 'Green']
        """
        super().__init__()
        self.track_file = track_file
        self.selected_lines = selected_lines or ["Green"]
        self.current_time = "00:00:00"
        
        # Initialize the main track model window
        self.main_window = MainWindow()
        
        # Auto-load the track file if provided
        if track_file and os.path.exists(track_file):
            self.load_track_layout(track_file)
        
        # Configure window for Master Interface integration
        self.setWindowTitle(f"Track Model - {', '.join(self.selected_lines)} Line(s)")
        
    def load_track_layout(self, track_file):
        """Load track layout file automatically"""
        try:
            self.main_window.track_layout = TrackLayoutReader(track_file)
            
            # Filter to selected lines only
            if self.selected_lines:
                # Set line selector to first selected line for display
                first_line = self.selected_lines[0]
                if hasattr(self.main_window, 'line_selector'):
                    index = self.main_window.line_selector.findText(first_line)
                    if index >= 0:
                        self.main_window.line_selector.setCurrentIndex(index)
                
                # Load the selected line
                self.main_window.display_selected_line(first_line)
            
            # Initialize train management system
            self.main_window.train_manager = TrainManager(self.main_window.track_layout, self.main_window.inputs)
            self.main_window.inputs.set_train_manager(self.main_window.train_manager)
            
            DebugTerminal.log(f"Track layout loaded: {', '.join(self.selected_lines)} line(s)")
            
        except Exception as e:
            DebugTerminal.log(f"Error loading track layout: {e}")
    
    def update_time(self, time_str):
        """
        Called by Master Control to update the current time.
        
        Args:
            time_str (str): Current time in "HH:MM:SS" format
        """
        self.current_time = time_str
        # Track model time is now handled by Master Interface get_time() function
        # No additional processing needed as all time calls use get_time()
        
    def show(self):
        """Show the track model interface"""
        self.main_window.show()
        super().show()
        
    def close(self):
        """Clean shutdown of track model"""
        try:
            # Stop all train operations
            if self.main_window.train_manager:
                self.main_window.train_manager.destroy_all_trains()
            
            # Stop all timers
            if hasattr(self.main_window.info_panel, 'clock_timer'):
                self.main_window.info_panel.clock_timer.stop()
            if hasattr(self.main_window.debug_window, 'update_timer'):
                self.main_window.debug_window.update_timer.stop()
            if hasattr(self.main_window, 'poll_timer'):
                self.main_window.poll_timer.stop()
                
            # Close main window
            self.main_window.close()
            super().close()
            
            DebugTerminal.log("Track Model interface closed")
            
        except Exception as e:
            DebugTerminal.log(f"Error during Track Model shutdown: {e}")


if __name__ == '__main__':
    # Run normal GUI application
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QWidget { font-size: 13pt; font-family: Arial; }
        QPushButton { font-size: 13pt; font-family: Arial; }
        QLabel { font-size: 13pt; font-family: Arial; }
        QGroupBox { font-size: 13pt; font-weight: bold; font-family: Arial; }
    """)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
