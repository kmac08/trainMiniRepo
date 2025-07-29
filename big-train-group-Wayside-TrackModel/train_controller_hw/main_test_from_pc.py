# main_test.py
"""
Main integration file for Train Controller System with Test Bench
Location: train_controller_hw/main_test.py

This file integrates the backend TrainController with Driver UI, Engineer UI,
and the Train Model Test Bench.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
# QTimer no longer needed - using Master Interface time signals only

# Add paths for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'controller'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gui'))
# Add path to parent directory where Master_Interface is located
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import universal time function from Master Interface
try:
    from Master_Interface.master_control import get_time
except ImportError:
    raise ImportError("CRITICAL ERROR: Master Interface universal time function not available. Main test requires universal time synchronization.")

# Import backend components
from controller.train_controller import TrainController, TrackDataError
from controller.data_types import EngineerInput, TrainControllerInit
from controller.train_controller import TrainController

# Import GUI components
from gui.train_controller_driver_remote_fixed import DriverUI
from gui.train_controller_engineer import EngineerUI
from gui.train_model_testbench import TrainModelTestBench
from gui.initialization_ui import InitializationUI


class TrainControllerSystem(QMainWindow):
    """
    Main system coordinator that manages the train controller backend 
    and integrates it with all GUI components including the test bench.
    """
    
    def __init__(self):
        super().__init__()
        
        # =================================================================
        # START MASTER INTERFACE FIRST FOR UNIVERSAL TIME
        # =================================================================
        print("Starting Master Interface for universal time system...")
        self.start_master_interface()
        
        # =================================================================
        # INITIALIZATION STATUS
        # =================================================================
        self.train_controller = None  # type: TrainController | None
        self.driver_gui = None  # type: DriverUI | None 
        self.engineer_gui = None  # type: EngineerUI | None
        self.controller_initialized = False
        self.initialization_ui = None  # type: InitializationUI | None
        
        # =================================================================
        # SHOW INITIALIZATION UI FIRST
        # =================================================================
        print("Showing initialization UI...")
        self.show_initialization_ui()
        
        # Main window and other components will be set up after initialization
    
    def start_master_interface(self):
        """Start the Master Interface for universal time system"""
        try:
            from Master_Interface.master_control import MasterInterface
            self.master_interface = MasterInterface()
            self.master_interface.show()  # Show the Master Interface GUI for time control
            
            # Ensure time manager is not paused
            if self.master_interface.time_manager.is_time_paused():
                self.master_interface.time_manager.resume()
                print("Resumed paused time manager")
            
            # Start the time manager
            if not self.master_interface.time_manager.isRunning():
                self.master_interface.time_manager.start()
                print("Started Master Interface time manager")
                
                # Give it a moment to start
                import time
                time.sleep(0.1)
                
                if self.master_interface.time_manager.isRunning():
                    print("Time manager confirmed running")
                else:
                    print("WARNING: Time manager may not have started properly")
            else:
                print("Master Interface time manager was already running")
            
            print("Master Interface started successfully - Universal time system active")
            print(f"Time manager status: Running={self.master_interface.time_manager.isRunning()}, Paused={self.master_interface.time_manager.is_time_paused()}")
            print(f"Time multiplier: {self.master_interface.time_manager.time_multiplier}")
            
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to start Master Interface: {e}")
            raise RuntimeError(f"Cannot start universal time system: {e}")
        
    def setup_main_window(self):
        """Setup the main coordinator window"""
        self.setWindowTitle("Train Controller System - Main Control")
        self.setGeometry(50, 50, 500, 400)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("Train Controller System")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px; text-align: center;")
        layout.addWidget(title)
        
        # Status section
        status_group = QWidget()
        status_layout = QVBoxLayout(status_group)
        status_layout.setContentsMargins(10, 10, 10, 10)
        
        self.status_label = QLabel("Status: Running")
        self.controller_status = QLabel("Controller: Active")
        self.update_counter = QLabel("Updates: 0")
        self.test_bench_status = QLabel("Test Bench: Connected")
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.controller_status)
        status_layout.addWidget(self.update_counter)
        status_layout.addWidget(self.test_bench_status)
        
        status_group.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 5px;")
        layout.addWidget(status_group)
        
        # Control buttons
        button_layout = QVBoxLayout()
        
        self.show_driver_btn = QPushButton("Show Driver GUI")
        self.show_engineer_btn = QPushButton("Show Engineer GUI")
        self.show_test_bench_btn = QPushButton("Show Test Bench")
        self.emergency_stop_btn = QPushButton("EMERGENCY STOP")
        
        self.show_driver_btn.clicked.connect(self.show_driver_gui)
        self.show_engineer_btn.clicked.connect(self.show_engineer_gui)
        self.show_test_bench_btn.clicked.connect(self.show_test_bench)
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
        self.show_test_bench_btn.setStyleSheet(button_style)
        
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
        button_layout.addWidget(self.show_test_bench_btn)
        button_layout.addSpacing(20)
        button_layout.addWidget(self.emergency_stop_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        # Initialize update counter
        self.update_count = 0
        print("Update counter initialized to 0")
        
        # Track emergency state
        self.emergency_active = False
    
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
        
        # Now set up the main window and other components
        self.setup_main_window()
        self.setup_test_bench()
        
        # Set up update timer
        self.setup_update_timer()
        
        # Initialize the train controller with the complete initialization data
        self.initialize_train_controller(init_data)
        
        # Show the main window
        self.show()
        
        print("Train Controller System initialized successfully!")
        
    def initialize_train_controller(self, init_data: TrainControllerInit):
        """
        Initialize the train controller and GUIs when we receive proper initialization data.
        
        Args:
            init_data: TrainControllerInit object with track color and block information
        """
        try:
            print(f"Received initialization data for {init_data.track_color} Line, Block {init_data.current_block}")
            
            # Initialize train controller with track data
            self.train_controller = TrainController(init_data, kp=12.0, ki=1.2)
            
            # Now initialize the driver and engineer GUIs
            self.setup_driver_gui()
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
    
    def setup_driver_gui(self):
        """Initialize the Remote Driver GUI with GPIO communication"""
        # Use COM4 as default - can be modified for different serial ports
        self.driver_gui = DriverUI(serial_port='COM4', baud_rate=9600)
        self.driver_gui.set_train_controller(self.train_controller)
        self.driver_gui.setGeometry(600, 50, 1200, 700)
        self.driver_gui.show()
        print("Remote Driver GUI initialized and displayed with Pi GPIO communication")
    
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
        
    def setup_test_bench(self):
        """Initialize the Train Model Test Bench"""
        self.test_bench = TrainModelTestBench()
        self.test_bench.setGeometry(600, 400, 1200, 800)
        self.test_bench.show()
        print("Train Model Test Bench initialized and displayed")
    
    def setup_update_timer(self):
        """Setup updates synchronized with Master Interface time updates"""
        if not hasattr(self, 'master_interface') or not hasattr(self.master_interface, 'time_manager'):
            raise RuntimeError("CRITICAL ERROR: Master Interface not available for time synchronization. Cannot proceed without universal time.")
        
        # Ensure time manager is running before connecting
        if not self.master_interface.time_manager.isRunning():
            print("Time manager not running, starting it now...")
            self.master_interface.time_manager.start()
            import time
            time.sleep(0.1)  # Give it time to start
        
        # Connect to Master Interface time updates for proper simulation time sync
        self.master_interface.time_manager.time_update.connect(self.on_time_update)
        print("Connected to Master Interface time updates for simulation time sync")
        print(f"Master Interface time manager running: {self.master_interface.time_manager.isRunning()}")
        print(f"Master Interface time manager paused: {self.master_interface.time_manager.is_time_paused()}")
        print(f"Master Interface time multiplier: {self.master_interface.time_manager.time_multiplier}")
    
    def on_time_update(self, time_str):
        """Handle time updates from Master Interface and trigger system updates on every signal"""
        try:
            # Update system on every master interface signal
            # This automatically provides 0.1 simulation seconds at 1x speed
            # and 0.01 simulation seconds at 10x speed
            if hasattr(self, 'update_count'):
                if self.update_count % 50 == 0:  # Print every 5 seconds (50 * 0.1s)
                    print(f"Master Interface time update: {time_str}, Main Update #{self.update_count}")
            self.update_system()
                
        except Exception as e:
            print(f"Error in time update handling: {e}")
            raise RuntimeError("CRITICAL ERROR: Failed to handle universal time update. System cannot continue without proper time synchronization.")
    
# =============================================================
# update_system(self) is what connects controller with driver and engineer UI
# =============================================================   
    def update_system(self):
        """
        Main system update function called every 0.1 seconds
        This is where the real-time control loop happens
        """
        # Skip updates if controller not initialized yet
        if not self.controller_initialized or self.train_controller is None:
            return
        
        # Type guard - at this point we know these are not None
        assert self.driver_gui is not None
        assert self.engineer_gui is not None
        assert self.train_controller is not None
            
        try:
            # =============================================================
            # 1. GET DRIVER INPUT FROM GUI
            # =============================================================
            driver_input = self.driver_gui.get_driver_input()
            
            # Apply emergency stop if active: WILL NOT BE NEEDED WHEN TEST UI IS REMOVED. ONLY FOR TEST UI
            if self.emergency_active:
                driver_input.emergency_brake = True
            
            # =============================================================
            # 2. GET TRAIN MODEL DATA FROM TEST BENCH: THIS WILL BE CONNECTED TO THE TRAIN MODEL INPUT SIDE
            # =============================================================
            train_model_input = self.test_bench.to_train_controller()
            
            # =============================================================
            # 3. UPDATE TRAIN CONTROLLER WITH INPUTS:
            # -> Now since we have both driver and train model inputs, we can do a regular update to the controller.
            # -> Currently every .1 seconds but can change
            # =============================================================
            self.train_controller.update(train_model_input, driver_input)
            
            # =============================================================
            # 4. GET CONTROLLER OUTPUT AND SEND TO TEST BENCH
            # =============================================================
            controller_output = self.train_controller.get_output()
            if(controller_output.station_stop_complete):
                print("still true in main_test.py")
            self.test_bench.from_train_controller(controller_output)
            
            # =============================================================
            # 4.5. UPDATE TEST BENCH WITH CURRENT BLOCK INFORMATION
            # =============================================================
            current_block = self.train_controller.current_block
            current_block_data = self.train_controller.get_block_essentials(current_block)
            self.test_bench.update_current_block_info(current_block, current_block_data)
            
            # =============================================================
            # 5. UPDATE DRIVER GUI WITH LATEST DATA
            # =============================================================
            self.driver_gui.update_from_train_controller()
            
            # =============================================================
            # 6. UPDATE ENGINEER GUI WITH CURRENT GAINS
            # =============================================================
            kp, ki = self.train_controller.get_gains()
            self.engineer_gui.update_current_values(kp, ki)
            
            # Update status
            self.update_count += 1
            self.update_counter.setText(f"Updates: {self.update_count}")
            
            # Debug: Show update rate info periodically with simulation time
            if self.update_count % 100 == 0:  # Every 10 seconds at 0.1s intervals
                try:
                    sim_time = get_time()
                    ms = sim_time.microsecond // 1000
                    time_str = f"{sim_time.hour:02d}:{sim_time.minute:02d}:{sim_time.second:02d}.{ms:03d}"
                    print(f"🔄 Main Update #{self.update_count} - Simulation Time: {time_str} (Source: Master Interface)")
                except:
                    print(f"🔄 Main Update #{self.update_count} - Master Interface time unavailable")
                print(f"Update rate: {self.update_count} updates total (expect ~10 per sim second)")
            
            # Update controller status with more info
            self.controller_status.setText(f"Controller: Kp={kp:.1f}, Ki={ki:.1f}")
            
            # Show some key values in status
            if self.update_count % 10 == 0:  # Every second
                mode = "Auto" if driver_input.auto_mode else "Manual"
                speed = train_model_input.actual_speed
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
                
                self.status_label.setText(f"Status: {mode} | Speed: {speed:.1f} mph | Power: {power:.1f} kW{fault_str}")
            
        except Exception as e:
            print(f"Error in system update: {e}")
            self.status_label.setText(f"Status: Error - {str(e)}")
            self.test_bench_status.setText("Test Bench: Error")
    
    def update_controller_gains(self, engineer_input: EngineerInput):
        """Handle controller gain updates from Engineer GUI"""
        if self.train_controller is not None:
            self.train_controller.update_from_engineer_input(engineer_input)  # This sets kp_ki_set flag
            print(f"Controller gains updated: Kp={engineer_input.kp}, Ki={engineer_input.ki}, kp_ki_set={self.train_controller.kp_ki_set}")
    
    def show_driver_gui(self):
        """Show/raise the driver GUI window"""
        if self.driver_gui is None:
            print("Driver GUI not initialized yet. Please provide initialization data from Test Bench first.")
            return
        self.driver_gui.show()
        self.driver_gui.raise_()
        self.driver_gui.activateWindow()
    
    def show_engineer_gui(self):
        """Show/raise the engineer GUI window"""
        if self.engineer_gui is None:
            print("Engineer GUI not initialized yet. Please provide initialization data from Test Bench first.")
            return
        self.engineer_gui.show()
        self.engineer_gui.raise_()
        self.engineer_gui.activateWindow()
        
    def show_test_bench(self):
        """Show/raise the test bench window"""
        self.test_bench.show()
        self.test_bench.raise_()
        self.test_bench.activateWindow()
    
    def emergency_stop(self):
        """Emergency stop - forces emergency brake activation"""
        self.emergency_active = not self.emergency_active
        
        if self.emergency_active:
            print("EMERGENCY STOP ACTIVATED!")
            self.emergency_stop_btn.setText("RELEASE EMERGENCY")
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
            print("Emergency stop released")
            self.emergency_stop_btn.setText("EMERGENCY STOP")
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
        print("Shutting down Train Controller System...")
        
        # Disconnect from Master Interface time updates
        if hasattr(self, 'master_interface'):
            try:
                self.master_interface.time_manager.time_update.disconnect(self.on_time_update)
            except:
                pass
        
        # Close all GUI windows
        if hasattr(self, 'driver_gui') and self.driver_gui is not None:
            self.driver_gui.cleanup_gpio()  # Clean up GPIO emulator
            self.driver_gui.close()
        if hasattr(self, 'engineer_gui') and self.engineer_gui is not None:
            self.engineer_gui.close()
        if hasattr(self, 'test_bench') and self.test_bench is not None:
            self.test_bench.close()
        
        # Stop Master Interface
        if hasattr(self, 'master_interface'):
            print("Stopping Master Interface...")
            self.master_interface.stop_all_modules()
            self.master_interface.close()
        
        print("System shutdown complete")
        event.accept()


def main():
    """
    Main entry point for the Train Controller System
    """
    print("=" * 60)
    print("TRAIN CONTROLLER SYSTEM STARTUP")
    print("=" * 60)
    
    # Create QApplication
    app = QApplication(sys.argv)
    
    try:
        # Create and show the main system
        system = TrainControllerSystem()
        system.show()
        
        print("\n" + "=" * 60)
        print("SYSTEM READY - All components active")
        print("Driver GUI: Controls train operation")
        print("Engineer GUI: Adjusts controller parameters")
        print("Test Bench: Simulates train model inputs/outputs")
        print("Main Window: System coordination and emergency control")
        print("Update Rate: 10Hz (every 0.1 seconds)")
        print("=" * 60)
        print("\nINSTRUCTIONS:")
        print("1. Use Test Bench to set train conditions")
        print("2. Click 'SAVE AND SEND' to apply changes")
        print("3. Use Driver GUI to control the train")
        print("4. Use Engineer GUI to adjust controller gains")
        print("5. Watch outputs update in real-time on Test Bench")
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