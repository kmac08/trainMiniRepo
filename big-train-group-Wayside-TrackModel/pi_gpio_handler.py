#!/usr/bin/env python3
"""
Raspberry Pi GPIO Handler - Runs on Pi
Handles GPIO input/output and communicates with PC via serial
"""

import json
import serial
import time
import threading
from typing import Dict, Any

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("Warning: RPi.GPIO not available. Running in simulation mode.")
    GPIO_AVAILABLE = False

class PiGPIOHandler:
    def __init__(self, serial_port='/dev/serial0', baud_rate=9600):
        """Initialize GPIO handler with serial communication"""
        
        # GPIO pin definitions (matching train_controller_hw)
        self.GPIO_PINS = {
            'HEADLIGHT': 17,
            'INTERIOR_LIGHT': 27,
            'EMERGENCY_BRAKE': 21,
            'SERVICE_BRAKE': 26,
            'LEFT_DOOR': 6,
            'RIGHT_DOOR': 19,
            'SPEED_UP': 20,
            'SPEED_DOWN': 16,
            'TEMP_UP': 23,
            'TEMP_DOWN': 24,
            'AUTO_MANUAL_MODE': 13
        }
        
        # GPIO input states
        self.gpio_states = {}
        self.gpio_prev_states = {}
        
        # Serial communication
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.serial = None
        
        # Threading control
        self.running = False
        self.gpio_thread = None
        self.serial_thread = None
        
        self.setup_gpio()
        self.setup_serial()
    
    def setup_gpio(self):
        """Initialize GPIO pins"""
        if not GPIO_AVAILABLE:
            print("GPIO not available - running in simulation mode")
            # Initialize simulation states
            for pin_name in self.GPIO_PINS:
                self.gpio_states[pin_name] = False
                self.gpio_prev_states[pin_name] = True  # Simulate pull-up
            return
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup all pins as input with pull-up resistors
        for pin_name, pin_num in self.GPIO_PINS.items():
            GPIO.setup(pin_num, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self.gpio_states[pin_name] = GPIO.input(pin_num)
            self.gpio_prev_states[pin_name] = GPIO.input(pin_num)
            print(f"GPIO pin {pin_num} ({pin_name}) initialized")
    
    def setup_serial(self):
        """Initialize serial communication"""
        try:
            self.serial = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
            print(f"Serial communication initialized on {self.serial_port} at {self.baud_rate} baud")
            time.sleep(2)  # Allow serial to initialize
        except Exception as e:
            print(f"Error initializing serial: {e}")
            self.serial = None
    
    def read_gpio_inputs(self):
        """Read all GPIO pins and detect state changes"""
        if not GPIO_AVAILABLE:
            return {}
        
        changes = {}
        
        for pin_name, pin_num in self.GPIO_PINS.items():
            current_state = GPIO.input(pin_num)
            prev_state = self.gpio_prev_states[pin_name]
            
            # Mode control pin - level triggered
            if pin_name == 'AUTO_MANUAL_MODE':
                auto_mode = not current_state  # Inverted: LOW = auto, HIGH = manual
                if auto_mode != self.gpio_states.get('auto_mode', True):
                    changes['auto_mode'] = auto_mode
                    self.gpio_states['auto_mode'] = auto_mode
            else:
                # Button pins - edge triggered (high to low = press)
                if prev_state == True and current_state == False:
                    changes[pin_name] = True
                    print(f"Button press detected: {pin_name}")
            
            self.gpio_prev_states[pin_name] = current_state
        
        return changes
    
    def gpio_monitor_loop(self):
        """Main GPIO monitoring loop"""
        print("Starting GPIO monitoring loop...")
        
        while self.running:
            changes = self.read_gpio_inputs()
            
            if changes and self.serial:
                # Send GPIO changes to PC
                message = {
                    'type': 'gpio_input',
                    'data': changes,
                    'timestamp': time.time()
                }
                self.send_message(message)
            
            time.sleep(0.05)  # 50ms polling rate
    
    def send_message(self, message: Dict[str, Any]):
        """Send JSON message via serial"""
        if not self.serial:
            return
        
        try:
            json_str = json.dumps(message) + '\n'
            self.serial.write(json_str.encode('utf-8'))
            print(f"Sent: {json_str.strip()}")
        except Exception as e:
            print(f"Error sending message: {e}")
    
    def serial_listener_loop(self):
        """Listen for messages from PC"""
        print("Starting serial listener loop...")
        
        while self.running:
            if not self.serial:
                time.sleep(1)
                continue
            
            try:
                line = self.serial.readline().decode('utf-8').strip()
                if line:
                    message = json.loads(line)
                    self.handle_pc_message(message)
                    
            except json.JSONDecodeError:
                print(f"Invalid JSON received: {line}")
            except Exception as e:
                print(f"Error reading serial: {e}")
    
    def handle_pc_message(self, message: Dict[str, Any]):
        """Handle messages from PC"""
        msg_type = message.get('type')
        
        if msg_type == 'ping':
            # Respond to ping
            response = {
                'type': 'pong',
                'timestamp': time.time()
            }
            self.send_message(response)
            
        elif msg_type == 'gpio_status_request':
            # Send current GPIO status
            current_status = {
                'auto_mode': self.gpio_states.get('auto_mode', True),
                'gpio_available': GPIO_AVAILABLE,
                'pins': self.GPIO_PINS
            }
            response = {
                'type': 'gpio_status',
                'data': current_status,
                'timestamp': time.time()
            }
            self.send_message(response)
            
        else:
            print(f"Unknown message type: {msg_type}")
    
    def start(self):
        """Start the GPIO handler threads"""
        if self.running:
            print("GPIO handler already running")
            return
        
        self.running = True
        
        # Start GPIO monitoring thread
        self.gpio_thread = threading.Thread(target=self.gpio_monitor_loop)
        self.gpio_thread.daemon = True
        self.gpio_thread.start()
        
        # Start serial listener thread
        self.serial_thread = threading.Thread(target=self.serial_listener_loop)
        self.serial_thread.daemon = True
        self.serial_thread.start()
        
        print("GPIO handler started")
    
    def stop(self):
        """Stop the GPIO handler"""
        self.running = False
        
        if self.gpio_thread:
            self.gpio_thread.join(timeout=1)
        
        if self.serial_thread:
            self.serial_thread.join(timeout=1)
        
        if self.serial:
            self.serial.close()
        
        if GPIO_AVAILABLE:
            GPIO.cleanup()
        
        print("GPIO handler stopped")

def main():
    """Main function for standalone operation"""
    handler = PiGPIOHandler()
    
    try:
        handler.start()
        print("Pi GPIO Handler running. Press Ctrl+C to stop.")
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        handler.stop()

if __name__ == "__main__":
    main()