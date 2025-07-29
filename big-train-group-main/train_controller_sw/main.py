#!/usr/bin/env python3
"""
Main application integrating Driver UI, Engineer UI, and Train Controller.
This version uses the new OutputToDriver data structure for cleaner data flow.
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtCore import QTimer

# Import all components
from gui.train_controller_driver import DriverUI
from gui.train_controller_engineer import EngineerUI
from controller.train_controller import TrainController
from controller.data_types import TrainModelInput, DriverInput, EngineerInput


class MainWindow(QMainWindow):
    """Main window that contains both UIs and manages the controller"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Train Control System")
        self.setGeometry(100, 100, 1400, 950)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Initialize the train controller
        self.train_controller = TrainController(kp=12.0, ki=1.2)
        
        # Create Engineer UI
        self.engineer_ui = EngineerUI()
        self.engineer_ui.setMaximumHeight(250)
        layout.addWidget(self.engineer_ui)
        
        # Create Driver UI
        self.driver_ui = DriverUI()
        layout.addWidget(self.driver_ui)
        
        # Connect engineer UI to update controller gains
        self.engineer_ui.apply_button.clicked.connect(self.update_controller_gains)
        self.engineer_ui.kp_ki_submitted.connect(self.update_controller_from_engineer)
        
        # Set the train controller in driver UI
        self.driver_ui.set_train_controller(self.train_controller)
        
        # Initialize with default train input
        self.current_train_input = TrainModelInput(
            fault_status={'signal': False, 'brake': False, 'engine': False},
            authority=1000.0,
            actual_speed=0.0,
            commanded_speed=0.0,
            speed_limit=40.0,
            passenger_emergency_brake=False,
            cabin_temperature=72.0,
            next_station="Central Station",
            station_side="right"
        )
        
        # Setup update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_system)
        self.timer.start(100)  # Update every 100ms
        
        # Simulation timer for demo
        self.sim_timer = QTimer()
        self.sim_timer.timeout.connect(self.simulate_train_movement)
        self.sim_timer.start(1000)  # Update every second
    
    def update_controller_gains(self):
        """Update controller gains from engineer UI"""
        kp = self.engineer_ui.kp_spinbox.value()
        ki = self.engineer_ui.ki_spinbox.value()
        self.train_controller.kp = kp
        self.train_controller.ki = ki
        print(f"Updated controller gains: Kp={kp}, Ki={ki}")
    
    def update_controller_from_engineer(self, engineer_input: EngineerInput):
        """Update controller from EngineerInput signal"""
        self.train_controller.kp = engineer_input.kp
        self.train_controller.ki = engineer_input.ki
        print(f"Updated controller gains from signal: Kp={engineer_input.kp}, Ki={engineer_input.ki}")
    
    def update_system(self):
        """Main update loop - processes inputs and updates outputs"""
        # Get driver input from UI
        driver_input = self.driver_ui.get_driver_input()
        
        # Update the controller
        self.train_controller.update(self.current_train_input, driver_input)
        
        # Update the driver UI with all necessary information
        self.driver_ui.update_from_train_controller()
        
        # Update engineer UI with current controller values
        current_kp, current_ki = self.train_controller.get_gains()
        self.engineer_ui.update_current_values(current_kp, current_ki)
        
        # Get output for train model (in a real system, this would be sent to the train)
        train_output = self.train_controller.get_output()
        
        # Print some debug info
        if hasattr(self, '_last_print_time'):
            if self.timer.remainingTime() < 0:  # Print occasionally
                self._last_print_time = 0
                driver_display = self.train_controller.get_output_to_driver()
                print(f"Mode: {'Auto' if driver_display.auto_mode else 'Manual'}, "
                      f"Speed: {driver_display.actual_speed:.1f}/{driver_display.input_speed:.1f} mph, "
                      f"Power: {driver_display.power_output:.1f} kW, "
                      f"E-Brake: {driver_display.emergency_brake_active}")
    
    def simulate_train_movement(self):
        """Simulate train physics for demo purposes"""
        # Simple physics simulation
        power = self.train_controller.get_output().power_kw
        current_speed = self.current_train_input.actual_speed
        
        # Simulate acceleration/deceleration based on power
        if self.train_controller.get_output().emergency_brake_status:
            # Emergency brake - rapid deceleration
            new_speed = max(0, current_speed - 5.0)
        elif self.train_controller.get_output().service_brake_status:
            # Service brake - normal deceleration
            new_speed = max(0, current_speed - 2.0)
        else:
            # Power-based acceleration (simplified)
            acceleration = (power / 120.0) * 3.0  # Max 3 mph/s at full power
            new_speed = current_speed + acceleration
            new_speed = min(new_speed, self.current_train_input.speed_limit)
            new_speed = max(0, new_speed)
        
        # Update train input with new speed
        self.current_train_input.actual_speed = new_speed
        
        # Simulate temperature changes
        set_temp = self.train_controller.get_output().set_cabin_temperature
        current_temp = self.current_train_input.cabin_temperature
        temp_diff = set_temp - current_temp
        self.current_train_input.cabin_temperature += temp_diff * 0.1  # Gradual change
        
        # Demo: Change commanded speed and simulate station stops
        import time
        t = int(time.time()) % 120  # 2-minute cycle
        
        if t < 20:
            self.current_train_input.commanded_speed = 25.0
            self.current_train_input.authority = 1000.0
        elif t < 30:
            # Approaching station - slow down
            self.current_train_input.commanded_speed = 10.0
            self.current_train_input.authority = 100.0
        elif t < 45:
            # At station - stop
            self.current_train_input.commanded_speed = 0.0
            self.current_train_input.authority = 0.0
            self.current_train_input.next_station = "Downtown"
            self.current_train_input.station_side = "left"
        elif t < 70:
            # Departing station
            self.current_train_input.commanded_speed = 35.0
            self.current_train_input.authority = 2000.0
        elif t < 80:
            # Approaching another station
            self.current_train_input.commanded_speed = 15.0
            self.current_train_input.authority = 150.0
        elif t < 95:
            # At station
            self.current_train_input.commanded_speed = 0.0
            self.current_train_input.authority = 0.0
            self.current_train_input.next_station = "Airport"
            self.current_train_input.station_side = "right"
        else:
            # Departing
            self.current_train_input.commanded_speed = 30.0
            self.current_train_input.authority = 1500.0
        
        # Demo: Simulate failures
        if t == 60:
            # Engine failure - should trigger emergency brake in auto mode
            self.current_train_input.fault_status['engine'] = True
            print("DEMO: Engine failure detected!")
        elif t == 65:
            self.current_train_input.fault_status['engine'] = False
            print("DEMO: Engine failure cleared")
        
        # Demo: Signal failure
        if t == 100:
            self.current_train_input.fault_status['signal'] = True
            print("DEMO: Signal failure detected!")
        elif t == 105:
            self.current_train_input.fault_status['signal'] = False
            print("DEMO: Signal failure cleared")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()