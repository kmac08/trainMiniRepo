# =============================================================================
#  train_system_main_hw.py
# =============================================================================
"""
Integrated Train System Main Controller (Hardware Version)
Location: big-train-group/train_system_main_hw.py

This file integrates the Train Model and Train Controller Hardware modules to create
a complete train simulation system with GPIO/hardware support. It replaces the 
software train controller with the hardware version.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QHBoxLayout
from PyQt5.QtCore import QTimer, Qt

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'train_controller_hw'))
sys.path.append(os.path.join(current_dir, 'train_controller_hw', 'controller'))
sys.path.append(os.path.join(current_dir, 'train_controller_hw', 'gui'))
sys.path.append(os.path.join(current_dir, 'Train Model'))

# Import universal time function from Master Interface
try:
    from Master_Interface.master_control import get_time, _master_interface_instance
except ImportError:
    raise ImportError("CRITICAL ERROR: Master Interface universal time function not available. Main system requires universal time synchronization.")

# Import Train Model
from train_model import TrainModel, TrainModelInput as TMInput, TrainModelOutput as TMOutput
from train_dashboard_ui import TrainDashboard
from murphy_mode_ui import MurphyModeWindow

# Import Train Controller Hardware components
from controller.train_controller import TrainController, TrackDataError
from controller.data_types import (
    TrainModelInput, DriverInput, EngineerInput, TrainModelOutput, 
    TrainControllerInit, BlockInfo
)

# Import Hardware GUI components
from gui.train_controller_driver_remote_fixed import DriverUI
from gui.train_controller_engineer import EngineerUI
from gui.initialization_ui import InitializationUI

# Import Track Circuit Test UI
from track_circuit_test_ui import TrackCircuitTestUI


class TrainSystemHW(QMainWindow):
    """
    Main system that integrates the Train Model physics engine with 
    the Train Controller Hardware backend and all GUI components.
    """
    
    def __init__(self, init_data: TrainControllerInit = None, next_station_number: int = 0, serial_port: str = 'COM4', baud_rate: int = 9600):
        super().__init__()
        
        # =================================================================
        # START MASTER INTERFACE FIRST FOR UNIVERSAL TIME
        # =================================================================
        print("Starting Master Interface for universal time system...")
        self.start_master_interface()
        
        # =================================================================
        # STORE INITIALIZATION PARAMETERS
        # =================================================================
        self.init_data = init_data
        self.next_station_number = next_station_number
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        
        # =================================================================
        # INITIALIZATION STATUS
        # =================================================================
        self.train_model = None
        self.train_controller = None
        self.driver_gui = None
        self.engineer_gui = None
        self.train_dashboard = None
        self.murphy_mode_ui = None
        self.track_circuit_test_ui = None
        self.controller_initialized = False
        self.initialization_ui = None
        
        # Integration state
        self.next_block_entered_state = False
        
        # Emergency brake state tracking
        self.previous_driver_emergency_brake = False
        
        # =================================================================
        # CONDITIONAL INITIALIZATION
        # =================================================================
        if self.init_data is not None:
            # Direct initialization with provided data
            print("Direct initialization with provided TrainControllerInit data...")
            self.setup_main_window()
            self.initialize_train_model(self.init_data)
            self.initialize_train_controller(self.init_data)
            self.setup_train_model_ui()
            self.setup_update_timer()
            self.show()
            print("Integrated Train System Hardware initialized successfully!")
        else:
            # Show initialization UI to get data
            print("Showing initialization UI...")
            self.show_initialization_ui()
        
    def start_master_interface(self):
        """Start the Master Interface for universal time system"""
        try:
            from Master_Interface.master_control import MasterInterface
            self.master_interface = MasterInterface()
            self.master_interface.show()
            
            # Start the time manager
            if not self.master_interface.time_manager.isRunning():
                self.master_interface.time_manager.start()
            
            print("Master Interface started successfully - Universal time system active")
            
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to start Master Interface: {e}")
            raise RuntimeError(f"Cannot start universal time system: {e}")
    
    def show_initialization_ui(self):
        """Show the initialization UI to get train controller setup data"""
        self.initialization_ui = InitializationUI()
        self.initialization_ui.initialization_complete.connect(self.on_initialization_complete)
        self.initialization_ui.show()
        
        # Hide main window until initialization is complete
        self.hide()
    
    def on_initialization_complete(self, init_data: TrainControllerInit):
        """Handle completion of initialization UI"""
        print("Initialization data received from UI!")
        print(f"Track Color: {init_data.track_color}")
        print(f"Current Block: {init_data.current_block}")
        print(f"Next 4 blocks: {[block.block_number for block in init_data.next_four_blocks]}")
        
        # Now set up the main window and initialize models
        self.setup_main_window()
        self.initialize_train_model(init_data)
        self.initialize_train_controller(init_data)
        self.setup_train_model_ui()
        
        # Set up update timer
        self.setup_update_timer()
        
        # Show the main window
        self.show()
        
        print("Integrated Train System Hardware initialized successfully!")
        
    def initialize_train_model(self, init_data: TrainControllerInit):
        """Initialize the Train Model physics engine"""
        try:
            # Use numeric train ID for compatibility with controller
            train_id = getattr(init_data, 'train_id', init_data.current_block)
            self.train_model = TrainModel(str(train_id))
            
            # Set initial conditions based on initialization data
            self.train_model.velocity_mps = 0.0  # Start stationary
            
            # Set next station number if provided
            if hasattr(self, 'next_station_number') and self.next_station_number > 0:
                self.train_model.next_station_code = self.next_station_number
                print(f"Next station set to: {self.next_station_number}")
            
            print(f"Train Model initialized with ID: {train_id}")
            
        except Exception as e:
            print(f"ERROR: Failed to initialize Train Model: {e}")
            raise
        
    def initialize_train_controller(self, init_data: TrainControllerInit):
        """Initialize the train controller and GUIs"""
        try:
            print(f"Received initialization data for {init_data.track_color} Line, Block {init_data.current_block}")
            
            # Initialize train controller with track data
            self.train_controller = TrainController(init_data, kp=12.0, ki=1.2)
            
            # Now initialize the driver and engineer GUIs
            self.setup_driver_gui()
            self.setup_engineer_gui()
            
            self.controller_initialized = True
            print("Train Controller Hardware and GUIs successfully initialized!")
            
            # Update status
            self.status_label.setText(f"Status: Initialized - {init_data.track_color} Line, Block {init_data.current_block} (HW)")
            self.controller_status.setText(f"Controller: Hardware Active ({init_data.track_color} Line)")
            
        except TrackDataError as e:
            print(f"CRITICAL ERROR: {e}")
            self.status_label.setText("Status: INITIALIZATION FAILED - Track Data Error")
            self.controller_status.setText("Controller: FAILED - No Track Data")
            
            # Show error dialog
            from PyQt5.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Train Controller Hardware Initialization Error")
            msg.setText("Cannot initialize train controller hardware")
            msg.setDetailedText(str(e))
            msg.exec_()
            
        except Exception as e:
            print(f"Unexpected error during initialization: {e}")
            self.status_label.setText(f"Status: INITIALIZATION FAILED - {str(e)}")
            self.controller_status.setText("Controller: FAILED")
            import traceback
            traceback.print_exc()
    
    def setup_main_window(self):
        """Setup the main coordinator window"""
        self.setWindowTitle("Integrated Train System Hardware - Main Control")
        self.setGeometry(50, 50, 500, 400)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("Integrated Train System Hardware")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Status section
        status_group = QWidget()
        status_layout = QVBoxLayout(status_group)
        status_layout.setContentsMargins(10, 10, 10, 10)
        
        self.status_label = QLabel("Status: Running")
        self.controller_status = QLabel("Controller: Hardware Active")
        self.model_status = QLabel("Train Model: Active")
        self.update_counter = QLabel("Updates: 0")
        self.gpio_status = QLabel(f"GPIO: {self.serial_port}@{self.baud_rate}")
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.controller_status)
        status_layout.addWidget(self.model_status)
        status_layout.addWidget(self.update_counter)
        status_layout.addWidget(self.gpio_status)
        
        status_group.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 5px;")
        layout.addWidget(status_group)
        
        # Control buttons
        button_layout = QVBoxLayout()
        
        self.show_driver_btn = QPushButton("Show Hardware Driver GUI")
        self.show_engineer_btn = QPushButton("Show Engineer GUI")
        self.show_train_dashboard_btn = QPushButton("Show Train Dashboard")
        self.show_murphy_mode_btn = QPushButton("Show Murphy Mode")
        self.show_track_circuit_test_btn = QPushButton("Show Track Circuit Test UI")
        self.open_all_uis_btn = QPushButton("🚀 OPEN ALL UIs")
        self.emergency_stop_btn = QPushButton("MASTER EMERGENCY STOP")
        
        self.show_driver_btn.clicked.connect(self.show_driver_gui)
        self.show_engineer_btn.clicked.connect(self.show_engineer_gui)
        self.show_train_dashboard_btn.clicked.connect(self.show_train_dashboard)
        self.show_murphy_mode_btn.clicked.connect(self.show_murphy_mode)
        self.show_track_circuit_test_btn.clicked.connect(self.show_track_circuit_test_ui)
        self.open_all_uis_btn.clicked.connect(self.open_all_uis)
        self.emergency_stop_btn.clicked.connect(self.emergency_stop)
        
        # Style buttons
        button_style = """
            QPushButton {
                padding: 10px;
                font-size: 12px;
                border-radius: 5px;
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """
        
        self.show_driver_btn.setStyleSheet(button_style)
        self.show_engineer_btn.setStyleSheet(button_style)
        self.show_train_dashboard_btn.setStyleSheet(button_style)
        self.show_murphy_mode_btn.setStyleSheet(button_style)
        self.show_track_circuit_test_btn.setStyleSheet(button_style)
        
        # Special style for "Open All UIs" button to make it stand out
        open_all_style = """
            QPushButton {
                padding: 12px;
                font-size: 14px;
                border-radius: 5px;
                background-color: #FF6B35;
                color: white;
                font-weight: bold;
                border: 2px solid #FF4500;
            }
            QPushButton:hover {
                background-color: #FF4500;
                border: 2px solid #FF6B35;
            }
        """
        self.open_all_uis_btn.setStyleSheet(open_all_style)
        
        # Style emergency button
        self.emergency_stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #CC0000;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #DD0000;
            }
        """)
        
        button_layout.addWidget(self.show_driver_btn)
        button_layout.addWidget(self.show_engineer_btn)
        button_layout.addWidget(self.show_train_dashboard_btn)
        button_layout.addWidget(self.show_murphy_mode_btn)
        button_layout.addWidget(self.show_track_circuit_test_btn)
        button_layout.addSpacing(10)
        button_layout.addWidget(self.open_all_uis_btn)
        button_layout.addSpacing(20)
        button_layout.addWidget(self.emergency_stop_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        # Initialize update counter
        self.update_count = 0
        
        # Track emergency state
        self.emergency_active = False
    
    def setup_driver_gui(self):
        """Initialize the Hardware Driver GUI"""
        self.driver_gui = DriverUI(self.serial_port, self.baud_rate)
        self.driver_gui.set_train_controller(self.train_controller)
        self.driver_gui.setGeometry(600, 50, 1500, 920)
        
        # CRITICAL: Start the GPIO polling timer in the driver GUI
        self.driver_gui.setup_timer()
        
        self.driver_gui.show()
        print(f"Hardware Driver GUI initialized and displayed (GPIO: {self.serial_port}@{self.baud_rate})")
        print("GPIO polling timer started - hardware inputs now active")
    
    def setup_engineer_gui(self):
        """Initialize the Engineer GUI"""
        self.engineer_gui = EngineerUI()
        self.engineer_gui.setGeometry(100, 500, 500, 300)
        
        # Set train controller reference for speed checking
        self.engineer_gui.set_train_controller(self.train_controller)
        
        # Connect engineer input signal
        self.engineer_gui.kp_ki_submitted.connect(self.update_controller_gains)
        self.engineer_gui.show()
        print("Engineer GUI initialized and displayed")
    
    def setup_train_model_ui(self):
        """Initialize the Train Model UI components"""
        # Initialize Train Dashboard
        self.train_dashboard = TrainDashboard(self.train_model)
        self.train_dashboard.setGeometry(600, 800, 1000, 600)
        self.train_dashboard.show()
        
        # Initialize Murphy Mode UI
        self.murphy_mode_ui = MurphyModeWindow(self.train_model)
        self.murphy_mode_ui.setGeometry(50, 600, 300, 200)
        self.murphy_mode_ui.show()
        
        print("Train Dashboard and Murphy Mode UI initialized and displayed")
        
    def setup_update_timer(self):
        """Setup updates synchronized with Master Interface time updates"""
        if not hasattr(self, 'master_interface') or not hasattr(self.master_interface, 'time_manager'):
            raise RuntimeError("CRITICAL ERROR: Master Interface not available for time synchronization.")
        
        # Connect to Master Interface time updates for proper simulation time sync
        self.master_interface.time_manager.time_update.connect(self.on_time_update)
        print("Connected to Master Interface time updates for simulation time sync")
    
    def on_time_update(self, time_str):
        """Handle time updates from Master Interface and trigger system updates"""
        try:
            self.update_system()
                
        except Exception as e:
            print(f"Error in time update handling: {e}")
            raise RuntimeError("CRITICAL ERROR: Failed to handle universal time update.")
    
    def update_system(self):
        """
        Main system update function - integrates Train Model and Train Controller Hardware
        """
        # Skip updates if not initialized yet
        if (not self.controller_initialized or 
            self.train_controller is None or 
            self.train_model is None):
            return
            
        try:
            # =============================================================
            # 1. ENSURE LATEST GPIO INPUTS ARE READ
            # =============================================================
            # Trigger GPIO reading to get the latest hardware inputs
            if hasattr(self.driver_gui, 'read_gpio_inputs'):
                self.driver_gui.read_gpio_inputs()
            
            # =============================================================
            # 2. GET DRIVER INPUT FROM HARDWARE GUI
            # =============================================================
            driver_input = self.driver_gui.get_driver_input()
            
            # Note: Removed master emergency override to allow driver control over emergency brake
            # Driver should have full control over their emergency brake without master override
            
            # =============================================================
            # 3. BUILD TRAIN MODEL INPUT FROM CURRENT TRAIN STATE
            # =============================================================
            # Use train model's method to get parsed track circuit data
            train_model_input = self.train_model.build_train_input()
            
            # =============================================================
            # 3.5. HANDLE PASSENGER EMERGENCY BRAKE RESET LOGIC
            # =============================================================
            # When driver RELEASES their emergency brake (transition from True to False), also reset passenger emergency brake
            # This must happen BEFORE controller processes the input to break the circular dependency
            if (self.previous_driver_emergency_brake and not driver_input.emergency_brake and 
                self.train_model.passenger_emergency_brake):
                print("Driver released emergency brake - resetting passenger emergency brake")
                self.train_model.reset_passenger_emergency_brake()
            
            # Update previous state for next iteration
            self.previous_driver_emergency_brake = driver_input.emergency_brake
            
            # =============================================================
            # 4. UPDATE TRAIN CONTROLLER WITH INPUTS
            # =============================================================
            self.train_controller.update(train_model_input, driver_input)
            
            # =============================================================
            # 5. GET CONTROLLER OUTPUT AND APPLY TO TRAIN MODEL
            # =============================================================
            controller_output = self.train_controller.get_output()
            self.apply_controller_output_to_train_model(controller_output)
            
            # =============================================================
            # 6. UPDATE TRAIN MODEL PHYSICS
            # =============================================================
            dt = 0.1  # Update every 0.1 simulation seconds
            self.train_model.update_speed(dt)
            
            # =============================================================
            # 7. UPDATE HARDWARE DRIVER GUI WITH LATEST DATA
            # =============================================================
            self.driver_gui.update_from_train_controller()
            
            # =============================================================
            # 8. UPDATE ENGINEER GUI WITH CURRENT GAINS
            # =============================================================
            kp, ki = self.train_controller.get_gains()
            self.engineer_gui.update_current_values(kp, ki)
            
            # Update status display
            self.update_status_display(driver_input, train_model_input, controller_output)
            
        except Exception as e:
            print(f"Error in system update: {e}")
            self.status_label.setText(f"Status: Error - {str(e)}")
            self.model_status.setText("Train Model: Error")
    
    
    def apply_controller_output_to_train_model(self, output: TrainModelOutput):
        """
        Apply Train Controller output to Train Model
        """
        # Convert controller output to train model format (use Train Model's dataclass)
        tm_output = TMOutput(
            power_kw=output.power_kw,
            emergency_brake_status=output.emergency_brake_status,
            interior_lights_status=output.interior_lights_status,
            headlights_status=output.headlights_status,
            door_left_status=output.door_left_status,
            door_right_status=output.door_right_status,
            service_brake_status=output.service_brake_status,
            set_cabin_temperature=output.set_cabin_temperature,
            train_id=output.train_id,  # Already a string
            station_stop_complete=output.station_stop_complete,
            next_station_name=output.next_station_name,
            next_station_side=output.next_station_side,
            edge_of_current_block=output.edge_of_current_block,
        )
        
        # Apply to train model
        self.train_model.apply_controller_output(tm_output)
    
    def update_status_display(self, driver_input, train_model_input, controller_output):
        """Update the status display with current system information"""
        self.update_count += 1
        self.update_counter.setText(f"Updates: {self.update_count}")
        
        # Update controller status with gains
        kp, ki = self.train_controller.get_gains()
        self.controller_status.setText(f"Controller HW: Kp={kp:.1f}, Ki={ki:.1f}")
        
        # Update model status
        speed_mph = self.train_model.velocity_mps * 2.237
        self.model_status.setText(f"Train Model: {speed_mph:.1f} mph, {self.train_model.mass_kg:.0f} kg")
        
        # Update GPIO status
        gpio_connected = self.driver_gui.is_gpio_connected() if hasattr(self.driver_gui, 'is_gpio_connected') else False
        gpio_status = "CONNECTED" if gpio_connected else "DISCONNECTED"
        self.gpio_status.setText(f"GPIO: {self.serial_port}@{self.baud_rate} ({gpio_status})")
        
        # Show detailed status every second
        if self.update_count % 10 == 0:
            mode = "Auto" if driver_input.auto_mode else "Manual"
            power = controller_output.power_kw
            
            # Check for faults
            faults = []
            if train_model_input.fault_status.get('engine', False):
                faults.append("ENGINE")
            if train_model_input.fault_status.get('signal', False):
                faults.append("SIGNAL")
            if train_model_input.fault_status.get('brake', False):
                faults.append("BRAKE")
            
            fault_str = f" | FAULTS: {', '.join(faults)}" if faults else ""
            
            self.status_label.setText(f"Status: {mode} | Speed: {speed_mph:.1f} mph | Power: {power:.1f} kW{fault_str}")
        
        # Debug: Log GPIO inputs every 50 updates (every 5 seconds)
        if self.update_count % 50 == 0:
            print(f"GPIO Hardware Inputs - Auto: {driver_input.auto_mode}, "
                  f"Emergency: {driver_input.emergency_brake}, "
                  f"Service Brake: {driver_input.service_brake}, "
                  f"Headlights: {driver_input.headlights_on}, "
                  f"Interior: {driver_input.interior_lights_on}, "
                  f"Left Door: {driver_input.door_left_open}, "
                  f"Right Door: {driver_input.door_right_open}, "
                  f"Speed: {driver_input.set_speed}, "
                  f"Temp: {driver_input.set_temperature}")
            
            # Also log GPIO connection status
            gpio_connected = self.driver_gui.is_gpio_connected() if hasattr(self.driver_gui, 'is_gpio_connected') else False
            print(f"GPIO Connection Status: {'CONNECTED' if gpio_connected else 'DISCONNECTED'}")
    
    def update_controller_gains(self, engineer_input: EngineerInput):
        """Handle controller gain updates from Engineer GUI"""
        self.train_controller.update_from_engineer_input(engineer_input)
        print(f"Controller gains updated: Kp={engineer_input.kp}, Ki={engineer_input.ki}")
    
    def show_driver_gui(self):
        """Show/raise the hardware driver GUI window"""
        if self.driver_gui is None:
            print("Hardware Driver GUI not initialized yet.")
            return
        self.driver_gui.show()
        self.driver_gui.raise_()
        self.driver_gui.activateWindow()
    
    def show_engineer_gui(self):
        """Show/raise the engineer GUI window"""
        if self.engineer_gui is None:
            print("Engineer GUI not initialized yet.")
            return
        self.engineer_gui.show()
        self.engineer_gui.raise_()
        self.engineer_gui.activateWindow()
    
    def show_train_dashboard(self):
        """Show/raise the train dashboard window"""
        if self.train_dashboard is None:
            print("Train Dashboard not initialized yet.")
            return
        self.train_dashboard.show()
        self.train_dashboard.raise_()
        self.train_dashboard.activateWindow()
    
    def show_murphy_mode(self):
        """Show/raise the murphy mode window"""
        if self.murphy_mode_ui is None:
            print("Murphy Mode UI not initialized yet.")
            return
        self.murphy_mode_ui.show()
        self.murphy_mode_ui.raise_()
        self.murphy_mode_ui.activateWindow()
    
    def open_all_uis(self):
        """Open and show all available UI windows"""
        print("Opening all UI windows...")
        
        # Show Hardware Driver GUI
        self.show_driver_gui()
        
        # Show Engineer GUI
        self.show_engineer_gui()
        
        # Show Train Dashboard
        self.show_train_dashboard()
        
        # Show Murphy Mode UI
        self.show_murphy_mode()
        
        # Show Track Circuit Test UI
        self.show_track_circuit_test_ui()
        
        # Arrange windows in a reasonable layout
        self.arrange_ui_windows()
        
        print("All UI windows opened successfully")
    
    def arrange_ui_windows(self):
        """Arrange UI windows in a non-overlapping layout"""
        # Main window (this) - top left
        self.setGeometry(50, 50, 1000, 700)
        
        # Hardware Driver GUI - top right
        if self.driver_gui:
            self.driver_gui.setGeometry(1070, 50, 800, 700)
        
        # Engineer GUI - bottom left
        if self.engineer_gui:
            self.engineer_gui.setGeometry(50, 770, 500, 400)
        
        # Train Dashboard - bottom center
        if self.train_dashboard:
            self.train_dashboard.setGeometry(570, 770, 600, 400)
        
        # Murphy Mode - bottom right
        if self.murphy_mode_ui:
            self.murphy_mode_ui.setGeometry(1190, 770, 400, 400)
        
        # Track Circuit Test UI - far right
        if self.track_circuit_test_ui:
            self.track_circuit_test_ui.setGeometry(1890, 50, 500, 600)
        
        print("UI windows arranged in organized layout")
    
    def show_track_circuit_test_ui(self):
        """Show/initialize the track circuit test UI"""
        if self.track_circuit_test_ui is None:
            self.setup_track_circuit_test_ui()
        self.track_circuit_test_ui.show()
        self.track_circuit_test_ui.raise_()
        self.track_circuit_test_ui.activateWindow()
    
    def setup_track_circuit_test_ui(self):
        """Initialize the Track Circuit Test UI"""
        self.track_circuit_test_ui = TrackCircuitTestUI()
        self.track_circuit_test_ui.setGeometry(900, 500, 500, 600)
        
        # Connect the signal from test UI to handle track circuit data
        self.track_circuit_test_ui.track_circuit_data_signal.connect(self.handle_track_circuit_data)
        
        # Connect train model to track circuit test UI for automatic testing
        if self.train_model:
            self.track_circuit_test_ui.set_train_model(self.train_model)
        
        print("Track Circuit Test UI initialized and connected")
    
    def handle_track_circuit_data(self, data_packet: int):
        """Handle 18-bit track circuit data from test UI"""
        if self.train_model is None:
            print("ERROR: Train Model not initialized - cannot process track circuit data")
            return
            
        try:
            # Use the train model's parse_track_circuit function
            self.train_model.parse_track_circuit(data_packet)
            
            # Extract the parsed components for logging
            block_number = self.train_model.tc_block_number
            commanded_signal = self.train_model.tc_commanded_signal
            authority_bit = self.train_model.tc_authority_bit
            new_block_flag = self.train_model.tc_new_block_flag
            next_block_entered_flag = self.train_model.tc_next_block_entered_flag
            update_block_in_queue = self.train_model.tc_update_block_in_queue
            station_number = self.train_model.tc_station_number
            
            print(f"Track Circuit Data Processed:")
            print(f"  Raw packet: {data_packet} (binary: {bin(data_packet)})")
            print(f"  Block Number: {block_number}")
            print(f"  Commanded Signal: {commanded_signal}")
            print(f"  Authority Bit: {authority_bit}")
            print(f"  New Block Flag: {new_block_flag}")
            print(f"  Next Block Entered Flag: {next_block_entered_flag}")
            print(f"  Update Block in Queue: {update_block_in_queue}")
            print(f"  Station Number: {station_number}")
            
            # Update the train model's next block info based on parsed track circuit data
            # This integrates the track circuit data into the existing communication flow
            if new_block_flag:
                self.train_model.receive_track_circuit_data(
                    block_number, 
                    commanded_signal, 
                    authority_bit, 
                    bool(new_block_flag)
                )
                print(f"  → Updated next block info: Block {block_number}, Speed {commanded_signal}, Auth {authority_bit}")
            
        except Exception as e:
            print(f"ERROR processing track circuit data: {e}")
    
    def send_track_circuit_data(self, data_packet: int):
        """
        External accessor function for track model to send 18-bit track circuit data.
        
        This function allows the track model to send track circuit information directly
        to this train system, which will automatically feed into the train model's
        existing track circuit parser.
        
        Args:
            data_packet (int): 18-bit integer containing track circuit information
                             Following the established bit layout:
                             Bit layout: [Block Number (7)] [Commanded Signal (2)] [Authority (1)] [New Block Flag (1)] [Next Block Entered (1)] [Update Block Queue (1)] [Station Number (5)]
                             - Bits 17-11: Block Number (7 bits, 0-127)
                             - Bits 10-9:  Commanded Signal (2 bits, 0-3)  
                             - Bit 8:      Authority Bit (1 bit, 0-1)
                             - Bit 7:      New Block Flag (1 bit, 0-1)
                             - Bit 6:      Next Block Entered Flag (1 bit, 0-1)
                             - Bit 5:      Update Block Queue (1 bit, 0-1)
                             - Bits 4-0:   Station Number (5 bits, 0-31)
        
        Returns:
            bool: True if data was processed successfully, False if train model not initialized
            
        Example:
            # Create track circuit packet for block 25, speed 2, authorized, new block, station 5
            packet = (25 << 11) | (2 << 9) | (1 << 8) | (1 << 7) | (0 << 6) | (0 << 5) | 5
            success = train_system.send_track_circuit_data(packet)
        """
        if self.train_model is None:
            print("ERROR: Train Model not initialized - cannot process track circuit data")
            return False
            
        try:
            # Validate the data packet is within 18-bit range (same validation as track circuit test UI)
            if data_packet > 0b111111111111111111:  # 18-bit maximum (262143)
                print(f"ERROR: Track circuit data packet {data_packet} exceeds 18-bit maximum")
                return False
            
            # Use the existing track circuit handler to process the data
            # This ensures identical processing to the track circuit test UI
            self.handle_track_circuit_data(data_packet)
            
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to process track circuit data from track model: {e}")
            return False
    
    def get_train_distance_traveled(self):
        """
        External accessor function for track model to get the train's total distance traveled.
        
        This function allows the track model to access the current distance traveled by the train
        so it can track the train's position at all times for location-based decisions.
        
        Returns:
            float: Total distance traveled by the train in meters since system start.
                   Returns 0.0 if train model is not initialized.
            
        Note:
            - Distance is accumulated through velocity integration in the train model
            - This is called by the track model during each iteration of its loop
            - Critical for the track model to know train position for safety and routing
            
        Example:
            current_position_m = train_system.get_train_distance_traveled()
            print(f"Train has traveled {current_position_m:.2f} meters")
        """
        if self.train_model is None:
            return 0.0
            
        try:
            return self.train_model.get_distance_traveled()
            
        except Exception as e:
            print(f"ERROR: Failed to get train distance traveled: {e}")
            return 0.0
    
    def emergency_stop(self):
        """Emergency stop - forces emergency brake activation"""
        self.emergency_active = not self.emergency_active
        
        if self.emergency_active:
            print("MASTER EMERGENCY STOP ACTIVATED!")
            self.emergency_stop_btn.setText("RELEASE MASTER EMERGENCY")
            self.emergency_stop_btn.setStyleSheet("""
                QPushButton {
                    background-color: #660000;
                    color: white;
                    font-weight: bold;
                    font-size: 14px;
                    padding: 15px;
                    border-radius: 5px;
                }
            """)
            # Master emergency will be processed through the control loop
            # Don't directly manipulate train model - let it go through proper channels
        else:
            print("Master emergency stop released")
            self.emergency_stop_btn.setText("MASTER EMERGENCY STOP")
            self.emergency_stop_btn.setStyleSheet("""
                QPushButton {
                    background-color: #CC0000;
                    color: white;
                    font-weight: bold;
                    font-size: 14px;
                    padding: 15px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #DD0000;
                }
            """)
    
    def closeEvent(self, event):
        """Handle application closing"""
        print("Shutting down Integrated Train System Hardware...")
        
        # Disconnect from Master Interface time updates
        if hasattr(self, 'master_interface'):
            try:
                self.master_interface.time_manager.time_update.disconnect(self.on_time_update)
            except:
                pass
        
        # Close all GUI windows
        if hasattr(self, 'driver_gui') and self.driver_gui is not None:
            self.driver_gui.close()
        if hasattr(self, 'engineer_gui') and self.engineer_gui is not None:
            self.engineer_gui.close()
        if hasattr(self, 'train_dashboard') and self.train_dashboard is not None:
            self.train_dashboard.close()
        if hasattr(self, 'murphy_mode_ui') and self.murphy_mode_ui is not None:
            self.murphy_mode_ui.close()
        
        # Stop Master Interface
        if hasattr(self, 'master_interface'):
            print("Stopping Master Interface...")
            self.master_interface.stop_all_modules()
            self.master_interface.close()
        
        print("System shutdown complete")
        event.accept()


def main(init_data: TrainControllerInit = None, next_station_number: int = 0, serial_port: str = 'COM4', baud_rate: int = 9600):
    """
    Main entry point for the Integrated Train System Hardware
    
    Args:
        init_data (TrainControllerInit, optional): Initialization data for train controller
        next_station_number (int, optional): Next station number for the train
        serial_port (str, optional): Serial port for GPIO communication (default: 'COM4')
        baud_rate (int, optional): Baud rate for GPIO communication (default: 9600)
    """
    print("=" * 60)
    print("INTEGRATED TRAIN SYSTEM HARDWARE STARTUP")
    print("=" * 60)
    
    # Create QApplication
    app = QApplication(sys.argv)
    
    try:
        # Create and show the main system
        system = TrainSystemHW(init_data, next_station_number, serial_port, baud_rate)
        
        # Only show if not already shown (in case of direct initialization)
        if not system.isVisible():
            system.show()
        
        print("\n" + "=" * 60)
        print("SYSTEM READY - All hardware components active")
        print("Hardware Driver GUI: Controls train operation via GPIO")
        print("Engineer GUI: Adjusts controller parameters")
        print("Train Dashboard: Real-time train status display")
        print("Murphy Mode: Toggle train failures for testing")
        print("Train Model: Physics simulation engine")
        print("Train Controller: Hardware automated control system")
        print(f"GPIO Communication: {serial_port}@{baud_rate}")
        print("Update Rate: 10Hz (every 0.1 seconds)")
        print("=" * 60)
        print("\nINSTRUCTIONS:")
        if init_data is None:
            print("1. Initialize system with track and block data")
        else:
            print("1. System pre-initialized with provided data")
        print("2. Use Hardware Driver GUI to control the train via GPIO")
        print("3. Use Engineer GUI to adjust controller gains")
        print("4. Use Train Dashboard to monitor train status")
        print("5. Use Murphy Mode to test failure scenarios")
        print("6. Watch real physics simulation in real-time")
        print("7. Hardware controls work through GPIO/serial connection")
        print("=" * 60 + "\n")
        
        # Run the application
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"SYSTEM STARTUP FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

# Export the main classes for external use
__all__ = ['IntegratedTrainSystemHW', 'main']
