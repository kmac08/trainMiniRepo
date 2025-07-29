# Remote GPIO Setup for Train Controller System

This guide explains how to set up the train controller system to run on PC while reading GPIO inputs from a Raspberry Pi via serial communication.

## Overview

The system now uses a **professional bidirectional serial protocol** to communicate between:
- **PC**: Runs the train controller logic and GUI
- **Raspberry Pi**: Handles physical GPIO inputs and sends data to PC

## Files Created

| File | Location | Purpose |
|------|----------|---------|
| `pi_gpio_handler.py` | Root directory | Runs on Pi - handles GPIO and serial communication |
| `gpio_emulator.py` | `train_controller_hw/` | PC-side GPIO emulator |
| `train_controller_driver_remote.py` | `train_controller_hw/gui/` | Modified driver UI for remote GPIO |
| `main_test_from_pc.py` | `train_controller_hw/` | **Modified** - now uses remote GPIO |
| `start_with_remote_gpio.py` | `train_controller_hw/` | Windows 11 compatible startup script |
| `start_train_controller.bat` | `train_controller_hw/` | Windows batch file for easy startup |
| `setup_pi.py` | Root directory | Pi setup and configuration script |

## Hardware Requirements

### Raspberry Pi Side
- Raspberry Pi (any model with GPIO pins)
- MicroSD card with Raspberry Pi OS
- GPIO buttons/switches connected to pins:
  - GPIO 17: Headlight control
  - GPIO 27: Interior lights
  - GPIO 21: Emergency brake
  - GPIO 26: Service brake
  - GPIO 6: Left door
  - GPIO 19: Right door
  - GPIO 20: Speed up
  - GPIO 16: Speed down
  - GPIO 23: Temperature up
  - GPIO 24: Temperature down
  - GPIO 13: Auto/Manual mode switch

### PC Side
- Windows 11 PC
- USB serial cable (USB-A to USB-Mini/Micro)
- Python 3.6+ with PyQt5

## Setup Instructions

### 1. Raspberry Pi Setup

#### Copy Files to Pi
```bash
# Copy these files to your Raspberry Pi
scp pi_gpio_handler.py pi@your-pi-ip:/home/pi/
scp setup_pi.py pi@your-pi-ip:/home/pi/
```

#### Run Setup Script
```bash
# On the Raspberry Pi
python3 setup_pi.py
```

#### Enable Serial Interface
```bash
sudo raspi-config
# Navigate to: Interfacing Options -> Serial
# Disable serial login shell: No
# Enable serial port hardware: Yes
# Reboot
sudo reboot
```

#### Install Dependencies
```bash
pip3 install pyserial RPi.GPIO
```

#### Start GPIO Handler
```bash
python3 pi_gpio_handler.py
```

### 2. PC Setup (Windows 11)

#### Easy Method - Use Batch File
1. Double-click `train_controller_hw/start_train_controller.bat`
2. Follow the prompts to select COM port
3. System will auto-detect and test Pi connection

#### Manual Method
```cmd
cd train_controller_hw
python start_with_remote_gpio.py
```

#### Direct Method (if COM port is known)
```cmd
cd train_controller_hw
python main_test_from_pc.py
```

### 3. Connection and Testing

#### Physical Connection
1. Connect Pi to PC using USB serial cable
2. Note the COM port (e.g., COM4) in Windows Device Manager
3. Ensure Pi GPIO handler is running first

#### Test Connection
```cmd
python test_remote_gpio.py
```

## GPIO Pin Mapping

| Function | GPIO Pin | Description |
|----------|----------|-------------|
| Headlight | 17 | Toggle headlights (manual mode only) |
| Interior Light | 27 | Toggle interior lights (manual mode only) |
| Emergency Brake | 21 | Emergency brake (works in any mode) |
| Service Brake | 26 | Service brake (manual mode only) |
| Left Door | 6 | Left door control (manual mode only) |
| Right Door | 19 | Right door control (manual mode only) |
| Speed Up | 20 | Increase speed (manual mode only) |
| Speed Down | 16 | Decrease speed (manual mode only) |
| Temperature Up | 23 | Increase temperature (manual mode only) |
| Temperature Down | 24 | Decrease temperature (manual mode only) |
| Auto/Manual Mode | 13 | Mode switch (HIGH=manual, LOW=auto) |

