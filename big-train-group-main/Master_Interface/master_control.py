"""
Master Control Interface for Big Train Group System
Coordinates all modules and manages system-wide time and line configuration.
"""

import sys
import os
import json
import time
from typing import List, Dict, Optional
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QLabel, QSlider, QComboBox, 
                            QTextEdit, QGroupBox, QCheckBox, QSpinBox, QLineEdit, QTimeEdit)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt, QTime
from PyQt5.QtGui import QFont
from datetime import datetime, timedelta


# Global reference to the master interface for easy access by other modules
_master_interface_instance = None


def get_time():
    """
    Global function to get current simulation time as datetime object.
    
    This function can be imported and used by any module to get the current
    simulation time. It returns a datetime object with today's date and the
    current simulation time.
    
    Returns:
        datetime: Current simulation time as datetime object
        
    Raises:
        RuntimeError: If the master interface is not running
        
    Example:
        from Master_Interface.master_control import get_time
        
        current_time = get_time()
        print(f"Current simulation time: {current_time}")
        
        # Access time components
        hour = current_time.hour
        minute = current_time.minute
        second = current_time.second
    """
    global _master_interface_instance
    if _master_interface_instance is None:
        raise RuntimeError("Master interface is not running. Cannot get simulation time.")
    return _master_interface_instance.get_time()


