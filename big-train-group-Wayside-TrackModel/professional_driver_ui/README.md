# Professional Driver UI Suite

This folder contains completely redesigned, professional-grade driver interfaces for both software and hardware train controllers. The UIs feature modern design principles, enhanced readability, and cross-platform compatibility.

## Files

### `professional_sw_driver_ui.py`
Professional software driver interface with manual UI controls.

### `professional_hw_driver_ui.py`
Professional hardware driver interface with GPIO integration for Raspberry Pi controls.

## Key Features

### ✨ Modern Design
- **Card-based layout** with clean, modern aesthetics
- **Professional color scheme** using contemporary UI design principles
- **Consistent typography** with clear hierarchy and excellent readability
- **Rounded corners and subtle shadows** for a polished look
- **Responsive layouts** that adapt to different screen sizes

### 📱 Enhanced Readability
- **Large, bold fonts** (36px+ for important values)
- **High contrast colors** for excellent visibility
- **Generous spacing** preventing visual clutter
- **Clear visual hierarchy** with proper sizing and color coding
- **Professional status indicators** with color-coded states

### 🖥️ Cross-Platform Compatibility
- **Responsive design** that works on Windows and Mac
- **Minimum size constraints** ensuring readability on all screens
- **Scalable fonts and layouts** adapting to different DPI settings
- **Professional system fonts** (Segoe UI, San Francisco, Helvetica Neue)
- **Consistent appearance** across different operating systems

### 🎛️ Comprehensive Functionality

#### Software Version (`professional_sw_driver_ui.py`)
- **Manual/Auto mode control** with clear visual feedback
- **Speed and temperature controls** with up/down buttons
- **Environmental controls** (headlights, interior lights, doors)
- **Brake system controls** (emergency and service brakes)
- **Real-time status displays** for all train parameters
- **System health monitoring** with failure indicators
- **Next station announcements**
- **PID controller status**

#### Hardware Version (`professional_hw_driver_ui.py`)
- **GPIO integration** with Raspberry Pi hardware controls
- **Real-time GPIO status monitoring** with connection indicators
- **11 GPIO pins configured** for comprehensive hardware control
- **Hardware input validation** and safety interlocks
- **GPIO pin mapping display** for troubleshooting
- **Serial communication status** (COM port, baud rate)
- **Emergency brake always accessible** regardless of mode

### 🛡️ Safety Features
- **Emergency brake prominently displayed** in red with large buttons
- **Door controls disabled when moving** for safety
- **Manual controls only active in manual mode**
- **Visual status indicators** for all critical systems
- **System failure alerts** with clear error states
- **Real-time monitoring** of all safety-critical parameters

### 🔧 Technical Specifications

#### Display Layout
- **Header Section**: Time, Train ID, Next Station
- **Left Column**: Control mode and manual settings (SW) / GPIO status (HW)
- **Center Column**: Train status, speed, power, authority
- **Right Column**: System health, failures, environment status
- **Footer Section**: Emergency controls and system summary

#### Color Coding
- **Green**: Normal operation, success states
- **Blue**: Information, active manual mode
- **Yellow/Orange**: Warnings, active states
- **Red**: Errors, failures, emergency states
- **Gray**: Inactive, disabled, or normal states

#### Responsive Features
- **Minimum window size**: 1400x900 (SW) / 1600x1000 (HW)
- **Dynamic font scaling** based on window size
- **Flexible layouts** that maintain readability
- **Consistent margins and spacing** across all screen sizes

## Integration Instructions

### For Software Controller
```python
from professional_driver_ui.professional_sw_driver_ui import ProfessionalSoftwareDriverUI

# Create and show the UI
driver_ui = ProfessionalSoftwareDriverUI()
driver_ui.set_train_controller(your_train_controller)
driver_ui.show()

# Get driver input
driver_input = driver_ui.get_driver_input()
```

### For Hardware Controller
```python
from professional_driver_ui.professional_hw_driver_ui import ProfessionalHardwareDriverUI

# Create and show the UI with GPIO configuration
driver_ui = ProfessionalHardwareDriverUI(serial_port='COM4', baud_rate=9600)
driver_ui.set_train_controller(your_train_controller)
driver_ui.show()

# Get driver input (from GPIO)
driver_input = driver_ui.get_driver_input()
```

## Backend Compatibility

Both UIs are fully compatible with the existing train controller backends:
- `train_controller_sw.controller.train_controller.TrainController`
- `train_controller_hw.controller.train_controller.TrainController`

They use the same data types:
- `DriverInput` - User inputs to the controller
- `OutputToDriver` - Controller data for display
- `TrainControllerInit` - Initialization parameters

## GPIO Pin Configuration (Hardware Version)

| Pin | Function | Description |
|-----|----------|-------------|
| 13  | Mode Control | HIGH=Manual, LOW=Auto |
| 17  | Headlights | Toggle headlights |
| 27  | Interior Lights | Toggle interior lights |
| 21  | Emergency Brake | Emergency brake (always active) |
| 26  | Service Brake | Service brake (manual mode only) |
| 6   | Left Door | Toggle left door (manual + stopped) |
| 19  | Right Door | Toggle right door (manual + stopped) |
| 20  | Speed Up | Increase speed (manual mode only) |
| 16  | Speed Down | Decrease speed (manual mode only) |
| 23  | Temperature Up | Increase temperature (manual mode only) |
| 24  | Temperature Down | Decrease temperature (manual mode only) |

## Design Philosophy

### Modern UI Principles
- **Clarity over complexity** - Every element has a clear purpose
- **Consistency** - Similar elements look and behave similarly
- **Accessibility** - High contrast, large fonts, clear labels
- **Professional appearance** - Suitable for real-world train operations
- **Error prevention** - Clear states and safety interlocks

### Visual Hierarchy
1. **Critical information** (speed, emergency brake) - Largest, most prominent
2. **Primary controls** - Medium size, easy to access
3. **Status information** - Clear but not overwhelming
4. **Secondary details** - Smaller but still readable

### User Experience
- **Immediate feedback** - All interactions provide visual confirmation
- **Clear status** - Always know the current state of the system
- **Safety first** - Emergency controls are always accessible
- **Professional workflow** - Designed for trained operators
- **Minimal learning curve** - Intuitive layout and controls

## Testing and Validation

Both UIs have been designed and tested for:
- ✅ **Readability** at various screen sizes and resolutions
- ✅ **Professional appearance** suitable for real-world deployment
- ✅ **Cross-platform compatibility** (Windows and Mac)
- ✅ **Complete functionality** matching original UI capabilities
- ✅ **Safety compliance** with proper interlocks and emergency controls
- ✅ **Performance** with smooth 10 FPS updates
- ✅ **Integration** with existing train controller backends

## Future Enhancements

Potential future improvements:
- **Dark mode theme** for low-light operations
- **Customizable layouts** for different operator preferences
- **Audio alerts** for critical system states
- **Touch screen optimization** for tablet deployment
- **Multi-language support** for international use
- **Advanced diagnostics** with detailed system logs