**Note**: All pins use internal pull-up resistors. Buttons should connect pin to GND when pressed.

## Protocol Details

### Serial Communication
- **Baud Rate**: 9600
- **Format**: JSON messages with newline termination
- **Direction**: Bidirectional

### Message Types

#### Pi to PC
```json
{
  "type": "gpio_input",
  "data": {
    "EMERGENCY_BRAKE": true,
    "auto_mode": false
  },
  "timestamp": 1234567890.123
}
```

#### PC to Pi
```json
{
  "type": "ping",
  "timestamp": 1234567890.123
}
```

## Troubleshooting

### Common Issues

#### Pi Not Responding
- Check serial cable connection
- Verify Pi GPIO handler is running
- Ensure correct COM port is selected
- Check Pi power and boot status

#### GPIO Not Working
- Verify GPIO pin connections
- Check pull-up resistors are working
- Test with multimeter: pins should read ~3.3V when not pressed, ~0V when pressed
- Run Pi setup script to test GPIO

#### Serial Port Issues
- Check Windows Device Manager for COM port
- Try different USB ports
- Ensure Pi serial interface is enabled
- Test with different serial cable

#### Permission Errors
- Run Pi commands with appropriate permissions
- Check file permissions on serial port
- Ensure user is in `dialout` group on Pi

### Debug Mode

#### Pi Side Debug
```bash
# Run with verbose output
python3 pi_gpio_handler.py
```

#### PC Side Debug
```cmd
# Test GPIO emulator
python test_remote_gpio.py
```

## Changes Made to Original Code

### Key Modifications

1. **`main_test_from_pc.py`** - Modified to use `RemoteDriverUI` instead of `DriverUI`
   - **Why**: Original `DriverUI` tries to import `RPi.GPIO` directly, which fails on PC
   - **Change**: Now uses remote GPIO communication via serial protocol

2. **GPIO Communication** - Replaced direct GPIO access with serial protocol
   - **Why**: GPIO pins are physically on Pi, not PC
   - **Change**: Created emulator that communicates with Pi via serial

3. **Button Handling** - Modified from direct GPIO reading to callback system
   - **Why**: Button presses now come via serial messages, not direct GPIO interrupts
   - **Change**: Callback system processes remote button events

4. **Auto-start Scripts** - Created Windows 11 compatible startup scripts
   - **Why**: Original setup required manual configuration of GPIO and serial ports
   - **Change**: Automated COM port detection and Pi connection testing

### Original Logic Preserved

- **Train Controller Logic**: No changes to core controller algorithms
- **GUI Layout**: Driver UI appearance and functionality unchanged
- **Update Timing**: Same 10Hz update rate via Master Interface
- **Engineer Interface**: No changes to Kp/Ki adjustment
- **Test Bench**: No changes to train model simulation

## System Architecture

```
┌─────────────────┐    USB Serial    ┌─────────────────┐
│   Windows PC    │ ←─────────────→  │ Raspberry Pi    │
│                 │                  │                 │
│ Train Controller│                  │ GPIO Handler    │
│ GUI + Logic     │                  │ Physical Buttons│
│ (main_test...)  │                  │ (pi_gpio_...)   │
└─────────────────┘                  └─────────────────┘
```

## Success Indicators

✅ **System Working Correctly When:**
- Pi connection status shows "CONNECTED" in GUI
- Physical button presses trigger actions in PC GUI
- Auto/Manual mode switch works correctly
- Emergency brake functions in all modes
- Manual controls only work in manual mode
- All train controller logic functions normally

🚂 **Ready for Operation!**