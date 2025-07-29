"""
Wayside Controller Management Application
=========================================
Main application for creating and managing wayside controllers.
Includes both Infrastructure-Only view and Complete All-Blocks view.
"""

from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QLabel, QComboBox, QTableWidget, 
                            QTableWidgetItem, QGroupBox, QGridLayout, QCheckBox, 
                            QSpinBox, QTextEdit, QTabWidget, QScrollArea, QFrame,
                            QHeaderView, QMessageBox, QFileDialog, QSplitter,
                            QButtonGroup, QRadioButton)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette
import sys
import os
from typing import Dict, List, Set

# Import the wayside controller
try:
    from WaysideController import WaysideController
    WAYSIDE_AVAILABLE = True
except ImportError:
    WAYSIDE_AVAILABLE = False
    print("ERROR: WaysideController not available")

# Line-specific total block counts (including yard as block 0)
LINE_BLOCK_COUNTS = {
    "Green": 151,  # Green line has 151 blocks (0-150) including yard
    "Red": 77,     # Red line has 77 blocks (0-76) including yard
    "Blue": 16     # Blue line has 16 blocks (0-15) including yard
}

def create_mock_track_data(line: str, total_blocks: int):
    """Create mock track data for a specific line with correct block count"""
    return {
        line: {
            "automatic": {
                "blocks": [{"block": i, "occupied": False, "speed_hazard": False, "authority": 0} 
                          for i in range(total_blocks)],
                "switches": [{"id": i, "suggested_toggle": False, "plc_num": 1, "toggled": False} 
                            for i in range(total_blocks)],
                "crossings": [{"id": i, "toggled": False, "plc_num": 1} 
                             for i in range(total_blocks)],
                "traffic_lights": [{"id": i, "toggled": False, "plc_num": 1} 
                                  for i in range(total_blocks)]
            }
        }
    }

# Default mock track data using standard block counts
MOCK_TRACK_DATA = {}
for line, block_count in LINE_BLOCK_COUNTS.items():
    MOCK_TRACK_DATA.update(create_mock_track_data(line, block_count))

# ========== INFRASTRUCTURE-ONLY WIDGET ==========

