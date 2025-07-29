"""
CTC Communication Test UI
========================
Test interface for proper CTC-Wayside-TicketStation communication
according to UML specifications with event-driven architecture.

This UI demonstrates:
- Wayside controller registration via provide_wayside_controller()
- Event-driven train command system (block-specific commands)
- Block closure communication via set_occupied()
- Automatic switch control on block occupation updates
- Ticket station throughput updates by line
- Real-time display of CTC outputs and Wayside inputs

Key Features:
- Block-specific commands with update flags and next station info
- Commands sent only on events (routing, rerouting, block updates)
- Proper integration with actual CTC system
- Real-time command monitoring and logging
"""

import sys
import os
import json
import time
import logging
from datetime import datetime, time as dt_time
from typing import Dict, List, Optional, Tuple

# Set up logging
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                 QHBoxLayout, QGridLayout, QLabel, QPushButton, 
                                 QTextEdit, QTabWidget, QFrame, QComboBox, 
                                 QSpinBox, QGroupBox, QSplitter, QCheckBox,
                                 QTableWidget, QTableWidgetItem, QHeaderView,
                                 QScrollArea, QMessageBox, QSlider, QLineEdit)
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
    from PyQt5.QtGui import QFont, QColor
except ImportError:
    print("PyQt5 is required. Please install it: pip install PyQt5")
    sys.exit(1)

# Import master interface time management
try:
    from Master_Interface.master_control import TimeManager, get_time
    MASTER_INTERFACE_AVAILABLE = True
except ImportError:
    print("Warning: Master interface not available. Time management will be limited.")
    MASTER_INTERFACE_AVAILABLE = False
    def get_time():
        return datetime.now()

# Import CTC system
try:
    from CTC.ctc_main import create_ctc_office
    CTC_AVAILABLE = True
except ImportError:
    print("Warning: CTC system not available.")
    CTC_AVAILABLE = False


class MockWaysideController:
    """Mock wayside controller for testing"""
    def __init__(self, controller_id: str, blocks_covered: List[int]):
        self.controller_id = controller_id
        self.blocks_covered = blocks_covered
        self.communication_handler = None
        
        # State tracking
        self.block_occupancy = {block: False for block in blocks_covered}
        self.switch_positions = {}  # switch_id -> position (0/1)
        self.railway_crossings = {}  # crossing_id -> active (True/False)
        
        # Track commands received
        self.last_train_commands = {}
        self.last_switch_commands = {}
    
    def command_train(self, suggestedSpeed: List[int], authority: List[int], blockNum: List[int], 
                     updatePreviousFlag: List[int], nextStation: List[int]):
        """Receive block-specific train commands from CTC"""
        self.last_train_commands = {
            'suggested_speed': suggestedSpeed,
            'authority': authority, 
            'block_num': blockNum,
            'update_previous_flag': updatePreviousFlag,
            'next_station': nextStation,
            'timestamp': datetime.now()
        }
        
        # Log if yard commands are received
        if -1 in blockNum:
            yard_index = blockNum.index(-1)
            print(f"[{self.controller_id}] Received YARD command: Speed={suggestedSpeed[yard_index]}, Authority={authority[yard_index]}")
        
        return True
    
    def command_switch(self, switchPositions: List[bool]):
        """Receive switch commands from CTC"""
        self.last_switch_commands = {
            'positions': switchPositions,
            'timestamp': datetime.now()
        }
        return True
    
    def set_occupied(self, blockList: List[bool]):
        """Receive manual block occupation from CTC"""
        for i, block_num in enumerate(self.blocks_covered):
            if i < len(blockList):
                self.block_occupancy[block_num] = blockList[i]
        return True


