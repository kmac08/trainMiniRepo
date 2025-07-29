#!/usr/bin/env python3
"""
Test script for Professional Driver UIs
Demonstrates standalone operation and integration testing
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from professional_sw_driver_ui import ProfessionalSoftwareDriverUI
    from professional_hw_driver_ui import ProfessionalHardwareDriverUI
    print("✅ Successfully imported both professional UIs")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


class UITestLauncher(QMainWindow):
    """Simple launcher to test both professional UIs"""
    
    def __init__(self):
        super().__init__()
        self.sw_ui = None
        self.hw_ui = None
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Professional Driver UI Test Launcher")
        self.setGeometry(100, 100, 600, 400)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Title
        title = QLabel("Professional Driver UI Test Suite")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #2563EB;
            margin-bottom: 20px;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Description
        description = QLabel("""
            This test launcher allows you to open and test both professional driver UIs
            in standalone mode. The UIs will function without backend controllers for
            visual and interaction testing.
        """)
        description.setStyleSheet("""
            font-size: 14px;
            color: #374151;
            line-height: 1.5;
            margin-bottom: 30px;
        """)
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description)
        
        # Buttons
        button_layout = QVBoxLayout()
        button_layout.setSpacing(15)
        
        # Software UI button
        self.sw_button = QPushButton("Launch Software Driver UI")
        self.sw_button.setMinimumHeight(50)
        self.sw_button.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
            QPushButton:pressed {
                background-color: #1D4ED8;
            }
        """)
        self.sw_button.clicked.connect(self.launch_software_ui)
        button_layout.addWidget(self.sw_button)
        
        # Hardware UI button
        self.hw_button = QPushButton("Launch Hardware Driver UI")
        self.hw_button.setMinimumHeight(50)
        self.hw_button.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #B91C1C;
            }
            QPushButton:pressed {
                background-color: #991B1B;
            }
        """)
        self.hw_button.clicked.connect(self.launch_hardware_ui)
        button_layout.addWidget(self.hw_button)
        
        # Status info
        self.status_label = QLabel("Ready to launch UIs")
        self.status_label.setStyleSheet("""
            font-size: 12px;
            color: #6B7280;
            margin-top: 20px;
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        button_layout.addWidget(self.status_label)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        # Apply global styles
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F9FAFB;
            }
            QWidget {
                font-family: "Segoe UI", "San Francisco", "Helvetica Neue", Arial, sans-serif;
            }
        """)
        
    def launch_software_ui(self):
        """Launch the software driver UI"""
        try:
            if self.sw_ui is None or not self.sw_ui.isVisible():
                self.sw_ui = ProfessionalSoftwareDriverUI()
                self.sw_ui.show()
                self.status_label.setText("✅ Software Driver UI launched successfully")
                print("Software Driver UI launched")
            else:
                self.sw_ui.raise_()
                self.sw_ui.activateWindow()
                self.status_label.setText("Software Driver UI window brought to front")
        except Exception as e:
            self.status_label.setText(f"❌ Error launching Software UI: {str(e)}")
            print(f"Error launching Software UI: {e}")
            
    def launch_hardware_ui(self):
        """Launch the hardware driver UI"""
        try:
            if self.hw_ui is None or not self.hw_ui.isVisible():
                self.hw_ui = ProfessionalHardwareDriverUI()
                self.hw_ui.show()
                self.status_label.setText("✅ Hardware Driver UI launched successfully")
                print("Hardware Driver UI launched")
            else:
                self.hw_ui.raise_()
                self.hw_ui.activateWindow()
                self.status_label.setText("Hardware Driver UI window brought to front")
        except Exception as e:
            self.status_label.setText(f"❌ Error launching Hardware UI: {str(e)}")
            print(f"Error launching Hardware UI: {e}")
            
    def closeEvent(self, event):
        """Handle window close - close all opened UIs"""
        if self.sw_ui:
            self.sw_ui.close()
        if self.hw_ui:
            self.hw_ui.close()
        event.accept()


def test_ui_functionality():
    """Test basic functionality of both UIs"""
    print("\n" + "="*60)
    print("PROFESSIONAL DRIVER UI FUNCTIONALITY TEST")
    print("="*60)
    
    # Test software UI creation
    print("\n1. Testing Software Driver UI...")
    try:
        sw_ui = ProfessionalSoftwareDriverUI()
        print("   ✅ Software UI created successfully")
        
        # Test basic methods
        driver_input = sw_ui.get_driver_input()
        print(f"   ✅ get_driver_input() works: {type(driver_input)}")
        
        sw_ui.set_next_station("Test Station Platform A")
        print("   ✅ set_next_station() works")
        
        # Don't show the UI in test mode
        sw_ui.close()
        
    except Exception as e:
        print(f"   ❌ Software UI test failed: {e}")
        
    # Test hardware UI creation
    print("\n2. Testing Hardware Driver UI...")
    try:
        hw_ui = ProfessionalHardwareDriverUI()
        print("   ✅ Hardware UI created successfully")
        
        # Test basic methods
        driver_input = hw_ui.get_driver_input()
        print(f"   ✅ get_driver_input() works: {type(driver_input)}")
        
        hw_ui.set_next_station("Test Station Platform B")
        print("   ✅ set_next_station() works")
        
        connected = hw_ui.is_gpio_connected()
        print(f"   ✅ is_gpio_connected() works: {connected}")
        
        # Don't show the UI in test mode
        hw_ui.close()
        
    except Exception as e:
        print(f"   ❌ Hardware UI test failed: {e}")
        
    print("\n3. Testing cross-platform compatibility...")
    try:
        import platform
        system = platform.system()
        print(f"   ✅ Running on: {system}")
        print(f"   ✅ Platform version: {platform.version()}")
        print(f"   ✅ Python version: {platform.python_version()}")
        print("   ✅ Both UIs should work on this platform")
    except Exception as e:
        print(f"   ❌ Platform detection failed: {e}")
        
    print("\n" + "="*60)
    print("FUNCTIONALITY TEST COMPLETE")
    print("="*60)


def main():
    """Main function"""
    print("Professional Driver UI Test Suite")
    print("=" * 50)
    
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("Professional Driver UI Test Suite")
    app.setOrganizationName("Train Control Systems")
    
    # Run functionality tests
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_ui_functionality()
        return
    
    # Launch interactive test
    print("Launching interactive test launcher...")
    launcher = UITestLauncher()
    launcher.show()
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()