import sys
import os
import threading
import time  # Keep for performance timing only  
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QFileDialog, QPushButton, QComboBox, QTextEdit, QSizePolicy,
    QLineEdit, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer
from track_reader import TrackLayoutReader, TrackBlock
from Inputs import TrackModelInputs
from Outputs import get_16bit_track_model_output  # Import from Outputs.py

# Master Interface Time Integration
try:
    from Master_Interface.master_control import get_time
    MASTER_TIME_AVAILABLE = True
except ImportError:
    MASTER_TIME_AVAILABLE = False
    # Fallback function if Master Interface not available
    def get_time():
        return datetime.now()

# --- Debug Terminal Singleton ---
class DebugTerminal(QTextEdit):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DebugTerminal, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self.setReadOnly(True)
        self.setStyleSheet("font-family: Consolas; font-size: 11pt;")
        self.setLineWrapMode(QTextEdit.NoWrap)
        self._initialized = True

    @staticmethod
    def log(message):
        instance = DebugTerminal._instance or DebugTerminal()
        timestamp = get_time().strftime("%H:%M:%S")
        instance.append(f"{timestamp} {message}")

# --- Debug Window ---
class DebugWindow(QWidget):
    def __init__(self, inputs: TrackModelInputs):
        super().__init__()
        self.inputs = inputs
        self.setVisible(False)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Inputs panel
        self.inputs_label = QLabel(self.generate_inputs_text())
        self.inputs_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.inputs_label.setStyleSheet("font-family: Arial; font-size: 11pt;")
        self.inputs_label.setMinimumWidth(280)
        self.inputs_label.setWordWrap(True)

        # Outputs panel
        self.outputs_label = QLabel(self.generate_outputs_text())
        self.outputs_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.outputs_label.setStyleSheet("font-family: Arial; font-size: 11pt;")
        self.outputs_label.setMinimumWidth(280)
        self.outputs_label.setWordWrap(True)

        # --- Bit structure display and button under Outputs ---
        self.bits_display = QLabel("Output Bits: ")
        self.bits_display.setAlignment(Qt.AlignLeft)
        self.bits_display.setStyleSheet("font-family: Consolas; font-size: 12pt; color: #333333;")
        self.bits_display.setWordWrap(True)

        self.gen_bits_button = QPushButton("Generate bit structure")
        self.gen_bits_button.setStyleSheet("font-size: 11pt; font-family: Arial;")
        self.gen_bits_button.clicked.connect(self.display_bits)

        # Terminal panel (center)
        self.terminal = DebugTerminal()

        # Layouts
        left = QVBoxLayout()
        left.addWidget(QLabel("<b>Inputs</b>"))
        left.addWidget(self.inputs_label)

        center = QVBoxLayout()
        center.addWidget(QLabel("<b>Debug Terminal</b>"))
        center.addWidget(self.terminal)

        right = QVBoxLayout()
        right.addWidget(QLabel("<b>Outputs</b>"))
        right.addWidget(self.bits_display)
        right.addWidget(self.gen_bits_button)
        right.addWidget(self.outputs_label)

        layout = QHBoxLayout()
        layout.addLayout(left, 1)
        layout.addLayout(center, 2)
        layout.addLayout(right, 1)
        self.setLayout(layout)

        # Start background update thread for inputs/outputs texts
        threading.Thread(target=self.update_loop, daemon=True).start()

    def display_bits(self):
        bits = get_16bit_track_model_output()
        self.bits_display.setText(f"Output Bits: {bits}")

    def update_loop(self):
        # Convert to QTimer-based updates instead of blocking thread
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(2000)  # Update every 2 seconds
    
    def update_display(self):
        """Update display labels - called by QTimer"""
        self.inputs_label.setText(self.generate_inputs_text())
        self.outputs_label.setText(self.generate_outputs_text())

    def generate_inputs_text(self):
        # Summarize block failures as a comma-separated list of block IDs with active failures
        def summarize_map(data_map):
            active = [str(k) for k, v in data_map.items() if v]
            return ", ".join(active) if active else "None"

        return (
            f"Train Layout\t{str(self.inputs.get_train_layout()) if self.inputs.get_train_layout() else 'None'}\n"
            f"Temperature\t{self.inputs.get_temperature()}\n"
            f"Broken Rail Failure\t{summarize_map(self.inputs._broken_rail_failure)}\n"
            f"Track Circuit Failure\t{summarize_map(self.inputs._track_circuit_failure)}\n"
            f"Power Failure\t{summarize_map(self.inputs._power_failure)}\n"
            f"Commanded Speed\t\n"
            f"Authority\t\n"
            f"# Blocks Ahead\t\n"
            f"Block Changed Bit\t\n"
            f"Switch Positions\t\n"
            f"Signal (traffic light)\t\n"
            f"Railroad Crossings\t\n"
            f"Train Distance Traveled\t\n"
        )

    def generate_outputs_text(self):
        return (
            f"Authority\n"
            f"Commanded Speed\n"
            f"Next Block #s\n"
            f"Update Previous Bit\n"
            f"Next Station #\n"
        )

    @staticmethod
    def print_to_terminal(message):
        DebugTerminal.log(message)