class MockCommunicationHandler:
    """Mock Communication Handler implementing UML interface"""
    def __init__(self):
        # Attributes from UML
        self.scheduledClosures = []  # List[Tuple[Block, DateTime]]
        self.scheduledTrains = []    # List[Route]
        
        # Additional attributes
        self.wayside_controllers = []  # List[WaysideController]
        self.block_to_controller = {}  # Dict[int, WaysideController]
        self.ctc_system = None
        self.ui_callback = None
        
        # Track last values
        self.last_occupied_blocks = {}
        self.last_switch_positions = {}
        self.last_railway_crossings = {}
        
        # Track throughput by line
        self.throughput_by_line = {
            'Blue': 0,
            'Red': 0,
            'Green': 0
        }
        self.throughput_total = 0
    
    def provide_wayside_controller(self, waysideController: MockWaysideController, blocksCovered: List[int]):
        """Called by wayside to register controller and its blocks"""
        self.wayside_controllers.append(waysideController)
        for block in blocksCovered:
            self.block_to_controller[block] = waysideController
        waysideController.communication_handler = self
        
        if self.ui_callback:
            self.ui_callback('wayside_registered', {
                'controller_id': waysideController.controller_id,
                'blocks': blocksCovered
            })
    
    def update_occupied_blocks(self, occupiedBlocks: List[bool]):
        """Receive occupation status from wayside controller"""
        self.last_occupied_blocks = occupiedBlocks
        if self.ui_callback:
            self.ui_callback('occupied_blocks_update', {'blocks': occupiedBlocks})
    
    def update_switch_positions(self, switchPositions: List[bool]):
        """Receive switch positions from wayside controller"""
        self.last_switch_positions = switchPositions
        if self.ui_callback:
            self.ui_callback('switch_positions_update', {'switches': switchPositions})
    
    def update_railway_crossings(self, railwayCrossings: List[bool]):
        """Receive crossing status from wayside controller"""
        self.last_railway_crossings = railwayCrossings
        if self.ui_callback:
            self.ui_callback('railway_crossings_update', {'crossings': railwayCrossings})
    
    def schedule_route(self, route):
        """Schedule a train route with wayside"""
        self.scheduledTrains.append(route)
        if self.ui_callback:
            self.ui_callback('route_scheduled', {'route_id': str(route)})
    
    def schedule_closure(self, block, time):
        """Schedule block closure"""
        self.scheduledClosures.append((block, time))
        if self.ui_callback:
            self.ui_callback('closure_scheduled', {'block': block, 'time': str(time)})
    
    def send_train_info(self):
        """Send train commands to wayside controllers"""
        # In real implementation, this would calculate and send commands
        # For testing, we'll generate sample commands
        for controller in self.wayside_controllers:
            # Generate commands for each block
            suggested_speeds = []
            authorities = []
            num_blocks = []
            
            for block in controller.blocks_covered:
                # Sample logic: occupied blocks get stop command
                if controller.block_occupancy.get(block, False):
                    suggested_speeds.append(0)  # Stop
                    authorities.append(0)       # No authority
                else:
                    suggested_speeds.append(3)  # Full speed
                    authorities.append(1)       # Full authority
                num_blocks.append(4)  # Standard 4-block lookahead
            
            controller.command_train(suggested_speeds, authorities, num_blocks)
            
            if self.ui_callback:
                self.ui_callback('train_commands_sent', {
                    'controller': controller.controller_id,
                    'commands': {
                        'suggested_speeds': suggested_speeds,
                        'authorities': authorities,
                        'num_blocks_ahead': num_blocks
                    }
                })
    
    def tickets_purchased(self, line: str, numTickets: int):
        """Handle throughput update from ticket system for specific line"""
        if line in self.throughput_by_line:
            self.throughput_by_line[line] += numTickets
            
        if self.ui_callback:
            self.ui_callback('tickets_purchased', {
                'line': line,
                'tickets': numTickets,
                'line_totals': self.throughput_by_line.copy()
            })
        
        # Forward to CTC System (if connected)
        if self.ctc_system:
            self.ctc_system.update_throughput(numTickets)
    
    def stop_train(self, train):
        """Emergency stop a specific train"""
        if self.ui_callback:
            self.ui_callback('emergency_stop', {'train': str(train)})
    
    def command_train(self, suggestedSpeed: List[int], authority: List[int], blockNum: List[int], 
                      updatePreviousFlag: List[int], nextStation: List[int]):
        """Send block-specific train commands to wayside controllers"""
        # Group commands by controller
        controller_commands = {}
        
        for i in range(len(blockNum)):
            block = blockNum[i]
            if block in self.block_to_controller:
                controller = self.block_to_controller[block]
                
                if controller not in controller_commands:
                    controller_commands[controller] = {
                        'suggestedSpeed': [],
                        'authority': [],
                        'blockNum': [],
                        'updatePreviousFlag': [],
                        'nextStation': []
                    }
                
                controller_commands[controller]['suggestedSpeed'].append(suggestedSpeed[i])
                controller_commands[controller]['authority'].append(authority[i])
                controller_commands[controller]['blockNum'].append(blockNum[i])
                controller_commands[controller]['updatePreviousFlag'].append(updatePreviousFlag[i])
                controller_commands[controller]['nextStation'].append(nextStation[i])
        
        # Send commands to each controller
        for controller, commands in controller_commands.items():
            result = controller.command_train(
                commands['suggestedSpeed'],
                commands['authority'], 
                commands['blockNum'],
                commands['updatePreviousFlag'],
                commands['nextStation']
            )
            if self.ui_callback:
                self.ui_callback('train_commands_sent', {
                    'controller': controller.controller_id,
                    'commands': commands
                })
        
        return True
    
    def command_switch(self, controller: MockWaysideController, switchPositions: List[bool]):
        """Send switch commands to specific wayside controller"""
        result = controller.command_switch(switchPositions)
        if self.ui_callback:
            self.ui_callback('switch_commands_sent', {
                'controller': controller.controller_id,
                'positions': switchPositions
            })
        return result
    
    def set_occupied(self, controller: MockWaysideController, blockList: List[bool]):
        """Set block occupation for manual closures"""
        result = controller.set_occupied(blockList)
        if self.ui_callback:
            self.ui_callback('manual_occupation_set', {
                'controller': controller.controller_id,
                'blocks': blockList
            })
        return result


class StyledMessageBox(QMessageBox):
    """Custom message box with CTC styling"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QMessageBox {
                background-color: white;
                border: 2px solid #808080;
                color: black;
                font-size: 13pt;
            }
            QMessageBox QLabel {
                color: black;
                background-color: transparent;
                padding: 15px;
                font-size: 13pt;
            }
            QMessageBox QPushButton {
                background-color: #E0E0E0;
                border: 1px solid #808080;
                color: black;
                padding: 6px 20px;
                min-width: 70px;
                margin: 5px;
            }
            QMessageBox QPushButton:hover {
                background-color: #D0D0D0;
            }
            QMessageBox QPushButton:pressed {
                background-color: #C0C0C0;
            }
        """)


