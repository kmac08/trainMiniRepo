#!/usr/bin/env python3
"""
Test script for remote GPIO communication system
Tests the Pi GPIO handler and PC GPIO emulator
"""

import time
import sys
from PyQt5.QtWidgets import QApplication

def test_pi_gpio_handler():
    """Test the Pi GPIO handler in simulation mode"""
    print("Testing Pi GPIO Handler...")
    print("=" * 50)
    
    try:
        from pi_gpio_handler import PiGPIOHandler
        
        # Create handler instance
        handler = PiGPIOHandler()
        
        print("OK Pi GPIO Handler created successfully")
        print(f"OK GPIO pins configured: {len(handler.GPIO_PINS)}")
        print(f"OK Serial port: {handler.serial_port}")
        print(f"OK Baud rate: {handler.baud_rate}")
        
        # Test message sending
        test_message = {
            'type': 'test',
            'data': 'Hello from Pi handler',
            'timestamp': time.time()
        }
        
        handler.send_message(test_message)
        print("OK Message sending test passed")
        
        return True
        
    except Exception as e:
        print(f"ERROR Pi GPIO Handler test failed: {e}")
        return False

def test_pc_gpio_emulator():
    """Test the PC GPIO emulator"""
    print("\nTesting PC GPIO Emulator...")
    print("=" * 50)
    
    try:
        from train_controller_hw.gpio_emulator import create_gpio_emulator
        
        # Create emulator instance
        emulator = create_gpio_emulator('COM4')
        
        print("OK GPIO Emulator created successfully")
        print(f"OK GPIO pins configured: {len(emulator.GPIO_PINS)}")
        print(f"OK Serial port: {emulator.serial_port}")
        print(f"OK Baud rate: {emulator.baud_rate}")
        
        # Test callback registration
        def test_callback():
            print("OK Test callback executed")
        
        emulator.register_button_callback('EMERGENCY_BRAKE', test_callback)
        print("OK Button callback registration test passed")
        
        # Test message sending
        test_message = {
            'type': 'test',
            'data': 'Hello from PC emulator',
            'timestamp': time.time()
        }
        
        emulator.send_message(test_message)
        print("OK Message sending test passed")
        
        # Test auto mode
        print(f"OK Auto mode: {emulator.get_auto_mode()}")
        
        # Stop emulator
        emulator.stop()
        print("OK Emulator stopped successfully")
        
        return True
        
    except Exception as e:
        print(f"ERROR GPIO Emulator test failed: {e}")
        return False

def test_remote_driver_ui():
    """Test the remote driver UI"""
    print("\nTesting Remote Driver UI...")
    print("=" * 50)
    
    try:
        from train_controller_hw.gui.train_controller_driver_remote import RemoteDriverUI
        
        # Create Qt application
        app = QApplication(sys.argv)
        
        # Create remote driver UI
        driver_ui = RemoteDriverUI('COM4')
        
        print("OK Remote Driver UI created successfully")
        print(f"OK GPIO pins configured: {len(driver_ui.GPIO_PINS)}")
        print(f"OK Train ID: {driver_ui.train_id}")
        
        # Test driver input generation
        driver_input = driver_ui.get_driver_input()
        print(f"OK Driver input generated: auto_mode={driver_input.auto_mode}")
        
        # Test GPIO status update
        driver_ui.update_gpio_status_display()
        print("OK GPIO status display updated")
        
        # Cleanup
        driver_ui.cleanup_gpio()
        print("OK GPIO cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"ERROR Remote Driver UI test failed: {e}")
        return False

def main():
    """Main test function"""
    print("Remote GPIO Communication System Test")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 3
    
    # Test Pi GPIO handler
    if test_pi_gpio_handler():
        tests_passed += 1
    
    # Test PC GPIO emulator
    if test_pc_gpio_emulator():
        tests_passed += 1
    
    # Test remote driver UI
    if test_remote_driver_ui():
        tests_passed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("All tests passed! Remote GPIO system is ready.")
        print("\nSetup Instructions:")
        print("1. Copy pi_gpio_handler.py to Raspberry Pi")
        print("2. On Pi: python3 pi_gpio_handler.py")
        print("3. On PC: python3 train_controller_hw/gui/train_controller_driver_remote.py")
        print("4. Connect Pi to PC via USB serial cable")
        print("5. Ensure COM port matches in both scripts")
    else:
        print("Some tests failed. Please check the error messages above.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()