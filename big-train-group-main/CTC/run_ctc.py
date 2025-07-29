#!/usr/bin/env python3
"""
Simple runner script for the CTC interface
"""
import sys
import os
import argparse

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)
sys.path.insert(0, current_dir)

from PyQt5.QtWidgets import QApplication
from CTC.UI.ctc_interface import CTCInterface

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Run CTC Interface with specific line(s)')
    parser.add_argument('--lines', '-l', 
                       type=str,
                       default='Blue',
                       help='Comma-separated list of lines to load (default: Blue)')
    parser.add_argument('--track-file', '-f',
                       default="Track_Reader/Track Layout & Vehicle Data vF2.xlsx",
                       help='Path to track layout file')
    parser.add_argument('--time-multiplier', '-t',
                       type=float,
                       default=1.0,
                       help='Time acceleration multiplier (1.0 to 10.0, default: 1.0)')
    return parser.parse_args()

if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()
    
    # Process lines argument (convert comma-separated string to list)
    if isinstance(args.lines, str):
        lines_list = [line.strip() for line in args.lines.split(',')]
    else:
        lines_list = args.lines
    
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
    
    # Create and show CTC Interface with specified lines and time multiplier
    ctc = CTCInterface(track_file=args.track_file, selected_lines=lines_list, time_multiplier=args.time_multiplier)
    ctc.show()
    
    print(f"CTC Interface is now running with lines: {', '.join(lines_list)}")
    print(f"Time multiplier set to: {args.time_multiplier}x")
    print("You should see the CTC control window open.")
    
    # Run the application
    sys.exit(app.exec_())