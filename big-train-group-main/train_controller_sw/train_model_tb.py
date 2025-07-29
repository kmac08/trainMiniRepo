#train_model_tb.py
"""
Test Bench Demo Script
Shows how to use the Train Model Test Bench programmatically
"""

import sys
import time
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

# Add path for imports
sys.path.append(sys.path[0] + '/..')

from gui.train_model_testbench import TrainModelTestBench
from controller.train_controller import TrainController
from controller.data_types import DriverInput, TrainModelInput


class TestBenchDemo:
    """Demo class showing programmatic control of test bench"""
    
    def __init__(self):
        # Create train controller
        self.controller = TrainController(kp=15.0, ki=1.5)
        
        # Create test bench UI
        self.test_bench = TrainModelTestBench()
        self.test_bench.set_train_controller(self.controller)
        
        # Setup demo scenarios
        self.scenario_index = 0
        self.scenarios = [
            self.scenario_normal_operation,
            self.scenario_station_stop,
            self.scenario_emergency_brake,
            self.scenario_fault_detection,
            self.scenario_manual_mode
        ]
        
        # Setup scenario timer
        self.scenario_timer = QTimer()
        self.scenario_timer.timeout.connect(self.run_next_scenario)
        self.scenario_timer.start(10000)  # Change scenario every 10 seconds
        
        # Run first scenario
        self.run_next_scenario()
        
    def run_next_scenario(self):
        """Run the next scenario in sequence"""
        scenario = self.scenarios[self.scenario_index]
        print(f"\n{'='*50}")
        print(f"Running Scenario {self.scenario_index + 1}: {scenario.__name__}")
        print(f"{'='*50}")
        
        scenario()
        
        self.scenario_index = (self.scenario_index + 1) % len(self.scenarios)
        
    def scenario_normal_operation(self):
        """Normal operation scenario"""
        print("Setting up normal operation at 25 mph...")
        
        # Set driver to auto mode
        driver_input = DriverInput(
            auto_mode=True,
            headlights_on=False,
            interior_lights_on=False,
            door_left_open=False,
            door_right_open=False,
            set_temperature=72.0,
            emergency_brake=False,
            set_speed=0.0,
            service_brake=False
        )
        self.test_bench.set_driver_input(driver_input)
        
        # Set train model values
        self.test_bench.actual_speed_spin.setValue(20.0)
        self.test_bench.commanded_speed_spin.setValue(25.0)
        self.test_bench.speed_limit_spin.setValue(40.0)
        self.test_bench.authority_spin.setValue(1000.0)
        self.test_bench.cabin_temp_spin.setValue(70.0)
        self.test_bench.next_station_edit.setText("Downtown")
        self.test_bench.station_side_combo.setCurrentText("right")
        
        # Clear all faults
        self.test_bench.engine_fault_check.setChecked(False)
        self.test_bench.signal_fault_check.setChecked(False)
        self.test_bench.brake_fault_check.setChecked(False)
        self.test_bench.passenger_ebrake_check.setChecked(False)
        
        # Save values
        self.test_bench.save_values()
        
    def scenario_station_stop(self):
        """Station stop scenario"""
        print("Simulating station stop...")
        
        # Approach station
        self.test_bench.actual_speed_spin.setValue(5.0)
        self.test_bench.commanded_speed_spin.setValue(0.0)
        self.test_bench.authority_spin.setValue(50.0)
        self.test_bench.save_values()
        
        # After 2 seconds, stop at station
        QTimer.singleShot(2000, self.station_stop_complete)
        
    def station_stop_complete(self):
        """Complete the station stop"""
        self.test_bench.actual_speed_spin.setValue(0.0)
        self.test_bench.authority_spin.setValue(0.0)
        self.test_bench.next_station_edit.setText("Airport")
        self.test_bench.station_side_combo.setCurrentText("left")
        self.test_bench.save_values()
        print("Stopped at station - doors should open on left side")
        
    def scenario_emergency_brake(self):
        """Emergency brake scenario"""
        print("Testing emergency brake scenarios...")
        
        # Set normal speed
        self.test_bench.actual_speed_spin.setValue(30.0)
        self.test_bench.commanded_speed_spin.setValue(35.0)
        self.test_bench.save_values()
        
        # After 2 seconds, activate passenger emergency brake
        QTimer.singleShot(2000, lambda: [
            self.test_bench.passenger_ebrake_check.setChecked(True),
            self.test_bench.save_values(),
            print("Passenger emergency brake activated!")
        ])
        
        # After 5 seconds, release it
        QTimer.singleShot(5000, lambda: [
            self.test_bench.passenger_ebrake_check.setChecked(False),
            self.test_bench.save_values(),
            print("Emergency brake released")
        ])
        
    def scenario_fault_detection(self):
        """Fault detection scenario"""
        print("Testing fault detection in auto mode...")
        
        # Ensure auto mode
        driver_input = DriverInput(
            auto_mode=True,
            headlights_on=False,
            interior_lights_on=False,
            door_left_open=False,
            door_right_open=False,
            set_temperature=72.0,
            emergency_brake=False,
            set_speed=0.0,
            service_brake=False
        )
        self.test_bench.set_driver_input(driver_input)
        
        # Set normal operation
        self.test_bench.actual_speed_spin.setValue(25.0)
        self.test_bench.commanded_speed_spin.setValue(30.0)
        self.test_bench.save_values()
        
        # Trigger engine fault after 2 seconds
        QTimer.singleShot(2000, lambda: [
            self.test_bench.engine_fault_check.setChecked(True),
            self.test_bench.save_values(),
            print("Engine fault detected - emergency brake should activate!")
        ])
        
        # Clear fault after 5 seconds
        QTimer.singleShot(5000, lambda: [
            self.test_bench.engine_fault_check.setChecked(False),
            self.test_bench.save_values(),
            print("Engine fault cleared")
        ])
        
    def scenario_manual_mode(self):
        """Manual mode operation"""
        print("Testing manual mode operation...")
        
        # Switch to manual mode
        driver_input = DriverInput(
            auto_mode=False,
            headlights_on=True,
            interior_lights_on=True,
            door_left_open=False,
            door_right_open=False,
            set_temperature=75.0,
            emergency_brake=False,
            set_speed=20.0,  # Manual speed setting
            service_brake=False
        )
        self.test_bench.set_driver_input(driver_input)
        
        # Set train conditions
        self.test_bench.actual_speed_spin.setValue(15.0)
        self.test_bench.commanded_speed_spin.setValue(0.0)  # Ignored in manual
        self.test_bench.cabin_temp_spin.setValue(72.0)
        self.test_bench.save_values()
        
        print("Manual mode active - driver controls speed and systems")
        
        # Test service brake after 3 seconds
        QTimer.singleShot(3000, lambda: [
            self.test_bench.set_driver_input(DriverInput(
                auto_mode=False,
                headlights_on=True,
                interior_lights_on=True,
                door_left_open=False,
                door_right_open=False,
                set_temperature=75.0,
                emergency_brake=False,
                set_speed=20.0,
                service_brake=True  # Apply service brake
            )),
            print("Service brake applied in manual mode")
        ])


def main():
    """Run the test bench demo"""
    app = QApplication(sys.argv)
    
    # Create and show test bench
    demo = TestBenchDemo()
    demo.test_bench.show()
    
    # Print instructions
    print("\nTrain Model Test Bench Demo")
    print("="*50)
    print("This demo will cycle through different scenarios automatically.")
    print("Watch the test bench UI to see the values change!")
    print("Scenarios change every 10 seconds.")
    print("\nYou can also manually adjust values and click 'SAVE AND SEND'")
    print("to test your own scenarios.")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()