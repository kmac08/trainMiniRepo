#!/usr/bin/env python3
"""
Startup script for Train Controller System with Remote GPIO
Windows 11 compatible version with COM port detection
"""

import sys
import os
import serial.tools.list_ports
import subprocess
from pathlib import Path

def detect_com_ports():
    """Detect available COM ports on Windows"""
    ports = serial.tools.list_ports.comports()
    available_ports = []
    
    for port in ports:
        try:
            # Try to open the port briefly to check if it's available
            with serial.Serial(port.device, 9600, timeout=1) as test_serial:
                available_ports.append(port.device)
        except:
            pass
    
    return available_ports

def get_user_com_port():
    """Get COM port from user or auto-detect"""
    print("=" * 60)
    print("TRAIN CONTROLLER SYSTEM - REMOTE GPIO SETUP")
    print("=" * 60)
    
    # Detect available COM ports
    available_ports = detect_com_ports()
    
    if available_ports:
        print(f"Available COM ports: {', '.join(available_ports)}")
        
        # Use first available port as default
        default_port = available_ports[0]
        print(f"Default COM port: {default_port}")
        
        user_input = input(f"Press Enter to use {default_port} or enter a different COM port: ").strip()
        
        if user_input:
            return user_input
        else:
            return default_port
    else:
        print("No COM ports detected. Please ensure:")
        print("1. Raspberry Pi is connected via USB serial cable")
        print("2. Pi GPIO handler is running")
        print("3. Serial drivers are installed")
        
        manual_port = input("Enter COM port manually (e.g., COM4): ").strip()
        if not manual_port:
            return "COM4"  # Default fallback
        return manual_port

def check_pi_connection(com_port):
    """Check if Pi is responding on the specified COM port"""
    print(f"\nTesting connection to Raspberry Pi on {com_port}...")
    
    try:
        import serial
        import json
        import time
        
        # Try to connect and send a ping
        with serial.Serial(com_port, 9600, timeout=2) as ser:
            time.sleep(1)  # Let serial initialize
            
            # Send ping
            ping_message = {"type": "ping", "timestamp": time.time()}
            ser.write((json.dumps(ping_message) + '\n').encode('utf-8'))
            
            # Wait for response
            for _ in range(10):  # Wait up to 2 seconds
                line = ser.readline().decode('utf-8').strip()
                if line:
                    try:
                        response = json.loads(line)
                        if response.get('type') == 'pong':
                            print(f"✓ Pi connection successful on {com_port}")
                            return True
                    except json.JSONDecodeError:
                        continue
                time.sleep(0.2)
        
        print(f"✗ No response from Pi on {com_port}")
        return False
        
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        return False

def update_com_port_in_files(com_port):
    """Update COM port in the main test file"""
    main_test_path = Path(__file__).parent / "main_test_from_pc.py"
    
    if main_test_path.exists():
        # Read the file
        with open(main_test_path, 'r') as f:
            content = f.read()
        
        # Update the COM port
        updated_content = content.replace(
            "DriverUI(serial_port='COM4', baud_rate=9600)",
            f"DriverUI(serial_port='{com_port}', baud_rate=9600)"
        )
        
        # Write back
        with open(main_test_path, 'w') as f:
            f.write(updated_content)
        
        print(f"✓ Updated COM port to {com_port} in main_test_from_pc.py")
    else:
        print("✗ main_test_from_pc.py not found")

def main():
    """Main startup function"""
    print("Starting Train Controller System with Remote GPIO...")
    
    # Get COM port from user
    com_port = get_user_com_port()
    
    # Test Pi connection
    if not check_pi_connection(com_port):
        print("\n⚠️  WARNING: Could not connect to Raspberry Pi")
        print("Make sure:")
        print("1. Pi is connected and powered on")
        print("2. Pi GPIO handler is running: python3 pi_gpio_handler.py")
        print("3. Correct COM port is selected")
        
        continue_anyway = input("\nContinue anyway? (y/N): ").strip().lower()
        if continue_anyway != 'y':
            print("Startup cancelled.")
            sys.exit(1)
    
    # Update COM port in files
    update_com_port_in_files(com_port)
    
    print("\n" + "=" * 60)
    print("LAUNCHING TRAIN CONTROLLER SYSTEM")
    print("=" * 60)
    print(f"GPIO Communication: Remote via {com_port}")
    print("Hardware Requirements:")
    print("- Raspberry Pi connected via USB serial")
    print("- Pi GPIO handler running")
    print("- Physical GPIO buttons connected to Pi")
    print("=" * 60)
    
    # Add current directory to Python path for imports
    sys.path.insert(0, str(Path(__file__).parent))
    
    try:
        # Import and run the main test
        from main_test_from_pc import main as run_main_test
        run_main_test()
        
    except KeyboardInterrupt:
        print("\n\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nSystem error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()