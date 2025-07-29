"""
CTC Office Main Application - Modular Architecture
==================================================
Central Traffic Control Office for PAAC Light Rail System
Designed for dispatcher with philosophy background and 3/5 tech comfort

NEW MODULAR STRUCTURE:
- Core/: Business logic and data management
- UI/: User interface components
- Utils/: Helper utilities and workers

Integration with Wayside Controller:
- Sends: Suggested Speed, Authority
- Receives: Train Positions, Train Statuses, Train Speeds, Track Status, Railway Crossings

Author: [Your Name]
Course: ECE 1140 - Train Control System Project
"""

import sys
from PyQt5.QtWidgets import QApplication
from datetime import datetime

# Import the new modular CTC interface
from .UI.ctc_interface import CTCInterface


def create_ctc_office(track_file: str = "Track Layout & Vehicle Data vF2.xlsx"):
	"""Factory function to create CTC Office instance using new modular architecture"""
	return CTCInterface(track_file)


# Wayside Controller Integration API
def send_to_ctc(ctc_interface, message):
	"""
	Send message from Wayside Controller to CTC Interface.
	Enhanced to handle new message types.
	"""
	# Parse message if it's a string
	if isinstance(message, str):
		import json
		try:
			message = json.loads(message)
		except json.JSONDecodeError:
			print(f"Error: Invalid JSON message: {message}")
			return
	
	# Route message based on type
	msg_type = message.get("type")
	
	if msg_type == "train_list":
		# New: Handle comprehensive train list updates
		ctc_interface.communication_handler.receive_train_list(message.get("data", {}))
	elif msg_type == "train_update":
		# Handle single train position updates from UI
		ctc_interface.communication_handler.receive_train_list(message.get("data", {}))
	elif msg_type == "track_status":
		# Handle track status updates (normal/failure)
		ctc_interface.communication_handler.receive_track_status(message.get("data", {}))
	elif msg_type == "switch_position":
		# Handle switch position updates
		ctc_interface.communication_handler.receive_switch_positions(message.get("data", {}))
	elif msg_type == "switch_positions":
		# New: Handle switch position updates (plural form for compatibility)
		ctc_interface.communication_handler.receive_switch_positions(message.get("data", {}))
	elif msg_type == "railway_crossing":
		# Handle railway crossing status updates
		crossing_data = message.get("data", {})
		# Convert from flat format to expected format
		formatted_data = {}
		for key, status in crossing_data.items():
			if "," in key:
				line, block = key.split(",")
				formatted_data[key] = {"line": line, "block": int(block), "status": status}
		ctc_interface.communication_handler.receive_crossing_positions(formatted_data)
	elif msg_type == "crossing_positions":
		# New: Handle railway crossing status updates
		ctc_interface.communication_handler.receive_crossing_positions(message.get("data", {}))
	else:
		# Fallback to original message processing for backward compatibility
		ctc_interface.communication_handler.receive_message(message)


def get_from_ctc(ctc_interface):
	"""Get message from CTC Interface to Wayside Controller"""
	return ctc_interface.communication_handler.get_outgoing_message()


if __name__ == "__main__":
	# Create QApplication
	app = QApplication(sys.argv)
	
	# Set default font for the entire application
	from PyQt5.QtGui import QFont
	default_font = QFont()
	default_font.setPointSize(13)  # Increase default font size
	app.setFont(default_font)
	
	# Set global stylesheet to ensure all widgets use larger fonts
	app.setStyleSheet("""
		QWidget {
			font-size: 13pt;
		}
		QPushButton {
			font-size: 13pt;
		}
		QLabel {
			font-size: 13pt;
		}
		QLineEdit {
			font-size: 13pt;
		}
		QTextEdit {
			font-size: 13pt;
		}
		QComboBox {
			font-size: 13pt;
		}
		QTableWidget {
			font-size: 13pt;
		}
		QTableWidget QHeaderView::section {
			font-size: 13pt;
			font-weight: bold;
		}
		QListWidget {
			font-size: 13pt;
		}
		QGroupBox {
			font-size: 13pt;
			font-weight: bold;
		}
		QTabWidget::tab-bar {
			font-size: 13pt;
		}
		QTabBar::tab {
			font-size: 13pt;
		}
		QMenuBar {
			font-size: 13pt;
		}
		QMenu {
			font-size: 13pt;
		}
		QStatusBar {
			font-size: 13pt;
		}
	""")

	# Create and show CTC Interface using new modular architecture
	ctc = create_ctc_office()
	ctc.show()

	# Run the application
	sys.exit(app.exec_())