class TimeManager(QThread):
    """Manages system time acceleration and broadcasts time updates"""
    
    time_update = pyqtSignal(str)  # Current system time as string (HH:MM)
    
    def __init__(self):
        super().__init__()
        self.time_multiplier = 1.0
        self.is_running = False
        self.is_paused = False
        self.start_time = time.time()
        self.elapsed_system_time = 0.0  # Elapsed time in seconds
        self.simulation_start_time = "05:00"  # Default start time
        
    def set_time_multiplier(self, multiplier: float):
        """Set time acceleration multiplier (1.0 to 10.0)"""
        self.time_multiplier = max(1.0, min(10.0, multiplier))
        
    def set_start_time(self, start_time_str: str):
        """Set the simulation start time (HH:MM format)"""
        self.simulation_start_time = start_time_str
        
    def get_current_time_string(self):
        """Get current simulation time as HH:MM string"""
        # Parse start time
        try:
            start_hour, start_minute = map(int, self.simulation_start_time.split(':'))
        except:
            start_hour, start_minute = 5, 0  # Default fallback
            
        # Calculate current time based on elapsed simulation time
        total_minutes = start_hour * 60 + start_minute + (self.elapsed_system_time / 60)
        
        # Handle day rollover
        total_minutes = total_minutes % (24 * 60)
        
        current_hour = int(total_minutes // 60)
        current_minute = int(total_minutes % 60)
        
        return f"{current_hour:02d}:{current_minute:02d}"
        
    def get_time(self):
        """Get current simulation time as datetime object"""
        # Parse start time
        try:
            start_hour, start_minute = map(int, self.simulation_start_time.split(':'))
        except:
            start_hour, start_minute = 5, 0  # Default fallback
            
        # Calculate current time based on elapsed simulation time
        total_seconds = (start_hour * 3600) + (start_minute * 60) + self.elapsed_system_time
        
        # Handle day rollover
        total_seconds = total_seconds % (24 * 3600)
        
        current_hour = int(total_seconds // 3600)
        current_minute = int((total_seconds % 3600) // 60)
        current_second = int(total_seconds % 60)
        
        # Create datetime object with today's date and calculated time
        today = datetime.now().date()
        return datetime.combine(today, datetime.min.time().replace(
            hour=current_hour, 
            minute=current_minute, 
            second=current_second
        ))
        
    def pause(self):
        """Pause the time manager"""
        self.is_paused = True
        
    def resume(self):
        """Resume the time manager"""
        self.is_paused = False
        
    def is_time_paused(self):
        """Check if time is paused"""
        return self.is_paused
        
    def run(self):
        """Main time update loop"""
        self.is_running = True
        last_real_time = time.time()
        
        while self.is_running:
            current_real_time = time.time()
            real_delta = current_real_time - last_real_time
            
            # Only update system time if not paused
            if not self.is_paused:
                system_delta = real_delta * self.time_multiplier
                self.elapsed_system_time += system_delta
                
            # Emit current time as string
            current_time_str = self.get_current_time_string()
            self.time_update.emit(current_time_str)
            
            last_real_time = current_real_time
            
            # Calculate sleep time based on time multiplier
            # Base interval: 0.1s for 1x speed, scale inversely with multiplier
            base_interval = 0.1  # 0.1 seconds for 1x speed
            sleep_time = base_interval / self.time_multiplier
            time.sleep(sleep_time)
            
    def stop(self):
        """Stop the time manager"""
        self.is_running = False
        self.wait()


class MasterInterface(QMainWindow):
    """Main master control interface"""
    
    def __init__(self):
        super().__init__()
        self.time_manager = TimeManager()
        self.active_modules = {}
        self.selected_lines = ["Blue"]
        self.ctc_interface = None  # Store reference to CTC interface for direct communication
        
        # Set global reference for get_time() function
        global _master_interface_instance
        _master_interface_instance = self
        
        self.init_ui()
        self.setup_connections()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Big Train Group - Master Control")
        self.setGeometry(100, 100, 900, 700)
        
        # Set the same styling as CTC interface
        self.setStyleSheet("""
            QMainWindow { 
                color: black; 
                background-color: white; 
                font-family: Arial, sans-serif; 
                font-size: 10pt; 
            }
            QWidget { 
                color: black; 
                background-color: white; 
            }
            QLabel { 
                color: black; 
                background-color: transparent; 
                font-size: 10pt; 
            }
            QPushButton { 
                color: black; 
                background-color: #E0E0E0; 
                border: 1px solid #808080; 
                padding: 6px 12px; 
                font-size: 10pt; 
                font-weight: bold;
                min-height: 20px;
            }
            QPushButton:hover { 
                background-color: #D0D0D0; 
            }
            QPushButton:pressed { 
                background-color: #C0C0C0; 
            }
            QPushButton:disabled { 
                color: #808080; 
                background-color: #F0F0F0; 
            }
            QComboBox { 
                color: black; 
                background-color: white; 
                border: 1px solid #808080; 
                padding: 4px; 
            }
            QLineEdit { 
                color: black; 
                background-color: white; 
                border: 1px solid #808080; 
                padding: 4px; 
            }
            QTextEdit { 
                color: black; 
                background-color: white; 
                border: 1px solid #808080; 
            }
            QGroupBox { 
                color: black; 
                background-color: white; 
                border: 2px solid #808080; 
                font-weight: bold; 
                padding-top: 10px; 
                margin-top: 6px; 
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
                padding: 0 5px 0 5px; 
                background-color: white; 
            }
            QCheckBox { 
                color: black; 
                background-color: transparent; 
                spacing: 5px; 
            }
            QSlider::groove:horizontal {
                border: 1px solid #808080;
                height: 8px;
                background: white;
                margin: 2px 0;
            }
            QSlider::handle:horizontal {
                background: #E0E0E0;
                border: 1px solid #808080;
                width: 18px;
                margin: -2px 0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal:hover {
                background: #D0D0D0;
            }
        """)
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title header - similar to CTC
        header_layout = QHBoxLayout()
        title = QLabel("Big Train Group - Master Control Interface")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        
        # System status on right
        self.system_status_label = QLabel("System: Ready")
        self.system_status_label.setFont(QFont("Arial", 12, QFont.Bold))
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.system_status_label)
        header_layout.setContentsMargins(5, 2, 5, 2)
        
        layout.addLayout(header_layout)
        
        # Time Control Section
        time_group = QGroupBox("Time Control")
        time_layout = QVBoxLayout(time_group)
        
        # Start time input
        start_time_layout = QHBoxLayout()
        start_time_layout.addWidget(QLabel("Start Time:"))
        
        self.start_time_input = QLineEdit("05:00")
        self.start_time_input.setMaximumWidth(60)
        self.start_time_input.setPlaceholderText("HH:MM")
        start_time_layout.addWidget(self.start_time_input)
        
        start_time_layout.addWidget(QLabel("(24-hour format)"))
        start_time_layout.addStretch()
        
        time_layout.addLayout(start_time_layout)
        
        # Time multiplier slider
        time_control_layout = QHBoxLayout()
        time_control_layout.addWidget(QLabel("Speed:"))
        
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setMinimum(1)
        self.time_slider.setMaximum(10)
        self.time_slider.setValue(1)
        self.time_slider.setTickPosition(QSlider.TicksBelow)
        self.time_slider.setTickInterval(1)
        time_control_layout.addWidget(self.time_slider)
        
        self.time_label = QLabel("1x")
        self.time_label.setMinimumWidth(30)
        self.time_label.setFont(QFont("Arial", 10, QFont.Bold))
        time_control_layout.addWidget(self.time_label)
        
        time_layout.addLayout(time_control_layout)
        
        # Pause/Play and time display
        time_display_layout = QHBoxLayout()
        
        # Pause/Play button
        self.pause_play_btn = QPushButton("Play")
        self.pause_play_btn.setMaximumWidth(80)
        self.pause_play_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; }")
        time_display_layout.addWidget(self.pause_play_btn)
        
        time_display_layout.addStretch()
        
        # Current system time display
        self.system_time_label = QLabel("Current Time: 05:00")
        self.system_time_label.setFont(QFont("Arial", 11, QFont.Bold))
        time_display_layout.addWidget(self.system_time_label)
        
        time_layout.addLayout(time_display_layout)
        
        layout.addWidget(time_group)
        
        # Line Selection Section
        line_group = QGroupBox("Line Selection")
        line_layout = QHBoxLayout(line_group)
        
        self.blue_checkbox = QCheckBox("Blue Line")
        self.blue_checkbox.setChecked(True)
        line_layout.addWidget(self.blue_checkbox)
        
        self.green_checkbox = QCheckBox("Green Line")
        line_layout.addWidget(self.green_checkbox)
        
        self.red_checkbox = QCheckBox("Red Line")
        line_layout.addWidget(self.red_checkbox)
        
        layout.addWidget(line_group)
        
        # System Control Section
        control_group = QGroupBox("System Control")
        control_layout = QVBoxLayout(control_group)
        
        # Main system control buttons
        main_control_layout = QHBoxLayout()
        
        self.start_system_btn = QPushButton("Start Complete System")
        self.start_system_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; min-height: 40px; font-size: 12pt; }")
        main_control_layout.addWidget(self.start_system_btn)
        
        self.stop_all_btn = QPushButton("Stop All Systems")
        self.stop_all_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; min-height: 40px; font-size: 12pt; }")
        main_control_layout.addWidget(self.stop_all_btn)
        
        control_layout.addLayout(main_control_layout)
        
        
        layout.addWidget(control_group)
        
        # Status Section
        status_group = QGroupBox("System Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(150)
        self.status_text.setReadOnly(True)
        status_layout.addWidget(self.status_text)
        
        layout.addWidget(status_group)
        
    def setup_connections(self):
        """Setup signal connections"""
        self.time_slider.valueChanged.connect(self.on_time_multiplier_changed)
        self.time_manager.time_update.connect(self.on_time_update)
        
        self.start_time_input.textChanged.connect(self.on_start_time_changed)
        
        self.blue_checkbox.stateChanged.connect(self.on_line_selection_changed)
        self.green_checkbox.stateChanged.connect(self.on_line_selection_changed)
        self.red_checkbox.stateChanged.connect(self.on_line_selection_changed)
        
        self.pause_play_btn.clicked.connect(self.toggle_pause_play)
        
        self.start_system_btn.clicked.connect(self.start_system)
        self.stop_all_btn.clicked.connect(self.stop_all_modules)
        
    def on_time_multiplier_changed(self, value):
        """Handle time multiplier slider change"""
        self.time_manager.set_time_multiplier(float(value))
        self.time_label.setText(f"{value}x")
        self.log_status(f"Time multiplier set to {value}x")
        
    def on_time_update(self, current_time_str):
        """Handle time updates from time manager"""
        self.system_time_label.setText(f"Current Time: {current_time_str}")
        
        # Send time update to CTC if it's running
        if self.ctc_interface is not None:
            self.ctc_interface.update_time(current_time_str)
        
    def on_start_time_changed(self, time_str):
        """Handle start time input change"""
        # Validate time format
        try:
            if len(time_str) == 5 and time_str[2] == ':':
                hour, minute = map(int, time_str.split(':'))
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    self.time_manager.set_start_time(time_str)
                    self.log_status(f"Start time set to {time_str}")
        except ValueError:
            pass  # Invalid format, ignore
        
    def toggle_pause_play(self):
        """Toggle pause/play state of the time manager"""
        if self.time_manager.is_time_paused():
            # Resume time
            self.time_manager.resume()
            self.pause_play_btn.setText("Pause")
            self.pause_play_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; }")
            self.system_status_label.setText("System: Running")
            self.log_status("Time resumed")
        else:
            # Pause time
            self.time_manager.pause()
            self.pause_play_btn.setText("Play")
            self.pause_play_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; }")
            self.system_status_label.setText("System: Paused")
            self.log_status("Time paused")
        
    def on_line_selection_changed(self):
        """Handle line selection changes"""
        self.selected_lines = []
        if self.blue_checkbox.isChecked():
            self.selected_lines.append("Blue")
        if self.green_checkbox.isChecked():
            self.selected_lines.append("Green")
        if self.red_checkbox.isChecked():
            self.selected_lines.append("Red")
            
        if not self.selected_lines:
            # At least one line must be selected
            self.blue_checkbox.setChecked(True)
            self.selected_lines = ["Blue"]
            
        self.log_status(f"Selected lines: {', '.join(self.selected_lines)}")
        
    def launch_ctc(self):
        """Launch CTC module with selected parameters"""
        try:
            # Import CTC interface
            project_root = os.path.dirname(os.path.dirname(__file__))
            sys.path.insert(0, project_root)
            from CTC.UI.ctc_interface import CTCInterface
            
            # Create CTC interface directly for better communication
            track_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                    "Track_Reader", "Track Layout & Vehicle Data vF2.xlsx")
            
            self.ctc_interface = CTCInterface(
                track_file=track_file, 
                selected_lines=self.selected_lines, 
                time_multiplier=self.time_manager.time_multiplier
            )
            
            # Show CTC interface
            self.ctc_interface.show()
            
            # Set initial time
            current_time = self.time_manager.get_current_time_string()
            self.ctc_interface.update_time(current_time)
            
            # Store in active modules
            self.active_modules["CTC"] = self.ctc_interface
            
            
            self.log_status(f"CTC launched with lines: {', '.join(self.selected_lines)}")
            
        except Exception as e:
            self.log_status(f"Error launching CTC: {str(e)}")
            
    def stop_ctc(self):
        """Stop CTC module"""
        if "CTC" in self.active_modules:
            try:
                # Close CTC interface
                self.active_modules["CTC"].close()
                del self.active_modules["CTC"]
                self.ctc_interface = None
                
                
                self.log_status("CTC stopped")
                
            except Exception as e:
                self.log_status(f"Error stopping CTC: {str(e)}")
                
    def start_system(self):
        """Start the complete system"""
        if not self.time_manager.isRunning():
            self.time_manager.start()
            self.log_status("System time manager started")
        
        # Set system to running state
        self.time_manager.resume()
        self.pause_play_btn.setText("Pause")
        self.pause_play_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; }")
        self.system_status_label.setText("System: Running")
        
        # Auto-launch CTC if not already running
        if "CTC" not in self.active_modules:
            self.launch_ctc()
            
        self.log_status("Complete system started")
            
    def stop_all_modules(self):
        """Stop all running modules"""
        # Stop time manager
        if self.time_manager.isRunning():
            self.time_manager.stop()
            self.log_status("System time manager stopped")
            
        # Stop all modules
        for module_name, module in list(self.active_modules.items()):
            try:
                if module_name == "CTC" and hasattr(module, 'close'):
                    # Handle CTC interface directly
                    module.close()
                    self.ctc_interface = None
                else:
                    # Handle subprocess modules
                    module.terminate()
                    module.wait(timeout=5)
                self.log_status(f"{module_name} stopped")
            except Exception as e:
                self.log_status(f"Error stopping {module_name}: {str(e)}")
                
        self.active_modules.clear()
        
        # Reset UI state
        self.pause_play_btn.setText("Play")
        self.pause_play_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; }")
        self.system_status_label.setText("System: Stopped")
        
        self.log_status("All systems stopped")
        
    def get_time(self):
        """Get current simulation time as datetime object for use by other modules"""
        return self.time_manager.get_time()
        
    def log_status(self, message):
        """Add message to status log"""
        timestamp = time.strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")
        
    def closeEvent(self, event):
        """Handle window close event"""
        self.stop_all_modules()
        
        # Clear global reference
        global _master_interface_instance
        _master_interface_instance = None
        
        event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Big Train Group Master Control")
    app.setApplicationVersion("1.0")
    
    # Create and show main window
    window = MasterInterface()
    window.show()
    
    # Start application
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()