class InfrastructureOnlyWidget(QWidget):
    """Widget to display only infrastructure blocks (switches and crossings)"""
    
    def __init__(self, controller: 'WaysideController'):
        super().__init__()
        self.controller = controller
        
        # Infrastructure data hardcoded from track layout
        self.infrastructure_blocks = self._load_infrastructure_blocks()
        
        self.init_ui()
        
        # Connect to controller signals
        if hasattr(controller, 'data_updated'):
            controller.data_updated.connect(self.update_display)
        if hasattr(controller, 'switch_changed'):
            controller.switch_changed.connect(self.on_switch_changed)
    
    def _load_infrastructure_blocks(self) -> Dict[str, Set[int]]:
        """Load infrastructure block information - hardcoded from track layout"""
        infrastructure = {
            'switches': set(),
            'crossings': set(),
            'all_infrastructure': set()
        }
        
        # Hardcoded infrastructure data from Track Layout & Vehicle Data vF2.xlsx
        line_infrastructure = {
            'Green': {
                'switches': {13, 29, 57, 63, 77, 101},  # Green line switch blocks
                'crossings': {47, 48}  # Green line crossing blocks
            },
            'Red': {
                'switches': {15, 27, 38, 48, 60, 66, 72},  # Red line switch blocks
                'crossings': {16, 25}  # Red line crossing blocks
            },
            'Blue': {
                'switches': {15},  # Blue line switch blocks
                'crossings': {4}   # Blue line crossing blocks
            }
        }
        
        # Get infrastructure for this controller's line
        line_data = line_infrastructure.get(self.controller.line, {'switches': set(), 'crossings': set()})
        
        infrastructure['switches'] = line_data['switches'].copy()
        infrastructure['crossings'] = line_data['crossings'].copy()
        infrastructure['all_infrastructure'] = infrastructure['switches'] | infrastructure['crossings']
        
        return infrastructure
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        header_group = QGroupBox(f"Controller {self.controller.plcNum} - Infrastructure Only View")
        header_group.setStyleSheet("QGroupBox { font-weight: bold; color: #2E8B57; }")
        header_layout = QGridLayout(header_group)
        
        info_items = [
            ("Line:", self.controller.line),
            ("Infrastructure Blocks:", f"{len(self.infrastructure_blocks['all_infrastructure'])} blocks"),
            ("Switches:", f"{len(self.infrastructure_blocks['switches'])} blocks"),
            ("Crossings:", f"{len(self.infrastructure_blocks['crossings'])} blocks")
        ]
        
        for i, (label, value) in enumerate(info_items):
            header_layout.addWidget(QLabel(label), i, 0)
            value_label = QLabel(value)
            value_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 2px; }")
            header_layout.addWidget(value_label, i, 1)
        
        layout.addWidget(header_group)
        
        # Infrastructure table
        self.infrastructure_table = QTableWidget()
        self.infrastructure_table.setColumnCount(8)
        self.infrastructure_table.setHorizontalHeaderLabels([
            "Block", "Type", "Occupied", "Suggested Speed", "Commanded Speed", 
            "Suggested Auth", "Commanded Auth", "Infrastructure State"
        ])
        
        # Make table read-only
        self.infrastructure_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        layout.addWidget(self.infrastructure_table)
        
        # Initial display update
        self.update_display()
    
    def update_display(self):
        """Update the display"""
        # Get infrastructure blocks that this controller manages
        infrastructure_blocks = [block for block in self.infrastructure_blocks['all_infrastructure'] 
                               if block < len(self.controller.blocksCovered) and self.controller.blocksCovered[block]]
        
        self.infrastructure_table.setRowCount(len(infrastructure_blocks))
        
        for row, block_num in enumerate(sorted(infrastructure_blocks)):
            # Block number (0-150)
            self.infrastructure_table.setItem(row, 0, QTableWidgetItem(str(block_num)))
            
            # Type
            block_type = []
            if block_num in self.infrastructure_blocks['switches']:
                block_type.append("Switch")
            if block_num in self.infrastructure_blocks['crossings']:
                block_type.append("Crossing")
            
            type_item = QTableWidgetItem(" + ".join(block_type))
            if "Switch" in block_type:
                type_item.setBackground(QColor(173, 216, 230))  # Light blue
            if "Crossing" in block_type:
                type_item.setBackground(QColor(255, 182, 193))  # Light pink
            self.infrastructure_table.setItem(row, 1, type_item)
            
            # Occupied
            occupied = self.controller.blocks[block_num]
            occupied_item = QTableWidgetItem("Yes" if occupied else "No")
            if occupied:
                occupied_item.setBackground(QColor(255, 99, 71))
            self.infrastructure_table.setItem(row, 2, occupied_item)
            
            # Speeds and authority
            self.infrastructure_table.setItem(row, 3, QTableWidgetItem(str(self.controller.suggestedSpeed[block_num])))
            self.infrastructure_table.setItem(row, 4, QTableWidgetItem(str(self.controller.commandedSpeed[block_num])))
            self.infrastructure_table.setItem(row, 5, QTableWidgetItem("Yes" if self.controller.suggestedAuthority[block_num] else "No"))
            self.infrastructure_table.setItem(row, 6, QTableWidgetItem("Yes" if self.controller.commandedAuthority[block_num] else "No"))
            
            # Infrastructure state
            state_parts = []
            if block_num in self.infrastructure_blocks['switches']:
                switch_state = "High" if self.controller.switches[block_num] else "Low"
                state_parts.append(f"Switch: {switch_state}")
            
            if block_num in self.infrastructure_blocks['crossings']:
                crossing_state = "Down" if self.controller.crossings[block_num] else "Up"
                state_parts.append(f"Crossing: {crossing_state}")
            
            self.infrastructure_table.setItem(row, 7, QTableWidgetItem(" | ".join(state_parts)))
    
    def on_switch_changed(self, block_num: int, position: bool):
        """Handle switch change signal"""
        if block_num in self.infrastructure_blocks['switches']:
            self.update_display()


