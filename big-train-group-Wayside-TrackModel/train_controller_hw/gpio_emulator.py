#!/usr/bin/env python3
"""
GPIO Emulator for PC - Communicates with Raspberry Pi via Serial
Replaces direct GPIO access with serial communication
"""

import json
import serial
import time
import threading
from typing import Dict, Any, Optional

class GPIOEmulator:
    """Emulates GPIO functionality by communicating with Raspberry Pi via serial"""
    
    def __init__(self, serial_port='COM4', baud_rate=9600):
        """Initialize GPIO emulator with serial communication"""
        
        # GPIO pin definitions (for reference)
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
        
        # GPIO state tracking
        self.gpio_states = {}
        self.gpio_prev_states = {}
        self.auto_mode = True
        
        # Serial communication
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.serial = None
        
        # Threading
        self.running = False
        self.listener_thread = None
        self.connected = False
        
        # Button press callbacks
        self.button_callbacks = {}
        
        self.setup_serial()
        self.start_listener()
    
    def setup_serial(self):
        """Initialize serial communication"""
        try:
            self.serial = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
            print(f"Serial communication initialized on {self.serial_port} at {self.baud_rate} baud")
            time.sleep(2)  # Allow serial to initialize
            self.connected = True
        except Exception as e:
            print(f"Error initializing serial: {e}")
            self.serial = None
            self.connected = False
    
    def send_message(self, message: Dict[str, Any]):
        """Send JSON message via serial"""
        if not self.serial:
            return
        
        try:
            json_str = json.dumps(message) + '\n'
            self.serial.write(json_str.encode('utf-8'))
            print(f"Sent to Pi: {json_str.strip()}")
        except Exception as e:
            print(f"Error sending message: {e}")
    
    def ping_pi(self):
        """Send ping to Pi to check connection"""
        message = {
            'type': 'ping',
            'timestamp': time.time()
        }
        self.send_message(message)
    
    def request_gpio_status(self):
        """Request current GPIO status from Pi"""
        message = {
            'type': 'gpio_status_request',
            'timestamp': time.time()
        }
        self.send_message(message)
    
    def handle_pi_message(self, message: Dict[str, Any]):
        """Handle messages from Pi"""
        msg_type = message.get('type')
        
        if msg_type == 'gpio_input':
            # Handle GPIO input changes from Pi
            data = message.get('data', {})
            self.process_gpio_changes(data)
            
        elif msg_type == 'pong':
            # Pi responded to ping
            print("Pi connection confirmed")
            self.connected = True
            
        elif msg_type == 'gpio_status':
            # GPIO status response
            data = message.get('data', {})
            self.auto_mode = data.get('auto_mode', True)
            print(f"Pi GPIO status: auto_mode={self.auto_mode}")
            
        else:
            print(f"Unknown message type from Pi: {msg_type}")
    
    def process_gpio_changes(self, changes: Dict[str, Any]):
        """Process GPIO changes received from Pi"""
        for pin_name, value in changes.items():
            if pin_name == 'auto_mode':
                self.auto_mode = value
                print(f"Mode changed to: {'AUTO' if value else 'MANUAL'}")
            else:
                # Button press detected
                if pin_name in self.button_callbacks:
                    self.button_callbacks[pin_name]()
                print(f"Button press: {pin_name}")
    
    def serial_listener_loop(self):
        """Listen for messages from Pi"""
        print("Starting serial listener for Pi communication...")
        
        while self.running:
            if not self.serial:
                time.sleep(1)
                continue
            
            try:
                line = self.serial.readline().decode('utf-8').strip()
                if line:
                    message = json.loads(line)
                    self.handle_pi_message(message)
                    
            except json.JSONDecodeError:
                print(f"Invalid JSON from Pi: {line}")
            except Exception as e:
                print(f"Error reading from Pi: {e}")
    
    def start_listener(self):
        """Start the serial listener thread"""
        if self.running:
            return
        
        self.running = True
        self.listener_thread = threading.Thread(target=self.serial_listener_loop)
        self.listener_thread.daemon = True
        self.listener_thread.start()
        
        # Send initial ping
        time.sleep(0.5)
        self.ping_pi()
    
    def stop(self):
        """Stop the GPIO emulator"""
        self.running = False
        
        if self.listener_thread:
            self.listener_thread.join(timeout=1)
        
        if self.serial:
            self.serial.close()
        
        print("GPIO emulator stopped")
    
    def register_button_callback(self, pin_name: str, callback):
        """Register a callback for button presses"""
        self.button_callbacks[pin_name] = callback
    
    def is_connected(self) -> bool:
        """Check if connected to Pi"""
        return self.connected and self.serial is not None
    
    def get_auto_mode(self) -> bool:
        """Get current auto mode state"""
        return self.auto_mode

class MockGPIO:
    """Mock GPIO class that uses the emulator"""
    
    BCM = "BCM"
    IN = "IN"
    OUT = "OUT"
    PUD_UP = "PUD_UP"
    PUD_DOWN = "PUD_DOWN"
    
    _emulator: Optional[GPIOEmulator] = None
    
    @classmethod
    def setup_emulator(cls, emulator: GPIOEmulator):
        """Setup the GPIO emulator instance"""
        cls._emulator = emulator
    
    @classmethod
    def setmode(cls, mode):
        """Set GPIO mode (no-op for emulator)"""
        pass
    
    @classmethod
    def setwarnings(cls, warnings):
        """Set GPIO warnings (no-op for emulator)"""
        pass
    
    @classmethod
    def setup(cls, pin, direction, pull_up_down=None):
        """Setup GPIO pin (no-op for emulator)"""
        pass
    
    @classmethod
    def input(cls, pin):
        """Read GPIO pin (always returns HIGH for pull-up simulation)"""
        return True
    
    @classmethod
    def cleanup(cls):
        """Clean up GPIO (no-op for emulator)"""
        pass

def create_gpio_emulator(serial_port='COM4', baud_rate=9600) -> GPIOEmulator:
    """Create and return a GPIO emulator instance"""
    emulator = GPIOEmulator(serial_port, baud_rate)
    MockGPIO.setup_emulator(emulator)
    return emulator

# Export the mock GPIO for use in train_controller_hw
GPIO = MockGPIO
GPIO_AVAILABLE = True  # Always available with emulator