# --- Info Panel ---
class InfoPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.label = QLabel("Select a block")
        self.label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.label.setWordWrap(True)
        self.label.setStyleSheet("font-size: 18pt; font-family: Arial;")
        self.temp_edit = QLineEdit()
        self.temp_edit.setFixedWidth(120)
        self.temp_edit.setStyleSheet("font-size: 13pt; font-family: Arial;")
        self.temp_edit.setAlignment(Qt.AlignLeft)
        self.temp_edit.setPlaceholderText("Temperature (°F)")
        self.temp_edit.returnPressed.connect(self._try_set_temperature)
        self.temp_edit.editingFinished.connect(self._try_set_temperature)
        self.inputs = None  # Will be set in update_info

        # Simulation clock
        self.clock_label = QLabel("Elapsed Time: 00:00:00")
        self.clock_label.setStyleSheet("font-size: 13pt; font-family: Arial;")
        self.sim_start_time = get_time()

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addStretch()
        layout.addWidget(self.clock_label)
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Temperature:"))
        temp_layout.addWidget(self.temp_edit)
        temp_layout.addWidget(QLabel("°F"))
        temp_layout.addStretch()
        layout.addLayout(temp_layout)
        self.setLayout(layout)

    def _clock_update_loop(self):
        # Convert to QTimer-based updates instead of blocking thread
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock_display)
        self.clock_timer.start(2000)  # Update every 2 seconds
    
    def update_clock_display(self):
        """Update clock display - called by QTimer"""
        elapsed = int((get_time() - self.sim_start_time).total_seconds())
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        seconds = elapsed % 60
        self.clock_label.setText(f"Elapsed Time: {hours:02}:{minutes:02}:{seconds:02}")

    def update_info(self, block: TrackBlock, inputs: TrackModelInputs = None):
        self.inputs = inputs
        info = f"<b>Line:</b> {block.line}<br><b>Section:</b> {block.section}<br>"
        info += f"<b>Block Number:</b> {block.block_number}<br>"
        info += f"<b>Block Length (m):</b> {block.length_m}<br>"
        info += f"<b>Block Grade (%):</b> {block.grade_percent}<br>"
        info += f"<b>Speed Limit (km/h):</b> {block.speed_limit_kmh}<br>"
        info += f"<b>Elevation (m):</b> {block.elevation_m}<br>"
        info += f"<b>Direction:</b> {block.get_direction_description()}<br>"
        info += f"<b>Infrastructure:</b><div style='white-space: pre-wrap; max-width: 380px;'>{block.get_infrastructure_description()}</div><br>"
        if inputs:
            bid = f"{block.line[0].upper()}{block.block_number}"
            info += f"<b>Broken Rail Failure:</b> {'Active' if inputs.get_broken_rail_failure(bid) else 'None'}<br>"
            info += f"<b>Track Circuit Failure:</b> {'Active' if inputs.get_track_circuit_failure(bid) else 'None'}<br>"
            info += f"<b>Power Failure:</b> {'Active' if inputs.get_power_failure(bid) else 'None'}<br>"
            # Set the temperature box to the current value
            temp_val = inputs.get_temperature()
            self.temp_edit.setText(f"{temp_val:.1f}")
        self.label.setText(info)

    def _try_set_temperature(self):
        if self.inputs is None:
            return
        text = self.temp_edit.text().strip().replace("°F", "")
        try:
            value = float(text)
            if not (-25.0 <= value <= 105.0):
                raise ValueError
        except Exception:
            # Only show the popup and reset once
            if self.temp_edit.hasFocus():
                self._show_temp_error()
            self.temp_edit.setText(f"{self.inputs.get_temperature():.1f}")
            return
        # Only update and print if the value is actually different
        if value != self.inputs.get_temperature():
            self.inputs.set_temperature(value)
            self.temp_edit.setText(f"{value:.1f}")
            DebugWindow.print_to_terminal(f"Temperature set to {value:.1f}°F")

    def _show_temp_error(self):
        QMessageBox.warning(self, "Invalid Temperature", "Please only enter numerical values between -25.0 and 105.0")