class CTCCommunicationTestUI(QMainWindow):
    """Test UI for CTC Communication"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CTC Communication Test Interface with Time Control")
        self.setGeometry(100, 100, 1400, 1000)
        
        # Time management
        self.time_manager = None
        self.ctc_instance = None
        self.simulation_running = False
        
        # Initialize time manager if available
        if MASTER_INTERFACE_AVAILABLE:
            self.time_manager = TimeManager()
            self.time_manager.time_update.connect(self.on_time_update)
        
        # Apply CTC styling
        self.setStyleSheet("""
            QMainWindow { 
                background-color: white; 
            }
            QWidget {
                background-color: white;
                color: black;
            }
            QLabel { 
                color: black; 
                background-color: transparent; 
            }
            QPushButton { 
                color: black; 
                background-color: #E0E0E0; 
                border: 1px solid #808080; 
                padding: 6px 12px; 
            }
            QPushButton:hover { 
                background-color: #D0D0D0; 
            }
            QPushButton:pressed {
                background-color: #C0C0C0;
            }
            QComboBox { 
                color: black; 
                background-color: white; 
                border: 1px solid #808080; 
                padding: 4px; 
                min-height: 20px;
            }
            QComboBox::drop-down {
                border: 0px;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #808080;
                color: black;
                selection-background-color: #3399FF;
                selection-color: white;
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
            QSpinBox {
                color: black;
                background-color: white;
                border: 1px solid #808080;
                padding: 4px;
            }
            QGroupBox {
                color: black;
                font-weight: bold;
                border: 1px solid #808080;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QTableWidget { 
                color: black; 
                background-color: white; 
                border: 1px solid #808080; 
                gridline-color: #C0C0C0; 
            }
            QTableWidget::item { 
                color: black; 
                background-color: white; 
                padding: 2px;
            }
            QTableWidget::item:selected { 
                background-color: #3399FF; 
                color: white; 
            }
            QHeaderView::section { 
                color: black; 
                background-color: #F0F0F0; 
                border: 1px solid #808080; 
                padding: 4px; 
            }
            QTabWidget::pane { 
                border: 1px solid #808080; 
                background-color: white; 
            }
            QTabBar::tab { 
                color: black; 
                background-color: #F0F0F0; 
                border: 1px solid #808080; 
                padding: 8px 16px; 
            }
            QTabBar::tab:selected { 
                background-color: white; 
            }
            QCheckBox {
                color: black;
            }
            QCheckBox::indicator {
                width: 13px;
                height: 13px;
                border: 1px solid #808080;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #3399FF;
            }
        """)
        
        # Create mock components
        self.communication_handler = MockCommunicationHandler()
        self.communication_handler.ui_callback = self.handle_communication_event
        
        # Create wayside controllers
        # Blue_A and Red_A include block -1 to indicate they control the yard
        self.wayside_controllers = {
            'Blue_A': MockWaysideController('Blue_A', [-1] + list(range(1, 16))),  # Includes yard (block -1)
            'Blue_B': MockWaysideController('Blue_B', list(range(16, 28))),
            'Red_A': MockWaysideController('Red_A', [-1] + list(range(1, 25))),  # Includes yard (block -1)
            'Red_B': MockWaysideController('Red_B', list(range(25, 45))),
            'Green_A': MockWaysideController('Green_A', list(range(1, 30))),
            'Green_B': MockWaysideController('Green_B', list(range(30, 58)))
        }
        
        # Message log
        self.message_log = []
        
        # Current time display
        self.current_time = "05:00"
        
        self.init_ui()
        
        # Wayside controllers will be registered when CTC system starts
        # No automatic registration in test mode
        
        # Auto-update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_displays)
        self.update_timer.start(1000)  # Update every second
    
    def init_ui(self):
        """Initialize the UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Top header layout with throughput and time (matching main CTC interface)
        top_header_layout = QHBoxLayout()
        
        # Throughput info on left
        self.throughput_label = QLabel("Blue Line: 0 pass/hr  |  Red Line: 0 pass/hr  |  Green Line: 0 pass/hr")
        self.throughput_label.setFont(QFont("Arial", 18, QFont.Bold))
        
        # Time display on right
        self.time_label = QLabel(f"Time: {self.current_time}")
        self.time_label.setFont(QFont("Arial", 21, QFont.Bold))
        self.time_label.setMaximumHeight(30)
        
        top_header_layout.addWidget(self.throughput_label)
        top_header_layout.addStretch()
        top_header_layout.addWidget(self.time_label)
        top_header_layout.setContentsMargins(5, 5, 5, 5)
        
        main_layout.addLayout(top_header_layout)
        
        # Title
        title = QLabel("CTC Communication Test Interface")
        title.setFont(QFont("Arial", 16))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Time Control and CTC Management Section
        control_group = QGroupBox("System Control")
        control_layout = QVBoxLayout(control_group)
        
        # Time Control Row
        time_control_layout = QHBoxLayout()
        
        # Start Time Selection
        time_control_layout.addWidget(QLabel("Start Time (HH:MM):"))
        self.start_time_edit = QLineEdit("05:00")
        self.start_time_edit.setMaximumWidth(80)
        self.start_time_edit.textChanged.connect(self.on_start_time_changed)
        time_control_layout.addWidget(self.start_time_edit)
        
        time_control_layout.addWidget(QLabel("  |  "))
        
        # Time Speed Control
        time_control_layout.addWidget(QLabel("Time Speed:"))
        self.time_speed_slider = QSlider(Qt.Horizontal)
        self.time_speed_slider.setMinimum(1)
        self.time_speed_slider.setMaximum(10)
        self.time_speed_slider.setValue(1)
        self.time_speed_slider.setMaximumWidth(200)
        self.time_speed_slider.valueChanged.connect(self.on_time_speed_changed)
        time_control_layout.addWidget(self.time_speed_slider)
        
        self.time_speed_label = QLabel("1.0x")
        self.time_speed_label.setMinimumWidth(40)
        time_control_layout.addWidget(self.time_speed_label)
        
        time_control_layout.addWidget(QLabel("  |  "))
        
        # Time Control Buttons
        self.pause_play_btn = QPushButton("▶ Start")
        self.pause_play_btn.setMaximumWidth(100)
        self.pause_play_btn.clicked.connect(self.toggle_time_control)
        time_control_layout.addWidget(self.pause_play_btn)
        
        time_control_layout.addStretch()
        control_layout.addLayout(time_control_layout)
        
        # CTC Control Row
        ctc_control_layout = QHBoxLayout()
        
        # Line Selection
        ctc_control_layout.addWidget(QLabel("Track Line:"))
        self.line_selection = QComboBox()
        self.line_selection.addItems(["Blue Line", "Green/Red Line"])
        self.line_selection.setMaximumWidth(150)
        self.line_selection.currentTextChanged.connect(self.on_line_selection_changed)
        ctc_control_layout.addWidget(self.line_selection)
        
        ctc_control_layout.addWidget(QLabel("  |  "))
        
        self.start_ctc_btn = QPushButton("Start CTC System")
        self.start_ctc_btn.setMaximumWidth(150)
        self.start_ctc_btn.clicked.connect(self.start_ctc_system)
        self.start_ctc_btn.setEnabled(CTC_AVAILABLE)
        ctc_control_layout.addWidget(self.start_ctc_btn)
        
        self.stop_ctc_btn = QPushButton("Stop CTC System")
        self.stop_ctc_btn.setMaximumWidth(150)
        self.stop_ctc_btn.clicked.connect(self.stop_ctc_system)
        self.stop_ctc_btn.setEnabled(False)
        ctc_control_layout.addWidget(self.stop_ctc_btn)
        
        self.ctc_status_label = QLabel("CTC Status: Not Running")
        self.ctc_status_label.setStyleSheet("color: red; font-weight: bold;")
        ctc_control_layout.addWidget(self.ctc_status_label)
        
        ctc_control_layout.addStretch()
        control_layout.addLayout(ctc_control_layout)
        
        main_layout.addWidget(control_group)
        
        # Create tab widget for all content
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont("Arial", 11))
        main_layout.addWidget(self.tabs)
        
        # Create main tab with wayside inputs and CTC outputs
        self.create_main_tab()
        
        # Create separate tabs
        self.create_ticket_tab()
        self.create_message_log_tab()
        
        # Status bar
        self.statusBar().showMessage("Ready")
        self.statusBar().setFont(QFont("Arial", 10))
    
    def create_main_tab(self):
        """Create main tab with wayside inputs and CTC outputs"""
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        
        # Left side - Wayside Inputs (now larger)
        self.create_wayside_inputs(main_layout)
        
        # Right side - CTC Outputs (block commands table only)
        self.create_ctc_outputs(main_layout)
        
        self.tabs.addTab(main_widget, "Main - Wayside & CTC")
    
    def create_wayside_inputs(self, parent_layout):
        """Create wayside controller input section"""
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        
        # Header
        wayside_group = QGroupBox("Wayside Controller Inputs to CTC")
        wayside_group.setStyleSheet("QGroupBox { font-size: 14px; font-weight: bold; color: #2E8B57; }")
        wayside_layout = QVBoxLayout(wayside_group)
        
        # Controller selection
        control_layout = QHBoxLayout()
        controller_label = QLabel("Controller:")
        controller_label.setFont(QFont("Arial", 11))
        control_layout.addWidget(controller_label)
        self.controller_combo = QComboBox()
        self.controller_combo.addItems(list(self.wayside_controllers.keys()))
        self.controller_combo.currentTextChanged.connect(self.update_wayside_display)
        self.controller_combo.setFont(QFont("Arial", 11))
        control_layout.addWidget(self.controller_combo)
        control_layout.addStretch()
        wayside_layout.addLayout(control_layout)
        
        # Block occupancy
        occ_group = QGroupBox("Block Occupancy")
        occ_layout = QVBoxLayout(occ_group)
        
        self.occupancy_table = QTableWidget()
        self.occupancy_table.setColumnCount(4)
        self.occupancy_table.setHorizontalHeaderLabels(['Block', 'Occupied', 'Block', 'Occupied'])
        occ_layout.addWidget(self.occupancy_table)
        
        occ_btn_layout = QHBoxLayout()
        update_btn = QPushButton("Update Occupancy")
        update_btn.clicked.connect(self.send_occupancy_update)
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_occupancy)
        test_btn = QPushButton("Set Test Pattern")
        test_btn.clicked.connect(self.set_test_occupancy)
        occ_btn_layout.addWidget(update_btn)
        occ_btn_layout.addWidget(clear_btn)
        occ_btn_layout.addWidget(test_btn)
        occ_layout.addLayout(occ_btn_layout)
        
        wayside_layout.addWidget(occ_group)
        
        # Switch positions
        switch_group = QGroupBox("Switch Positions")
        switch_layout = QVBoxLayout(switch_group)
        
        self.switch_table = QTableWidget()
        self.switch_table.setColumnCount(3)
        self.switch_table.setHorizontalHeaderLabels(['Switch ID', 'Normal (0)', 'Reverse (1)'])
        switch_layout.addWidget(self.switch_table)
        
        switch_btn = QPushButton("Update Switch Positions")
        switch_btn.clicked.connect(self.send_switch_update)
        switch_layout.addWidget(switch_btn)
        
        wayside_layout.addWidget(switch_group)
        
        # Railway crossings
        crossing_group = QGroupBox("Railway Crossings")
        crossing_layout = QVBoxLayout(crossing_group)
        
        self.crossing_table = QTableWidget()
        self.crossing_table.setColumnCount(2)
        self.crossing_table.setHorizontalHeaderLabels(['Crossing ID', 'Active'])
        crossing_layout.addWidget(self.crossing_table)
        
        crossing_btn = QPushButton("Update Crossings")
        crossing_btn.clicked.connect(self.send_crossing_update)
        crossing_layout.addWidget(crossing_btn)
        
        wayside_layout.addWidget(crossing_group)
        
        input_layout.addWidget(wayside_group)
        parent_layout.addWidget(input_widget)
        
        # Initialize display
        self.update_wayside_display()
    
    def create_ticket_tab(self):
        """Create ticket station tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Ticket purchase simulation
        ticket_group = QGroupBox("Ticket Purchase Simulation")
        ticket_layout = QGridLayout(ticket_group)
        
        ticket_layout.addWidget(QLabel("Line:"), 0, 0)
        self.ticket_line = QComboBox()
        self.ticket_line.addItems(["Blue", "Red", "Green"])
        self.ticket_line.setFont(QFont("Arial", 11))
        ticket_layout.addWidget(self.ticket_line, 0, 1)
        
        ticket_layout.addWidget(QLabel("Number of Tickets:"), 1, 0)
        self.ticket_spin = QSpinBox()
        self.ticket_spin.setRange(1, 100)
        self.ticket_spin.setValue(5)
        self.ticket_spin.setFont(QFont("Arial", 11))
        ticket_layout.addWidget(self.ticket_spin, 1, 1)
        
        purchase_btn = QPushButton("Purchase Tickets")
        purchase_btn.clicked.connect(self.purchase_tickets)
        purchase_btn.setFont(QFont("Arial", 11))
        ticket_layout.addWidget(purchase_btn, 2, 0, 1, 2)
        
        layout.addWidget(ticket_group)
        
        # Line-specific throughput display
        throughput_group = QGroupBox("Throughput Information by Line")
        throughput_layout = QVBoxLayout(throughput_group)
        
        # Create table for throughput display
        self.throughput_table = QTableWidget()
        self.throughput_table.setColumnCount(3)
        self.throughput_table.setHorizontalHeaderLabels(['Line', 'Total Tickets', 'Tickets/Hour'])
        self.throughput_table.setRowCount(3)
        
        # Initialize rows
        lines = ['Blue', 'Red', 'Green']
        for i, line in enumerate(lines):
            self.throughput_table.setItem(i, 0, QTableWidgetItem(line))
            self.throughput_table.setItem(i, 1, QTableWidgetItem('0'))
            self.throughput_table.setItem(i, 2, QTableWidgetItem('0'))
        
        # Make table read-only
        self.throughput_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.throughput_table.horizontalHeader().setStretchLastSection(True)
        throughput_layout.addWidget(self.throughput_table)
        
        # Recent purchases log
        self.throughput_log = QTextEdit()
        self.throughput_log.setReadOnly(True)
        self.throughput_log.setMaximumHeight(200)
        self.throughput_log.setFont(QFont("Monaco", 10))
        throughput_layout.addWidget(QLabel("Recent Ticket Purchases:"))
        throughput_layout.addWidget(self.throughput_log)
        
        layout.addWidget(throughput_group)
        
        self.tabs.addTab(widget, "Ticket Station")
    
    def create_ctc_outputs(self, parent_layout):
        """Create CTC output section"""
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        
        # Block Commands Table
        block_commands_group = QGroupBox("Block Commands from CTC")
        block_commands_group.setStyleSheet("QGroupBox { font-size: 14px; font-weight: bold; color: #8B4513; }")
        block_commands_layout = QVBoxLayout(block_commands_group)
        
        # Controller selection for block commands
        block_control_layout = QHBoxLayout()
        block_control_layout.addWidget(QLabel("Controller:"))
        self.block_controller_combo = QComboBox()
        self.block_controller_combo.addItems(list(self.wayside_controllers.keys()))
        self.block_controller_combo.currentTextChanged.connect(self.update_block_commands_table)
        block_control_layout.addWidget(self.block_controller_combo)
        block_control_layout.addStretch()
        
        # Auto-refresh toggle
        self.auto_refresh_check = QCheckBox("Auto-refresh (1s)")
        self.auto_refresh_check.setChecked(True)
        block_control_layout.addWidget(self.auto_refresh_check)
        
        block_commands_layout.addLayout(block_control_layout)
        
        # Block commands table
        self.block_commands_table = QTableWidget()
        self.block_commands_table.setColumnCount(8)
        self.block_commands_table.setHorizontalHeaderLabels([
            'Block #', 'Command Block', 'Occupied', 'Speed Command', 'Authority', 'Update Flag', 'Next Station', 'Last Updated'
        ])
        self.block_commands_table.horizontalHeader().setStretchLastSection(True)
        self.block_commands_table.setAlternatingRowColors(True)
        self.block_commands_table.setStyleSheet("""
            QTableWidget::item:alternate {
                background-color: #F5F5F5;
            }
        """)
        block_commands_layout.addWidget(self.block_commands_table)
        
        output_layout.addWidget(block_commands_group)
        
        parent_layout.addWidget(output_widget)
        
        # Initialize block commands table
        self.update_block_commands_table()
    
    def create_message_log_tab(self):
        """Create message log tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Controls
        control_layout = QHBoxLayout()
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.clear_message_log)
        control_layout.addWidget(clear_btn)
        
        self.auto_scroll_check = QCheckBox("Auto-scroll")
        self.auto_scroll_check.setChecked(True)
        control_layout.addWidget(self.auto_scroll_check)
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # Message display
        self.message_display = QTextEdit()
        self.message_display.setReadOnly(True)
        self.message_display.setFont(QFont("Monaco", 10))
        layout.addWidget(self.message_display)
        
        self.tabs.addTab(widget, "Message Log")
    
    def update_wayside_display(self):
        """Update wayside controller display"""
        controller_id = self.controller_combo.currentText()
        if controller_id not in self.wayside_controllers:
            return
        
        controller = self.wayside_controllers[controller_id]
        
        # Update occupancy table
        blocks = controller.blocks_covered
        num_rows = (len(blocks) + 1) // 2
        self.occupancy_table.setRowCount(num_rows)
        
        for i, block in enumerate(blocks):
            row = i // 2
            col_offset = (i % 2) * 2
            
            # Block number (show "Yard" for block -1)
            block_display = "Yard" if block == -1 else str(block)
            self.occupancy_table.setItem(row, col_offset, 
                QTableWidgetItem(block_display))
            
            # Checkbox for occupancy
            check_widget = QWidget()
            check_layout = QHBoxLayout(check_widget)
            check_layout.setContentsMargins(0, 0, 0, 0)
            check_layout.setAlignment(Qt.AlignCenter)
            
            check = QCheckBox()
            check.setChecked(controller.block_occupancy.get(block, False))
            check.stateChanged.connect(lambda state, b=block: 
                self.update_block_occupancy(b, state == Qt.Checked))
            check_layout.addWidget(check)
            
            self.occupancy_table.setCellWidget(row, col_offset + 1, check_widget)
        
        # Update switch table based on selected line and controller
        selected_line = self.line_selection.currentText() if hasattr(self, 'line_selection') else "Blue Line"
        switches_for_line = self.get_switches_for_line_and_controller(controller_id, selected_line)
        
        self.switch_table.setRowCount(len(switches_for_line))
        
        for i, switch_info in enumerate(switches_for_line):
            self.switch_table.setItem(i, 0, QTableWidgetItem(f"Block {switch_info['block']} Switch"))
            
            # Radio buttons for position
            normal_check = QCheckBox()
            reverse_check = QCheckBox()
            
            # Make them exclusive
            normal_check.toggled.connect(lambda checked, rc=reverse_check: 
                rc.setChecked(False) if checked else None)
            reverse_check.toggled.connect(lambda checked, nc=normal_check: 
                nc.setChecked(False) if checked else None)
            
            # Set default
            normal_check.setChecked(True)
            
            self.switch_table.setCellWidget(i, 1, normal_check)
            self.switch_table.setCellWidget(i, 2, reverse_check)
        
        # Update crossing table based on selected line and controller
        crossings_for_line = self.get_crossings_for_line_and_controller(controller_id, selected_line)
        self.crossing_table.setRowCount(len(crossings_for_line))
        
        for i, crossing_info in enumerate(crossings_for_line):
            self.crossing_table.setItem(i, 0, QTableWidgetItem(f"Block {crossing_info['block']} Crossing"))
            
            check_widget = QWidget()
            check_layout = QHBoxLayout(check_widget)
            check_layout.setContentsMargins(0, 0, 0, 0)
            check_layout.setAlignment(Qt.AlignCenter)
            
            check = QCheckBox()
            check_layout.addWidget(check)
            
            self.crossing_table.setCellWidget(i, 1, check_widget)
    
    def get_switches_for_line_and_controller(self, controller_id, selected_line):
        """Get switches for specific line and controller based on real track data"""
        switches = []
        
        # Define switches based on the track analysis
        if selected_line == "Blue Line":
            if controller_id == "Blue_A":  # Blocks 1-15
                switches = [
                    {'block': 5, 'type': 'multi_destination'},
                    {'block': 6, 'type': 'connection'},
                    {'block': 11, 'type': 'connection'}
                ]
        else:  # Green/Red Line
            if controller_id == "Red_A":  # Blocks 1-24
                switches = [
                    {'block': 9, 'type': 'yard'},
                    {'block': 15, 'type': 'multi_destination'}
                ]
            elif controller_id == "Red_B":  # Blocks 25-44
                switches = [
                    {'block': 27, 'type': 'multi_destination'},
                    {'block': 32, 'type': 'multi_destination'},
                    {'block': 38, 'type': 'multi_destination'},
                    {'block': 43, 'type': 'multi_destination'}
                ]
            elif controller_id == "Green_A":  # Blocks 1-29
                switches = [
                    {'block': 12, 'type': 'multi_destination'},
                    {'block': 29, 'type': 'multi_destination'}
                ]
            elif controller_id == "Green_B":  # Blocks 30-57
                switches = [
                    {'block': 52, 'type': 'multi_destination'}  # From Red line but potentially shared
                ]
        
        return switches
    
    def get_crossings_for_line_and_controller(self, controller_id, selected_line):
        """Get railway crossings for specific line and controller based on real track data"""
        crossings = []
        
        # Define crossings based on the track analysis
        if selected_line == "Blue Line":
            # Blue line has no railway crossings
            pass
        else:  # Green/Red Line
            if controller_id == "Red_B":  # Blocks 25-44, contains block 47
                # Note: Block 47 is beyond Red_B range, but let's include for demonstration
                pass
            elif controller_id == "Green_A":  # Blocks 1-29, contains block 19
                crossings = [
                    {'block': 19, 'type': 'railway_crossing'}
                ]
        
        return crossings
    
    def update_block_occupancy(self, block: int, occupied: bool):
        """Update block occupancy state"""
        controller_id = self.controller_combo.currentText()
        if controller_id in self.wayside_controllers:
            self.wayside_controllers[controller_id].block_occupancy[block] = occupied
    
    def send_occupancy_update(self):
        """Send occupancy update from current controller"""
        controller_id = self.controller_combo.currentText()
        if controller_id not in self.wayside_controllers:
            return
        
        controller = self.wayside_controllers[controller_id]
        occupancy_list = [controller.block_occupancy.get(block, False) 
                         for block in controller.blocks_covered]
        
        self.communication_handler.update_occupied_blocks(occupancy_list)
        self.statusBar().showMessage(f"Sent occupancy update from {controller_id}")
    
    def clear_occupancy(self):
        """Clear all occupancy"""
        controller_id = self.controller_combo.currentText()
        if controller_id in self.wayside_controllers:
            controller = self.wayside_controllers[controller_id]
            for block in controller.blocks_covered:
                controller.block_occupancy[block] = False
            self.update_wayside_display()
    
    def set_test_occupancy(self):
        """Set a test occupancy pattern"""
        controller_id = self.controller_combo.currentText()
        if controller_id in self.wayside_controllers:
            controller = self.wayside_controllers[controller_id]
            # Set every 3rd block as occupied
            for i, block in enumerate(controller.blocks_covered):
                controller.block_occupancy[block] = (i % 3 == 0)
            self.update_wayside_display()
    
    def send_switch_update(self):
        """Send switch position update"""
        positions = []
        for i in range(self.switch_table.rowCount()):
            reverse_check = self.switch_table.cellWidget(i, 2)
            if reverse_check and isinstance(reverse_check, QCheckBox):
                positions.append(reverse_check.isChecked())
            else:
                positions.append(False)
        
        self.communication_handler.update_switch_positions(positions)
        self.statusBar().showMessage("Sent switch position update")
    
    def send_crossing_update(self):
        """Send railway crossing update"""
        crossings = []
        for i in range(self.crossing_table.rowCount()):
            check_widget = self.crossing_table.cellWidget(i, 1)
            if check_widget:
                check = check_widget.findChild(QCheckBox)
                if check:
                    crossings.append(check.isChecked())
                else:
                    crossings.append(False)
        
        self.communication_handler.update_railway_crossings(crossings)
        self.statusBar().showMessage("Sent railway crossing update")
    
    def purchase_tickets(self):
        """Simulate ticket purchase"""
        line = self.ticket_line.currentText()
        num_tickets = self.ticket_spin.value()
        self.communication_handler.tickets_purchased(line, num_tickets)
        self.statusBar().showMessage(f"Purchased {num_tickets} tickets for {line} Line")
    
    
    def handle_communication_event(self, event_type: str, data: dict):
        """Handle communication events"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Enhanced logging for CTC function calls
        if event_type in ['train_commands_sent', 'switch_commands_sent']:
            # These are CTC function calls - make them prominent
            function_name = "command_train()" if event_type == 'train_commands_sent' else "command_switch()"
            message = f"[{timestamp}] *** CTC FUNCTION CALL *** {function_name}: {json.dumps(data, indent=2)}"
        else:
            # Regular message
            message = f"[{timestamp}] {event_type}: {json.dumps(data, indent=2)}"
        
        self.message_log.append(message)
        
        # Update displays based on event type
        if event_type == 'tickets_purchased':
            self.update_throughput_display()
        elif event_type in ['train_commands_sent', 'switch_commands_sent']:
            self.update_command_displays()
            # Also update the block commands table
            self.update_block_commands_table()
        
        # Update message log display
        self.update_message_log()
    
    def update_throughput_display(self):
        """Update throughput display"""
        if not hasattr(self, 'throughput_table'):
            return
            
        # Update table with line totals
        lines = ['Blue', 'Red', 'Green']
        for i, line in enumerate(lines):
            total = self.communication_handler.throughput_by_line.get(line, 0)
            self.throughput_table.setItem(i, 1, QTableWidgetItem(str(total)))
            # Calculate hourly rate (simplified - in real system would track time)
            hourly = total * 12  # Assume 5-minute intervals for demo
            self.throughput_table.setItem(i, 2, QTableWidgetItem(str(hourly)))
        
        # Update header throughput display
        blue_total = self.communication_handler.throughput_by_line.get('Blue', 0)
        red_total = self.communication_handler.throughput_by_line.get('Red', 0)
        green_total = self.communication_handler.throughput_by_line.get('Green', 0)
        
        # Calculate hourly rates
        blue_hourly = blue_total * 12
        red_hourly = red_total * 12
        green_hourly = green_total * 12
        
        self.throughput_label.setText(
            f"Blue Line: {blue_hourly} pass/hr  |  "
            f"Red Line: {red_hourly} pass/hr  |  "
            f"Green Line: {green_hourly} pass/hr"
        )
        
        # Update recent purchases log
        if hasattr(self, 'throughput_log'):
            ticket_messages = [msg for msg in self.message_log if 'tickets_purchased' in msg]
            log_text = ""
            for msg in ticket_messages[-10:]:  # Last 10 purchases
                # Extract timestamp and details from message
                if '[' in msg:
                    timestamp_end = msg.find(']')
                    if timestamp_end > 0:
                        timestamp = msg[1:timestamp_end]
                        # Parse the JSON to get line and ticket info
                        try:
                            json_start = msg.find('{')
                            if json_start > 0:
                                json_data = json.loads(msg[json_start:])
                                data = json_data.get('data', {}) if 'data' in json_data else json_data
                                line = data.get('line', 'Unknown')
                                tickets = data.get('tickets', 0)
                                log_text += f"[{timestamp}] {line} Line: {tickets} tickets\n"
                        except:
                            pass
            
            self.throughput_log.setText(log_text)
    
    def update_command_displays(self):
        """Update command displays - now updates the block commands table"""
        # The block commands table now serves as the main command display
        # This method is called when commands are updated to refresh the table
        if hasattr(self, 'block_commands_table'):
            self.update_block_commands_table()
    
    
    def update_block_commands_table(self):
        """Update the block commands table with current CTC commands"""
        if not hasattr(self, 'block_commands_table'):
            return
            
        controller_id = self.block_controller_combo.currentText()
        if controller_id not in self.wayside_controllers:
            return
        
        controller = self.wayside_controllers[controller_id]
        blocks = controller.blocks_covered
        
        # Set up table
        self.block_commands_table.setRowCount(len(blocks))
        
        # Current time will be used in the last updated column
        
        for i, block in enumerate(blocks):
            # Block number (show "Yard" for block -1)
            block_display = "Yard" if block == -1 else str(block)
            self.block_commands_table.setItem(i, 0, QTableWidgetItem(block_display))
            
            # Command block (the block the command is targeting)
            self.block_commands_table.setItem(i, 1, QTableWidgetItem(block_display))
            
            # Occupied status
            occupied = controller.block_occupancy.get(block, False)
            occupied_item = QTableWidgetItem("Yes" if occupied else "No")
            occupied_item.setBackground(QColor("#FFE6E6") if occupied else QColor("#E6FFE6"))
            self.block_commands_table.setItem(i, 2, occupied_item)
            
            # Commands from last train command
            if controller.last_train_commands:
                cmd = controller.last_train_commands
                
                # Find if this block has a command in the block_num list
                block_command_index = -1
                if 'block_num' in cmd and block in cmd['block_num']:
                    block_command_index = cmd['block_num'].index(block)
                
                if block_command_index >= 0:
                    # Speed command
                    speed_val = cmd['suggested_speed'][block_command_index]
                    speed_map = {0: 'STOP', 1: '1/3 Speed', 2: '2/3 Speed', 3: 'Full Speed'}
                    speed_text = speed_map.get(speed_val, f'Speed {speed_val}')
                    speed_item = QTableWidgetItem(speed_text)
                    if speed_val == 0:
                        speed_item.setBackground(QColor("#FFE6E6"))  # Red for stop
                    elif speed_val == 3:
                        speed_item.setBackground(QColor("#E6FFE6"))  # Green for full speed
                    else:
                        speed_item.setBackground(QColor("#FFFEE6"))  # Yellow for partial speed
                    self.block_commands_table.setItem(i, 3, speed_item)
                    
                    # Authority
                    auth_val = cmd['authority'][block_command_index]
                    auth_text = "Granted" if auth_val else "Denied"
                    auth_item = QTableWidgetItem(auth_text)
                    auth_item.setBackground(QColor("#E6FFE6") if auth_val else QColor("#FFE6E6"))
                    self.block_commands_table.setItem(i, 4, auth_item)
                    
                    # Update flag
                    update_flag = cmd.get('update_previous_flag', [0])[block_command_index] if block_command_index < len(cmd.get('update_previous_flag', [])) else 0
                    update_text = "Update" if update_flag else "New"
                    self.block_commands_table.setItem(i, 5, QTableWidgetItem(update_text))
                    
                    # Next station
                    next_station = cmd.get('next_station', [0])[block_command_index] if block_command_index < len(cmd.get('next_station', [])) else 0
                    station_text = f"Station {next_station}" if next_station else "None"
                    self.block_commands_table.setItem(i, 6, QTableWidgetItem(station_text))
                    
                    # Last updated
                    last_update = cmd['timestamp'].strftime("%H:%M:%S")
                    self.block_commands_table.setItem(i, 7, QTableWidgetItem(last_update))
                else:
                    # No command data for this specific block
                    self.block_commands_table.setItem(i, 3, QTableWidgetItem("No Command"))
                    self.block_commands_table.setItem(i, 4, QTableWidgetItem("No Command"))
                    self.block_commands_table.setItem(i, 5, QTableWidgetItem("-"))
                    self.block_commands_table.setItem(i, 6, QTableWidgetItem("-"))
                    self.block_commands_table.setItem(i, 7, QTableWidgetItem("-"))
            else:
                # No commands yet
                self.block_commands_table.setItem(i, 3, QTableWidgetItem("No Commands"))
                self.block_commands_table.setItem(i, 4, QTableWidgetItem("No Commands"))
                self.block_commands_table.setItem(i, 5, QTableWidgetItem("-"))
                self.block_commands_table.setItem(i, 6, QTableWidgetItem("-"))
                self.block_commands_table.setItem(i, 7, QTableWidgetItem("-"))
        
        # Resize columns to content
        self.block_commands_table.resizeColumnsToContents()
    
    def update_message_log(self):
        """Update message log display"""
        self.message_display.clear()
        for message in self.message_log[-100:]:  # Show last 100 messages
            self.message_display.append(message + "\n")
        
        if self.auto_scroll_check.isChecked():
            scrollbar = self.message_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def clear_message_log(self):
        """Clear the message log"""
        self.message_log.clear()
        self.message_display.clear()
    
    def update_displays(self):
        """Update all displays"""
        self.update_command_displays()
        # Update block commands table if auto-refresh is enabled
        if hasattr(self, 'auto_refresh_check') and self.auto_refresh_check.isChecked():
            self.update_block_commands_table()
    
    # Time Control Methods
    def on_start_time_changed(self):
        """Handle start time input changes"""
        start_time_text = self.start_time_edit.text()
        try:
            # Validate time format
            dt_time.fromisoformat(start_time_text + ":00")
            if self.time_manager:
                self.time_manager.set_start_time(start_time_text)
        except ValueError:
            # Invalid time format, could show error message
            pass
    
    def on_time_speed_changed(self, value):
        """Handle time speed slider changes"""
        speed = float(value)
        self.time_speed_label.setText(f"{speed:.1f}x")
        if self.time_manager:
            self.time_manager.set_time_multiplier(speed)
    
    def toggle_time_control(self):
        """Toggle time simulation start/pause"""
        if not self.time_manager:
            return
            
        if self.simulation_running:
            # Pause simulation
            self.time_manager.pause()
            self.pause_play_btn.setText("▶ Resume")
            self.simulation_running = False
        else:
            # Start/Resume simulation
            if not self.time_manager.is_running:
                # First time start
                start_time = self.start_time_edit.text()
                self.time_manager.set_start_time(start_time)
                self.time_manager.start()
            else:
                # Resume from pause
                self.time_manager.resume()
            self.pause_play_btn.setText("⏸ Pause")
            self.simulation_running = True
    
    def on_time_update(self, time_str):
        """Handle time updates from time manager"""
        self.current_time = time_str
        self.time_label.setText(f"Time: {time_str}")
        
        # Update CTC instance with new time if available
        if self.ctc_instance and hasattr(self.ctc_instance, 'update_time'):
            self.ctc_instance.update_time(time_str)
    
    # CTC Control Methods
    def start_ctc_system(self):
        """Start the CTC system"""
        if not CTC_AVAILABLE:
            self.show_message("Error", "CTC system is not available. Please check the installation.")
            return
            
        try:
            # Create CTC instance with correct track file path and selected lines
            track_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                         "Track_Reader", "Track Layout & Vehicle Data vF2.xlsx")
            
            # Determine selected lines based on UI selection
            selected_line = self.line_selection.currentText()
            if selected_line == "Blue Line":
                selected_lines = ['Blue']
            else:  # Green/Red Line
                selected_lines = ['Green', 'Red']
            
            # Create CTC instance with selected lines
            from CTC.UI.ctc_interface import CTCInterface
            self.ctc_instance = CTCInterface(track_file_path, selected_lines=selected_lines)
            
            # Register wayside controllers with CTC system
            self._register_wayside_controllers_with_ctc()
            
            # Connect CTC to our communication handler for UI updates
            if hasattr(self.ctc_instance, 'ctc_system') and hasattr(self.ctc_instance.ctc_system, 'communicationHandler'):
                # Set up UI callback for the CTC communication handler
                self.ctc_instance.ctc_system.communicationHandler.ui_callback = self.handle_communication_event
            
            # Show CTC interface
            self.ctc_instance.show()
            
            # Update UI
            self.start_ctc_btn.setEnabled(False)
            self.stop_ctc_btn.setEnabled(True)
            selected_line = self.line_selection.currentText()
            self.ctc_status_label.setText(f"CTC Status: Running ({selected_line})")
            self.ctc_status_label.setStyleSheet("color: green; font-weight: bold;")
            
            self.message_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] System: CTC system started for {selected_line}")
            
        except Exception as e:
            self.show_message("Error", f"Failed to start CTC system: {str(e)}")
    
    def stop_ctc_system(self):
        """Stop the CTC system"""
        if self.ctc_instance:
            try:
                self.ctc_instance.close()
                self.ctc_instance = None
                
                # Restore mock communication handler
                self.communication_handler = MockCommunicationHandler()
                self.communication_handler.ui_callback = self.handle_communication_event
                
                # Re-register wayside controllers for current line
                self.update_wayside_controllers_for_line()
                
                # Update UI
                self.start_ctc_btn.setEnabled(True)
                self.stop_ctc_btn.setEnabled(False)
                self.ctc_status_label.setText("CTC Status: Not Running")
                self.ctc_status_label.setStyleSheet("color: red; font-weight: bold;")
                
                self.message_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] System: CTC system stopped")
                
            except Exception as e:
                self.show_message("Error", f"Error stopping CTC system: {str(e)}")
    
    def show_message(self, title, message):
        """Show a styled message box"""
        msg_box = StyledMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec_()
    
    def _register_wayside_controllers_with_ctc(self):
        """Register wayside controllers with actual CTC system"""
        if not self.ctc_instance:
            return
            
        selected_line = self.line_selection.currentText()
        
        # Determine which controllers to register based on selected line
        if selected_line == "Blue Line":
            controllers_to_register = ['Blue_A', 'Blue_B']
        else:  # Green/Red Line
            controllers_to_register = ['Red_A', 'Red_B', 'Green_A', 'Green_B']
        
        # Register controllers with CTC system using provide_wayside_controller()
        for controller_id in controllers_to_register:
            if controller_id in self.wayside_controllers:
                controller = self.wayside_controllers[controller_id]
                # Access the CTC system through the CTCInterface
                if hasattr(self.ctc_instance, 'ctc_system'):
                    self.ctc_instance.ctc_system.provide_wayside_controller(controller, controller.blocks_covered)
                    self.message_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] System: Registered {controller_id} with CTC")
                else:
                    logger.error(f"CTCInterface does not have ctc_system attribute")
        
        logger.info(f"Registered {len(controllers_to_register)} wayside controllers with CTC system")
    
    def update_wayside_controllers_for_line(self):
        """Update wayside controllers based on selected line (for UI display only)"""
        selected_line = self.line_selection.currentText() if hasattr(self, 'line_selection') else "Blue Line"
        
        # Update UI combo boxes for the selected line
        if selected_line == "Blue Line":
            controllers_to_register = ['Blue_A', 'Blue_B']
        else:  # Green/Red Line
            controllers_to_register = ['Red_A', 'Red_B', 'Green_A', 'Green_B']
        
        # Update combo box in wayside tab
        if hasattr(self, 'controller_combo'):
            self.controller_combo.clear()
            self.controller_combo.addItems(controllers_to_register)
        
        # Update combo box in CTC output tab
        if hasattr(self, 'block_controller_combo'):
            self.block_controller_combo.clear()
            self.block_controller_combo.addItems(controllers_to_register)
        
        # Update displays to reflect new line selection
        if hasattr(self, 'controller_combo'):
            self.update_wayside_display()
        if hasattr(self, 'block_commands_table'):
            self.update_block_commands_table()
    
    def on_line_selection_changed(self, text):
        """Handle line selection change"""
        # Update wayside controllers
        self.update_wayside_controllers_for_line()
        
        # Stop CTC if running (need to restart with new line)
        if self.ctc_instance:
            self.stop_ctc_system()
            self.show_message("Line Changed", f"CTC system stopped. Please restart for {text}.")
        
        # Update throughput display to show only selected lines
        self.update_throughput_display()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    # Set application style to match main CTC interface
    app.setStyle('Fusion')
    
    # Set default font for the entire application
    default_font = QFont()
    default_font.setPointSize(11)
    app.setFont(default_font)
    
    # Create and show window
    window = CTCCommunicationTestUI()
    
    # Set up global master interface instance for get_time() function
    if MASTER_INTERFACE_AVAILABLE and window.time_manager:
        import Master_Interface.master_control as master_control
        master_control._master_interface_instance = window
        
        # Add get_time method to window for compatibility
        def get_time_method():
            if window.time_manager and window.time_manager.is_running:
                return datetime.combine(datetime.now().date(), 
                                      dt_time.fromisoformat(window.current_time + ":00"))
            return datetime.now()
        window.get_time = get_time_method
    
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()