# ========== COMPLETE ALL-BLOCKS WIDGET ==========

class CompleteAllBlocksWidget(QWidget):
    """Widget to display complete status for all blocks"""
    
    def __init__(self, controller: 'WaysideController'):
        super().__init__()
        self.controller = controller
        
        # Hardcoded infrastructure locations
        self.infrastructure_locations = self._get_infrastructure_locations()
        
        self.init_ui()
        
        # Connect to controller signals
        if hasattr(controller, 'data_updated'):
            controller.data_updated.connect(self.update_display)
        if hasattr(controller, 'switch_changed'):
            controller.switch_changed.connect(self.update_display)
    
    def _get_infrastructure_locations(self) -> Dict[str, Set[int]]:
        """Get hardcoded infrastructure locations"""
        all_infrastructure = {
            'Green': {
                'switches': {13, 29, 57, 63, 77, 101},
                'traffic_lights': {19, 32, 40, 62, 85, 100, 110, 120, 130, 140},
                'crossings': {47, 48}
            },
            'Red': {
                'switches': {15, 27, 38, 48, 60, 66, 72},
                'traffic_lights': {12, 25, 35, 45, 55, 65, 70, 75},
                'crossings': {16, 25}
            },
            'Blue': {
                'switches': {15},
                'traffic_lights': {8, 12, 14},
                'crossings': {4}
            }
        }
        
        return all_infrastructure.get(self.controller.line, {
            'switches': set(), 
            'traffic_lights': set(), 
            'crossings': set()
        })
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        header_group = QGroupBox(f"Controller {self.controller.plcNum} - All Blocks View")
        header_group.setStyleSheet("QGroupBox { font-weight: bold; color: #2E8B57; }")
        header_layout = QGridLayout(header_group)
        
        info_items = [
            ("Line:", self.controller.line),
            ("Total Blocks:", f"{self.controller.total_blocks} blocks"),
            ("Managed Blocks:", f"{sum(self.controller.blocksCovered)} blocks"),
            ("Switches:", f"{len(self.infrastructure_locations['switches'])} locations"),
            ("Traffic Lights:", f"{len(self.infrastructure_locations['traffic_lights'])} locations"),
            ("Crossings:", f"{len(self.infrastructure_locations['crossings'])} locations")
        ]
        
        for i, (label, value) in enumerate(info_items):
            header_layout.addWidget(QLabel(label), i, 0)
            value_label = QLabel(value)
            value_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 2px; }")
            header_layout.addWidget(value_label, i, 1)
        
        layout.addWidget(header_group)
        
        # Control panel
        controls_group = QGroupBox("Display Controls")
        controls_layout = QHBoxLayout(controls_group)
        
        controls_layout.addWidget(QLabel("Start Block:"))
        self.start_block_spin = QSpinBox()
        self.start_block_spin.setRange(0, self.controller.total_blocks - 1)
        self.start_block_spin.setValue(0)
        self.start_block_spin.valueChanged.connect(self.update_display)
        controls_layout.addWidget(self.start_block_spin)
        
        controls_layout.addWidget(QLabel("End Block:"))
        self.end_block_spin = QSpinBox()
        self.end_block_spin.setRange(0, self.controller.total_blocks - 1)
        self.end_block_spin.setValue(min(50, self.controller.total_blocks - 1))
        self.end_block_spin.valueChanged.connect(self.update_display)
        controls_layout.addWidget(self.end_block_spin)
        
        # Quick range buttons
        all_blocks_btn = QPushButton("All Blocks")
        all_blocks_btn.clicked.connect(lambda: self.set_range(0, self.controller.total_blocks - 1))
        controls_layout.addWidget(all_blocks_btn)
        
        managed_btn = QPushButton("Managed Only")
        managed_btn.clicked.connect(self.show_managed_only)
        controls_layout.addWidget(managed_btn)
        
        controls_layout.addStretch()
        layout.addWidget(controls_group)
        
        # Complete blocks table
        self.blocks_table = QTableWidget()
        self.blocks_table.setColumnCount(10)
        self.blocks_table.setHorizontalHeaderLabels([
            "Block", "Managed", "Occupied", "Sugg Speed", "Cmd Speed", 
            "Sugg Auth", "Cmd Auth", "Switch", "Traffic Light", "Crossing"
        ])
        
        # Make table read-only
        self.blocks_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        layout.addWidget(self.blocks_table)
        
        # Initial display update
        self.update_display()
    
    def set_range(self, start: int, end: int):
        """Set block range"""
        self.start_block_spin.setValue(start)
        self.end_block_spin.setValue(end)
        self.update_display()
    
    def show_managed_only(self):
        """Show only managed blocks"""
        managed_blocks = [i for i, covered in enumerate(self.controller.blocksCovered) if covered]
        if managed_blocks:
            self.set_range(min(managed_blocks), max(managed_blocks))
    
    def update_display(self):
        """Update the display"""
        start = self.start_block_spin.value()
        end = self.end_block_spin.value()
        blocks_to_show = list(range(start, min(end + 1, self.controller.total_blocks)))
        
        self.blocks_table.setRowCount(len(blocks_to_show))
        
        for row, block_num in enumerate(blocks_to_show):
            # Block number (0-150)
            self.blocks_table.setItem(row, 0, QTableWidgetItem(str(block_num)))
            
            # Managed
            managed = self.controller.blocksCovered[block_num]
            managed_item = QTableWidgetItem("1" if managed else "0")
            if managed:
                managed_item.setBackground(QColor(144, 238, 144))
            self.blocks_table.setItem(row, 1, managed_item)
            
            # Occupied
            occupied = self.controller.blocks[block_num]
            occupied_item = QTableWidgetItem("1" if occupied else "0")
            if occupied:
                occupied_item.setBackground(QColor(255, 99, 71))
            self.blocks_table.setItem(row, 2, occupied_item)
            
            # Speeds and authority
            self.blocks_table.setItem(row, 3, QTableWidgetItem(str(self.controller.suggestedSpeed[block_num])))
            self.blocks_table.setItem(row, 4, QTableWidgetItem(str(self.controller.commandedSpeed[block_num])))
            self.blocks_table.setItem(row, 5, QTableWidgetItem("1" if self.controller.suggestedAuthority[block_num] else "0"))
            self.blocks_table.setItem(row, 6, QTableWidgetItem("1" if self.controller.commandedAuthority[block_num] else "0"))
            
            # Infrastructure (only where it exists)
            switch_text = self.get_switch_text(block_num)
            light_text = self.get_light_text(block_num)
            crossing_text = self.get_crossing_text(block_num)
            
            # Switch with color coding
            switch_item = QTableWidgetItem(switch_text)
            if block_num in self.infrastructure_locations['switches']:
                if self.controller.switches[block_num]:  # 1 = reverse (higher block)
                    switch_item.setBackground(QColor(255, 182, 193))  # Light red for reverse
                else:  # 0 = normal (lower block)  
                    switch_item.setBackground(QColor(144, 238, 144))  # Light green for normal
            self.blocks_table.setItem(row, 7, switch_item)
            
            # Traffic Light with color coding
            light_item = QTableWidgetItem(light_text)
            if block_num in self.infrastructure_locations['traffic_lights']:
                if self.controller.trafficLights[block_num]:  # 1 = red
                    light_item.setBackground(QColor(255, 99, 71))  # Red background
                else:  # 0 = green
                    light_item.setBackground(QColor(144, 238, 144))  # Green background
            self.blocks_table.setItem(row, 8, light_item)
            
            # Crossing with color coding
            crossing_item = QTableWidgetItem(crossing_text)
            if block_num in self.infrastructure_locations['crossings']:
                if self.controller.crossings[block_num]:  # 1 = down (safe for trains)
                    crossing_item.setBackground(QColor(144, 238, 144))  # Green for down (safe)
                else:  # 0 = up (unsafe for trains)
                    crossing_item.setBackground(QColor(255, 99, 71))  # Red for up (unsafe)
            self.blocks_table.setItem(row, 9, crossing_item)
    
    def get_switch_text(self, block_num: int) -> str:
        """Get switch text for block"""
        if block_num not in self.infrastructure_locations['switches']:
            return "—"  # No switch at this block
        return "1" if self.controller.switches[block_num] else "0"
    
    def get_light_text(self, block_num: int) -> str:
        """Get traffic light text for block"""
        if block_num not in self.infrastructure_locations['traffic_lights']:
            return "—"  # No traffic light at this block
        return "1" if self.controller.trafficLights[block_num] else "0"
    
    def get_crossing_text(self, block_num: int) -> str:
        """Get crossing text for block"""
        if block_num not in self.infrastructure_locations['crossings']:
            return "—"  # No crossing at this block
        return "1" if self.controller.crossings[block_num] else "0"


