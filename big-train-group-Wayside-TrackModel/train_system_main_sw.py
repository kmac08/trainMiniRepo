# =============================================================================
#  train_system_main_sw.py
# =============================================================================
"""
Integrated Train System with New Professional Software Driver UI
Location: big-train-group/train_system_with_new_sw_ui/train_system_with_new_sw_ui.py

This file integrates the Train Model and Train Controller modules with the new 
professional software driver UI to create a complete train simulation system.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QHBoxLayout
from PyQt5.QtCore import QTimer, Qt

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'train_controller_sw'))
sys.path.append(os.path.join(current_dir, 'train_controller_sw', 'controller'))
sys.path.append(os.path.join(current_dir, 'train_controller_sw', 'gui'))
sys.path.append(os.path.join(current_dir, 'Train Model'))
sys.path.append(os.path.join(current_dir, 'professional_driver_ui'))

# Import universal time function from Master Interface
try:
    from Master_Interface.master_control import get_time, _master_interface_instance
except ImportError:
    raise ImportError("CRITICAL ERROR: Master Interface universal time function not available. Main system requires universal time synchronization.")

# Import Train Model
from train_model import TrainModel, TrainModelInput as TMInput, TrainModelOutput as TMOutput
from train_dashboard_ui import TrainDashboard
from murphy_mode_ui import MurphyModeWindow

# Import Train Controller components
from controller.train_controller import TrainController, TrackDataError
from controller.data_types import (
    TrainModelInput, DriverInput, EngineerInput, TrainModelOutput, 
    TrainControllerInit, BlockInfo
)

# Import GUI components - use new professional driver UI
from professional_sw_driver_ui import ProfessionalSoftwareDriverUI
from gui.train_controller_engineer import EngineerUI
from gui.initialization_ui import InitializationUI

# Import Track Circuit Test UI
from track_circuit_test_ui import TrackCircuitTestUI


class TrainSystemSW(QMainWindow):
    """
    Main system that integrates the Train Model physics engine with 
    the Train Controller backend and the new professional software driver UI.
    """
    
    def __init__(self, init_data: TrainControllerInit = None, next_station_number: int = 0):
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
            print("Integrated Train System with New SW UI initialized successfully!")
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
        
        print("Integrated Train System with New SW UI initialized successfully!")
        
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
                print(f"Train Model: Next station set to: {self.next_station_number}")
            elif hasattr(init_data, 'next_station_number') and init_data.next_station_number > 0:
                self.train_model.next_station_code = init_data.next_station_number
                print(f"Train Model: Next station set from init_data to: {init_data.next_station_number}")
            else:
                print(f"Train Model: No next station number provided")
                
            print(f"Train Model next_station_code after initialization: {getattr(self.train_model, 'next_station_code', 'NOT SET')}")
            
            print(f"Train Model initialized with ID: {train_id}")
            
        except Exception as e:
            print(f"ERROR: Failed to initialize Train Model: {e}")
            raise
        
    def initialize_train_controller(self, init_data: TrainControllerInit):
        """Initialize the train controller and GUIs"""
        try:
            print(f"Received initialization data for {init_data.track_color} Line, Block {init_data.current_block}")
            print(f"Initialization data next_station_number: {getattr(init_data, 'next_station_number', 'NOT SET')}")
            
            # Ensure next station number is set in initialization data
            if hasattr(self, 'next_station_number') and self.next_station_number > 0:
                init_data.next_station_number = self.next_station_number
                print(f"Overriding next station number to: {self.next_station_number}")
            
            print(f"Final initialization data next_station_number: {init_data.next_station_number}")
            
            # Initialize train controller with track data
            self.train_controller = TrainController(init_data, kp=12.0, ki=1.2)
            
            # Create initial train model input with next station number
            print("DEBUG: Creating initial train model input...")
            initial_train_input = TrainModelInput(
                fault_status={'signal': False, 'brake': False, 'engine': False},
                actual_speed=0.0,
                passenger_emergency_brake=False,
                cabin_temperature=72.0,
                next_station_number=init_data.next_station_number,
                authority_threshold=50.0,
                add_new_block_info=False,
                next_block_info={},
                next_block_entered=False,
                update_next_block_info=False
            )
            
            initial_driver_input = DriverInput(
                auto_mode=True,
                headlights_on=False,
                interior_lights_on=False,
                door_left_open=False,
                door_right_open=False,
                set_temperature=72.0,
                emergency_brake=False,
                set_speed=0.0,
                service_brake=False,
                train_id=init_data.train_id
            )
            
            # Do an initial update to set up the station information
            print(f"DEBUG: Doing initial controller update with next_station_number: {init_data.next_station_number}")
            self.train_controller.update(initial_train_input, initial_driver_input)
            
            # Now initialize the professional driver GUI and engineer GUI
            self.setup_professional_driver_gui()
            self.setup_engineer_gui()
            
            self.controller_initialized = True
            print("Train Controller and GUIs successfully initialized!")
            
            # Update status
            self.status_label.setText(f"Status: Initialized - {init_data.track_color} Line, Block {init_data.current_block}")
            self.controller_status.setText(f"Controller: Active ({init_data.track_color} Line)")
            
        except TrackDataError as e:
            print(f"CRITICAL ERROR: {e}")
            self.status_label.setText("Status: INITIALIZATION FAILED - Track Data Error")
            self.controller_status.setText("Controller: FAILED - No Track Data")
            
            # Show error dialog
            from PyQt5.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Train Controller Initialization Error")
            msg.setText("Cannot initialize train controller")
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
        self.setWindowTitle("Integrated Train System with New Professional SW UI - Main Control")
        self.setGeometry(50, 50, 600, 450)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("Integrated Train System\nwith Professional Software Driver UI")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Status section
        status_group = QWidget()
        status_layout = QVBoxLayout(status_group)
        status_layout.setContentsMargins(10, 10, 10, 10)
        
        self.status_label = QLabel("Status: Running")
        self.controller_status = QLabel("Controller: Active")
        self.model_status = QLabel("Train Model: Active")
        self.driver_ui_status = QLabel("Professional Driver UI: Active")
        self.update_counter = QLabel("Updates: 0")
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.controller_status)
        status_layout.addWidget(self.model_status)
        status_layout.addWidget(self.driver_ui_status)
        status_layout.addWidget(self.update_counter)
        
        status_group.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 5px;")
        layout.addWidget(status_group)
        
        # Control buttons
        button_layout = QVBoxLayout()
        
        self.show_driver_btn = QPushButton("Show Professional Driver UI")
        self.show_engineer_btn = QPushButton("Show Engineer GUI")
        self.show_train_dashboard_btn = QPushButton("Show Train Dashboard")
        self.show_murphy_mode_btn = QPushButton("Show Murphy Mode")
        self.show_track_circuit_test_btn = QPushButton("Show Track Circuit Test UI")
        self.open_all_uis_btn = QPushButton("🚀 OPEN ALL UIs")
        self.emergency_stop_btn = QPushButton("MASTER EMERGENCY STOP")
        
        self.show_driver_btn.clicked.connect(self.show_professional_driver_gui)
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
    
    def setup_professional_driver_gui(self):
        """Initialize the Professional Software Driver GUI"""
        self.driver_gui = ProfessionalSoftwareDriverUI()
        self.driver_gui.set_train_controller(self.train_controller)
        self.driver_gui.setGeometry(600, 50, 1400, 900)
        self.driver_gui.show()
        print("Professional Software Driver GUI initialized and displayed")
        
        # Try to get and display initial station information
        print("DEBUG: Attempting to get initial station info...")
        try:
            initial_output = self.train_controller.get_output_to_driver()
            print(f"DEBUG: Initial output next_station: '{initial_output.next_station}', station_side: '{initial_output.station_side}'")
        except Exception as e:
            print(f"DEBUG: Error getting initial output: {e}")
    
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
        Main system update function - integrates Train Model and Train Controller
        """
        # Skip updates if not initialized yet
        if (not self.controller_initialized or 
            self.train_controller is None or 
            self.train_model is None):
            return
            
        try:
            # =============================================================
            # 1. GET DRIVER INPUT FROM PROFESSIONAL GUI
            # =============================================================
            driver_input = self.driver_gui.get_driver_input()
            
            # =============================================================
            # 2. BUILD TRAIN MODEL INPUT FROM CURRENT TRAIN STATE
            # =============================================================
            # Use train model's method to get parsed track circuit data
            train_model_input = self.train_model.build_train_input()
            
            # =============================================================
            # 2.5. HANDLE PASSENGER EMERGENCY BRAKE RESET LOGIC
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
            # 3. UPDATE TRAIN CONTROLLER WITH INPUTS
            # =============================================================
            self.train_controller.update(train_model_input, driver_input)
            
            # =============================================================
            # 4. GET CONTROLLER OUTPUT AND APPLY TO TRAIN MODEL
            # =============================================================
            controller_output = self.train_controller.get_output()
            self.apply_controller_output_to_train_model(controller_output)
            
            # =============================================================
            # 5. UPDATE TRAIN MODEL PHYSICS
            # =============================================================
            dt = 0.1  # Update every 0.1 simulation seconds
            self.train_model.update_speed(dt)
            
            # =============================================================
            # 6. UPDATE PROFESSIONAL DRIVER GUI WITH LATEST DATA
            # =============================================================
            self.driver_gui.update_from_train_controller()
            
            # =============================================================
            # 7. UPDATE ENGINEER GUI WITH CURRENT GAINS
            # =============================================================
            kp, ki = self.train_controller.get_gains()
            self.engineer_gui.update_current_values(kp, ki)
            
            # Update status display
            self.update_status_display(driver_input, train_model_input, controller_output)
            
        except Exception as e:
            print(f"Error in system update: {e}")
            self.status_label.setText(f"Status: Error - {str(e)}")
            self.model_status.setText("Train Model: Error")
            self.driver_ui_status.setText("Professional Driver UI: Error")
    
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
        self.controller_status.setText(f"Controller: Kp={kp:.1f}, Ki={ki:.1f}")
        
        # Update model status
        speed_mph = self.train_model.velocity_mps * 2.237
        self.model_status.setText(f"Train Model: {speed_mph:.1f} mph, {self.train_model.mass_kg:.0f} kg")
        
        # Update driver UI status
        mode = "AUTO" if driver_input.auto_mode else "MANUAL"
        self.driver_ui_status.setText(f"Professional Driver UI: {mode} Mode")
        
        # Show detailed status every second
        if self.update_count % 10 == 0:
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
    
    def update_controller_gains(self, engineer_input: EngineerInput):
        """Handle controller gain updates from Engineer GUI"""
        self.train_controller.update_from_engineer_input(engineer_input)
        print(f"Controller gains updated: Kp={engineer_input.kp}, Ki={engineer_input.ki}")
    
    def show_professional_driver_gui(self):
        """Show/raise the professional driver GUI window"""
        if self.driver_gui is None:
            print("Professional Driver GUI not initialized yet.")
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
    
    def show_track_circuit_test_ui(self):
        """Show/initialize the track circuit test UI"""
        if self.track_circuit_test_ui is None:
            self.setup_track_circuit_test_ui()
        self.track_circuit_test_ui.show()
        self.track_circuit_test_ui.raise_()
        self.track_circuit_test_ui.activateWindow()
    
    def open_all_uis(self):
        """Open and show all available UI windows"""
        print("Opening all UI windows...")
        
        # Show Professional Driver GUI
        self.show_professional_driver_gui()
        
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
        
        print("✓ All UI windows opened successfully")
    
    def arrange_ui_windows(self):
        """Arrange UI windows in a non-overlapping layout"""
        # Main window (this) - top left
        self.setGeometry(50, 50, 1000, 700)
        
        # Professional Driver GUI - top right
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
        
        print("✓ UI windows arranged in organized layout")
    
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
        print("Shutting down Integrated Train System with New SW UI...")
        
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