# --- Clickable Block ---
class ClickableBox(QFrame):
    def __init__(self, block: TrackBlock, info_panel: QWidget, main_window, inputs: TrackModelInputs):
        super().__init__()
        self.block = block
        self.info_panel = info_panel
        self.main_window = main_window
        self.inputs = inputs
        self.block_id_str = f"{self.block.line[0].upper()}{self.block.block_number}"
        self.setFixedSize(30, 30)
        # Only display the block number (no R/G) for visibility
        self.label = QLabel(str(self.block.block_number))
        self.label.setAlignment(Qt.AlignCenter)
        # Smaller, bold, black text with subtle white shadow for contrast
        self.label.setStyleSheet(
            "font-size: 9pt; font-family: Arial; font-weight: bold; color: #000000;"
        )
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.setFrameShape(QFrame.StyledPanel)
        self.set_failure_color()

    def mousePressEvent(self, event):
        self.info_panel.update_info(self.block, self.inputs)
        self.main_window.set_selected_block(self)

    def set_failure(self, failure_type, failed):
        bid = self.block_id_str
        if failure_type == 'power':
            self.inputs.set_power_failure(bid, failed)
        elif failure_type == 'broken_rail':
            self.inputs.set_broken_rail_failure(bid, failed)
        elif failure_type == 'track_circuit':
            self.inputs.set_track_circuit_failure(bid, failed)
        self.set_failure_color()

    def set_failure_color(self):
        bid = self.block_id_str
        color = "#4CAF50" if self.block.line.lower() == "green" else "#f44336" if self.block.line.lower() == "red" else "salmon"
        if self.inputs.get_power_failure(bid):
            color = "#FB8C00"
        elif self.inputs.get_broken_rail_failure(bid):
            color = "#FFA726"
        elif self.inputs.get_track_circuit_failure(bid):
            color = "#FF9800"
        self.setStyleSheet(
            f"background-color: {color}; border: 0.5px solid #222; "
            "border-radius: 4px; "
        )
        # Only show the block number (no R/G) for clarity
        self.label.setText(str(self.block.block_number))

