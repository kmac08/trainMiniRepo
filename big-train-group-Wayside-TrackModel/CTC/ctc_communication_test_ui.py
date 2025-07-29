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

def _get_simulation_time():
    """Get simulation time with lazy import to avoid circular dependencies"""
    try:
        from Master_Interface.master_control import get_time
        return get_time()
    except ImportError:
        from datetime import datetime
        return datetime.now()

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
from Master_Interface.master_control import TimeManager
MASTER_INTERFACE_AVAILABLE = True

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
        self.railway_crossings = {}  # crossing_id -> active mp(True/False)
        
        # Track commands received
        self.last_train_commands = {}
        self.last_switch_commands = {}
    
    def command_train(self, suggestedSpeed: List[int], authority: List[int], blockNum: List[int], 
                     updateBlockInQueue: List[bool], nextStation: List[int], blocksAway: List[int]):
        """Receive block-specific train commands from CTC
        
        CTC sends commands for entire line to all wayside controllers.
        This controller receives the full line information and stores it.
        """
        # Enhanced debugging output
        timestamp = _get_simulation_time().strftime("%H:%M:%S.%f")[:-3]
        print(f"[WAYSIDE_RECEIVED] {timestamp} - Controller: {self.controller_id} - Function: command_train()")
        print(f"  Full Line Commands - Total Blocks: {len(blockNum)}")
        print(f"  Blocks: {blockNum}")
        print(f"  Speeds: {suggestedSpeed}")
        print(f"  Authority: {authority}")
        print(f"  Update Flags: {updateBlockInQueue}")
        print(f"  Next Stations: {nextStation}")
        print(f"  Blocks Away: {blocksAway}")
        
        # Show which blocks this controller actually manages
        if hasattr(self, 'blocks_covered_bool') and self.blocks_covered_bool:
            managed_blocks = [i for i, is_managed in enumerate(self.blocks_covered_bool) if is_managed]
            print(f"  Controller {self.controller_id} manages blocks: {managed_blocks}")
        
        # Store the FULL line commands (wayside controller receives everything)
        self.last_train_commands = {
            'suggested_speed': suggestedSpeed,
            'authority': authority, 
            'block_num': blockNum,
            'update_block_in_queue': updateBlockInQueue,
            'next_station': nextStation,
            'blocks_away': blocksAway,
            'timestamp': _get_simulation_time()
        }
        
        return True
    
    
    def set_occupied(self, blockList: List[bool]):
        """Receive manual block occupation from CTC"""
        # Enhanced debugging output
        timestamp = _get_simulation_time().strftime("%H:%M:%S.%f")[:-3]
        print(f"[WAYSIDE_RECEIVED] {timestamp} - Controller: {self.controller_id} - Function: set_occupied()")
        print(f"  Block List: {blockList}")
        
        # Show which blocks are being affected
        affected_blocks = []
        
        # ENFORCES NEW COMMUNICATION PROTOCOL: blocks_covered_bool is required
        if not hasattr(self, 'blocks_covered_bool') or not self.blocks_covered_bool:
            error_msg = f"PROTOCOL VIOLATION: Controller {self.controller_id} missing blocks_covered_bool attribute. New protocol requires all controllers to have this attribute."
            print(f"  ERROR: {error_msg}")
            raise ValueError(error_msg)
        
        # Process using blocks_covered_bool - blockList is indexed by block number
        for block_num in range(len(blockList)):
            if block_num < len(self.blocks_covered_bool) and self.blocks_covered_bool[block_num]:
                # This controller manages this block
                old_state = self.block_occupancy.get(block_num, False)
                new_state = blockList[block_num]
                if old_state != new_state:
                    affected_blocks.append(f"Block {block_num}: {old_state} -> {new_state}")
                self.block_occupancy[block_num] = new_state
        
        if affected_blocks:
            print(f"  Changes: {affected_blocks}")
        else:
            print(f"  No occupation changes")
            
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
    
    def provide_wayside_controller(self, waysideController: MockWaysideController, blocksCovered: List[bool], redLine: bool):
        """Called by wayside to register controller and its blocks
        
        NEW SIGNATURE: blocksCovered is now a List[bool] and redLine indicates line.
        """
        self.wayside_controllers.append(waysideController)
        
        # Convert boolean list to actual block numbers for internal use
        managed_blocks = [i for i, is_managed in enumerate(blocksCovered) if is_managed]
        
        # Store both the boolean list and line information on the controller for later use  
        waysideController.blocks_covered_bool = blocksCovered
        waysideController.red_line = redLine
        waysideController.managed_blocks = managed_blocks
        
        # Map blocks to controller
        for block in managed_blocks:
            self.block_to_controller[block] = waysideController
        waysideController.communication_handler = self
        
        line_name = "Red" if redLine else "Green"
        print(f"MockCommunicationHandler: Registered {waysideController.controller_id} for {line_name} line covering blocks {managed_blocks}")
        
        if self.ui_callback:
            self.ui_callback('wayside_registered', {
                'controller_id': waysideController.controller_id,
                'blocks': managed_blocks,
                'line': line_name
            })
    
    def update_occupied_blocks(self, occupiedBlocks: List[bool], sending_controller=None):
        """Receive occupation status from wayside controller"""
        self.last_occupied_blocks = occupiedBlocks
        if self.ui_callback:
            self.ui_callback('occupied_blocks_update', {
                'blocks': occupiedBlocks,
                'sender': getattr(sending_controller, 'controller_id', 'Unknown') if sending_controller else None
            })
    
    def update_switch_positions(self, switchPositions: List[bool], sending_controller=None):
        """Receive switch positions from wayside controller"""
        self.last_switch_positions = switchPositions
        if self.ui_callback:
            self.ui_callback('switch_positions_update', {
                'switches': switchPositions,
                'sender': getattr(sending_controller, 'controller_id', 'Unknown') if sending_controller else None
            })
    
    def update_railway_crossings(self, railwayCrossings: List[bool], sending_controller=None):
        """
        Receive crossing status from wayside controller
        
        railwayCrossings is a block-length array for the line.
        Only blocks with railway crossings have meaningful values.
        """
        self.last_railway_crossings = railwayCrossings
        if self.ui_callback:
            self.ui_callback('railway_crossings_update', {
                'crossings': railwayCrossings,
                'sender': getattr(sending_controller, 'controller_id', 'Unknown') if sending_controller else None
            })
    
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
            block_nums = []
            update_flags = []
            next_stations = []
            blocks_away = []
            
            for i, block in enumerate(controller.blocks_covered):
                # Sample logic: occupied blocks get stop command
                if controller.block_occupancy.get(block, False):
                    suggested_speeds.append(0)  # Stop
                    authorities.append(0)       # No authority
                else:
                    suggested_speeds.append(3)  # Full speed
                    authorities.append(1)       # Full authority
                block_nums.append(block)
                update_flags.append(0)  # New command
                next_stations.append(0)  # No station info
                blocks_away.append(i + 1)  # Distance from current position
            
            controller.command_train(suggested_speeds, authorities, block_nums, update_flags, next_stations, blocks_away)
            
            if self.ui_callback:
                self.ui_callback('train_commands_sent', {
                    'controller': controller.controller_id,
                    'commands': {
                        'suggested_speeds': suggested_speeds,
                        'authorities': authorities,
                        'block_nums': block_nums
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
        
        # Create wayside controllers with complete track coverage
        # All A controllers include block 0 (yard) to indicate they control the yard
        self.wayside_controllers = {
            'Blue_A': MockWaysideController('Blue_A', list(range(0, 16))),  # Complete Blue Line (blocks 0-15, covers actual 1-15)
            'Red_A': MockWaysideController('Red_A', list(range(0, 39))),  # Red Line first half (blocks 0-38, covers actual 1-38)
            'Red_B': MockWaysideController('Red_B', list(range(39, 77))),  # Red Line second half (blocks 39-76, covers actual 39-76)
            'Green_A': MockWaysideController('Green_A', list(range(0, 76))),  # Green Line first half (blocks 0-75, covers actual 1-75)
            'Green_B': MockWaysideController('Green_B', list(range(76, 151)))  # Green Line second half (blocks 76-150, covers actual 76-150)
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
        self.create_ctc_commands_tab()
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
    
    def create_ctc_commands_tab(self):
        """Create dedicated CTC commands monitoring tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Header with current time
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Live CTC Command Monitoring"))
        header_layout.addStretch()
        self.ctc_commands_time_label = QLabel("Simulation Time: 05:00")
        self.ctc_commands_time_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(self.ctc_commands_time_label)
        layout.addLayout(header_layout)
        
        # Commands table
        commands_group = QGroupBox("Recent CTC Function Calls")
        commands_layout = QVBoxLayout(commands_group)
        
        self.ctc_commands_table = QTableWidget()
        self.ctc_commands_table.setColumnCount(5)
        self.ctc_commands_table.setHorizontalHeaderLabels([
            'Time', 'Function', 'Controller', 'Parameters', 'Status'
        ])
        self.ctc_commands_table.horizontalHeader().setStretchLastSection(True)
        self.ctc_commands_table.setAlternatingRowColors(True)
        self.ctc_commands_table.setEditTriggers(QTableWidget.NoEditTriggers)
        commands_layout.addWidget(self.ctc_commands_table)
        
        # Control buttons
        control_layout = QHBoxLayout()
        clear_commands_btn = QPushButton("Clear Commands Log")
        clear_commands_btn.clicked.connect(self.clear_ctc_commands)
        control_layout.addWidget(clear_commands_btn)
        
        self.auto_scroll_commands_check = QCheckBox("Auto-scroll to latest")
        self.auto_scroll_commands_check.setChecked(True)
        control_layout.addWidget(self.auto_scroll_commands_check)
        control_layout.addStretch()
        commands_layout.addLayout(control_layout)
        
        layout.addWidget(commands_group)
        
        # Yard departure sequence tracking
        yard_group = QGroupBox("Yard Departure Command Sequence")
        yard_layout = QVBoxLayout(yard_group)
        
        self.yard_sequence_text = QTextEdit()
        self.yard_sequence_text.setReadOnly(True)
        self.yard_sequence_text.setMaximumHeight(150)
        self.yard_sequence_text.setFont(QFont("Monaco", 10))
        yard_layout.addWidget(self.yard_sequence_text)
        
        layout.addWidget(yard_group)
        
        # Initialize command tracking lists
        self.recent_ctc_commands = []
        self.yard_departure_sequence = []
        
        self.tabs.addTab(widget, "CTC Commands")
    
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
            
            # Block number (show "Yard" for block 0)
            block_display = "Yard" if block == 0 else str(block)
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
            return []
        else:  # Green/Red Line
            if controller_id == "Red_B":  # Blocks 25-44, contains block 47
                # Note: Block 47 is beyond Red_B range, but let's include for demonstration
                return []
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
    
    def _get_line_length_for_controller(self, controller_id: str) -> int:
        """
        Get the total line length (number of blocks) for a controller's line using dynamic logic
        
        Args:
            controller_id: ID of the controller (e.g., 'Red_A', 'Green_B', 'Blue_A')
            
        Returns:
            Total number of blocks on the line
        """
        # Determine line name from controller ID
        if controller_id.startswith('Red_'):
            line_name = 'Red'
        elif controller_id.startswith('Green_'):
            line_name = 'Green'
        elif controller_id.startswith('Blue_'):
            line_name = 'Blue'
        else:
            raise ValueError(f"Unknown controller prefix for {controller_id}")
        
        # Use the same dynamic logic as the communication handler
        return self._get_dynamic_line_length(line_name)
    
    def _create_line_length_array(self, controller, controller_data: dict, line_length: int) -> List[bool]:
        """
        Create a line-length array from controller-specific data
        
        Args:
            controller: Controller object with blocks_covered attribute
            controller_data: Dict mapping block numbers to boolean values for blocks this controller manages
            line_length: Total number of blocks on the line
            
        Returns:
            List of boolean values with length = line_length, where:
            - Index i corresponds to block i
            - True/False values are set for blocks the controller manages
            - False is set for all blocks the controller doesn't manage
        """
        # Initialize array with False for all blocks
        line_array = [False] * line_length
        
        # Set values for blocks this controller manages
        if hasattr(controller, 'blocks_covered'):
            for block_num in controller.blocks_covered:
                if 0 <= block_num < line_length:
                    # Set the value from controller_data, defaulting to False
                    line_array[block_num] = controller_data.get(block_num, False)
        
        return line_array
    
    def send_occupancy_update(self):
        """Send occupancy update from current controller using block-length arrays"""
        controller_id = self.controller_combo.currentText()
        if controller_id not in self.wayside_controllers:
            return
        
        controller = self.wayside_controllers[controller_id]
        
        # Get the line length for this controller
        line_length = self._get_line_length_for_controller(controller_id)
        
        # Create line-length array from controller's block occupancy data
        occupancy_line_array = self._create_line_length_array(
            controller, 
            controller.block_occupancy, 
            line_length
        )
        
        # Debug output for protocol compliance
        print(f"[PROTOCOL_FIX] Controller {controller_id} sending block-length occupancy array:")
        print(f"  Controller manages blocks: {controller.blocks_covered}")
        print(f"  Line length: {line_length} blocks")
        print(f"  Sending array length: {len(occupancy_line_array)}")
        print(f"  Occupied blocks (True indices): {[i for i, occupied in enumerate(occupancy_line_array) if occupied]}")
        
        # Pass the controller object as the sender
        self.communication_handler.update_occupied_blocks(occupancy_line_array, sending_controller=controller)
        self.statusBar().showMessage(f"Sent block-length occupancy update from {controller_id} ({len(occupancy_line_array)} blocks)")
    
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
        """Send switch position update from current controller"""
        controller_id = self.controller_combo.currentText()
        if controller_id not in self.wayside_controllers:
            return
        
        controller = self.wayside_controllers[controller_id]
        line_length = self._get_line_length_for_controller(controller_id)
        
        # Get switch positions from UI
        switch_data = {}
        for i in range(self.switch_table.rowCount()):
            reverse_check = self.switch_table.cellWidget(i, 2)
            if reverse_check and isinstance(reverse_check, QCheckBox):
                switch_data[i] = reverse_check.isChecked()
        
        # Create line-length array for switch positions
        switch_line_array = self._create_line_length_array(controller, switch_data, line_length)
        
        # Debug output for protocol compliance
        print(f"[PROTOCOL_FIX] Controller {controller_id} sending block-length switch array:")
        print(f"  Controller manages blocks: {controller.blocks_covered}")
        print(f"  Line length: {line_length} blocks")
        print(f"  Sending array length: {len(switch_line_array)}")
        
        # Pass the controller object as the sender
        self.communication_handler.update_switch_positions(switch_line_array, sending_controller=controller)
        self.statusBar().showMessage(f"Sent switch position update from {controller_id}")
    
    def send_crossing_update(self):
        """Send railway crossing update from current controller"""
        controller_id = self.controller_combo.currentText()
        if controller_id not in self.wayside_controllers:
            return
        
        controller = self.wayside_controllers[controller_id]
        line_length = self._get_line_length_for_controller(controller_id)
        
        # Get crossing data from UI
        crossing_data = {}
        for i in range(self.crossing_table.rowCount()):
            check_widget = self.crossing_table.cellWidget(i, 1)
            if check_widget:
                check = check_widget.findChild(QCheckBox)
                if check:
                    crossing_data[i] = check.isChecked()
        
        # Create line-length array for railway crossings
        crossing_line_array = self._create_line_length_array(controller, crossing_data, line_length)
        
        # Debug output for protocol compliance
        print(f"[PROTOCOL_FIX] Controller {controller_id} sending block-length crossing array:")
        print(f"  Controller manages blocks: {controller.blocks_covered}")
        print(f"  Line length: {line_length} blocks")
        print(f"  Sending array length: {len(crossing_line_array)}")
        
        # Pass the controller object as the sender
        self.communication_handler.update_railway_crossings(crossing_line_array, sending_controller=controller)
        self.statusBar().showMessage(f"Sent railway crossing update from {controller_id}")
    
    def purchase_tickets(self):
        """Simulate ticket purchase"""
        line = self.ticket_line.currentText()
        num_tickets = self.ticket_spin.value()
        self.communication_handler.tickets_purchased(line, num_tickets)
        self.statusBar().showMessage(f"Purchased {num_tickets} tickets for {line} Line")
    
    
    def handle_communication_event(self, event_type: str, data: dict):
        """Handle communication events"""
        timestamp = _get_simulation_time().strftime("%H:%M:%S.%f")[:-3]
        
        # Enhanced logging for CTC function calls
        if event_type in ['train_commands_sent', 'switch_commands_sent', 'manual_occupation_set']:
            # These are CTC function calls - make them prominent
            if event_type == 'train_commands_sent':
                function_name = "command_train()"
            elif event_type == 'switch_commands_sent':
                function_name = "switch_position_update()"
            else:  # manual_occupation_set
                function_name = "set_occupied()"
            
            message = f"[{timestamp}] *** CTC FUNCTION CALL *** {function_name}: {json.dumps(data, indent=2)}"
            print(f"\n=== CTC COMMAND EXECUTED ===\n{message}\n========================\n")  # Console output for visibility
            
            # Track in CTC commands table
            if not hasattr(self, 'recent_ctc_commands'):
                self.recent_ctc_commands = []
            
            # Extract controller and parameters for table
            controller = data.get('controller', 'Unknown')
            if event_type == 'train_commands_sent':
                params = f"Blocks: {data.get('commands', {}).get('blockNum', [])}, Speeds: {data.get('commands', {}).get('suggestedSpeed', [])}"
            elif event_type == 'switch_commands_sent':
                params = f"Positions: {data.get('positions', [])}"
            else:  # set_occupied
                params = f"Blocks: {data.get('blocks', [])}"
            
            self.recent_ctc_commands.append({
                'time': timestamp,
                'function': function_name,
                'controller': controller,
                'parameters': params,
                'status': 'Executed'
            })
            
            # Track yard departure sequences
            if "Departure command" in message:
                self.track_yard_departure_sequence(message)
        else:
            # Regular message
            message = f"[{timestamp}] {event_type}: {json.dumps(data, indent=2)}"
        
        self.message_log.append(message)
        
        # Update displays based on event type
        if event_type == 'tickets_purchased':
            self.update_throughput_display()
        elif event_type in ['train_commands_sent', 'switch_commands_sent', 'manual_occupation_set']:
            self.update_command_displays()
            # Also update the block commands table
            self.update_block_commands_table()
            # Update CTC commands table
            self.update_ctc_commands_table()
        
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
                        except Exception:
                            # Error parsing throughput data - skip entry
                            continue
            
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
            # Block number (show "Yard" for block 0)
            block_display = "Yard" if block == 0 else str(block)
            self.block_commands_table.setItem(i, 0, QTableWidgetItem(block_display))
            
            # Command block (the block the command is targeting)
            # The command block should be the block number at position i in the command list
            if controller.last_train_commands and 'block_num' in controller.last_train_commands:
                cmd_blocks = controller.last_train_commands['block_num']
                if i < len(cmd_blocks):
                    cmd_block_num = cmd_blocks[i]
                    cmd_block_display = "Yard" if cmd_block_num == 0 else str(cmd_block_num)
                    self.block_commands_table.setItem(i, 1, QTableWidgetItem(cmd_block_display))
                else:
                    self.block_commands_table.setItem(i, 1, QTableWidgetItem("-"))
            else:
                self.block_commands_table.setItem(i, 1, QTableWidgetItem("-"))
            
            # Occupied status
            occupied = controller.block_occupancy.get(block, False)
            occupied_item = QTableWidgetItem("Yes" if occupied else "No")
            occupied_item.setBackground(QColor("#FFE6E6") if occupied else QColor("#E6FFE6"))
            self.block_commands_table.setItem(i, 2, occupied_item)
            
            # Commands from last train command
            if controller.last_train_commands:
                cmd = controller.last_train_commands
                
                # Use the position i directly to get command data
                # Each row i corresponds to position i in the command arrays
                if i < len(cmd.get('suggested_speed', [])) and i < len(cmd.get('block_num', [])):
                    # Speed command
                    speed_val = cmd['suggested_speed'][i]
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
                    auth_val = cmd['authority'][i]
                    auth_text = "Granted" if auth_val else "Denied"
                    auth_item = QTableWidgetItem(auth_text)
                    auth_item.setBackground(QColor("#E6FFE6") if auth_val else QColor("#FFE6E6"))
                    self.block_commands_table.setItem(i, 4, auth_item)
                    
                    # Update flag
                    update_flag = cmd.get('update_block_in_queue', [0])[i] if i < len(cmd.get('update_block_in_queue', [])) else 0
                    update_text = "Update" if update_flag else "New"
                    self.block_commands_table.setItem(i, 5, QTableWidgetItem(update_text))
                    
                    # Next station
                    next_station = cmd.get('next_station', [0])[i] if i < len(cmd.get('next_station', [])) else 0
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
    
    def clear_ctc_commands(self):
        """Clear the CTC commands log"""
        if hasattr(self, 'recent_ctc_commands'):
            self.recent_ctc_commands.clear()
        if hasattr(self, 'yard_departure_sequence'):
            self.yard_departure_sequence.clear()
        if hasattr(self, 'ctc_commands_table'):
            self.ctc_commands_table.setRowCount(0)
        if hasattr(self, 'yard_sequence_text'):
            self.yard_sequence_text.clear()
    
    def update_ctc_commands_table(self):
        """Update the CTC commands table with recent commands"""
        if not hasattr(self, 'ctc_commands_table'):
            return
            
        # Show last 50 commands
        commands_to_show = self.recent_ctc_commands[-50:] if hasattr(self, 'recent_ctc_commands') else []
        
        self.ctc_commands_table.setRowCount(len(commands_to_show))
        
        for i, cmd in enumerate(commands_to_show):
            self.ctc_commands_table.setItem(i, 0, QTableWidgetItem(cmd['time']))
            self.ctc_commands_table.setItem(i, 1, QTableWidgetItem(cmd['function']))
            self.ctc_commands_table.setItem(i, 2, QTableWidgetItem(cmd['controller']))
            self.ctc_commands_table.setItem(i, 3, QTableWidgetItem(cmd['parameters']))
            self.ctc_commands_table.setItem(i, 4, QTableWidgetItem(cmd['status']))
            
            # Color-code by function type
            if 'command_train' in cmd['function']:
                for j in range(5):
                    self.ctc_commands_table.item(i, j).setBackground(QColor("#E6FFE6"))  # Light green
            elif 'switch_position' in cmd['function']:
                for j in range(5):
                    self.ctc_commands_table.item(i, j).setBackground(QColor("#E6F3FF"))  # Light blue
            elif 'set_occupied' in cmd['function']:
                for j in range(5):
                    self.ctc_commands_table.item(i, j).setBackground(QColor("#FFE6E6"))  # Light red
        
        # Auto-scroll to bottom if enabled
        if hasattr(self, 'auto_scroll_commands_check') and self.auto_scroll_commands_check.isChecked():
            self.ctc_commands_table.scrollToBottom()
    
    def track_yard_departure_sequence(self, message):
        """Track yard departure command sequences"""
        if not hasattr(self, 'yard_departure_sequence'):
            self.yard_departure_sequence = []
            
        if "Departure command" in message:
            self.yard_departure_sequence.append(message)
            
            # Keep only recent sequences (last 20 commands)
            if len(self.yard_departure_sequence) > 20:
                self.yard_departure_sequence = self.yard_departure_sequence[-20:]
            
            # Update yard sequence display
            if hasattr(self, 'yard_sequence_text'):
                sequence_text = "\n".join(self.yard_departure_sequence)
                self.yard_sequence_text.setText(sequence_text)
                self.yard_sequence_text.moveCursor(self.yard_sequence_text.textCursor().End)
    
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
            # Invalid time format - ignore
            return
    
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
        
        # Update CTC commands tab time display
        if hasattr(self, 'ctc_commands_time_label'):
            self.ctc_commands_time_label.setText(f"Simulation Time: {time_str}")
        
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
            controllers_to_register = ['Blue_A']  # Blue_B removed (blocks don't exist)
        else:  # Green/Red Line
            controllers_to_register = ['Red_A', 'Red_B', 'Green_A', 'Green_B']
        
        # Register controllers with CTC system using provide_wayside_controller()
        communication_handler_received = False
        for controller_id in controllers_to_register:
            if controller_id in self.wayside_controllers:
                controller = self.wayside_controllers[controller_id]
                # Access the CTC system through the CTCInterface
                if hasattr(self.ctc_instance, 'ctc_system'):
                    # Convert block numbers to boolean coverage format and determine line
                    blocks_covered_bool = self._convert_blocks_to_boolean_coverage(controller.blocks_covered)
                    red_line = controller_id.startswith('Red_')
                    
                    # Get the CommunicationHandler reference from registration
                    communication_handler = self.ctc_instance.ctc_system.provide_wayside_controller(
                        controller, blocks_covered_bool, red_line)
                    if communication_handler and not communication_handler_received:
                        # Replace the mock handler with the real CTC communication handler (only once)
                        self.communication_handler = communication_handler
                        # Set UI callback if the real handler supports it
                        if hasattr(self.communication_handler, 'ui_callback'):
                            self.communication_handler.ui_callback = self.handle_communication_event
                        communication_handler_received = True
                        self.message_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] System: Switched to real CTC communication handler")
                    
                    if communication_handler:
                        self.message_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] System: Registered {controller_id} with CTC")
                    else:
                        logger.error(f"Failed to get communication handler for {controller_id}")
                        self.message_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] Error: Failed to register {controller_id}")
                else:
                    logger.error(f"CTCInterface does not have ctc_system attribute")
        
        logger.info(f"Registered {len(controllers_to_register)} wayside controllers with CTC system")
    
    def _convert_blocks_to_boolean_coverage(self, blocks_covered: List[int]) -> List[bool]:
        """
        Convert list of block numbers to boolean coverage format using dynamic line length
        
        Args:
            blocks_covered: List of block numbers [0, 1, 2, 5, 6, ...]
            
        Returns:
            Boolean list where index i is True if block i is managed by controller
            [True, True, True, False, False, True, True, ...]
        """
        if not blocks_covered:
            return []
            
        # Determine which line this controller belongs to based on block numbers
        max_block = max(blocks_covered)
        
        # Determine line name from controller ID to get proper line length
        controller_line = None
        for controller_id, controller in self.wayside_controllers.items():
            if controller.blocks_covered == blocks_covered:
                if controller_id.startswith('Red_'):
                    controller_line = 'Red'
                elif controller_id.startswith('Green_'):
                    controller_line = 'Green'
                elif controller_id.startswith('Blue_'):
                    controller_line = 'Blue'
                break
        
        # Use dynamic line length determination (same logic as communication handler)
        coverage_size = self._get_dynamic_line_length(controller_line)
        
        # Create boolean list
        blocks_covered_bool = [False] * coverage_size
        
        # Set True for blocks this controller manages
        for block_num in blocks_covered:
            if 0 <= block_num < coverage_size:
                blocks_covered_bool[block_num] = True
        
        return blocks_covered_bool
    
    def _get_dynamic_line_length(self, line_name: str) -> int:
        """
        Get dynamic line length using the same logic as the communication handler
        
        Priority 1: Use CTC communication handler (when CTC is running)
        Priority 2: Use mock communication handler track_reader (when available)
        Priority 3: Use actual track data from track file (fallback for test UI)
        Priority 4: Error handling - no hardcoded values
        
        Args:
            line_name: Name of the line ('Red', 'Green', 'Blue')
            
        Returns:
            Total number of blocks on the line including yard (block 0)
        """
        # Priority 1: Try to get line length from actual CTC system if available
        if self.ctc_instance and hasattr(self.ctc_instance, 'ctc_system'):
            ctc_system = self.ctc_instance.ctc_system
            if hasattr(ctc_system, 'communicationHandler'):
                comm_handler = ctc_system.communicationHandler
                if hasattr(comm_handler, '_get_line_length'):
                    line_length = comm_handler._get_line_length(line_name)
                    if line_length > 0:  # Valid line length returned
                        print(f"[TEST_UI_DEBUG] Line length for {line_name}: {line_length} blocks (from CTC communication handler)")
                        return line_length
        
        # Priority 2: Use track reader from mock communication handler (if available)
        if hasattr(self, 'communication_handler') and hasattr(self.communication_handler, 'track_reader'):
            track_reader = self.communication_handler.track_reader
            if track_reader and hasattr(track_reader, 'lines'):
                line_blocks = track_reader.lines.get(line_name, [])
                if line_blocks:
                    line_length = len(line_blocks)
                    print(f"[TEST_UI_DEBUG] Line length for {line_name}: {line_length} blocks (from track_reader)")
                    return line_length
        
        # Priority 3: Load track data directly for test purposes (when no CTC is running)
        try:
            import os
            track_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                         "Track_Reader", "Track Layout & Vehicle Data vF2.xlsx")
            if os.path.exists(track_file_path):
                from Track_Reader.track_reader import TrackLayoutReader
                temp_track_reader = TrackLayoutReader(track_file_path, selected_lines=[line_name])
                line_blocks = temp_track_reader.lines.get(line_name, [])
                if line_blocks:
                    line_length = len(line_blocks)
                    print(f"[TEST_UI_DEBUG] Line length for {line_name}: {line_length} blocks (from direct track file read)")
                    return line_length
        except Exception as e:
            print(f"[TEST_UI_DEBUG] Could not read track file directly: {e}")
        
        # Priority 4: No track data available - return error
        error_msg = f"Cannot determine line length for {line_name} - no track data available"
        print(f"[TEST_UI_ERROR] {error_msg}")
        print(f"[TEST_UI_ERROR] CTC available: {self.ctc_instance is not None}")
        print(f"[TEST_UI_ERROR] Communication handler: {hasattr(self, 'communication_handler')}")
        
        # Return 0 to indicate error - calling code should handle this
        return 0
    
    def update_wayside_controllers_for_line(self):
        """Update wayside controllers based on selected line (for UI display only)"""
        selected_line = self.line_selection.currentText() if hasattr(self, 'line_selection') else "Blue Line"
        
        # Update UI combo boxes for the selected line
        if selected_line == "Blue Line":
            controllers_to_register = ['Blue_A']  # Blue_B removed (blocks don't exist)
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