def main(init_data: TrainControllerInit = None, next_station_number: int = 0):
    """
    Main entry point for the Integrated Train System with New Professional SW UI
    
    Args:
        init_data (TrainControllerInit, optional): Initialization data for train controller
        next_station_number (int, optional): Next station number for the train
    """
    print("=" * 70)
    print("INTEGRATED TRAIN SYSTEM WITH NEW PROFESSIONAL SW UI STARTUP")
    print("=" * 70)
    
    # Create QApplication
    app = QApplication(sys.argv)
    
    try:
        # Create and show the main system
        system = TrainSystemSW(init_data, next_station_number)
        
        # Only show if not already shown (in case of direct initialization)
        if not system.isVisible():
            system.show()
        
        print("\n" + "=" * 70)
        print("SYSTEM READY - All components active with New Professional SW UI")
        print("Professional Driver GUI: Modern professional train operation interface")
        print("Engineer GUI: Adjusts controller parameters")
        print("Train Dashboard: Real-time train status display")
        print("Murphy Mode: Toggle train failures for testing")
        print("Train Model: Physics simulation engine")
        print("Train Controller: Automated control system")
        print("Update Rate: 10Hz (every 0.1 seconds)")
        print("=" * 70)
        print("\nINSTRUCTIONS:")
        if init_data is None:
            print("1. Initialize system with track and block data")
        else:
            print("1. System pre-initialized with provided data")
        print("2. Use Professional Driver GUI to control the train")
        print("3. Use Engineer GUI to adjust controller gains")
        print("4. Use Train Dashboard to monitor train status")
        print("5. Use Murphy Mode to test failure scenarios")
        print("6. Watch real physics simulation in real-time")
        print("=" * 70 + "\n")
        
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
__all__ = ['TrainSystemSW', 'main']