# ========== MAIN APPLICATION ==========

class WaysideControllerWidget(QWidget):
    """Main controller widget that contains both views"""
    
    def __init__(self, controller: 'WaysideController'):
        super().__init__()
        self.controller = controller
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI with both widget options"""
        layout = QVBoxLayout(self)
        
        # View selection
        view_group = QGroupBox("View Selection")
        view_layout = QHBoxLayout(view_group)
        
        self.view_buttons = QButtonGroup()
        
        self.infrastructure_radio = QRadioButton("Infrastructure Only")
        self.infrastructure_radio.setChecked(True)
        self.infrastructure_radio.toggled.connect(self.switch_view)
        self.view_buttons.addButton(self.infrastructure_radio)
        view_layout.addWidget(self.infrastructure_radio)
        
        self.all_blocks_radio = QRadioButton("All Blocks")
        self.all_blocks_radio.toggled.connect(self.switch_view)
        self.view_buttons.addButton(self.all_blocks_radio)
        view_layout.addWidget(self.all_blocks_radio)
        
        view_layout.addStretch()
        layout.addWidget(view_group)
        
        # Create both widgets
        self.infrastructure_widget = InfrastructureOnlyWidget(self.controller)
        self.all_blocks_widget = CompleteAllBlocksWidget(self.controller)
        
        # Add both widgets (only one will be visible at a time)
        layout.addWidget(self.infrastructure_widget)
        layout.addWidget(self.all_blocks_widget)
        
        # Initially show infrastructure view
        self.switch_view()
    
    def switch_view(self):
        """Switch between the two views"""
        if self.infrastructure_radio.isChecked():
            self.infrastructure_widget.setVisible(True)
            self.all_blocks_widget.setVisible(False)
        else:
            self.infrastructure_widget.setVisible(False)
            self.all_blocks_widget.setVisible(True)
    
    def update_display(self):
        """Update both widgets"""
        self.infrastructure_widget.update_display()
        self.all_blocks_widget.update_display()


class WaysideApp(QMainWindow):
    """Main application for wayside controller management"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wayside Controller Management System")
        self.setGeometry(100, 100, 1400, 900)
        
        # Controllers storage
        self.controllers: Dict[int, WaysideController] = {}
        self.controller_widgets: Dict[int, WaysideControllerWidget] = {}
        
        # Current simulation time
        self.current_time = "05:00:00"
        
        # Initialize UI
        self.init_ui()
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_displays)
        self.update_timer.start(1000)  # Update every second
        
        # Master timing simulation
        self.master_timer = QTimer()
        self.master_timer.timeout.connect(self.simulate_master_timing)
        self.master_timer.start(100)  # 100ms like real master
        
        print("Wayside Controller Management System initialized")
    
    def init_ui(self):
        """Initialize the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Wayside Controller Management System")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.time_label = QLabel(f"Simulation Time: {self.current_time}")
        self.time_label.setFont(QFont("Arial", 12))
        header_layout.addWidget(self.time_label)
        
        main_layout.addLayout(header_layout)
        
        # Control panel (simplified - no create/remove)
        control_group = QGroupBox("Controller Status")
        control_layout = QHBoxLayout(control_group)
        
        self.status_label = QLabel("Controller Ready")
        self.status_label.setStyleSheet("QLabel { background-color: #90EE90; padding: 5px; }")
        control_layout.addWidget(self.status_label)
        
        control_layout.addStretch()
        
        main_layout.addWidget(control_group)
        
        # Controller widget area (no splitter needed for single controller)
        self.controller_area = QWidget()
        self.controller_layout = QVBoxLayout(self.controller_area)
        main_layout.addWidget(self.controller_area)
        
        # Create the predefined controller
        self.create_predefined_controller()
    
    def create_predefined_controller(self):
        """Create the predefined controller with GreenLinePlcV1.py"""
        if not WAYSIDE_AVAILABLE:
            self.status_label.setText("ERROR: WaysideController not available")
            self.status_label.setStyleSheet("QLabel { background-color: #FF6B6B; padding: 5px; }")
            return
        
        try:
            # Use GreenLinePlcV1.py as the PLC file
            plc_file = "GreenLinePlcV1.py"
            
            # Check if PLC file exists
            if not os.path.exists(plc_file):
                self.status_label.setText(f"ERROR: PLC file {plc_file} not found")
                self.status_label.setStyleSheet("QLabel { background-color: #FF6B6B; padding: 5px; }")
                return
            
            # Create controller with predefined settings
            plc_num = 1
            line = "Green"
            
            # Initial block coverage (will be updated by PLC to all blocks)
            # Get total blocks for the line
            total_blocks = LINE_BLOCK_COUNTS.get(line, 151)
            initial_blocks_covered = [False] * total_blocks
            
            # Create controller
            controller = WaysideController(
                data=MOCK_TRACK_DATA,
                line=line,
                mode="automatic",
                auto=True,
                plc_num=plc_num,
                plc_file=plc_file,
                blocks_covered=initial_blocks_covered,
                total_blocks=total_blocks
            )
            
            # Store controller
            self.controllers[plc_num] = controller
            
            # Create widget for controller (with both views)
            controller_widget = WaysideControllerWidget(controller)
            self.controller_widgets[plc_num] = controller_widget
            
            # Add to layout
            self.controller_layout.addWidget(controller_widget)
            
            managed_blocks = sum(controller.blocksCovered)
            self.status_label.setText(f"Green Line Controller - {managed_blocks} blocks managed")
            self.status_label.setStyleSheet("QLabel { background-color: #90EE90; padding: 5px; }")
            
            print(f"Created Green Line Controller with PLC: {plc_file}")
            print(f"Managing {managed_blocks} blocks")
            
        except Exception as e:
            self.status_label.setText(f"ERROR: {str(e)}")
            self.status_label.setStyleSheet("QLabel { background-color: #FF6B6B; padding: 5px; }")
            print(f"Error creating predefined controller: {e}")
    
    def simulate_master_timing(self):
        """Simulate master controller timing"""
        # Update simulation time (simple increment)
        time_parts = self.current_time.split(":")
        hours = int(time_parts[0])
        minutes = int(time_parts[1])
        seconds = int(time_parts[2])
        
        seconds += 1
        if seconds >= 60:
            seconds = 0
            minutes += 1
            if minutes >= 60:
                minutes = 0
                hours += 1
                if hours >= 24:
                    hours = 0
        
        self.current_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        self.time_label.setText(f"Simulation Time: {self.current_time}")
        
        # Send time update to controller
        for controller in self.controllers.values():
            if hasattr(controller, 'update_time'):
                controller.update_time(self.current_time)
    
    def update_displays(self):
        """Update controller display"""
        for widget in self.controller_widgets.values():
            widget.update_display()
    
    def closeEvent(self, event):
        """Handle application close"""
        # Stop the controller
        for controller in self.controllers.values():
            controller.stop_operations()
        
        print("Application closed")
        event.accept()


def main():
    """Main function"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = WaysideApp()
    window.show()
    
    print("Wayside Controller Management System started")
    print("Features:")
    print("- Predefined Green Line Controller with GreenLinePlcV1.py")
    print("- Switch between Infrastructure-Only and All-Blocks views")
    print("- Monitor complete block status and infrastructure states")
    print("- Master timing simulation")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()