# --- Main Window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Track Grid Display")
        self.setGeometry(100, 100, 1200, 800)

        self.inputs = TrackModelInputs()
        self.debug_window = DebugWindow(self.inputs)
        self.info_panel = InfoPanel()
        self.grid_container = QWidget()
        self.grid_container.setMinimumSize(800, 700)
        self.grid_container.setStyleSheet("background-color: white;")
        self.selected_block = None

        self.load_button = QPushButton("Load Track Layout")
        self.power_button = QPushButton("Power Failure")
        self.track_button = QPushButton("Track Circuit Failure")
        self.rail_button = QPushButton("Broken Rail Failure")
        self.toggle_debug_button = QPushButton(">_")
        self.line_selector = QComboBox()
        self.line_selector.addItems(["Green", "Red"])

        for btn in [self.load_button, self.power_button, self.track_button, self.rail_button, self.toggle_debug_button]:
            btn.setStyleSheet("font-size: 13pt; font-family: Arial;")

        hdr = QHBoxLayout()
        hdr.addWidget(self.load_button)
        hdr.addWidget(self.power_button)
        hdr.addWidget(self.track_button)
        hdr.addWidget(self.rail_button)
        hdr.addWidget(QLabel("Line:"))
        hdr.addWidget(self.line_selector)
        hdr.addStretch()
        hdr.addWidget(self.toggle_debug_button)

        row = QHBoxLayout()
        row.addWidget(self.grid_container)
        row.addWidget(self.info_panel)

        main = QVBoxLayout()
        main.addLayout(hdr)
        main.addLayout(row)
        main.addWidget(self.debug_window, stretch=0)

        root = QWidget()
        root.setLayout(main)
        self.setCentralWidget(root)

        self.load_button.clicked.connect(self.load_track_data)
        self.toggle_debug_button.clicked.connect(self.toggle_debug_window)
        self.power_button.clicked.connect(lambda: self.toggle_failure('power'))
        self.track_button.clicked.connect(lambda: self.toggle_failure('track_circuit'))
        self.rail_button.clicked.connect(lambda: self.toggle_failure('broken_rail'))
        self.line_selector.currentTextChanged.connect(self.display_selected_line)
        self.reader = None

        # Hide debug window by default
        self.debug_window.setVisible(False)
        self.debug_window.setMaximumHeight(int(self.height() * 0.3))

        # --- Polling for clock in main event loop ---
        self.last_clock_update = 0

        # Start polling timer
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_events)
        self.poll_timer.start(50)  # Poll 20 times per second for higher responsiveness

    def poll_events(self):
        # Update the InfoPanel clock every 0.1 seconds
        now = time.time()
        if now - self.last_clock_update > 0.1:
            self.last_clock_update = now
            self.update_info_panel_clock()

    def update_info_panel_clock(self):
        elapsed = int((get_time() - self.info_panel.sim_start_time).total_seconds())
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        seconds = elapsed % 60
        self.info_panel.clock_label.setText(f"Elapsed Time: {hours:02}:{minutes:02}:{seconds:02}")

    def resizeEvent(self, event):
        # Keep debug window at ~30% of window height
        self.debug_window.setMaximumHeight(int(self.height() * 0.3))
        super().resizeEvent(event)

    def toggle_debug_window(self):
        vis = not self.debug_window.isVisible()
        self.debug_window.setVisible(vis)

    def load_track_data(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Track Layout Excel", "", "Excel Files (*.xlsx)")
        if not path:
            return
        try:
            self.reader = TrackLayoutReader(path, selected_lines=["Green", "Red"])
            self.display_selected_line()
            DebugWindow.print_to_terminal(f"Loaded: {os.path.basename(path)}")
        except Exception as e:
            DebugWindow.print_to_terminal(f"Error: {e}")

    def display_selected_line(self):
        if not self.reader:
            return
        line = self.line_selector.currentText()
        blocks = self.reader.lines.get(line, [])
        for child in self.grid_container.findChildren(QWidget):
            child.deleteLater()
        spacing = 40
        cols = 10
        for i, blk in enumerate(blocks):
            box = ClickableBox(blk, self.info_panel, main_window=self, inputs=self.inputs)
            box.setParent(self.grid_container)
            row = i // cols
            col = i % cols
            box.move(10 + col * spacing, 10 + row * spacing)
            box.show()
        self.selected_block = None

    def set_selected_block(self, box):
        self.selected_block = box

    def toggle_failure(self, failure_type):
        if self.selected_block:
            bid = self.selected_block.block_id_str
            get = {
                'power': self.inputs.get_power_failure,
                'broken_rail': self.inputs.get_broken_rail_failure,
                'track_circuit': self.inputs.get_track_circuit_failure
            }[failure_type]
            val = get(bid)
            self.selected_block.set_failure(failure_type, not val)
            DebugWindow.print_to_terminal(f"{failure_type.replace('_', ' ').title()} toggled for {bid}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QWidget { font-size: 13pt; font-family: Arial; }
        QPushButton { font-size: 13pt; font-family: Arial; }
        QLabel { font-size: 13pt; font-family: Arial; }
        QGroupBox { font-size: 13pt; font-weight: bold; font-family: Arial; }
    """)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
