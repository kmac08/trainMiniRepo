"""
CTC UI - Main Interface
======================
PyQt5 GUI interface for the CTC Office application.
Separated from business logic for better modularity.
"""
from datetime import datetime, timedelta
import sys

# Import simulation time (lazy import to avoid circular dependencies)
# from Master_Interface.master_control import get_time


def _get_simulation_time():
    """Get simulation time with lazy import to avoid circular dependencies"""
    try:
        from Master_Interface.master_control import get_time
        return get_time()
    except ImportError:
        # Fallback to regular datetime if Master Interface not available
        from datetime import datetime
        return datetime.now()
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QGridLayout, QTabWidget, QLabel,
                             QPushButton, QLineEdit, QComboBox, QTextEdit, 
                             QListWidget, QFrame, QMessageBox, QTableWidget, 
                             QTableWidgetItem, QSplitter, QHeaderView, QAbstractItemView,
                             QFileDialog, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRegExp
from PyQt5.QtGui import QFont, QFontMetrics, QRegExpValidator, QIntValidator, QColor

# Import visualization components
from .track_visualization import TrackVisualization

# Import UML-compliant core components
from ..Core.ctc_system import CTCSystem
from ..Core.communication_handler import CommunicationHandler
from ..Core.display_manager import DisplayManager
from ..Core.failure_manager import FailureManager
from ..Utils.update_worker import UpdateWorker

# Import track reader
from Track_Reader.track_reader import TrackLayoutReader

# Import visualization libraries for consolidated display functionality
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from typing import Dict, List, Optional, Tuple
import numpy as np


class CTCVisualDisplay:
    """
    Creates visual displays of track layout for dispatcher interface.
    Focuses on clarity and ease of understanding.
    """

    # Color scheme designed for clarity and accessibility
    COLORS = {
        'track_normal': '#333333',  # Dark gray for regular track
        'track_maintenance': '#FF6B6B',  # Red for closed sections
        'station': '#4DABF7',  # Blue for stations
        'switch': '#69DB7C',  # Green for switches
        'crossing': '#FFD43B',  # Yellow for crossings
        'train': '#FF8CC8',  # Pink for trains (high visibility)
        'authority': '#C3FAD5',  # Light green for authority zones
        'background': '#F8F9FA',  # Light gray background
        'grid': '#DEE2E6'  # Grid lines
    }

    def __init__(self, track_reader):
        """Initialize with track layout data"""
        self.track_reader = track_reader

    def create_line_diagram(self, line: str,
                            active_trains: Optional[Dict[int, str]] = None,
                            maintenance_sections: Optional[List[str]] = None,
                            zoom_section: Optional[str] = None) -> plt.Figure:
        """
        Create a visual diagram of a track line.

        Args:
            line: Line name ("Blue", "Red", or "Green")
            active_trains: Dict of {block_number: train_id}
            maintenance_sections: List of sections closed for maintenance
            zoom_section: Optional section letter to zoom into

        Returns:
            matplotlib figure ready for display
        """
        if maintenance_sections is None:
            maintenance_sections = []
        if active_trains is None:
            active_trains = {}

        # Get track blocks
        blocks = self.track_reader.lines.get(line, [])
        if zoom_section:
            blocks = [b for b in blocks if b.section == zoom_section]

        if not blocks:
            return self._create_empty_diagram(f"No track data for {line} Line")

        # Create figure
        fig, ax = plt.subplots(figsize=(16, 8))
        ax.set_facecolor(self.COLORS['background'])

        # Calculate layout
        total_length = sum(b.length_m for b in blocks)
        scale = 1000 / total_length  # Scale to fit in 1000 pixel width

        # Draw track sections
        x_position = 50  # Starting position
        y_base = 400  # Base Y position

        for i, block in enumerate(blocks):
            block_width = block.length_m * scale

            # Determine track color
            if block.section in maintenance_sections:
                track_color = self.COLORS['track_maintenance']
            else:
                track_color = self.COLORS['track_normal']

            # Draw track segment
            track_rect = patches.Rectangle(
                (x_position, y_base - 20),
                block_width, 40,
                facecolor=track_color,
                edgecolor='black',
                linewidth=2
            )
            ax.add_patch(track_rect)

            # Add block number
            ax.text(x_position + block_width / 2, y_base,
                    str(block.block_number),
                    ha='center', va='center',
                    fontsize=14, fontweight='bold',
                    color='white' if track_color == self.COLORS['track_normal'] else 'black')

            # Draw elevation profile
            elevation_y = y_base - 100 - (block.cumulative_elevation_m * 5)
            if i > 0:
                prev_block = blocks[i - 1]
                prev_elevation_y = y_base - 100 - (prev_block.cumulative_elevation_m * 5)
                ax.plot([x_position, x_position],
                        [prev_elevation_y, elevation_y],
                        color='gray', linewidth=1, linestyle='--')

            # Draw infrastructure
            if block.has_station:
                self._draw_station(ax, x_position + block_width / 2, y_base, block.station.name)

            if block.has_switch:
                self._draw_switch(ax, x_position + block_width / 2, y_base)

            if block.has_crossing:
                self._draw_crossing(ax, x_position + block_width / 2, y_base)

            # Draw train if present
            if block.block_number in active_trains:
                self._draw_train(ax, x_position + block_width / 2, y_base,
                                 active_trains[block.block_number])

            # Add section divider
            if i < len(blocks) - 1 and blocks[i + 1].section != block.section:
                ax.axvline(x=x_position + block_width, color='black',
                           linewidth=3, linestyle='-')
                ax.text(x_position + block_width + 5, y_base + 60,
                        f"Section {blocks[i + 1].section}",
                        fontsize=16, fontweight='bold')

            x_position += block_width

        # Add title and labels
        title = f"{line} Line Track Layout"
        if zoom_section:
            title += f" - Section {zoom_section}"
        ax.set_title(title, fontsize=20, fontweight='bold', pad=20)

        # Add legend
        self._add_legend(ax)

        # Configure axes
        ax.set_xlim(0, 1100)
        ax.set_ylim(200, 600)
        ax.set_aspect('equal')
        ax.axis('off')

        # Add grid for easier reading
        ax.grid(True, alpha=0.3, color=self.COLORS['grid'])

        plt.tight_layout()
        return fig

    def _draw_station(self, ax, x: float, y: float, name: str):
        """Draw a station symbol"""
        # Station platform
        station_rect = patches.Rectangle(
            (x - 30, y + 25), 60, 15,
            facecolor=self.COLORS['station'],
            edgecolor='black',
            linewidth=1
        )
        ax.add_patch(station_rect)

        # Station name
        ax.text(x, y + 55, name, ha='center', va='bottom',
                fontsize=12, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor='white',
                          edgecolor=self.COLORS['station']))

    def _draw_switch(self, ax, x: float, y: float):
        """Draw a switch symbol"""
        # Draw switch diamond
        switch_points = np.array([
            [x, y - 35],  # top
            [x + 15, y - 20],  # right
            [x, y - 5],  # bottom
            [x - 15, y - 20]  # left
        ])
        switch_patch = patches.Polygon(
            switch_points,
            facecolor=self.COLORS['switch'],
            edgecolor='black',
            linewidth=2
        )
        ax.add_patch(switch_patch)

        # Add switch label
        ax.text(x, y - 45, 'SW', ha='center', va='top',
                fontsize=11, fontweight='bold')

    def _draw_crossing(self, ax, x: float, y: float):
        """Draw a railway crossing symbol"""
        # Draw crossing X
        crossing_size = 15
        ax.plot([x - crossing_size, x + crossing_size],
                [y - 50, y - 30],
                color=self.COLORS['crossing'], linewidth=4)
        ax.plot([x - crossing_size, x + crossing_size],
                [y - 30, y - 50],
                color=self.COLORS['crossing'], linewidth=4)

        # Add crossing label
        ax.text(x, y - 60, 'RR X-ing', ha='center', va='top',
                fontsize=11, fontweight='bold')

    def _draw_train(self, ax, x: float, y: float, train_id: str):
        """Draw a train symbol"""
        # Train body
        train_rect = patches.Rectangle(
            (x - 25, y - 15), 50, 30,
            facecolor=self.COLORS['train'],
            edgecolor='black',
            linewidth=2
        )
        ax.add_patch(train_rect)

        # Train ID
        ax.text(x, y, train_id, ha='center', va='center',
                fontsize=11, fontweight='bold', color='white')

        # Authority zone (simplified)
        authority_rect = patches.Rectangle(
            (x + 25, y - 20), 100, 40,
            facecolor=self.COLORS['authority'],
            alpha=0.3,
            edgecolor=self.COLORS['authority'],
            linewidth=1,
            linestyle='--'
        )
        ax.add_patch(authority_rect)

    def _add_legend(self, ax):
        """Add a legend to the diagram"""
        legend_elements = [
            patches.Rectangle((0, 0), 1, 1, facecolor=self.COLORS['track_normal'],
                              label='Normal Track'),
            patches.Rectangle((0, 0), 1, 1, facecolor=self.COLORS['track_maintenance'],
                              label='Maintenance Closure'),
            patches.Rectangle((0, 0), 1, 1, facecolor=self.COLORS['station'],
                              label='Station'),
            patches.Polygon([(0, 0), (1, 0.5), (0, 1)],
                            facecolor=self.COLORS['switch'], label='Switch'),
            patches.Rectangle((0, 0), 1, 1, facecolor=self.COLORS['crossing'],
                              label='Railway Crossing'),
            patches.Rectangle((0, 0), 1, 1, facecolor=self.COLORS['train'],
                              label='Train'),
        ]

        ax.legend(handles=legend_elements, loc='upper left',
                  bbox_to_anchor=(0.02, 0.98), framealpha=0.9)

    def _create_empty_diagram(self, message: str) -> plt.Figure:
        """Create an empty diagram with a message"""
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(0.5, 0.5, message, ha='center', va='center',
                fontsize=20, transform=ax.transAxes)
        ax.set_facecolor(self.COLORS['background'])
        ax.axis('off')
        return fig

    def create_system_overview(self, active_trains: Dict[str, Dict[int, str]] = None,
                               maintenance: Dict[str, List[str]] = None) -> plt.Figure:
        """
        Create an overview of all three lines for the dispatcher's main screen.
        """
        if active_trains is None:
            active_trains = {"Blue": {}, "Red": {}, "Green": {}}
        if maintenance is None:
            maintenance = {"Blue": [], "Red": [], "Green": []}

        fig, axes = plt.subplots(3, 1, figsize=(18, 12))
        fig.suptitle("PAAC Light Rail System Overview", fontsize=24, fontweight='bold')

        for i, line in enumerate(["Blue", "Red", "Green"]):
            ax = axes[i]
            ax.set_facecolor(self.COLORS['background'])

            # Get line statistics
            blocks = self.track_reader.lines.get(line, [])
            stations = self.track_reader.get_all_stations(line)
            switches = self.track_reader.get_all_switches(line)

            # Create simplified line view
            ax.text(0.02, 0.5, f"{line} Line", transform=ax.transAxes,
                    fontsize=18, fontweight='bold', va='center')

            # Stats box
            stats_text = (f"Blocks: {len(blocks)} | "
                          f"Stations: {len(stations)} | "
                          f"Switches: {len(switches)} | "
                          f"Trains: {len(active_trains[line])}")

            ax.text(0.98, 0.5, stats_text, transform=ax.transAxes,
                    fontsize=13, ha='right', va='center',
                    bbox=dict(boxstyle="round,pad=0.3",
                              facecolor='white', alpha=0.8))

            # Maintenance indicator
            if maintenance[line]:
                ax.text(0.5, 0.5, f"⚠️ Maintenance: Sections {', '.join(maintenance[line])}",
                        transform=ax.transAxes,
                        fontsize=13, ha='center', va='center',
                        color=self.COLORS['track_maintenance'],
                        fontweight='bold')

            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')

        plt.tight_layout()
        return fig


class CTCTrackDisplayHelper:
    """
    Consolidated track display functionality from ctc.py
    Manages track display and routing for the CTC Office interface.
    """

    def __init__(self, track_reader, ctc_system=None):
        """Initialize with track layout data and optional CTC system"""
        self.track_reader = track_reader
        self.ctc_system = ctc_system  # Use CTC system for UI delegation when available
        self.active_trains = {}  # Track trains on the system
        self.maintenance_closures = {
            "Blue": [],
            "Red": [],
            "Green": []
        }

    def get_morning_shift_summary(self) -> Dict:
        """Get a summary for the morning shift dispatcher"""
        summary = {
            "shift_start": "6:00 AM",
            "date": datetime.now().strftime("%A, %B %d, %Y"),
            "lines_status": {},
            "total_stations": 0,
            "total_switches": 0,
            "maintenance_sections": []
        }

        # Check each line using CTC system delegation methods when available
        for line in ["Blue", "Red", "Green"]:
            if self.ctc_system and hasattr(self.ctc_system, 'trackLayout'):
                stations = self.ctc_system.trackLayout.get_all_stations(line)
                switches = self.ctc_system.trackLayout.get_all_switches(line)
                line_blocks = self.ctc_system.trackLayout.lines[line]
            else:
                stations = self.track_reader.get_all_stations(line)
                switches = self.track_reader.get_all_switches(line)
                line_blocks = self.track_reader.lines[line]

            summary["lines_status"][line] = {
                "operational": len(self.maintenance_closures[line]) == 0,
                "stations": len(stations),
                "switches": len(switches),
                "blocks": len(line_blocks)
            }

            summary["total_stations"] += len(stations)
            summary["total_switches"] += len(switches)

        return summary

    def get_station_menu(self) -> Dict[str, List[Dict]]:
        """Get stations organized by line for dispatcher selection"""
        menu = {}
        for line in ["Blue", "Red", "Green"]:
            if self.ctc_system and hasattr(self.ctc_system, 'trackLayout'):
                stations = self.ctc_system.trackLayout.get_all_stations(line)
            else:
                stations = self.track_reader.get_all_stations(line)
            menu[f"{line} Line"] = [
                {
                    "display_name": f"{s['station_name']} (Block {s['block_number']})",
                    "station_name": s['station_name'],
                    "block_number": s['block_number'],
                    "platform": s['platform_side']
                }
                for s in stations
            ]
        return menu

    def plan_route_simple(self, from_station: str, to_station: str) -> Dict:
        """Plan a route between stations using CTC system delegation"""
        if self.ctc_system:
            return self.ctc_system.plan_route_between_stations(from_station, to_station)
        else:
            return {
                "success": False,
                "error": "CTC system not available"
            }

    def check_maintenance_conflict(self, line: str, route: List[int]) -> Tuple[bool, str]:
        """Check if a route conflicts with maintenance closures"""
        for block_num in route:
            block = self.track_reader.get_block_info(line, block_num)
            if block and block.section in self.maintenance_closures[line]:
                return True, f"Section {block.section} is closed for maintenance"
        return False, "Route is clear"

    def close_section_for_maintenance(self, line: str, section: str) -> Dict:
        """Close a track section for maintenance using CTC system delegation"""
        if section in self.maintenance_closures[line]:
            return {
                "success": False,
                "message": f"Section {section} is already closed"
            }

        # Find affected stations
        affected_stations = []
        for block in self.track_reader.lines[line]:
            if block.section == section and block.has_station:
                affected_stations.append(block.station.name)

        self.maintenance_closures[line].append(section)

        return {
            "success": True,
            "message": f"Section {section} closed for maintenance",
            "affected_stations": affected_stations,
            "notification": f"Passengers at {', '.join(affected_stations)} stations will experience delays"
            if affected_stations else "No stations directly affected"
        }

    def get_performance_metrics(self) -> Dict:
        """Calculate performance metrics for dispatcher's dashboard"""
        total_blocks = sum(len(blocks) for blocks in self.track_reader.lines.values())
        maintenance_blocks = 0

        for line in ["Blue", "Red", "Green"]:
            for section in self.maintenance_closures[line]:
                section_blocks = self.track_reader.sections[line].get(section, [])
                maintenance_blocks += len(section_blocks)

        operational_percentage = ((total_blocks - maintenance_blocks) / total_blocks * 100) if total_blocks > 0 else 0

        return {
            "shift_performance": {
                "operational_track_percentage": round(operational_percentage, 1),
                "active_trains": len(self.active_trains),
                "stations_served": len(self.track_reader.get_all_stations()),
            },
            "career_metrics": {
                "months_without_incidents": 3,
                "efficiency_rating": "Above Average",
                "supervisor_readiness": "78%",
                "years_until_eligible": 1.5
            }
        }

    def get_block_status_display(self, line: str, block_number: int) -> str:
        """Get a human-readable status for a track block"""
        block = self.track_reader.get_block_info(line, block_number)
        if not block:
            return "Block not found"

        status_parts = [
            f"Block {block_number} - Section {block.section}",
            f"Length: {block.length_m} meters",
            f"Speed Limit: {block.speed_limit_kmh} km/hr",
        ]

        if block.grade_percent != 0:
            grade_desc = "uphill" if block.grade_percent > 0 else "downhill"
            status_parts.append(f"Grade: {abs(block.grade_percent)}% {grade_desc}")

        if block.has_station:
            status_parts.append(f"Station: {block.station.name}")

        if block.has_switch:
            status_parts.append("Has track switch")

        if block.has_crossing:
            status_parts.append("Has railway crossing")

        if block.section in self.maintenance_closures[line]:
            status_parts.append("⚠️ CLOSED FOR MAINTENANCE")

        return "\n".join(status_parts)


class CTCVisualDisplayHelper:
    """
    Consolidated visual display functionality from ctc_display.py
    Creates visual representations of track layout for dispatcher interface.
    """

    # Color scheme for accessibility
    COLORS = {
        'track_normal': '#333333',
        'track_maintenance': '#FF6B6B',
        'station': '#4DABF7',
        'switch': '#69DB7C',
        'crossing': '#FFD43B',
        'train': '#FF8CC8',
        'authority': '#C3FAD5',
        'background': '#F8F9FA',
        'grid': '#DEE2E6'
    }

    def __init__(self, track_reader):
        """Initialize with track layout data"""
        self.track_reader = track_reader

    def create_line_diagram(self, line: str,
                            active_trains: Optional[Dict[int, str]] = None,
                            maintenance_sections: Optional[List[str]] = None,
                            zoom_section: Optional[str] = None) -> plt.Figure:
        """Create a visual diagram of a track line"""
        if maintenance_sections is None:
            maintenance_sections = []
        if active_trains is None:
            active_trains = {}

        # Get track blocks
        blocks = self.track_reader.lines.get(line, [])
        if zoom_section:
            blocks = [b for b in blocks if b.section == zoom_section]

        if not blocks:
            return self._create_empty_diagram(f"No track data for {line} Line")

        # Create figure
        fig, ax = plt.subplots(figsize=(16, 8))
        ax.set_facecolor(self.COLORS['background'])

        # Calculate layout
        total_length = sum(b.length_m for b in blocks)
        scale = 1000 / total_length

        # Draw track sections
        x_position = 50
        y_base = 400

        for i, block in enumerate(blocks):
            block_width = block.length_m * scale

            # Determine track color
            if block.section in maintenance_sections:
                track_color = self.COLORS['track_maintenance']
            else:
                track_color = self.COLORS['track_normal']

            # Draw track segment
            track_rect = patches.Rectangle(
                (x_position, y_base - 20),
                block_width, 40,
                facecolor=track_color,
                edgecolor='black',
                linewidth=2
            )
            ax.add_patch(track_rect)

            # Add block number
            ax.text(x_position + block_width / 2, y_base,
                    str(block.block_number),
                    ha='center', va='center',
                    fontsize=14, fontweight='bold',
                    color='white' if track_color == self.COLORS['track_normal'] else 'black')

            # Draw infrastructure
            if block.has_station:
                self._draw_station(ax, x_position + block_width / 2, y_base, block.station.name)

            if block.has_switch:
                self._draw_switch(ax, x_position + block_width / 2, y_base)

            if block.has_crossing:
                self._draw_crossing(ax, x_position + block_width / 2, y_base)

            # Draw train if present
            if block.block_number in active_trains:
                self._draw_train(ax, x_position + block_width / 2, y_base,
                                 active_trains[block.block_number])

            x_position += block_width

        # Configure display
        title = f"{line} Line Track Layout"
        if zoom_section:
            title += f" - Section {zoom_section}"
        ax.set_title(title, fontsize=20, fontweight='bold', pad=20)

        self._add_legend(ax)
        ax.set_xlim(0, 1100)
        ax.set_ylim(200, 600)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.grid(True, alpha=0.3, color=self.COLORS['grid'])

        plt.tight_layout()
        return fig

    def _draw_station(self, ax, x: float, y: float, name: str):
        """Draw a station symbol"""
        station_rect = patches.Rectangle(
            (x - 30, y + 25), 60, 15,
            facecolor=self.COLORS['station'],
            edgecolor='black',
            linewidth=1
        )
        ax.add_patch(station_rect)

        ax.text(x, y + 55, name, ha='center', va='bottom',
                fontsize=12, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor='white',
                          edgecolor=self.COLORS['station']))

    def _draw_switch(self, ax, x: float, y: float):
        """Draw a switch symbol"""
        switch_points = np.array([
            [x, y - 35],
            [x + 15, y - 20],
            [x, y - 5],
            [x - 15, y - 20]
        ])
        switch_patch = patches.Polygon(
            switch_points,
            facecolor=self.COLORS['switch'],
            edgecolor='black',
            linewidth=2
        )
        ax.add_patch(switch_patch)

        ax.text(x, y - 45, 'SW', ha='center', va='top',
                fontsize=11, fontweight='bold')

    def _draw_crossing(self, ax, x: float, y: float):
        """Draw a railway crossing symbol"""
        crossing_size = 15
        ax.plot([x - crossing_size, x + crossing_size],
                [y - 50, y - 30],
                color=self.COLORS['crossing'], linewidth=4)
        ax.plot([x - crossing_size, x + crossing_size],
                [y - 30, y - 50],
                color=self.COLORS['crossing'], linewidth=4)

        ax.text(x, y - 60, 'RR X-ing', ha='center', va='top',
                fontsize=11, fontweight='bold')

    def _draw_train(self, ax, x: float, y: float, train_id: str):
        """Draw a train symbol"""
        train_rect = patches.Rectangle(
            (x - 25, y - 15), 50, 30,
            facecolor=self.COLORS['train'],
            edgecolor='black',
            linewidth=2
        )
        ax.add_patch(train_rect)

        ax.text(x, y, train_id, ha='center', va='center',
                fontsize=11, fontweight='bold', color='white')

    def _add_legend(self, ax):
        """Add a legend to the diagram"""
        legend_elements = [
            patches.Rectangle((0, 0), 1, 1, facecolor=self.COLORS['track_normal'],
                              label='Normal Track'),
            patches.Rectangle((0, 0), 1, 1, facecolor=self.COLORS['track_maintenance'],
                              label='Maintenance Closure'),
            patches.Rectangle((0, 0), 1, 1, facecolor=self.COLORS['station'],
                              label='Station'),
            patches.Rectangle((0, 0), 1, 1, facecolor=self.COLORS['train'],
                              label='Train'),
        ]

        ax.legend(handles=legend_elements, loc='upper left',
                  bbox_to_anchor=(0.02, 0.98), framealpha=0.9)

    def _create_empty_diagram(self, message: str) -> plt.Figure:
        """Create an empty diagram with a message"""
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(0.5, 0.5, message, ha='center', va='center',
                fontsize=20, transform=ax.transAxes)
        ax.set_facecolor(self.COLORS['background'])
        ax.axis('off')
        return fig

    def create_system_overview(self, active_trains: Dict[str, Dict[int, str]] = None,
                               maintenance: Dict[str, List[str]] = None) -> plt.Figure:
        """Create an overview of all three lines for dispatcher's main screen"""
        if active_trains is None:
            active_trains = {"Blue": {}, "Red": {}, "Green": {}}
        if maintenance is None:
            maintenance = {"Blue": [], "Red": [], "Green": []}

        fig, axes = plt.subplots(3, 1, figsize=(18, 12))
        fig.suptitle("PAAC Light Rail System Overview", fontsize=24, fontweight='bold')

        for i, line in enumerate(["Blue", "Red", "Green"]):
            ax = axes[i]
            ax.set_facecolor(self.COLORS['background'])

            # Get line statistics
            blocks = self.track_reader.lines.get(line, [])
            stations = self.track_reader.get_all_stations(line)
            switches = self.track_reader.get_all_switches(line)

            # Create simplified line view
            ax.text(0.02, 0.5, f"{line} Line", transform=ax.transAxes,
                    fontsize=18, fontweight='bold', va='center')

            # Stats box
            stats_text = (f"Blocks: {len(blocks)} | "
                          f"Stations: {len(stations)} | "
                          f"Switches: {len(switches)} | "
                          f"Trains: {len(active_trains[line])}")

            ax.text(0.98, 0.5, stats_text, transform=ax.transAxes,
                    fontsize=13, ha='right', va='center',
                    bbox=dict(boxstyle="round,pad=0.3",
                              facecolor='white', alpha=0.8))

            # Maintenance indicator
            if maintenance[line]:
                ax.text(0.5, 0.5, f"⚠️ Maintenance: Sections {', '.join(maintenance[line])}",
                        transform=ax.transAxes,
                        fontsize=13, ha='center', va='center',
                        color=self.COLORS['track_maintenance'],
                        fontweight='bold')

            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')

        plt.tight_layout()
        return fig


class StyledMessageBox(QMessageBox):
	"""Custom message box with clean styling to match img_3.png"""
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setStyleSheet("""
			QMessageBox {
				background-color: white;
				border: 2px solid #808080;
				color: black;
				font-size: 16pt;
			}
			QMessageBox QLabel {
				color: black;
				background-color: transparent;
				padding: 15px;
				font-size: 16pt;
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
	
	@staticmethod
	def information(parent, title, text):
		msg = StyledMessageBox(parent)
		msg.setIcon(QMessageBox.NoIcon)  # Remove icon
		msg.setWindowTitle(title)
		msg.setText(text)
		msg.setStandardButtons(QMessageBox.Ok)
		msg.setDefaultButton(QMessageBox.Ok)
		return msg.exec_()
	
	@staticmethod
	def warning(parent, title, text):
		msg = StyledMessageBox(parent)
		msg.setIcon(QMessageBox.NoIcon)  # Remove icon
		msg.setWindowTitle(title)
		msg.setText(text)
		msg.setStandardButtons(QMessageBox.Ok)
		msg.setDefaultButton(QMessageBox.Ok)
		return msg.exec_()
	
	@staticmethod
	def critical(parent, title, text):
		msg = StyledMessageBox(parent)
		msg.setIcon(QMessageBox.NoIcon)  # Remove icon
		msg.setWindowTitle(title)
		msg.setText(text)
		msg.setStandardButtons(QMessageBox.Ok)
		msg.setDefaultButton(QMessageBox.Ok)
		return msg.exec_()
	
	@staticmethod
	def question(parent, title, text, buttons=QMessageBox.Yes | QMessageBox.No):
		msg = StyledMessageBox(parent)
		msg.setIcon(QMessageBox.NoIcon)  # Remove icon
		msg.setWindowTitle(title)
		msg.setText(text)
		msg.setStandardButtons(buttons)
		msg.setDefaultButton(QMessageBox.Yes)
		return msg.exec_()


class CTCInterface(QMainWindow):
	"""
	Main CTC Office GUI Interface
	Provides dispatcher interface for train control with separated business logic
	"""

	def __init__(self, track_file: str = "Track Layout & Vehicle Data vF2.xlsx", selected_lines: list = None, time_multiplier: float = 1.0):
		super().__init__()

		# Default to Blue line if no lines specified
		if selected_lines is None:
			selected_lines = ['Blue']
		
		self.selected_lines = selected_lines
		self.time_multiplier = time_multiplier
		self.current_time = "05:00"  # Default time

		# Core components - UML-compliant architecture
		self.trackReader = TrackLayoutReader(track_file, selected_lines=selected_lines)
		self.ctc_system = CTCSystem(self.trackReader)
		self.communication_handler = self.ctc_system.communicationHandler
		self.display_manager = self.ctc_system.displayManager
		self.failure_manager = self.ctc_system.failureManager
		self.route_manager = self.ctc_system.routeManager
		self.trackVisualization = TrackVisualization(self.trackReader)
		
		# Connect CTC system signals for real-time updates
		if hasattr(self.ctc_system, 'trains_updated'):
			self.ctc_system.trains_updated.connect(self.on_trains_updated)
		if hasattr(self.ctc_system, 'state_changed'):
			self.ctc_system.state_changed.connect(self.on_state_changed)
		if hasattr(self.ctc_system, 'maintenance_updated'):
			self.ctc_system.maintenance_updated.connect(self.on_maintenance_updated)
		if hasattr(self.ctc_system, 'warnings_updated'):
			self.ctc_system.warnings_updated.connect(self.on_warnings_updated)
		
		# Connect display manager signals if they exist
		if hasattr(self.display_manager, 'train_selected'):
			self.display_manager.train_selected.connect(self.on_train_selected)
		if hasattr(self.display_manager, 'block_selected'):
			self.display_manager.block_selected.connect(self.on_block_selected)
		if hasattr(self.display_manager, 'throughput_updated'):
			self.display_manager.throughput_updated.connect(self.on_throughput_updated)

		# UI state - determine display line based on loaded lines
		if len(selected_lines) == 1:
			# Single line loaded
			self.selectedLine = selected_lines[0]
			self.selectedDisplayLine = selected_lines[0]
		elif len(selected_lines) == 2 and "Red" in selected_lines and "Green" in selected_lines:
			# Red and Green loaded together
			self.selectedLine = "Red"
			self.selectedDisplayLine = "Red & Green" 
		else:
			# Multiple lines or other combinations - show first one
			self.selectedLine = selected_lines[0]
			self.selectedDisplayLine = selected_lines[0]
		self.shiftStartTime = _get_simulation_time().replace(hour=6, minute=0, second=0)

		# Cache for performance
		self.allBlocksData = []
		self.blockToRowMap = {}
		self.previousTrainPositions = {}

		# Thread management
		self.running = True
		self.updateWorker = None

		# Track visualization cache
		self.lastTrackUpdate = 0
		self.trackNeedsRedraw = True

		# Initialize GUI
		self.setup_gui()

		# Start update thread
		self.updateWorker = UpdateWorker(self)
		# Note: High frequency data updates removed - will be implemented when needed
		self.updateWorker.updateTables.connect(self.update_table_displays)
		self.updateWorker.updateVisuals.connect(self.update_visual_displays)
		self.updateWorker.start()

		# Initialize displays
		self.initialize_block_table()
		QTimer.singleShot(200, self.create_track_visualization)
# Removed auto-resize functionality that makes map too small
		# Note: Auto-resize functionality removed per user request
		# QTimer.singleShot(400, self.update_scheduled_closures_display)  # Temporarily disabled
		


	def setup_gui(self):
		"""Create the dispatcher interface"""
		self.setWindowTitle("PAAC CTC Office - Main Control Window")
		self.setGeometry(50, 50, 1800, 1200)
		
		# Set application-wide larger font according to style guide
		app = QApplication.instance()
		if app:
			default_font = QFont("Arial", 20)  # Default: 20pt for better readability
			app.setFont(default_font)
			
		# Set up the interface
		self.setup_main_interface()
	
	def set_widget_font(self, widget, size=14, bold=False):
		"""Helper function to set fonts on widgets according to style guide"""
		weight = QFont.Bold if bold else QFont.Normal
		widget.setFont(QFont("Arial", size, weight))
		
	def apply_fonts_to_all_widgets(self):
		"""Apply fonts according to PyQt5 Style Guide (updated larger sizes)"""
		# All controls: 20pt Arial for better readability
		for widget in self.findChildren(QPushButton):
			self.set_widget_font(widget, 20)
		for widget in self.findChildren(QComboBox):
			self.set_widget_font(widget, 20)
		for widget in self.findChildren(QLineEdit):
			self.set_widget_font(widget, 20)
		for widget in self.findChildren(QTextEdit):
			self.set_widget_font(widget, 20)
		# Also explicitly set table fonts to ensure they take effect
		for widget in self.findChildren(QTableWidget):
			self.set_widget_font(widget, 20)
			# Ensure table headers are properly sized
			if widget.horizontalHeader():
				widget.horizontalHeader().setFont(QFont("Arial", 16, QFont.Bold))
		
	def setup_styles(self):
		"""Set clean application styling with good contrast"""
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
				font-size: 20pt;
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
				font-size: 20pt;
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
				alternate-background-color: #F5F5F5;
				font-size: 20pt;
			}
			QComboBox QAbstractItemView::item {
				height: 25px;
				padding: 3px;
			}
			QComboBox QAbstractItemView::item:alternate {
				background-color: #F5F5F5;
			}
			QComboBox QAbstractItemView::item:hover {
				background-color: #E0E0E0;
				color: black;
			}
			QComboBox QAbstractItemView::item:selected {
				background-color: #3399FF;
				color: white;
			}
			QLineEdit { 
				color: black; 
				background-color: white; 
				border: 1px solid #808080; 
				padding: 4px; 
				font-size: 20pt;
			}
			QTextEdit { 
				color: black; 
				background-color: white; 
				border: 1px solid #808080; 
				font-size: 20pt;
			}
			QListWidget { 
				color: black; 
				background-color: white; 
				border: 1px solid #808080; 
				font-size: 20pt;
			}
			QTableWidget { 
				color: black; 
				background-color: white; 
				border: 1px solid #808080; 
				gridline-color: #C0C0C0; 
				font-size: 20pt;
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
			QFrame { 
				color: black; 
				background-color: white; 
				border: 1px solid #808080; 
			}
		""")

	def setup_main_interface(self):
		"""Set up the main interface after styles are applied"""
		# Apply styles first
		self.setup_styles()
		
		# Create central widget
		central_widget = QWidget()
		self.setCentralWidget(central_widget)

		# Main layout
		main_layout = QVBoxLayout()
		central_widget.setLayout(main_layout)

		# Top header layout with throughput and time
		top_header_layout = QHBoxLayout()
		
		# Throughput info on left - made larger, dynamically create based on selected lines
		initial_throughput_text = "  |  ".join([f"{line} Line: 0 pass/hr" for line in self.selected_lines])
		self.throughput_label = QLabel(initial_throughput_text)
		self.throughput_label.setFont(QFont("Arial", 20, QFont.Bold))  # Header size per style guide
		
		# Time display on right - made larger, removed speed multiplier
		self.time_label = QLabel("Time: 05:00")
		self.time_label.setFont(QFont("Arial", 24, QFont.Bold))  # Large header per style guide
		self.time_label.setMaximumHeight(30)
		
		top_header_layout.addWidget(self.throughput_label)
		top_header_layout.addStretch()
		top_header_layout.addWidget(self.time_label)
		top_header_layout.setContentsMargins(5, 5, 5, 5)
		
		main_layout.addLayout(top_header_layout)

		# Create tabbed interface
		self.tab_widget = QTabWidget()
		main_layout.addWidget(self.tab_widget)
		
		# Connect tab change signal to reset page states
		self.tab_widget.currentChanged.connect(self.on_tab_changed)

		# Create tabs
		self.setup_main_tab()
		self.setup_route_train_tab()
		self.setup_close_block_tab()
		
		# Apply larger fonts to all buttons and controls after all widgets are created
		self.apply_fonts_to_all_widgets()
		
		# Force widget updates to ensure font changes take effect
		self.update()
		for widget in self.findChildren(QWidget):
			widget.update()
		
		# Initialize dropdowns when Route Train tab is first accessed
		# Remove automatic initialization to prevent forcing tab switch on startup

	def update_time(self, time_str):
		"""Update the time display from external source"""
		self.current_time = time_str
		self.time_label.setText(f"Time: {time_str}")
		
		# Pass the current time to the train manager for ETA calculations
		if hasattr(self, 'ctc_system') and self.ctc_system:
			if hasattr(self.ctc_system, 'system_tick'):
				from datetime import datetime
				try:
					current_time = datetime.strptime(time_str, "%H:%M")
					self.ctc_system.system_tick(current_time)
				except ValueError:
					pass  # Invalid time format

	def update_throughput(self, throughput_data):
		"""Update the throughput display with real calculated data - only show active lines
		
		Args:
			throughput_data: Dict with per-line throughput rates
			              e.g., {'Blue': 15, 'Red': 23, 'Green': 18}
		"""
		if not throughput_data:
			# Default to zero if no data
			throughput_data = {'Blue': 0, 'Red': 0, 'Green': 0}
		
		# Only show throughput for selected (active) lines
		throughput_parts = []
		for line in self.selected_lines:
			rate = throughput_data.get(line, 0)
			throughput_parts.append(f"{line} Line: {rate} pass/hr")
		
		self.throughput_label.setText("  |  ".join(throughput_parts))

	def setup_main_tab(self):
		"""Setup the main overview tab"""
		main_widget = QWidget()
		main_layout = QVBoxLayout()
		main_widget.setLayout(main_layout)


		# Create main horizontal splitter with visible separator
		main_splitter = QSplitter(Qt.Horizontal)
		main_splitter.setStyleSheet("""
			QSplitter::handle {
				background-color: #808080;
				width: 8px;
				border: 2px solid #606060;
				border-radius: 3px;
			}
			QSplitter::handle:hover {
				background-color: #A0A0A0;
				border: 2px solid #707070;
			}
			QSplitter::handle:pressed {
				background-color: #909090;
			}
		""")
		main_layout.addWidget(main_splitter)

		# Left side - Track visualization
		left_widget = QWidget()
		left_layout = QVBoxLayout()
		left_widget.setLayout(left_layout)

		# Track display with dynamic line label
		track_label = QLabel(f"{self.selectedDisplayLine.upper()} LINE")
		track_label.setFont(QFont("Arial", 20, QFont.Bold))  # Header size per style guide
		track_label.setAlignment(Qt.AlignCenter)
		left_layout.addWidget(track_label)

		# Create a splitter for resizable track and table sections
		left_splitter = QSplitter(Qt.Vertical)
		
		# Track visualization widget (will be created by TrackVisualization)
		self.track_widget = self.trackVisualization.create_widget()
		left_splitter.addWidget(self.track_widget)

		# Container for train table and button
		table_container = QWidget()
		table_layout = QVBoxLayout()
		table_container.setLayout(table_layout)
		
		# Train information table with updated columns
		self.train_info_table = self.create_train_info_table()
		table_layout.addWidget(self.train_info_table)
		
		# Reroute Train button
		self.reroute_btn = QPushButton("Reroute Train")
		self.reroute_btn.setMaximumHeight(40)
		self.reroute_btn.clicked.connect(self.reroute_selected_train_from_main)
		self.set_widget_font(self.reroute_btn, 20)  # Match table content font
		table_layout.addWidget(self.reroute_btn)
		
		left_splitter.addWidget(table_container)
		left_splitter.setStretchFactor(0, 1)  # Track gets more space
		left_splitter.setStretchFactor(1, 0)  # Table gets less space
		
		left_layout.addWidget(left_splitter)

		main_splitter.addWidget(left_widget)

		# Right side - Warning and Block tables
		right_widget = QWidget()
		right_layout = QVBoxLayout()
		right_widget.setLayout(right_layout)

		# Compact warnings section (much smaller)
		warnings_frame = QFrame()
		warnings_frame.setFrameStyle(QFrame.Box)
		warnings_layout = QVBoxLayout()
		warnings_frame.setLayout(warnings_layout)
		
		warnings_label = QLabel("Warning Type")
		warnings_label.setFont(QFont("Arial", 18, QFont.Bold))  # Header size per style guide
		warnings_layout.addWidget(warnings_label)

		self.warnings_table = self.create_warnings_table()
		warnings_layout.addWidget(self.warnings_table)
		
		# Set warnings frame to take minimal space
		warnings_frame.setMaximumHeight(180)
		right_layout.addWidget(warnings_frame)

		# Block information table (takes most of the space)
		block_frame = QFrame()
		block_frame.setFrameStyle(QFrame.Box)
		block_layout = QVBoxLayout()
		block_frame.setLayout(block_layout)
		
		self.block_info_table = self.create_block_info_table()
		block_layout.addWidget(self.block_info_table)
		
		# Open/Close Block button (dynamic text based on selection)
		self.open_block_btn = QPushButton("Close Block")
		self.open_block_btn.setMaximumHeight(40)
		self.open_block_btn.clicked.connect(self.handle_open_close_block)
		block_layout.addWidget(self.open_block_btn)
		
		# Connect block table selection to update button text
		self.block_info_table.itemSelectionChanged.connect(self.update_open_close_button)
		
		right_layout.addWidget(block_frame)
		
		# Make block table take up most of the vertical space
		right_layout.setStretchFactor(warnings_frame, 0)
		right_layout.setStretchFactor(block_frame, 1)

		main_splitter.addWidget(right_widget)
		# Set more balanced initial sizes
		main_splitter.setSizes([1100, 450])  # Much more space for map, very compact right side
		main_splitter.setStretchFactor(0, 1)
		main_splitter.setStretchFactor(1, 0)

		self.tab_widget.addTab(main_widget, "Main")

	def create_train_info_table(self):
		"""Create and configure the train information table"""
		table = QTableWidget()
		table.setColumnCount(9)
		table.setHorizontalHeaderLabels(['Train ID', 'Line', 'Location (Section)', 'Location (Block)', 
		                               'Destination (Section)', 'Destination (Block)', 'Departure Time', 'ETA', 'Speed (mph)'])
		table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
		table.horizontalHeader().setStretchLastSection(False)
		table.resizeColumnsToContents()
		# Set proper column widths for 20pt font
		table.setColumnWidth(0, 120)  # Train ID
		table.setColumnWidth(1, 100)  # Line
		table.setColumnWidth(2, 150)  # Location (Section)
		table.setColumnWidth(3, 130)  # Location (Block)
		table.setColumnWidth(4, 160)  # Destination (Section)
		table.setColumnWidth(5, 140)  # Destination (Block)
		table.setColumnWidth(6, 170)  # Departure Time
		table.setColumnWidth(7, 120)  # ETA
		table.setColumnWidth(8, 130)  # Speed (mph)
		table.verticalHeader().setDefaultSectionSize(18)
		table.setMinimumHeight(150)
		table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
		table.setSelectionBehavior(QAbstractItemView.SelectRows)
		table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Make table non-editable
		# Set fonts according to style guide: 20pt content for better readability
		table.setFont(QFont("Arial", 20))
		table.horizontalHeader().setFont(QFont("Arial", 16, QFont.Bold))
		return table

	def create_warnings_table(self):
		"""Create and configure the warnings table"""
		table = QTableWidget()
		table.setColumnCount(6)
		table.setHorizontalHeaderLabels(['Warning Type', 'Train', 'Line', 'Section', 'Block', 'Resolved'])
		table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
		table.horizontalHeader().setStretchLastSection(False)
		table.resizeColumnsToContents()
		# Set minimum width for Line column
		table.setColumnWidth(2, 140)  # Line column - increased for 20pt font
		table.verticalHeader().setDefaultSectionSize(18)
		table.setMaximumHeight(100)  # Much smaller
		table.setMinimumHeight(80)
		table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Make table non-editable
		# Set fonts according to style guide: 20pt content for better readability
		table.setFont(QFont("Arial", 20))
		table.horizontalHeader().setFont(QFont("Arial", 16, QFont.Bold))
		return table

	def create_block_info_table(self):
		"""Create and configure the block information table"""
		table = QTableWidget()
		table.setColumnCount(9)
		table.setHorizontalHeaderLabels(['Line', 'Open?', 'Occupying Train', 'Section', 'Block', 
		                               'Speed Limit (mph)', 'Stop', 'Switch', 'Crossing'])
		table.setAlternatingRowColors(True)
		table.setSortingEnabled(True)
		table.verticalHeader().setDefaultSectionSize(16)
		table.setSelectionBehavior(QAbstractItemView.SelectRows)
		# Make columns user-adjustable but compact by default
		table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
		table.horizontalHeader().setStretchLastSection(False)  # Don't stretch last column
		# Set minimum widths for all columns to accommodate 20pt font
		table.setColumnWidth(0, 140)  # Line
		table.setColumnWidth(1, 90)   # Open?
		table.setColumnWidth(2, 180)  # Occupying Train
		table.setColumnWidth(3, 110)  # Section
		table.setColumnWidth(4, 90)   # Block
		table.setColumnWidth(5, 170)  # Speed Limit (mph)
		table.setColumnWidth(6, 90)   # Stop
		table.setColumnWidth(7, 110)  # Switch
		table.setColumnWidth(8, 110)  # Crossing
		# Store original column widths to prevent override
		self._user_adjusted_columns = set()
		table.horizontalHeader().sectionResized.connect(self._on_column_resized)
		# Initial compact sizing
		self._initial_compact_sizing(table)
		table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Make table non-editable
		# Set fonts according to style guide: 20pt content for better readability
		table.setFont(QFont("Arial", 20))
		table.horizontalHeader().setFont(QFont("Arial", 16, QFont.Bold))
		return table

	def setup_route_train_tab(self):
		"""Setup the train routing tab"""
		route_widget = QWidget()
		route_layout = QVBoxLayout()
		route_widget.setLayout(route_layout)


		# Main content splitter
		main_splitter = QSplitter(Qt.Horizontal)
		main_splitter.setStyleSheet("""
			QSplitter::handle {
				background-color: #808080;
				width: 8px;
				border: 2px solid #606060;
				border-radius: 3px;
			}
		""")
		route_layout.addWidget(main_splitter)

		# Left side panel
		left_widget = QWidget()
		left_layout = QVBoxLayout()
		left_widget.setLayout(left_layout)

		# Mode selection (tab-style buttons)
		mode_layout = QHBoxLayout()
		self.manually_route_btn = QPushButton("Manually Route")
		self.enter_schedule_btn = QPushButton("Enter Train Schedule")
		
		# Style the buttons like tabs
		self.manually_route_btn.setCheckable(True)
		self.enter_schedule_btn.setCheckable(True)
		self.manually_route_btn.setChecked(True)
		
		self.manually_route_btn.setStyleSheet("""
			QPushButton {
				border: 1px solid #808080;
				border-bottom: none;
				background-color: #F0F0F0;
				padding: 8px 16px;
				color: black;
			}
			QPushButton:checked {
				background-color: white;
				border-bottom: 1px solid white;
			}
			QPushButton:!checked {
				background-color: #F0F0F0;
			}
			QPushButton:hover {
				background-color: #E0E0E0;
			}
			QPushButton:checked:hover {
				background-color: white;
			}
			QPushButton:pressed {
				background-color: #D0D0D0;
			}
			QPushButton:checked:pressed {
				background-color: #F0F0F0;
			}
		""")
		self.enter_schedule_btn.setStyleSheet("""
			QPushButton {
				border: 1px solid #808080;
				border-bottom: none;
				border-left: none;
				background-color: #F0F0F0;
				padding: 8px 16px;
				color: black;
			}
			QPushButton:checked {
				background-color: white;
				border-bottom: 1px solid white;
			}
			QPushButton:!checked {
				background-color: #F0F0F0;
			}
			QPushButton:hover {
				background-color: #E0E0E0;
			}
			QPushButton:checked:hover {
				background-color: white;
			}
			QPushButton:pressed {
				background-color: #D0D0D0;
			}
			QPushButton:checked:pressed {
				background-color: #F0F0F0;
			}
		""")
		
		self.manually_route_btn.clicked.connect(self.set_manual_mode)
		self.enter_schedule_btn.clicked.connect(self.set_schedule_mode)
		
		mode_layout.addWidget(self.manually_route_btn)
		mode_layout.addWidget(self.enter_schedule_btn)
		mode_layout.addStretch()
		left_layout.addLayout(mode_layout)

		# Stacked widget for mode-specific content
		self.route_mode_stack = QWidget()
		stack_layout = QVBoxLayout()
		self.route_mode_stack.setLayout(stack_layout)

		# Manually Route content
		self.manually_route_widget = self.create_manually_route_widget()
		stack_layout.addWidget(self.manually_route_widget)

		# Enter Train Schedule content
		self.enter_schedule_widget = self.create_enter_schedule_widget()
		self.enter_schedule_widget.setVisible(False)
		stack_layout.addWidget(self.enter_schedule_widget)

		left_layout.addWidget(self.route_mode_stack)
		left_layout.addStretch()

		main_splitter.addWidget(left_widget)

		# Right side panel
		right_widget = QWidget()
		right_layout = QVBoxLayout()
		right_widget.setLayout(right_layout)

		# Trains Currently on the Track table
		trains_label = QLabel("Trains Currently on the Track")
		trains_label.setFont(QFont("Arial", 20, QFont.Bold))  # Header size per style guide
		trains_label.setAlignment(Qt.AlignCenter)
		right_layout.addWidget(trains_label)

		self.current_trains_table = self.create_current_trains_table()
		right_layout.addWidget(self.current_trains_table)

		# Reroute Train button
		self.reroute_train_btn = QPushButton("Reroute Train")
		self.reroute_train_btn.setMaximumHeight(40)
		self.reroute_train_btn.clicked.connect(self.reroute_selected_train)
		right_layout.addWidget(self.reroute_train_btn)

		# Track visualization (reuse from main tab)
		track_label = QLabel("Generated Route")
		track_label.setFont(QFont("Arial", 20, QFont.Bold))  # Header size per style guide
		track_label.setAlignment(Qt.AlignCenter)
		right_layout.addWidget(track_label)

		# Create a new track visualization instance for the route tab
		self.route_track_visualization = TrackVisualization(self.trackReader)
		self.route_track_widget = self.route_track_visualization.create_widget()
		right_layout.addWidget(self.route_track_widget)

		# New Train Information table
		new_train_label = QLabel("New Train Information")
		new_train_label.setFont(QFont("Arial", 18, QFont.Bold))  # Header size per style guide
		right_layout.addWidget(new_train_label)

		self.new_train_info_table = self.create_new_train_info_table()
		right_layout.addWidget(self.new_train_info_table)

		# Accept Route button
		self.accept_route_btn = QPushButton("Accept Route")
		self.accept_route_btn.setMaximumHeight(40)
		self.accept_route_btn.clicked.connect(self.accept_route)
		right_layout.addWidget(self.accept_route_btn)

		main_splitter.addWidget(right_widget)

		# Set splitter proportions - make left side much wider
		main_splitter.setSizes([700, 600])

		self.tab_widget.addTab(route_widget, "Route Train")

	def create_manually_route_widget(self):
		"""Create the manually route widget for the left panel"""
		widget = QWidget()
		# Remove conflicting parent widget styling to allow proper button inheritance
		widget.setStyleSheet("border: 1px solid #808080;")
		layout = QVBoxLayout()
		layout.setContentsMargins(15, 15, 15, 15)
		layout.setSpacing(15)
		widget.setLayout(layout)

		# Train ID Section (no frame, cleaner look)
		train_id_label = QLabel("Enter the ID of the train to route")
		train_id_label.setStyleSheet("border: none; font-size: 20pt; margin-bottom: 5px;")
		layout.addWidget(train_id_label)
		
		train_id_layout = QHBoxLayout()
		train_id_layout.addWidget(QLabel("Train ID"))
		
		self.route_train_id_entry = QLineEdit()
		# Set placeholder based on active lines
		line_examples = [f"{line[0]}{str(1).zfill(3)}" for line in self.selected_lines]
		self.route_train_id_entry.setPlaceholderText(f"Enter train ID (e.g., {', '.join(line_examples)})")
		# Restrict to valid train ID format: Only active line letters + 3 digits
		active_letters = ''.join([line[0] for line in self.selected_lines])
		train_id_regex = QRegExp(f"^[{active_letters}][0-9]{{3}}$")
		train_id_validator = QRegExpValidator(train_id_regex)
		self.route_train_id_entry.setValidator(train_id_validator)
		# Connect real-time validation
		# Train ID validation will only occur when Check Train button is pressed
		train_id_layout.addWidget(self.route_train_id_entry)
		
		self.check_train_btn = QPushButton("Check Train")
		self.check_train_btn.clicked.connect(self.check_train_id)
		# Use global button styling by not setting any custom stylesheet
		train_id_layout.addWidget(self.check_train_btn)
		
		layout.addLayout(train_id_layout)

		# Train Information Section
		train_info_label = QLabel("Train Information:")
		train_info_label.setStyleSheet("border: none; font-size: 20pt; margin-top: 10px; margin-bottom: 5px;")
		layout.addWidget(train_info_label)
		
		# Create a splitter for resizable table and controls sections
		route_splitter = QSplitter(Qt.Vertical)
		
		self.route_train_info_table = self.create_route_train_info_table()
		route_splitter.addWidget(self.route_train_info_table)

		# Container for destination and time controls
		controls_container = QWidget()
		controls_layout = QVBoxLayout()
		controls_container.setLayout(controls_layout)

		# Destination and Time in side-by-side layout
		dest_time_layout = QHBoxLayout()
		dest_time_layout.setSpacing(30)

		# Destination Section (left side)
		dest_widget = QWidget()
		dest_layout = QVBoxLayout()
		dest_layout.setContentsMargins(0, 0, 0, 0)
		dest_layout.setSpacing(8)
		dest_widget.setLayout(dest_layout)

		dest_title = QLabel("Destination:")
		dest_title.setStyleSheet("border: none; font-weight: bold; margin-bottom: 5px;")
		dest_layout.addWidget(dest_title)
		
		# Line selection
		line_layout = QGridLayout()
		line_layout.setHorizontalSpacing(10)
		line_layout.setVerticalSpacing(5)
		line_label = QLabel("Line")
		line_label.setFixedWidth(60)
		line_layout.addWidget(line_label, 0, 0)
		self.dest_line_combo = QComboBox()
		self.dest_line_combo.addItems(self.selected_lines)
		self.dest_line_combo.currentTextChanged.connect(self.update_dest_sections)
		self.dest_line_combo.setMinimumWidth(120)
		line_layout.addWidget(self.dest_line_combo, 0, 1)
		dest_layout.addLayout(line_layout)

		# Section selection
		section_layout = QGridLayout()
		section_layout.setHorizontalSpacing(10)
		section_layout.setVerticalSpacing(5)
		section_label = QLabel("Section")
		section_label.setFixedWidth(60)
		section_layout.addWidget(section_label, 0, 0)
		self.dest_section_combo = QComboBox()
		self.dest_section_combo.currentTextChanged.connect(self.update_dest_blocks)
		self.dest_section_combo.setMinimumWidth(120)
		section_layout.addWidget(self.dest_section_combo, 0, 1)
		dest_layout.addLayout(section_layout)

		# Block selection
		block_layout = QGridLayout()
		block_layout.setHorizontalSpacing(10)
		block_layout.setVerticalSpacing(5)
		block_label = QLabel("Block")
		block_label.setFixedWidth(60)
		block_layout.addWidget(block_label, 0, 0)
		self.dest_block_combo = QComboBox()
		self.dest_block_combo.setMinimumWidth(120)
		block_layout.addWidget(self.dest_block_combo, 0, 1)
		dest_layout.addLayout(block_layout)

		dest_time_layout.addWidget(dest_widget)

		# Arrival Time Section (right side)
		time_widget = QWidget()
		time_layout = QVBoxLayout()
		time_layout.setContentsMargins(0, 0, 0, 0)
		time_layout.setSpacing(8)
		time_widget.setLayout(time_layout)

		time_title = QLabel("Arrival Time:")
		time_title.setStyleSheet("border: none; font-weight: bold; margin-bottom: 5px;")
		time_layout.addWidget(time_title)
		
		self.arrival_time_entry = QLineEdit()
		self.arrival_time_entry.setPlaceholderText("HH:MM")
		self.arrival_time_entry.setMaxLength(5)
		self.arrival_time_entry.setMinimumWidth(120)
		# Add time format validation with better regex
		time_regex = QRegExp("^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
		time_validator = QRegExpValidator(time_regex)
		self.arrival_time_entry.setValidator(time_validator)
		time_layout.addWidget(self.arrival_time_entry)

		# Add stretching space
		time_layout.addStretch()

		dest_time_layout.addWidget(time_widget)
		controls_layout.addLayout(dest_time_layout)

		# Buttons layout
		button_layout = QHBoxLayout()
		self.select_dest_btn = QPushButton("Select Destination")
		self.select_dest_btn.clicked.connect(self.select_destination)
		# Use global button styling by not setting any custom stylesheet
		button_layout.addWidget(self.select_dest_btn)

		self.choose_time_btn = QPushButton("Choose Time")
		self.choose_time_btn.clicked.connect(self.choose_arrival_time)
		# Use global button styling by not setting any custom stylesheet
		button_layout.addWidget(self.choose_time_btn)
		
		controls_layout.addLayout(button_layout)
		
		route_splitter.addWidget(controls_container)
		route_splitter.setStretchFactor(0, 0)  # Table gets less space
		route_splitter.setStretchFactor(1, 1)  # Controls get more space
		
		layout.addWidget(route_splitter)

		# Initialize dropdowns and route state
		# Set default selection for line combo (sections/blocks will be populated later)
		if self.dest_line_combo.count() > 0:
			self.dest_line_combo.setCurrentIndex(0)
			# Populate initial dropdowns immediately after widget creation
			QTimer.singleShot(50, self.populate_initial_dropdowns)
		
		# Ensure alternating row colors are properly applied after initialization
		QTimer.singleShot(100, self.apply_dropdown_alternating_colors)
		
		self.destination_selected = False
		self.time_selected = False

		return widget

	def populate_initial_dropdowns(self):
		"""Populate the section and block dropdowns on initial load"""
		try:
			line = self.dest_line_combo.currentText()
			if not line:
				return
			
			# Populate dropdowns for the selected line
			
			# CRITICAL: Block signals during initialization to prevent recursion
			self.dest_section_combo.blockSignals(True)
			self.dest_block_combo.blockSignals(True)
			
			try:
				# Get sections for the current line
				sections = self.get_sections_for_line(line)
				print(f"[DEBUG] Found sections: {sections}")
				
				# Populate section dropdown
				self.dest_section_combo.clear()
				self.dest_section_combo.addItems(sections)
				print(f"[DEBUG] Section combo populated with {self.dest_section_combo.count()} items")
				
				# Set default section if available
				if sections:
					self.dest_section_combo.setCurrentIndex(0)
					print(f"[DEBUG] Section combo current text: {self.dest_section_combo.currentText()}")
					
					# Get blocks for the first section
					blocks = self.get_blocks_for_section(line, sections[0])
					print(f"[DEBUG] Found blocks for section {sections[0]}: {blocks}")
					
					# Populate block dropdown
					self.dest_block_combo.clear()
					self.dest_block_combo.addItems([str(block) for block in blocks])
					print(f"[DEBUG] Block combo populated with {self.dest_block_combo.count()} items")
					
					# Set default block if available
					if blocks:
						self.dest_block_combo.setCurrentIndex(0)
						print(f"[DEBUG] Block combo current text: {self.dest_block_combo.currentText()}")
			finally:
				# CRITICAL: Re-enable signals after initialization
				self.dest_section_combo.blockSignals(False)
				self.dest_block_combo.blockSignals(False)
				
				# CRITICAL DEBUG: Check widget visibility hierarchy
				print(f"[DEBUG] Section combo visible: {self.dest_section_combo.isVisible()}")
				print(f"[DEBUG] Block combo visible: {self.dest_block_combo.isVisible()}")
				
				# Check if manually_route_widget exists (might be called during widget creation)
				if hasattr(self, 'manually_route_widget'):
					print(f"[DEBUG] Manually route widget visible: {self.manually_route_widget.isVisible()}")
				else:
					print(f"[DEBUG] Manually route widget not yet created")
					
				if hasattr(self, 'route_mode_stack'):
					print(f"[DEBUG] Route mode stack visible: {self.route_mode_stack.isVisible()}")
				else:
					print(f"[DEBUG] Route mode stack not yet created")
				
				# CRITICAL FIX: Force visibility of entire widget hierarchy (if they exist)
				
				# Make sure we're in manual mode (not schedule mode)
				print(f"[DEBUG] Setting manual mode")
				self.set_manual_mode()
				
				# Force parent containers to be visible
				if hasattr(self, 'route_mode_stack'):
					self.route_mode_stack.setVisible(True)
					self.route_mode_stack.show()
					print(f"[DEBUG] After manual show - Route mode stack visible: {self.route_mode_stack.isVisible()}")
				if hasattr(self, 'manually_route_widget'):
					self.manually_route_widget.setVisible(True)
					self.manually_route_widget.show()
					print(f"[DEBUG] After manual show - Manually route widget visible: {self.manually_route_widget.isVisible()}")
				
				# Force dropdowns to be visible
				self.dest_section_combo.setVisible(True)
				self.dest_block_combo.setVisible(True)
				self.dest_section_combo.show()
				self.dest_block_combo.show()
				
				# Force refresh of the tab widget
				self.tab_widget.repaint()
				QTimer.singleShot(50, lambda: self.tab_widget.currentWidget().repaint())
				
				print(f"[DEBUG] After visibility fix - Section combo visible: {self.dest_section_combo.isVisible()}")
				print(f"[DEBUG] After visibility fix - Block combo visible: {self.dest_block_combo.isVisible()}")
					
		except Exception as e:
			print(f"Error populating initial dropdowns: {e}")
			import traceback
			traceback.print_exc()

	def initialize_route_dropdowns(self):
		"""Initialize route dropdowns when Route Train tab is accessed"""
		# Initializing route dropdowns
		try:
			if hasattr(self, 'dest_line_combo') and self.dest_line_combo.count() > 0:
				self.populate_initial_dropdowns()
		except Exception as e:
			print(f"Error in initialize_route_dropdowns: {e}")
			import traceback
			traceback.print_exc()

	def apply_dropdown_alternating_colors(self):
		"""Apply alternating row colors and hover effects to dropdowns"""
		dropdowns = [self.dest_line_combo, self.dest_section_combo, self.dest_block_combo]
		for dropdown in dropdowns:
			if dropdown:
				# Apply styling directly to the combo box to ensure it takes effect
				dropdown.setStyleSheet("""
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
						alternate-background-color: #F5F5F5;
						show-decoration-selected: 1;
					}
					QComboBox QAbstractItemView::item {
						height: 25px;
						padding: 3px;
						border: none;
					}
					QComboBox QAbstractItemView::item:alternate {
						background-color: #F5F5F5;
					}
					QComboBox QAbstractItemView::item:hover {
						background-color: #E0E0E0;
						color: black;
					}
					QComboBox QAbstractItemView::item:selected {
						background-color: #3399FF;
						color: white;
					}
				""")
				# Enable alternating row colors on the view
				if dropdown.view():
					dropdown.view().setAlternatingRowColors(True)

	def create_enter_schedule_widget(self):
		"""Create the enter schedule widget for the left panel"""
		widget = QWidget()
		layout = QVBoxLayout()
		widget.setLayout(layout)

		# File upload section
		upload_frame = QFrame()
		upload_frame.setFrameStyle(QFrame.Box)
		upload_layout = QGridLayout()
		upload_frame.setLayout(upload_layout)

		upload_layout.addWidget(QLabel("Upload a file:"), 0, 0, 1, 3)
		
		self.schedule_file_entry = QLineEdit()
		self.schedule_file_entry.setText("schedule.csv")
		upload_layout.addWidget(self.schedule_file_entry, 1, 0, 1, 2)

		self.browse_btn = QPushButton("Browse...")
		self.browse_btn.clicked.connect(self.browse_schedule_file)
		upload_layout.addWidget(self.browse_btn, 1, 2)

		self.generate_routes_btn = QPushButton("Generate Routes")
		self.generate_routes_btn.clicked.connect(self.generate_routes_from_schedule)
		upload_layout.addWidget(self.generate_routes_btn, 2, 0, 1, 3)

		layout.addWidget(upload_frame)
		layout.addStretch()

		return widget

	def create_current_trains_table(self):
		"""Create the current trains table for the right panel"""
		table = QTableWidget()
		table.setColumnCount(9)
		table.setHorizontalHeaderLabels(['Train ID', 'Line', 'Location (Section)', 'Location (Block)', 
		                               'Destination (Section)', 'Destination (Block)', 'Departure Time', 'ETA', 'Speed (mph)'])
		table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
		table.horizontalHeader().setStretchLastSection(False)
		table.resizeColumnsToContents()
		# Set minimum widths for specific columns
		table.setColumnWidth(1, 140)  # Line column - increased for 20pt font
		table.setColumnWidth(6, 200)  # Departure Time column - increased for 20pt font
		table.setColumnWidth(7, 140)  # ETA column - increased for 20pt font
		table.verticalHeader().setDefaultSectionSize(18)
		table.setMinimumHeight(150)
		table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
		table.setSelectionBehavior(QAbstractItemView.SelectRows)
		table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Make table non-editable
		# Set fonts according to style guide: 20pt content for better readability
		table.setFont(QFont("Arial", 20))
		table.horizontalHeader().setFont(QFont("Arial", 16, QFont.Bold))
		return table

	def create_new_train_info_table(self):
		"""Create the new train info table for the right panel"""
		table = QTableWidget()
		table.setColumnCount(10)
		table.setHorizontalHeaderLabels(['Train ID', 'On Track', 'Moving', 'Line', 'Location (Section)', 
		                               'Location (Block)', 'Destination (Section)', 'Destination (Block)', 'Departure Time', 'ETA'])
		table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
		table.horizontalHeader().setStretchLastSection(False)
		table.resizeColumnsToContents()
		# Set minimum widths for specific columns
		table.setColumnWidth(3, 140)  # Line column (index 3 in this table) - increased for 20pt font
		table.setColumnWidth(8, 200)  # Departure Time column - increased for 20pt font
		table.setColumnWidth(9, 140)  # ETA column - increased for 20pt font
		table.verticalHeader().setDefaultSectionSize(18)
		table.setMinimumHeight(100)
		table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
		table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Make table non-editable
		# Set fonts according to style guide: 20pt content for better readability
		table.setFont(QFont("Arial", 20))
		table.horizontalHeader().setFont(QFont("Arial", 16, QFont.Bold))
		return table

	def create_route_train_info_table(self):
		"""Create the train info table for manual routing"""
		table = QTableWidget()
		table.setColumnCount(10)
		table.setHorizontalHeaderLabels(['Train ID', 'On Track', 'Moving', 'Line', 'Location (Section)', 
		                               'Location (Block)', 'Destination (Section)', 'Destination (Block)', 'Departure Time', 'ETA'])
		table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
		table.horizontalHeader().setStretchLastSection(False)
		table.resizeColumnsToContents()
		# Set minimum widths for specific columns
		table.setColumnWidth(3, 140)  # Line column (index 3 in this table) - increased for 20pt font
		table.setColumnWidth(8, 200)  # Departure Time column - increased for 20pt font
		table.setColumnWidth(9, 140)  # ETA column - increased for 20pt font
		table.verticalHeader().setDefaultSectionSize(24)  # Increased row height
		table.setMaximumHeight(80)  # Increased table height
		table.setMinimumHeight(80)  # Set minimum height too
		table.setRowCount(1)  # Single row for the train being routed
		table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Make table non-editable
		# Set fonts according to style guide: 20pt content for better readability
		table.setFont(QFont("Arial", 20))
		table.horizontalHeader().setFont(QFont("Arial", 16, QFont.Bold))
		return table

	def setup_close_block_tab(self):
		"""Setup the block closure tab"""
		close_widget = QWidget()
		close_layout = QVBoxLayout()
		close_widget.setLayout(close_layout)


		# Main content splitter
		main_splitter = QSplitter(Qt.Horizontal)
		main_splitter.setStyleSheet("""
			QSplitter::handle {
				background-color: #808080;
				width: 8px;
				border: 2px solid #606060;
				border-radius: 3px;
			}
		""")
		close_layout.addWidget(main_splitter)

		# Left side panel
		left_widget = QWidget()
		left_layout = QVBoxLayout()
		left_widget.setLayout(left_layout)

		# Tab-style buttons for Open Block / Close Block
		mode_layout = QHBoxLayout()
		self.open_block_mode_btn = QPushButton("Open Block")
		self.close_block_mode_btn = QPushButton("Close Block")
		
		# Style the buttons like tabs
		self.open_block_mode_btn.setCheckable(True)
		self.close_block_mode_btn.setCheckable(True)
		self.close_block_mode_btn.setChecked(True)  # Default to Close Block
		
		tab_style = """
			QPushButton {
				border: 1px solid #808080;
				border-bottom: none;
				background-color: #F0F0F0;
				padding: 8px 16px;
				color: black;
			}
			QPushButton:checked {
				background-color: white;
				border-bottom: 1px solid white;
			}
			QPushButton:!checked {
				background-color: #F0F0F0;
			}
			QPushButton:hover {
				background-color: #E0E0E0;
			}
			QPushButton:checked:hover {
				background-color: white;
			}
		"""
		self.open_block_mode_btn.setStyleSheet(tab_style)
		self.close_block_mode_btn.setStyleSheet(tab_style.replace("border-left: none;", ""))
		
		self.open_block_mode_btn.clicked.connect(self.set_open_block_mode)
		self.close_block_mode_btn.clicked.connect(self.set_close_block_mode)
		
		mode_layout.addWidget(self.open_block_mode_btn)
		mode_layout.addWidget(self.close_block_mode_btn)
		mode_layout.addStretch()
		left_layout.addLayout(mode_layout)

		# Block selection content
		selection_frame = QWidget()
		selection_frame.setStyleSheet("border: 1px solid #808080;")
		selection_layout = QVBoxLayout()
		selection_layout.setContentsMargins(15, 15, 15, 15)
		selection_layout.setSpacing(15)
		selection_frame.setLayout(selection_layout)

		# Choose Block To Close / Select Time for Block to Close sections
		block_section_layout = QHBoxLayout()
		block_section_layout.setSpacing(30)

		# Left side - Block selection
		block_widget = QWidget()
		block_layout = QVBoxLayout()
		block_layout.setContentsMargins(0, 0, 0, 0)
		block_layout.setSpacing(8)
		block_widget.setLayout(block_layout)

		block_title = QLabel("Choose Block To Close")
		block_title.setStyleSheet("border: none; font-weight: bold; margin-bottom: 5px;")
		block_title.setFont(QFont("Arial", 16, QFont.Bold))  # Header size per style guide
		block_layout.addWidget(block_title)
		
		# Line selection
		line_layout = QGridLayout()
		line_layout.setHorizontalSpacing(10)
		line_layout.setVerticalSpacing(5)
		line_label = QLabel("Line")
		line_label.setFixedWidth(60)
		line_layout.addWidget(line_label, 0, 0)
		self.close_line_combo = QComboBox()
		self.close_line_combo.addItems(self.selected_lines)
		self.close_line_combo.currentTextChanged.connect(self.update_close_sections)
		self.close_line_combo.setMinimumWidth(120)
		line_layout.addWidget(self.close_line_combo, 0, 1)
		block_layout.addLayout(line_layout)

		# Section selection
		section_layout = QGridLayout()
		section_layout.setHorizontalSpacing(10)
		section_layout.setVerticalSpacing(5)
		section_label = QLabel("Section")
		section_label.setFixedWidth(60)
		section_layout.addWidget(section_label, 0, 0)
		self.close_section_combo = QComboBox()
		self.close_section_combo.currentTextChanged.connect(self.update_close_blocks)
		self.close_section_combo.setMinimumWidth(120)
		section_layout.addWidget(self.close_section_combo, 0, 1)
		block_layout.addLayout(section_layout)

		# Block selection
		block_select_layout = QGridLayout()
		block_select_layout.setHorizontalSpacing(10)
		block_select_layout.setVerticalSpacing(5)
		block_select_label = QLabel("Block")
		block_select_label.setFixedWidth(60)
		block_select_layout.addWidget(block_select_label, 0, 0)
		self.close_block_combo = QComboBox()
		self.close_block_combo.setMinimumWidth(120)
		block_select_layout.addWidget(self.close_block_combo, 0, 1)
		block_layout.addLayout(block_select_layout)

		block_section_layout.addWidget(block_widget)

		# Right side - Time selection
		time_widget = QWidget()
		time_layout = QVBoxLayout()
		time_layout.setContentsMargins(0, 0, 0, 0)
		time_layout.setSpacing(8)
		time_widget.setLayout(time_layout)

		time_title = QLabel("Select Time for Block to Close")
		time_title.setStyleSheet("border: none; font-weight: bold; margin-bottom: 5px;")
		time_title.setFont(QFont("Arial", 16, QFont.Bold))  # Header size per style guide
		time_layout.addWidget(time_title)
		
		self.close_time_entry = QLineEdit()
		self.close_time_entry.setPlaceholderText("HH:MM")
		self.close_time_entry.setMaxLength(5)
		self.close_time_entry.setMinimumWidth(120)
		# Add time format validation
		time_regex = QRegExp("^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
		time_validator = QRegExpValidator(time_regex)
		self.close_time_entry.setValidator(time_validator)
		time_layout.addWidget(self.close_time_entry)

		# Add stretching space
		time_layout.addStretch()

		block_section_layout.addWidget(time_widget)
		selection_layout.addLayout(block_section_layout)

		# Close Block button
		self.close_block_btn = QPushButton("Close Block")
		self.close_block_btn.clicked.connect(self.handle_close_block_request)
		selection_layout.addWidget(self.close_block_btn)

		left_layout.addWidget(selection_frame)
		
		# Add scheduled closures table
		scheduled_frame = QFrame()
		scheduled_frame.setMaximumHeight(300)
		scheduled_layout = QVBoxLayout()
		scheduled_layout.setContentsMargins(10, 10, 10, 10)
		scheduled_frame.setLayout(scheduled_layout)
		
		scheduled_title = QLabel("Scheduled Block Closures & Openings")
		scheduled_title.setStyleSheet("border: none; font-weight: bold; margin-bottom: 5px;")
		scheduled_title.setFont(QFont("Arial", 16, QFont.Bold))  # Header size per style guide
		scheduled_layout.addWidget(scheduled_title)
		
		# Create scheduled closures table
		self.scheduled_closures_table = QTableWidget()
		self.scheduled_closures_table.setColumnCount(6)
		self.scheduled_closures_table.setHorizontalHeaderLabels(['Line', 'Section', 'Block', 'Type', 'Scheduled Time', 'Status'])
		self.scheduled_closures_table.setAlternatingRowColors(True)
		self.scheduled_closures_table.setSortingEnabled(True)
		self.scheduled_closures_table.verticalHeader().setDefaultSectionSize(20)
		self.scheduled_closures_table.setSelectionBehavior(QAbstractItemView.SelectRows)
		self.scheduled_closures_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
		self.scheduled_closures_table.setMaximumHeight(200)
		self.scheduled_closures_table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Make table non-editable
		# Set larger font for table
		self.scheduled_closures_table.setFont(QFont("Arial", 12))
		self.scheduled_closures_table.horizontalHeader().setFont(QFont("Arial", 18, QFont.Bold))
		scheduled_layout.addWidget(self.scheduled_closures_table)
		
		# Cancel scheduled closure button
		self.cancel_scheduled_btn = QPushButton("Cancel Selected")
		self.cancel_scheduled_btn.clicked.connect(self.cancel_selected_scheduled_closure)
		self.cancel_scheduled_btn.setMaximumHeight(40)
		scheduled_layout.addWidget(self.cancel_scheduled_btn)
		
		left_layout.addWidget(scheduled_frame)
		left_layout.addStretch()

		main_splitter.addWidget(left_widget)

		# Right side panel - Block chart
		right_widget = QWidget()
		right_layout = QVBoxLayout()
		right_widget.setLayout(right_layout)

		# Create block chart table (same styling as main page)
		self.close_block_table = self.create_close_block_table()
		right_layout.addWidget(self.close_block_table)

		# Select Block button
		self.select_block_btn = QPushButton("Select Block")
		self.select_block_btn.setMaximumHeight(40)
		self.select_block_btn.clicked.connect(self.select_block_from_chart)
		right_layout.addWidget(self.select_block_btn)

		main_splitter.addWidget(right_widget)

		# Set splitter proportions
		main_splitter.setSizes([400, 800])

		# Initialize dropdowns
		self.update_close_sections()
		
		# Apply styling to dropdowns
		QTimer.singleShot(100, self.apply_close_dropdown_styling)

		self.tab_widget.addTab(close_widget, "Open/Close Block")

	def create_close_block_table(self):
		"""Create the block chart table with same styling as main page"""
		table = QTableWidget()
		table.setColumnCount(9)
		table.setHorizontalHeaderLabels(['Line', 'Open?', 'Occupying Train', 'Section', 'Block', 
		                               'Speed Limit (mph)', 'Stop', 'Switch', 'Crossing'])
		table.setAlternatingRowColors(True)
		table.setSortingEnabled(True)
		table.verticalHeader().setDefaultSectionSize(16)
		table.setSelectionBehavior(QAbstractItemView.SelectRows)
		table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
		table.horizontalHeader().setStretchLastSection(False)
		# Set minimum widths for all columns to accommodate 20pt font
		table.setColumnWidth(0, 140)  # Line
		table.setColumnWidth(1, 90)   # Open?
		table.setColumnWidth(2, 180)  # Occupying Train
		table.setColumnWidth(3, 110)  # Section
		table.setColumnWidth(4, 90)   # Block
		table.setColumnWidth(5, 170)  # Speed Limit (mph)
		table.setColumnWidth(6, 90)   # Stop
		table.setColumnWidth(7, 110)  # Switch
		table.setColumnWidth(8, 110)  # Crossing
		
		# Remove automatic selection update - only update on button press
		
		# Initialize with block data (same as main page)
		self.initialize_close_block_table(table)
		table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Make table non-editable
		# Set fonts according to style guide: 20pt content for better readability
		table.setFont(QFont("Arial", 20))
		table.horizontalHeader().setFont(QFont("Arial", 16, QFont.Bold))
		
		return table

	def initialize_close_block_table(self, table):
		"""Initialize the close block table with all blocks"""
		table.setSortingEnabled(False)
		table.setUpdatesEnabled(False)

		all_blocks_data = []
		row_index = 0
		for line in self.selected_lines:
			blocks = self.trackReader.lines.get(line, [])
			for block in blocks:
				block_data = {
					"line": line,
					"block_number": block.block_number,
					"section": block.section,
					"block": str(block.block_number).zfill(4),
					"speed": str(int(block.speed_limit_kmh * 0.621371)),
					"stop": block.station.name if block.has_station and block.station else "",
					"switch": "●" if block.has_switch else "",
					"crossing": "●" if block.has_crossing else ""
				}
				all_blocks_data.append(block_data)
				row_index += 1

		table.setRowCount(len(all_blocks_data))

		for row, block_data in enumerate(all_blocks_data):
			table.setItem(row, 0, QTableWidgetItem(block_data["line"]))
			table.setItem(row, 1, QTableWidgetItem("●"))  # Filled circle = open
			table.setItem(row, 2, QTableWidgetItem(""))    # Occupying Train
			table.setItem(row, 3, QTableWidgetItem(block_data["section"]))
			table.setItem(row, 4, QTableWidgetItem(block_data["block"]))
			table.setItem(row, 5, QTableWidgetItem(block_data["speed"]))
			table.setItem(row, 6, QTableWidgetItem(block_data["stop"]))
			table.setItem(row, 7, QTableWidgetItem(block_data["switch"]))
			table.setItem(row, 8, QTableWidgetItem(block_data["crossing"]))

		table.setUpdatesEnabled(True)
		table.setSortingEnabled(True)
		table.sortItems(0, Qt.AscendingOrder)


	def set_open_block_mode(self):
		"""Switch to open block mode"""
		self.open_block_mode_btn.setChecked(True)
		self.close_block_mode_btn.setChecked(False)
		self.close_block_btn.setText("Open Block")

	def set_close_block_mode(self):
		"""Switch to close block mode"""
		self.open_block_mode_btn.setChecked(False)
		self.close_block_mode_btn.setChecked(True)
		self.close_block_btn.setText("Close Block")

	def select_block_from_chart(self):
		"""Fill block selector with selected block from chart"""
		selected_items = self.close_block_table.selectedItems()
		if selected_items:
			row = selected_items[0].row()
			line_item = self.close_block_table.item(row, 0)
			section_item = self.close_block_table.item(row, 3)
			block_item = self.close_block_table.item(row, 4)
			
			if line_item and section_item and block_item:
				line_text = line_item.text()
				section_text = section_item.text()
				block_text = block_item.text()
				
				
				# Set the line first to trigger section update
				self.close_line_combo.setCurrentText(line_text)
				
				# Wait for the section combo to be populated, then set section
				# This ensures the section dropdown is properly updated with the correct line's sections
				def set_section_and_block():
					if section_text in [self.close_section_combo.itemText(i) for i in range(self.close_section_combo.count())]:
						self.close_section_combo.setCurrentText(section_text)
						# Wait for block combo to be populated, then set block
						def set_block():
							# Now that blocks are formatted with leading zeros, direct match should work
							target_block = block_text  # This should be in format like "0003"
							block_found = False
							for i in range(self.close_block_combo.count()):
								combo_text = self.close_block_combo.itemText(i)
								if combo_text == target_block:
									self.close_block_combo.setCurrentIndex(i)
									block_found = True
									break
							
							if not block_found:
								print(f"Warning: Block {target_block} not found in dropdown. Available: {[self.close_block_combo.itemText(i) for i in range(self.close_block_combo.count())]}")
						
						QTimer.singleShot(50, set_block)
				
				QTimer.singleShot(50, set_section_and_block)
		else:
			StyledMessageBox.warning(self, "No Selection", "Please select a block from the chart first")

	def update_close_sections(self):
		"""Update close sections when line changes"""
		line = self.close_line_combo.currentText()
		sections = self.get_sections_for_line(line)
		
		self.close_section_combo.clear()
		self.close_section_combo.addItems(sections)
		self.update_close_blocks()
		# Re-apply styling after updating dropdown content
		QTimer.singleShot(50, self.apply_close_dropdown_styling)

	def update_close_blocks(self):
		"""Update close blocks when section changes"""
		line = self.close_line_combo.currentText()
		section = self.close_section_combo.currentText()
		blocks = self.get_blocks_for_section(line, section)
		
		self.close_block_combo.clear()
		# Format blocks with leading zeros to match table format
		self.close_block_combo.addItems([str(block).zfill(4) for block in blocks])
		# Re-apply styling after updating dropdown content
		QTimer.singleShot(50, self.apply_close_dropdown_styling)

	def apply_close_dropdown_styling(self):
		"""Apply styling to close block tab dropdowns"""
		dropdowns = [self.close_line_combo, self.close_section_combo, self.close_block_combo]
		for dropdown in dropdowns:
			if dropdown:
				dropdown.setStyleSheet("""
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
						alternate-background-color: #F5F5F5;
						show-decoration-selected: 1;
					}
					QComboBox QAbstractItemView::item {
						height: 25px;
						padding: 3px;
						border: none;
					}
					QComboBox QAbstractItemView::item:alternate {
						background-color: #F5F5F5;
					}
					QComboBox QAbstractItemView::item:hover {
						background-color: #E0E0E0;
						color: black;
					}
					QComboBox QAbstractItemView::item:selected {
						background-color: #3399FF;
						color: white;
					}
				""")
				if dropdown.view():
					dropdown.view().setAlternatingRowColors(True)

	def check_block_close_possibility(self, line, block_num, close_time):
		"""Check if block can be closed at the requested time"""
		# Check for active trains using this block
		if self.ctc_system:
			block = self.ctc_system.get_block_by_line(line, block_num)
			if block and hasattr(block, 'occupied') and block.occupied:
				return False, "Block currently occupied by train"
		
		# Check for scheduled routes using this block around the close time
		# This would need integration with route scheduling system
		# For now, allow all closures unless block is occupied
		return True, None

	def handle_close_block_request(self):
		"""Handle the close block scheduling request"""
		line = self.close_line_combo.currentText()
		section = self.close_section_combo.currentText()
		block_text = self.close_block_combo.currentText()
		close_time = self.close_time_entry.text().strip()
		
		is_open_mode = self.open_block_mode_btn.isChecked()
		action = "open" if is_open_mode else "close"
		
		if not line or not section or not block_text:
			StyledMessageBox.warning(self, "Input Error", f"Please select a block to {action}")
			return
		
		if not close_time:
			StyledMessageBox.warning(self, "Input Error", f"Please enter a time for block {action}")
			return
		
		try:
			block_num = int(block_text)
		except ValueError:
			StyledMessageBox.warning(self, "Input Error", "Invalid block number")
			return
		
		if is_open_mode:
			# Handle scheduled open block
			try:
				# Parse time and create datetime for today
				from datetime import datetime, time
				hour, minute = map(int, close_time.split(':'))
				today = _get_simulation_time().date()
				scheduled_time = datetime.combine(today, time(hour, minute))
				
				# If the time is in the past, schedule for tomorrow
				if scheduled_time <= _get_simulation_time():
					from datetime import timedelta
					scheduled_time += timedelta(days=1)
				
				# Check if block is currently closed or scheduled for closure
				block = self.ctc_system.get_block_by_line(line, block_num)
				if block:
					
					# Check if block is currently closed using display manager
					line = getattr(block, 'line', 'Unknown')
					block_num = getattr(block, 'blockID', 0)
					is_closed = self.display_manager.is_block_closed(line, block_num, failure_manager=self.failure_manager)
					
					# Check if block has a scheduled closure before the opening time
					has_scheduled_closure = False
					closure_time = None
					if hasattr(self.communication_handler, 'scheduledClosures'):
						for scheduled_block, sched_time in self.communication_handler.scheduledClosures:
							if (getattr(scheduled_block, 'blockID', -1) == getattr(block, 'blockID', -2) and 
								getattr(scheduled_block, 'line', '') == line and 
								sched_time < scheduled_time):
								has_scheduled_closure = True
								closure_time = sched_time
								break
					
					if is_closed or has_scheduled_closure:
						# Schedule opening with communication handler
						self.communication_handler.schedule_opening(block, scheduled_time)
						if has_scheduled_closure:
							result = {"success": True, "message": f"Block {block_num} on {line} line opening scheduled for {scheduled_time} (after scheduled closure at {closure_time.strftime('%H:%M')})"}
						else:
							result = {"success": True, "message": f"Block {block_num} on {line} line opening scheduled for {scheduled_time}"}
					else:
						result = {"success": False, "message": f"Block {block_num} on {line} line cannot be scheduled for opening - it is not closed or scheduled for closure"}
				else:
					result = {"success": False, "message": f"Block {block_num} not found"}
				
				if result['success']:
					StyledMessageBox.information(self, "Success", result['message'])
					self.update_scheduled_closures_display()
					# Clear the form
					self.close_time_entry.clear()
				else:
					StyledMessageBox.warning(self, "Error", result['message'])
					
			except ValueError:
				StyledMessageBox.warning(self, "Input Error", "Please enter time in HH:MM format")
		else:
			# Handle schedule close block
			try:
				# Parse time and create datetime for today
				from datetime import datetime, time
				hour, minute = map(int, close_time.split(':'))
				today = _get_simulation_time().date()
				scheduled_time = datetime.combine(today, time(hour, minute))
				
				# If the time is in the past, schedule for tomorrow
				if scheduled_time <= _get_simulation_time():
					from datetime import timedelta
					scheduled_time += timedelta(days=1)
				
				# Schedule the closure
				# Use CTC system to schedule closure with line-aware block retrieval
				block = self.ctc_system.get_block_by_line(line, block_num)
				if block:
					if hasattr(self.ctc_system, 'validate_closure'):
						if self.ctc_system.validate_closure(block, scheduled_time):
							# Schedule closure with communication handler
							self.communication_handler.schedule_closure(block, scheduled_time)
							result = {"success": True, "message": f"Block {block_num} on {line} line closure scheduled for {scheduled_time}"}
						else:
							result = {"success": False, "message": f"Cannot schedule closure for block {block_num}"}
					else:
						# If no validation method, schedule anyway
						self.communication_handler.schedule_closure(block, scheduled_time)
						result = {"success": True, "message": f"Block {block_num} on {line} line closure scheduled for {scheduled_time}"}
				else:
					result = {"success": False, "message": f"Block {block_num} not found"}
				
				if result['success']:
					StyledMessageBox.information(self, "Success", result['message'])
					self.update_scheduled_closures_display()
					# Clear the form
					self.close_time_entry.clear()
				else:
					StyledMessageBox.warning(self, "Error", result['message'])
					
			except ValueError:
				StyledMessageBox.warning(self, "Input Error", "Please enter time in HH:MM format")

	def show_block_occupied_popup(self, earliest_time):
		"""Show the block occupied popup"""
		popup = StyledMessageBox(self)
		popup.setWindowTitle("Block Occupied")
		popup.setText("The block is currently occupied or will be occupied at the time you scheduled to close it by train 1234. "
		              "The earliest time the block can be closed is 05:00. Would you like to change the block closure time to 05:00 "
		              "or request train reroute using the route train tab?")
		
		# Make popup much wider and taller to fit text and buttons properly
		popup.setMinimumWidth(700)
		popup.setMinimumHeight(200)
		
		# Set word wrap for better text display
		popup.setStyleSheet(popup.styleSheet() + """
			QMessageBox QLabel {
				max-width: 650px;
				word-wrap: break-word;
				qproperty-wordWrap: true;
			}
		""")
		
		# Custom buttons
		use_time_btn = popup.addButton("Use Modified Time", QMessageBox.AcceptRole)
		cancel_btn = popup.addButton("Cancel (use route train tab to reroute trains)", QMessageBox.RejectRole)
		
		popup.setDefaultButton(use_time_btn)
		result = popup.exec_()
		
		if popup.clickedButton() == use_time_btn:
			# Update time field with the returned time
			self.close_time_entry.setText(earliest_time)
		# If cancel is clicked, just close the popup (do nothing)

	def show_confirm_open_popup(self, line, section, block_num, open_time):
		"""Show the confirm open block popup"""
		popup = StyledMessageBox(self)
		popup.setWindowTitle("Confirm Open Block")
		popup.setText(f"Do you confirm that you want to open this block at the specified time?\n\n"
		              f"Line: {line}\nSection: {section}\nBlock: {block_num}\nTime: {open_time}")
		
		popup.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
		popup.setDefaultButton(QMessageBox.Yes)
		
		result = popup.exec_()
		
		if result == QMessageBox.Yes:
			# Actually open the block
			self.execute_block_opening(line, block_num, open_time)

	def show_confirm_close_popup(self, line, section, block_num, close_time):
		"""Show the confirm close block popup"""
		popup = StyledMessageBox(self)
		popup.setWindowTitle("Confirm Close Block")
		popup.setText(f"Do you confirm that you want to close this block at the specified time?\n\n"
		              f"Line: {line}\nSection: {section}\nBlock: {block_num}\nTime: {close_time}")
		
		popup.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
		popup.setDefaultButton(QMessageBox.Yes)
		
		result = popup.exec_()
		
		if result == QMessageBox.Yes:
			# Actually close the block
			self.execute_block_closure(line, block_num, close_time)

	def execute_block_opening(self, line, block_num, open_time):
		"""Execute the actual block opening"""
		# Use the new line-aware block retrieval method
		block = self.ctc_system.get_block_by_line(line, block_num)
		if block:
			if hasattr(self.failure_manager, 'remove_failed_block'):
				self.failure_manager.remove_failed_block(block)
				result = {"success": True, "message": f"Block {block_num} on {line} line opened"}
			else:
				result = {"success": True, "message": f"Block {block_num} on {line} line opened"}
		else:
			result = {"success": False, "message": f"Block {block_num} not found on {line} line"}
		
		if result["success"]:
			StyledMessageBox.information(self, "Block Opened", 
			                           f"Block {block_num} on {line} line has been scheduled for opening at {open_time}")
			# Update the table display
			self.update_close_block_table_display()
		else:
			StyledMessageBox.warning(self, "Error", result["message"])

	def execute_block_closure(self, line, block_num, close_time):
		"""Execute the actual block closure"""
		# Use the new line-aware block retrieval method
		block = self.ctc_system.get_block_by_line(line, block_num)
		if block:
			if hasattr(self.failure_manager, 'add_failed_block'):
				self.failure_manager.add_failed_block(block)
				result = {"success": True, "message": f"Block {block_num} on {line} line closed"}
			else:
				result = {"success": True, "message": f"Block {block_num} on {line} line closed"}
		else:
			result = {"success": False, "message": f"Block {block_num} not found on {line} line"}
		
		if result["success"]:
			StyledMessageBox.information(self, "Block Closed", 
			                           f"Block {block_num} on {line} line has been scheduled for closure at {close_time}")
			# Update the table display
			self.update_close_block_table_display()
		else:
			StyledMessageBox.warning(self, "Error", result["message"])

	def update_close_block_table_display(self):
		"""Update the close block table display"""
		# Update the close block table similar to main page block table
		for row in range(self.close_block_table.rowCount()):
			line_item = self.close_block_table.item(row, 0)
			block_item = self.close_block_table.item(row, 4)

			if line_item and block_item:
				line = line_item.text()
				block_num = int(block_item.text())

				# Update Open? column (column 1)
				open_item = self.close_block_table.item(row, 1)
				# Check if block is failed/closed using display manager
				is_closed = self.display_manager.is_block_closed(line, block_num, failure_manager=self.failure_manager)
				open_text = "○" if is_closed else "●"  # ● = filled circle (open), ○ = empty circle (closed)
				if open_item:
					open_item.setText(open_text)



	# Update methods (using separated business logic)

	def update_table_displays(self):
		"""Medium frequency update - table content only"""
		self.update_train_info_table()
		self.update_block_info_table()
		self.update_warnings_table()
		# Update scheduled closures to reflect automatic status changes
		self.update_scheduled_closures_display()
		self.detect_and_handle_conflicts()
		# Keep tables compact after updates
# Removed compact tables functionality that affects map size
		# Note: Compact table sizing removed per user request

	def update_visual_displays(self):
		"""Low frequency update - visual charts and plots"""
		if self.trackNeedsRedraw:
			self.create_track_visualization()
			# Also update the route track widget if it exists
			if hasattr(self, 'route_track_widget'):
				self.update_route_track_visualization()

	def update_train_info_table(self):
		"""Update the train information table using display manager data - show only routed trains"""
		all_train_data = self.display_manager.get_train_info_for_display(
			trains=self.ctc_system.trains,
			train_suggested_speeds=self.ctc_system.trainSuggestedSpeeds
		)
		# Filter to show only routed trains
		train_data = [data for data in all_train_data if data['routing_status'] == "Routed"]
		self.train_info_table.setRowCount(len(train_data))

		for row, data in enumerate(train_data):
			self.train_info_table.setItem(row, 0, QTableWidgetItem(data['train_id']))
			self.train_info_table.setItem(row, 1, QTableWidgetItem(data['line']))
			self.train_info_table.setItem(row, 2, QTableWidgetItem(data['section_location']))
			self.train_info_table.setItem(row, 3, QTableWidgetItem(data['block_location']))
			self.train_info_table.setItem(row, 4, QTableWidgetItem(data.get('destination_section', '')))
			self.train_info_table.setItem(row, 5, QTableWidgetItem(data['destination_block']))
			self.train_info_table.setItem(row, 6, QTableWidgetItem(data.get('departure_time', '')))
			self.train_info_table.setItem(row, 7, QTableWidgetItem(data.get('eta', '')))
			self.train_info_table.setItem(row, 8, QTableWidgetItem(data['speed']))

		# Also update the current trains table in Route Train tab if it exists
		if hasattr(self, 'current_trains_table'):
			self.update_current_trains_table(train_data)

	def update_current_trains_table(self, filtered_train_data):
		"""Update the current trains table in the Route Train tab - show all existing trains for rerouting"""
		# For rerouting, we want to show ALL trains on track, not just routed ones
		if hasattr(self, 'ctc_system') and self.ctc_system:
			all_train_data = self.display_manager.get_train_info_for_display(
				trains=self.ctc_system.trains,
				train_suggested_speeds=self.ctc_system.trainSuggestedSpeeds
			)
		else:
			all_train_data = []
			
		self.current_trains_table.setRowCount(len(all_train_data))

		for row, data in enumerate(all_train_data):
			self.current_trains_table.setItem(row, 0, QTableWidgetItem(data['train_id']))
			self.current_trains_table.setItem(row, 1, QTableWidgetItem(data['line']))
			self.current_trains_table.setItem(row, 2, QTableWidgetItem(data['section_location']))
			self.current_trains_table.setItem(row, 3, QTableWidgetItem(data['block_location']))
			self.current_trains_table.setItem(row, 4, QTableWidgetItem(data.get('destination_section', '')))
			self.current_trains_table.setItem(row, 5, QTableWidgetItem(data['destination_block']))
			self.current_trains_table.setItem(row, 6, QTableWidgetItem(data.get('departure_time', '')))
			self.current_trains_table.setItem(row, 7, QTableWidgetItem(data.get('eta', '')))
			self.current_trains_table.setItem(row, 8, QTableWidgetItem(data['speed']))

	def update_warnings_table(self):
		"""Update the warnings table using display manager"""
		warnings = self.display_manager.get_warnings(
			failure_manager=self.failure_manager,
			track_status=self.ctc_system.trackStatus,
			railway_crossings=self.ctc_system.railwayCrossings
		)
		
		self.warnings_table.setRowCount(len(warnings))

		for row, warning in enumerate(warnings):
			self.warnings_table.setItem(row, 0, QTableWidgetItem(warning["type"]))
			self.warnings_table.setItem(row, 1, QTableWidgetItem(warning["train"]))
			self.warnings_table.setItem(row, 2, QTableWidgetItem(warning["line"]))
			self.warnings_table.setItem(row, 3, QTableWidgetItem(warning["section"]))
			self.warnings_table.setItem(row, 4, QTableWidgetItem(warning["block"]))
			resolved_text = "●" if warning["resolved"] else "○"
			self.warnings_table.setItem(row, 5, QTableWidgetItem(resolved_text))
	
	def detect_and_handle_conflicts(self):
		"""Detect emergencies and handle them - simplified"""
		try:
			# Detect all emergencies using the new threshold-based system
			if self.ctc_system.failureManager:
				emergencies = self.ctc_system.failureManager.detect_train_emergencies()
				
				if emergencies:
					# Show warning for emergencies (new format: list of dicts)
					for emergency_dict in emergencies:
						# Log the emergency for dispatcher attention
						emergency_msg = emergency_dict.get('description', 'Unknown emergency')
						print(f"Warning detected: {emergency_msg}")
						
		except Exception as e:
			# Don't let conflict detection errors crash the UI
			print(f"Error in conflict detection: {e}")
	
	

	def update_block_info_table(self):
		"""Update the block info table with current train positions"""
		# Build current train positions
		current_positions = {}
		for train_id, train in self.ctc_system.trains.items():
			current_positions[(train.line, self.get_block_number(train.currentBlock))] = train_id

		# Only update rows that have changed
		for row in range(self.block_info_table.rowCount()):
			line_item = self.block_info_table.item(row, 0)
			block_item = self.block_info_table.item(row, 4)  # Block column moved to position 4

			if line_item and block_item:
				line = line_item.text()
				block_num = int(block_item.text())
				key = (line, block_num)

				# Update Open? column (column 1)
				open_item = self.block_info_table.item(row, 1)
				# Use display manager as single source of truth for block closure status
				is_closed = self.display_manager.is_block_closed(line, block_num, failure_manager=self.failure_manager)
				open_text = "○" if is_closed else "●"  # ● = filled circle (open), ○ = empty circle (closed)
				if open_item:
					if open_item.text() != open_text:
						open_item.setText(open_text)
						# Block status updated
				else:
					self.block_info_table.setItem(row, 1, QTableWidgetItem(open_text))

				# Update train position (column 2)
				train_item = self.block_info_table.item(row, 2)
				if key in current_positions:
					new_text = current_positions[key]
					if train_item:
						if train_item.text() != new_text:
							train_item.setText(new_text)
					else:
						self.block_info_table.setItem(row, 2, QTableWidgetItem(new_text))
				else:
					if train_item and train_item.text():
						train_item.setText("")

	# Route Train Tab Event Handlers
	def set_manual_mode(self):
		"""Switch to manual route mode"""
		self.manually_route_btn.setChecked(True)
		self.enter_schedule_btn.setChecked(False)
		self.manually_route_widget.setVisible(True)
		self.enter_schedule_widget.setVisible(False)

	def set_schedule_mode(self):
		"""Switch to schedule mode"""
		self.manually_route_btn.setChecked(False)
		self.enter_schedule_btn.setChecked(True)
		self.manually_route_widget.setVisible(False)
		self.enter_schedule_widget.setVisible(True)

	def is_valid_train_id_for_routing(self, train_id: str) -> bool:
		"""
		Check if a train ID is valid for routing.
		Valid IDs are either:
		1. Existing trains on the track
		2. Next available train ID for the line
		"""
		try:
			# Check if CTC system is available
			if not hasattr(self, 'ctc_system') or not self.ctc_system:
				return False
				
			if not train_id or not self.ctc_system.is_valid_train_id(train_id):
				return False
			
			# Check if train already exists
			if train_id in self.ctc_system.trains:
				return True
			
			# Check if it's the next available train ID for the line
			line = self.ctc_system.get_line_from_train_id(train_id)
			next_available = self.ctc_system.get_next_id_preview(line)
			return train_id == next_available
		except (ValueError, AttributeError):
			return False

	def check_train_id(self):
		"""Check if train ID exists and populate train information"""
		train_id = self.route_train_id_entry.text().strip()
		print(f"Debug: check_train_id called with train_id: '{train_id}'")
		if not train_id:
			return

		# Validate train ID and provide visual feedback
		if not self.is_valid_train_id_for_routing(train_id):
			# Invalid train ID - show red border and error
			self.route_train_id_entry.setStyleSheet("border: 2px solid red;")
			self.show_train_id_error(train_id)
			print(f"Debug: Invalid train ID: {train_id}")
			return
		else:
			# Valid train ID - show green border
			self.route_train_id_entry.setStyleSheet("border: 2px solid green;")
			print(f"Debug: Valid train ID: {train_id}")

		# Clear the table first
		for col in range(self.route_train_info_table.columnCount()):
			self.route_train_info_table.setItem(0, col, QTableWidgetItem(""))

		# Set the train ID
		self.route_train_info_table.setItem(0, 0, QTableWidgetItem(train_id))

		# Check if train exists in current trains
		train_exists = train_id in self.ctc_system.trains
		
		if train_exists:
			train = self.ctc_system.trains[train_id]
			# Populate with actual train data
			self.route_train_info_table.setItem(0, 1, QTableWidgetItem("●"))  # On Track
			self.route_train_info_table.setItem(0, 2, QTableWidgetItem("●"))  # Moving
			self.route_train_info_table.setItem(0, 3, QTableWidgetItem(train.line))
			
			# Get section for current block
			current_section = self.get_section_for_block(train.line, train.currentBlock)
			self.route_train_info_table.setItem(0, 4, QTableWidgetItem(current_section))
			self.route_train_info_table.setItem(0, 5, QTableWidgetItem(str(self.get_block_number(train.currentBlock))))
			
			# Destination info (if available)
			if hasattr(train, 'destinationBlock') or hasattr(train, 'destination'):
				dest_block = getattr(train, 'destinationBlock', getattr(train, 'destination', None))
				if dest_block:
					dest_section = self.get_section_for_block(train.line, dest_block)
					self.route_train_info_table.setItem(0, 6, QTableWidgetItem(dest_section))
					self.route_train_info_table.setItem(0, 7, QTableWidgetItem(str(dest_block)))
			
			# Show departure time and ETA
			departure_time = getattr(train, 'departureTime', getattr(train, 'departure_time', None))
			if departure_time:
				departure_text = departure_time.strftime('%H:%M') if hasattr(departure_time, 'strftime') else str(departure_time)
			else:
				departure_text = ""  # No departure time available
			self.route_train_info_table.setItem(0, 8, QTableWidgetItem(departure_text))
			
			# ETA - calculate based on destination if available
			eta_text = ""
			if hasattr(train, 'destinationBlock') or hasattr(train, 'destination'):
				dest_block = getattr(train, 'destinationBlock', getattr(train, 'destination', None))
				if dest_block:
					# Try to get ETA from train attributes
					eta = getattr(train, 'eta', getattr(train, 'arrival_time', None))
					if eta:
						eta_text = eta.strftime('%H:%M') if hasattr(eta, 'strftime') else str(eta)
					else:
						# Calculate ETA based on current time and route
						from datetime import datetime, timedelta
						current_time = _get_simulation_time()
						# Use a default 30 minutes if no route info available
						eta_datetime = current_time + timedelta(minutes=30)
						eta_text = eta_datetime.strftime('%H:%M')
			self.route_train_info_table.setItem(0, 9, QTableWidgetItem(eta_text))

			# Highlight train in current trains table
			self.highlight_train_in_current_table(train_id)
		else:
			# Train doesn't exist - set unchecked indicators and blanks
			self.route_train_info_table.setItem(0, 1, QTableWidgetItem("○"))  # Not On Track
			self.route_train_info_table.setItem(0, 2, QTableWidgetItem("○"))  # Not Moving
			# Leave other fields blank

	def update_route_train_info(self, train_id):
		"""Update the route train info table with current train data"""
		try:
			# Clear the table first
			for col in range(self.route_train_info_table.columnCount()):
				self.route_train_info_table.setItem(0, col, QTableWidgetItem(""))

			# Set the train ID
			self.route_train_info_table.setItem(0, 0, QTableWidgetItem(train_id))

			# Check if train exists in current trains
			train_exists = train_id in self.ctc_system.trains
			
			if train_exists:
				train = self.ctc_system.trains[train_id]
				# Populate with actual train data
				self.route_train_info_table.setItem(0, 1, QTableWidgetItem("●"))  # On Track
				self.route_train_info_table.setItem(0, 2, QTableWidgetItem("●"))  # Moving
				self.route_train_info_table.setItem(0, 3, QTableWidgetItem(train.line))
				
				# Get section for current block
				current_section = self.get_section_for_block(train.line, train.currentBlock)
				self.route_train_info_table.setItem(0, 4, QTableWidgetItem(current_section))
				self.route_train_info_table.setItem(0, 5, QTableWidgetItem(str(self.get_block_number(train.currentBlock))))
				
				# Destination info (if available)
				if hasattr(train, 'destinationBlock') or hasattr(train, 'destination'):
					dest_block = getattr(train, 'destinationBlock', getattr(train, 'destination', None))
					if dest_block:
						dest_section = self.get_section_for_block(train.line, dest_block)
						self.route_train_info_table.setItem(0, 6, QTableWidgetItem(dest_section))
						self.route_train_info_table.setItem(0, 7, QTableWidgetItem(str(dest_block)))
				
				# Show departure time and ETA
				departure_time = getattr(train, 'departureTime', getattr(train, 'departure_time', None))
				if departure_time:
					departure_text = departure_time.strftime('%H:%M') if hasattr(departure_time, 'strftime') else str(departure_time)
				else:
					departure_text = ""  # No departure time available
				self.route_train_info_table.setItem(0, 8, QTableWidgetItem(departure_text))
				
				# ETA - calculate based on destination if available
				eta_text = ""
				if hasattr(train, 'destinationBlock') or hasattr(train, 'destination'):
					dest_block = getattr(train, 'destinationBlock', getattr(train, 'destination', None))
					if dest_block:
						# Try to get ETA from train attributes
						eta = getattr(train, 'eta', getattr(train, 'arrival_time', None))
						if eta:
							eta_text = eta.strftime('%H:%M') if hasattr(eta, 'strftime') else str(eta)
						else:
							# Calculate ETA based on current time and route
							from datetime import datetime, timedelta
							current_time = _get_simulation_time()
							# Use a default 30 minutes if no route info available
							eta_datetime = current_time + timedelta(minutes=30)
							eta_text = eta_datetime.strftime('%H:%M')
				self.route_train_info_table.setItem(0, 9, QTableWidgetItem(eta_text))

				# Highlight train in current trains table
				self.highlight_train_in_current_table(train_id)
			else:
				# Train doesn't exist - set unchecked indicators and blanks
				self.route_train_info_table.setItem(0, 1, QTableWidgetItem("○"))  # Not On Track
				self.route_train_info_table.setItem(0, 2, QTableWidgetItem("○"))  # Not Moving
				
		except Exception as e:
			logger.error(f"Error updating route train info: {e}")

	def validate_train_id_input(self):
		"""Provide real-time visual feedback for train ID input"""
		try:
			train_id = self.route_train_id_entry.text().strip()
			
			if not train_id:
				# Clear styling when empty
				self.route_train_id_entry.setStyleSheet("")
				return
			
			# Check if trainManager is available
			if not hasattr(self, 'ctc_system') or not self.ctc_system:
				# TrainManager not ready yet, use neutral styling
				self.route_train_id_entry.setStyleSheet("")
				return
			
			if len(train_id) == 4 and self.is_valid_train_id_for_routing(train_id):
				# Valid train ID - green border
				self.route_train_id_entry.setStyleSheet("border: 2px solid green;")
			elif len(train_id) == 4:
				# Invalid train ID - red border  
				self.route_train_id_entry.setStyleSheet("border: 2px solid red;")
			else:
				# Incomplete - neutral styling
				self.route_train_id_entry.setStyleSheet("")
		except Exception as e:
			# If any error occurs, just use neutral styling to avoid breaking the UI
			self.route_train_id_entry.setStyleSheet("")

	def show_train_id_error(self, train_id):
		"""Show error message for invalid train ID"""
		try:
			# Check if trainManager is available
			if not hasattr(self, 'ctc_system') or not self.ctc_system or not hasattr(self.ctc_system, 'id_manager'):
				error_msg = f"Invalid train ID: {train_id}\n\nSystem not ready. Please try again."
				QMessageBox.warning(self, "Invalid Train ID", error_msg)
				return
				
			line = self.ctc_system.id_manager.get_line_from_train_id(train_id)
			next_available = self.ctc_system.id_manager.get_next_id_preview(line)
			existing_trains = [tid for tid in self.ctc_system.trains.keys() 
							   if self.ctc_system.id_manager.get_line_from_train_id(tid) == line]
			
			if existing_trains:
				error_msg = f"Invalid train ID: {train_id}\n\n"
				error_msg += f"Valid train IDs for {line} line:\n"
				error_msg += f"• Existing trains: {', '.join(existing_trains)}\n"
				error_msg += f"• Next available: {next_available}"
			else:
				error_msg = f"Invalid train ID: {train_id}\n\n"
				error_msg += f"No trains currently on {line} line.\n"
				error_msg += f"Next available train ID: {next_available}"
		except (ValueError, AttributeError):
			error_msg = f"Invalid train ID format: {train_id}\n\n"
			error_msg += "Valid format: Letter + 3 digits (e.g., B001, G002, R003)\n"
			error_msg += "B = Blue line, G = Green line, R = Red line"
		
		QMessageBox.warning(self, "Invalid Train ID", error_msg)

	def highlight_train_in_current_table(self, train_id):
		"""Highlight a train in the current trains table"""
		for row in range(self.current_trains_table.rowCount()):
			item = self.current_trains_table.item(row, 0)  # Train ID column
			if item and item.text() == train_id:
				self.current_trains_table.selectRow(row)
				break

	def get_block_number(self, block_obj):
		"""Extract block number from Block object or return as-is if already a number"""
		if hasattr(block_obj, 'blockID'):
			return block_obj.blockID
		elif hasattr(block_obj, 'blockNumber'):
			return block_obj.blockNumber
		elif isinstance(block_obj, (int, float)):
			return int(block_obj)
		else:
			# Try to extract number from string representation
			try:
				return int(str(block_obj))
			except ValueError:
				return 1  # Default fallback

	def get_section_for_block(self, line, block_num):
		"""Get the section name for a given block"""
		# Extract block number if it's a Block object
		block_num = self.get_block_number(block_num)
		blocks = self.trackReader.lines.get(line, [])
		for block in blocks:
			if block.block_number == block_num:
				return block.section
		return ""

	def update_dest_sections(self):
		"""Update destination sections when line changes"""
		try:
			line = self.dest_line_combo.currentText()
			sections = self.get_sections_for_line(line)
			
			self.dest_section_combo.clear()
			self.dest_section_combo.addItems(sections)
			
			# Set default selection if sections are available
			if sections:
				self.dest_section_combo.setCurrentIndex(0)
			
			self.update_dest_blocks()
			# Re-apply styling after updating dropdown content
			QTimer.singleShot(50, self.apply_dropdown_alternating_colors)
			print('Dropdown section updated')
		except Exception as e:
			print(f"Error updating destination sections: {e}")
			# Continue without breaking the UI

	def update_dest_blocks(self):
		"""Update destination blocks when section changes"""
		try:
			line = self.dest_line_combo.currentText()
			section = self.dest_section_combo.currentText()
			blocks = self.get_blocks_for_section(line, section)
			
			self.dest_block_combo.clear()
			self.dest_block_combo.addItems([str(block) for block in blocks])
			
			# Set default selection if blocks are available
			if blocks:
				self.dest_block_combo.setCurrentIndex(0)
			
			# Re-apply styling after updating dropdown content
			QTimer.singleShot(50, self.apply_dropdown_alternating_colors)
			print('Dropdown block updated')
		except Exception as e:
			print(f"Error updating destination blocks: {e}")
			# Continue without breaking the UI

	def get_sections_for_line(self, line):
		"""Get all sections for a line"""
		try:
			if not hasattr(self, 'trackReader') or not self.trackReader:
				return []
			blocks = self.trackReader.lines.get(line, [])
			sections = list(set(block.section for block in blocks))
			return sorted(sections)
		except Exception as e:
			print(f"Error getting sections for line {line}: {e}")
			return []

	def get_blocks_for_section(self, line, section):
		"""Get all blocks for a section"""
		try:
			if not hasattr(self, 'trackReader') or not self.trackReader:
				return []
			blocks = self.trackReader.lines.get(line, [])
			block_nums = [block.block_number for block in blocks if block.section == section]
			return sorted(block_nums)
		except Exception as e:
			print(f"Error getting blocks for line {line}, section {section}: {e}")
			return []

	def select_destination(self):
		"""Handle destination selection and route validation"""
		line = self.dest_line_combo.currentText()
		section = self.dest_section_combo.currentText()
		block = self.dest_block_combo.currentText()
		
		if not block:
			StyledMessageBox.warning(self, "Input Error", "Please select a destination block")
			return

		# Check route possibility
		route_possible, alt_section, alt_block = self.check_route_possibility(line, section, int(block))
		
		# Only show popup if route is NOT possible
		if not route_possible:
			reply = StyledMessageBox.question(self, "Route Not Possible",
			                           f"Because of the positions and routes of current trains, a route to this destination could not be made. "
			                           f"The furthest the train could be routed to is Section {alt_section} block {alt_block}. "
			                           f"Route to this destination?",
			                           QMessageBox.Yes | QMessageBox.No)
			if reply == QMessageBox.Yes:
				# Update the selection to the alternative
				self.dest_section_combo.setCurrentText(alt_section)
				self.dest_block_combo.setCurrentText(str(alt_block))
			else:
				# User declined alternative - don't proceed
				return

		# Mark destination as selected (only if route is possible or alternative accepted)
		self.destination_selected = True
		self.check_and_generate_route()

	def check_route_possibility(self, line, section, block):
		"""Check if route is possible using the routing engine"""
		train_id = self.route_train_id_entry.text().strip()
		if not train_id:
			# No train ID provided - assume route is possible
			return True, section, block
			
		if train_id not in self.ctc_system.trains:
			# Train doesn't exist yet - route is possible (we'll create the train later)
			return True, section, block
			
		try:
			# Calculate route using route manager
			
			# Try to calculate a route to the destination
			route = self.ctc_system.calculate_route(train_id, block, 'SAFEST_PATH')
			
			if route is not None and route.estimatedTravelTime < float('inf'):
				# Route is possible
				return True, section, block
			else:
				# Route not possible, find alternative
				train = self.ctc_system.trains[train_id]
				
				# Find the furthest reachable block on the same line
				# Start from nearby blocks and work outward
				current_block = self.get_block_number(train.currentBlock)
				
				# Try blocks closer to the current position first
				test_blocks = []
				for distance in range(1, 20):  # Test up to 20 blocks away
					if current_block + distance <= block:
						test_blocks.append(current_block + distance)
					if current_block - distance >= 1:
						test_blocks.append(current_block - distance)
				
				# Find the furthest reachable block
				furthest_reachable = current_block
				for test_block in test_blocks:
					test_route = self.ctc_system.calculate_route(train_id, test_block, 'SAFEST_PATH')
					if test_route is not None and test_route.estimatedTravelTime < float('inf'):
						furthest_reachable = test_block
						if abs(test_block - block) < abs(furthest_reachable - block):
							furthest_reachable = test_block
				
				# Get section for the alternative block
				alt_section = self.get_section_for_block(line, furthest_reachable)
				return False, alt_section, furthest_reachable
				
		except Exception as e:
			print(f"Error checking route possibility: {e}")
			# Fallback to original logic
			return False, section, block

	def choose_arrival_time(self):
		"""Handle arrival time validation"""
		arrival_time_text = self.arrival_time_entry.text().strip()
		
		if not arrival_time_text:
			StyledMessageBox.warning(self, "Input Error", "Please enter an arrival time")
			return

		# Validate against current system time to prevent scheduling in the past
		try:
			# Parse the arrival time
			arrival_hour, arrival_minute = map(int, arrival_time_text.split(':'))
			
			# Use system time from master interface if available, otherwise fallback to real time
			system_time_str = getattr(self, 'current_time', None)
			if system_time_str:
				try:
					current_hour, current_minute = map(int, system_time_str.split(':'))
					current_time = _get_simulation_time().replace(hour=current_hour, minute=current_minute, second=0, microsecond=0)
				except:
					current_time = _get_simulation_time()  # Fallback if system time parsing fails
			else:
				current_time = _get_simulation_time()
			
			# Create arrival datetime for today
			arrival_datetime = current_time.replace(hour=arrival_hour, minute=arrival_minute, second=0, microsecond=0)
			
			# If the arrival time is earlier than current time, it must be for tomorrow
			if arrival_datetime <= current_time:
				# Check if it's reasonable for tomorrow (within 24 hours from now)
				arrival_datetime = arrival_datetime + timedelta(days=1)
				
				# If it's still too close (less than 5 minutes from now when considering tomorrow)
				min_future_time = current_time + timedelta(minutes=5)
				if arrival_datetime < min_future_time:
					display_time = system_time_str if system_time_str else current_time.strftime('%H:%M')
					StyledMessageBox.warning(self, "Invalid Time", 
						f"Arrival time must be at least 5 minutes in the future. "
						f"Current time is {display_time}.")
					return
			else:
				# Check if it's at least 5 minutes in the future for today
				min_future_time = current_time + timedelta(minutes=5)
				if arrival_datetime < min_future_time:
					display_time = system_time_str if system_time_str else current_time.strftime('%H:%M')
					StyledMessageBox.warning(self, "Invalid Time", 
						f"Arrival time must be at least 5 minutes in the future. "
						f"Current time is {display_time}.")
					return
					
		except ValueError:
			StyledMessageBox.warning(self, "Input Error", 
				"Please enter a valid time in HH:MM format (24-hour)")
			return
		except Exception as e:
			StyledMessageBox.warning(self, "Time Validation Error", 
				f"Error validating time: {str(e)}")
			return

		# Validate the arrival time against speed limits
		time_possible, earliest_time = self.check_time_possibility(arrival_time_text)
		
		# Only show popup if time is NOT possible
		if not time_possible:
			reply = StyledMessageBox.question(self, "Time Not Possible",
			                           f"Speed limits make that time impossible. "
			                           f"Earliest possible arrival time is {earliest_time}. "
			                           f"Use that time?",
			                           QMessageBox.Yes | QMessageBox.No)
			if reply == QMessageBox.Yes:
				self.arrival_time_entry.setText(earliest_time)
			else:
				# User declined alternative - don't proceed
				return

		# Mark time as selected (only if time is possible or alternative accepted)
		self.time_selected = True
		self.check_and_generate_route()

	def calculate_arrival_from_departure(self, departure_time):
		"""Calculate arrival time based on departure time and route duration"""
		try:
			from datetime import datetime, time, timedelta
			from ..Core.routing_engine import RouteType
			
			train_id = self.route_train_id_entry.text().strip()
			if not train_id:
				return None
				
			# Parse departure time
			hour, minute = map(int, departure_time.split(':'))
			
			# Get destination block
			dest_block_text = self.dest_block_combo.currentText()
			if not dest_block_text:
				return None
				
			destination_block = int(dest_block_text)
			
			# Check if train exists or use safest path calculation
			if train_id in self.ctc_system.trains:
				# Calculate route for existing train
				route = self.ctc_system.calculate_route(train_id, destination_block, 'SAFEST_PATH')
			else:
				# For new trains, estimate route time using current track data
				# This is a simplified calculation - in practice you might want more sophisticated logic
				route = None
				
			if route and route.estimatedTravelTime < float('inf'):
				# Calculate arrival time = departure time + travel time
				today = _get_simulation_time().date()
				departure_datetime = datetime.combine(today, time(hour, minute))
				
				# If departure time is in the past, assume it's for tomorrow
				if departure_datetime <= _get_simulation_time():
					departure_datetime += timedelta(days=1)
				
				arrival_datetime = departure_datetime + timedelta(seconds=route.estimatedTravelTime)
				return arrival_datetime.strftime("%H:%M")
			else:
				# Cannot calculate route - return None
				return None
				
		except Exception as e:
			print(f"Error calculating arrival from departure: {e}")
			return None

	def check_time_possibility(self, requested_time):
		"""Check if arrival time is possible based on routing calculations"""
		train_id = self.route_train_id_entry.text().strip()
		if not train_id:
			# No train ID provided - assume time is possible
			return True, requested_time
			
		if train_id not in self.ctc_system.trains:
			# Train doesn't exist yet - time is possible (we'll create the train later)
			return True, requested_time
			
		try:
			from datetime import datetime, time
			from ..Core.routing_engine import RouteType
			
			# Parse the requested time
			hour, minute = map(int, requested_time.split(':'))
			
			# Get destination block
			dest_block_text = self.dest_block_combo.currentText()
			if not dest_block_text:
				return False, requested_time
				
			destination_block = int(dest_block_text)
			
			# Calculate the route
			route = self.ctc_system.calculate_route(train_id, destination_block, 'FASTEST_TIME')
			
			if route is None or route.estimatedTravelTime == float('inf'):
				# Route not possible at all
				return False, requested_time
			
			# Calculate the earliest possible arrival time
			current_time = _get_simulation_time()
			earliest_arrival = current_time.timestamp() + route.estimatedTravelTime
			earliest_datetime = datetime.fromtimestamp(earliest_arrival)
			
			# Convert requested time to today's datetime
			today = _get_simulation_time().date()
			requested_datetime = datetime.combine(today, time(hour, minute))
			
			# If requested time is in the past, assume it's for tomorrow
			if requested_datetime <= current_time:
				from datetime import timedelta
				requested_datetime += timedelta(days=1)
			
			# Check if requested time is achievable
			if requested_datetime >= earliest_datetime:
				return True, requested_time
			else:
				# Return the earliest possible time
				earliest_time_str = earliest_datetime.strftime("%H:%M")
				return False, earliest_time_str
				
		except Exception as e:
			print(f"Error checking time possibility: {e}")
			# Fallback - assume time is possible
			return True, requested_time

	def browse_schedule_file(self):
		"""Open file browser for schedule CSV"""
		file_path, _ = QFileDialog.getOpenFileName(
			self, "Select Schedule CSV File", "", "CSV Files (*.csv)")
		if file_path:
			self.schedule_file_entry.setText(file_path)

	def generate_routes_from_schedule(self):
		"""Generate routes from uploaded schedule CSV"""
		file_path = self.schedule_file_entry.text().strip()
		if not file_path:
			StyledMessageBox.warning(self, "Input Error", "Please select a schedule file")
			return

		try:
			# Parse CSV and generate routes
			success, routes_or_error = self.parse_schedule_csv(file_path)
			
			if not success:
				if isinstance(routes_or_error, str) and "syntax" in routes_or_error.lower():
					StyledMessageBox.critical(self, "CSV Syntax Error",
					                   "The route csv had a syntax error so could not be parsed. "
					                   "Please see the instructions for creating a route csv to correct the syntax errors.")
				else:
					# Routes not possible - get actual failed trains from routing result
					failed_trains = getattr(routes_or_error, 'failed_trains', []) if hasattr(routes_or_error, 'failed_trains') else []
					revised_routes = getattr(routes_or_error, 'suggested_changes', "Please review the route requirements.") if hasattr(routes_or_error, 'suggested_changes') else "Please review the route requirements."
					
					reply = StyledMessageBox.question(self, "Routes Not Possible",
					                           f"Because of the positions and routes of current trains or the arrival time of the requested routes, "
					                           f"the following trains could not be routed:\n{', '.join(failed_trains)}\n\n"
					                           f"The following would allow these trains to be rerouted: {revised_routes}\n\n"
					                           f"Would you like to accept these changes or modify the csv to make manual changes.",
					                           QMessageBox.Yes | QMessageBox.No)
					if reply == QMessageBox.Yes:
						self.populate_new_train_info_table(routes_or_error)
			else:
				self.populate_new_train_info_table(routes_or_error)
				
		except Exception as e:
			StyledMessageBox.critical(self, "Error", f"Failed to process schedule file: {str(e)}")

	def parse_schedule_csv(self, file_path):
		"""Parse CSV schedule file and validate routes"""
		try:
			import csv
			routes = []
			
			with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
				reader = csv.DictReader(csvfile)
				for row in reader:
					# Validate required fields
					required_fields = ['train_id', 'line', 'dest_section', 'dest_block', 'eta']
					if all(field in row and row[field].strip() for field in required_fields):
						routes.append({
							"train_id": row['train_id'].strip(),
							"on_track": row.get('on_track', '○'),
							"moving": row.get('moving', '○'),
							"line": row['line'].strip(),
							"location_section": row.get('location_section', 'Yard'),
							"location_block": row.get('location_block', 'Yard'),
							"dest_section": row['dest_section'].strip(),
							"dest_block": row['dest_block'].strip(),
							"eta": row['eta'].strip()
						})
			
			if not routes:
				return False, "No valid routes found in CSV file"
			
			return True, routes
			
		except FileNotFoundError:
			return False, "CSV file not found"
		except Exception as e:
			return False, f"CSV parsing error: {str(e)}"

	def populate_new_train_info_table(self, routes):
		"""Populate the new train information table with routes"""
		self.new_train_info_table.setRowCount(len(routes))
		
		for row, route in enumerate(routes):
			self.new_train_info_table.setItem(row, 0, QTableWidgetItem(route["train_id"]))
			self.new_train_info_table.setItem(row, 1, QTableWidgetItem(route["on_track"]))
			self.new_train_info_table.setItem(row, 2, QTableWidgetItem(route["moving"]))
			self.new_train_info_table.setItem(row, 3, QTableWidgetItem(route["line"]))
			self.new_train_info_table.setItem(row, 4, QTableWidgetItem(route["location_section"]))
			self.new_train_info_table.setItem(row, 5, QTableWidgetItem(route["location_block"]))
			self.new_train_info_table.setItem(row, 6, QTableWidgetItem(route["dest_section"]))
			self.new_train_info_table.setItem(row, 7, QTableWidgetItem(route["dest_block"]))
			self.new_train_info_table.setItem(row, 8, QTableWidgetItem(route.get("departure_time", "")))
			self.new_train_info_table.setItem(row, 9, QTableWidgetItem(route["eta"]))

	def reroute_selected_train(self):
		"""Handle rerouting a selected train from the current trains table"""
		selected_items = self.current_trains_table.selectedItems()
		print(f"Debug: Selected items count: {len(selected_items) if selected_items else 0}")
		if selected_items:
			row = selected_items[0].row()
			train_id_item = self.current_trains_table.item(row, 0)
			if train_id_item:
				train_id = train_id_item.text()
				print(f"Debug: Rerouting train {train_id}")
				# Switch to Route Trains tab
				self.tab_widget.setCurrentIndex(1)
				# Populate train info in Route Trains tab
				self.route_train_id_entry.setText(train_id)
				self.check_train_id()
			else:
				print("Debug: No train ID item found in selected row")
		else:
			print("Debug: No train selected in current trains table")

	def reroute_selected_train_from_main(self):
		"""Handle rerouting a selected train from the main page train table"""
		selected_items = self.train_info_table.selectedItems()
		print(f"Debug: Selected items from main table count: {len(selected_items) if selected_items else 0}")
		if selected_items:
			row = selected_items[0].row()
			train_id_item = self.train_info_table.item(row, 0)
			if train_id_item:
				train_id = train_id_item.text()
				print(f"Debug: Rerouting train {train_id} from main page")
				# Switch to Route Trains tab
				self.tab_widget.setCurrentIndex(1)
				# Populate train info in Route Trains tab
				self.route_train_id_entry.setText(train_id)
				self.check_train_id()
			else:
				print("Debug: No train ID item found in selected row on main page")
		else:
			print("Debug: No train selected in main page train table")

	def accept_route(self):
		"""Handle route acceptance with confirmation"""
		reply = StyledMessageBox.question(self, "Confirm Accept Route",
		                           "Do you confirm that these route details are correct and you would like to route the train to the specified destination?",
		                           QMessageBox.Yes | QMessageBox.No)
		if reply == QMessageBox.Yes:
			# Placeholder route implementation
			self.implement_route()

	def implement_route(self):
		"""Actually implement the route using the advanced routing engine"""
		try:
			# Get route information from pending route info
			if not hasattr(self, 'pending_route_info'):
				StyledMessageBox.warning(self, "Route Error", "No route information available")
				return
				
			route_info = self.pending_route_info
			train_id = route_info['train_id']
			is_new_train = route_info.get('is_new_train', False)
			route = route_info.get('calculated_route')

			if not route:
				StyledMessageBox.warning(self, "Route Error", "Could not retrieve calculated route. Please generate the route again.")
				return

			# If it's a new train, it must be added to the train manager first
			if is_new_train:
				if train_id not in self.ctc_system.trains:
					line = route_info['line']
					start_block = route_info.get('start_block', 1)
					self.ctc_system.add_train(line, start_block, train_id=train_id)
			
			# Activate the route
			success = self.ctc_system.activate_route(train_id, route)
			
			if success:
				# Add terminal output for route acceptance
				print(f"✅ ROUTE ACCEPTED: Train {train_id} route activated")
				if route and hasattr(route, 'blockSequence'):
					block_ids = [block.blockID for block in route.blockSequence]
					print(f"   Route blocks: {block_ids}")
				print(f"   Route ID: {route.routeID if route else 'Unknown'}")
				
				# Store route in communication handler for timed command execution
				if self.ctc_system.communicationHandler and route:
					self.ctc_system.communicationHandler.schedule_route(route)
				
				# Clear pending route info
				delattr(self, 'pending_route_info')
				
				# First refresh the route train info table to show updated departure time
				self.update_route_train_info(train_id)
				
				# Then reset form first (but preserve train info table for a moment)
				self.clear_route_form_preserve_train_info()
				
				# Clear the train info table after 3 seconds to let user see the departure time
				QTimer.singleShot(3000, self.clear_route_train_info_table)
				
				# Show success message
				StyledMessageBox.information(self, "Route Success", 
					f"Route activated for train {train_id}")
				
			else:
				StyledMessageBox.warning(self, "Route Error", 
					f"Failed to activate route for train {train_id}")
				# If activation fails for a new train, remove it from the system
				if is_new_train:
					self.ctc_system.remove_train(train_id)
			
		except Exception as e:
			StyledMessageBox.warning(self, "Route Error", f"Error implementing route: {e}")

	def clear_route_form_preserve_train_info(self):
		"""Clear the route form but preserve the train info table for a moment"""
		# Clear form fields to prepare for next train routing
		self.route_train_id_entry.clear()  # Clear train ID for next routing
		self.route_train_id_entry.setStyleSheet("")  # Remove any validation styling
		# Repopulate destination dropdowns instead of just clearing them
		self.update_dest_sections()
		self.arrival_time_entry.clear()
		
		# Clear state variables
		if hasattr(self, 'destination_selected'):
			self.destination_selected = False
		if hasattr(self, 'time_selected'):
			self.time_selected = False
		if hasattr(self, 'pending_route'):
			delattr(self, 'pending_route')
		if hasattr(self, 'pending_route_data'):
			delattr(self, 'pending_route_data')
		if hasattr(self, 'pending_route_info'):
			delattr(self, 'pending_route_info')
		
		# Clear new train info table
		self.new_train_info_table.setRowCount(0)

	def clear_route_train_info_table(self):
		"""Clear the route train info table"""
		try:
			if hasattr(self, 'route_train_info_table'):
				for col in range(self.route_train_info_table.columnCount()):
					self.route_train_info_table.setItem(0, col, QTableWidgetItem(""))
		except Exception as e:
			logger.error(f"Error clearing route train info table: {e}")

	def clear_route_form(self):
		"""Clear the route form and reset state variables"""
		# Clear form fields
		self.route_train_id_entry.clear()
		self.route_train_id_entry.setStyleSheet("")  # Remove any validation styling
		self.dest_line_combo.setCurrentIndex(0)
		# Repopulate destination dropdowns instead of just clearing them
		self.update_dest_sections()
		self.arrival_time_entry.clear()
		
		# Clear state variables
		if hasattr(self, 'destination_selected'):
			self.destination_selected = False
		if hasattr(self, 'time_selected'):
			self.time_selected = False
		if hasattr(self, 'pending_route'):
			delattr(self, 'pending_route')
		if hasattr(self, 'pending_route_data'):
			delattr(self, 'pending_route_data')
		if hasattr(self, 'pending_route_info'):
			delattr(self, 'pending_route_info')
		
		# Clear the new train info table
		self.new_train_info_table.setRowCount(0)
		
		# Clear route train info table
		for col in range(self.route_train_info_table.columnCount()):
			self.route_train_info_table.setItem(0, col, QTableWidgetItem(""))

	def check_and_generate_route(self):
		"""Check if both destination and time are selected, then generate route"""
		if hasattr(self, 'destination_selected') and hasattr(self, 'time_selected'):
			if self.destination_selected and self.time_selected:
				self.generate_and_display_route()

	def generate_and_display_route(self):
		"""Generate the routing algorithm and display route on map"""
		# Get the train ID and route parameters
		train_id = self.route_train_id_entry.text().strip()
		if not train_id:
			return

		# Validate train ID format (but don't create train yet)
		if not self.is_valid_train_id_for_routing(train_id):
			StyledMessageBox.warning(self, "Route Error", 
				f"Invalid train ID format: {train_id}. Please use format like B001, G002, R003.")
			return
		
		# Get line from destination selection and validate
		line = self.dest_line_combo.currentText()
		if not line:
			StyledMessageBox.warning(self, "Route Error", "Please select a destination line first.")
			return
		
		# Verify train ID matches the destination line
		train_line_letter = train_id[0].upper()
		expected_letter = line[0].upper()
		if train_line_letter != expected_letter:
			StyledMessageBox.warning(self, "Route Error", 
				f"Train ID {train_id} does not match destination line {line}. "
				f"Train ID should start with {expected_letter}.")
			return

		section = self.dest_section_combo.currentText()
		block = self.dest_block_combo.currentText()
		arrival_time = self.arrival_time_entry.text().strip()

		try:
			# Calculate route using route manager
			destination_block = int(block)
			
			# Get scheduled_arrival from arrival_time_entry
			scheduled_arrival = None
			if arrival_time:
				try:
					from datetime import datetime, time, timedelta
					hour, minute = map(int, arrival_time.split(':'))
					today = _get_simulation_time().date()
					
					# Use system time for "today"
					system_time_str = getattr(self, 'current_time', None)
					if system_time_str:
						try:
							current_hour, current_minute = map(int, system_time_str.split(':'))
							current_time_base = _get_simulation_time().replace(hour=current_hour, minute=current_minute)
							today = current_time_base.date()
						except:
							pass  # use real date

					scheduled_arrival = datetime.combine(today, time(hour, minute))
					
					# If the arrival time is earlier than current time, it must be for tomorrow
					current_check_time = _get_simulation_time()
					if system_time_str:
						try:
							current_hour, current_minute = map(int, system_time_str.split(':'))
							current_check_time = _get_simulation_time().replace(hour=current_hour, minute=current_minute, second=0, microsecond=0)
						except:
							pass  # use real time

					if scheduled_arrival <= current_check_time:
						scheduled_arrival += timedelta(days=1)
				except Exception as e:
					print(f"Error parsing arrival time in generate_and_display_route: {e}")

			# Use BFS algorithm directly via generate_route() - no more old sequential algorithms
			# Get start block (yard) and destination block objects
			start_block_obj = self.ctc_system.get_block_by_number(0)  # Yard block
			end_block_obj = self.ctc_system.find_block_for_destination(destination_block, train_id)
			
			if not start_block_obj:
				StyledMessageBox.warning(self, "Route Error", "Yard block not found - cannot generate route")
				return
			
			if not end_block_obj:
				StyledMessageBox.warning(self, "Route Error", f"Destination block {destination_block} not found")
				return
			
			# Use Display Manager to generate and display route
			result = self.display_manager.generate_and_display_route(
				train_id=train_id,
				from_station=start_block_obj,
				to_station=end_block_obj,
				arrival_time=scheduled_arrival,
				route_manager=self.ctc_system.routeManager
			)
			
			if not result['success']:
				StyledMessageBox.warning(self, "Route Error", result['message'])
				return
				
			route = result['route']
			
			# Add terminal output for successful route generation
			print(f"🚂 ROUTE GENERATED: Train {train_id} to Block {destination_block}")
			if route and hasattr(route, 'blockSequence'):
				block_ids = [block.blockID for block in route.blockSequence]
				print(f"   Route blocks: {block_ids}")
				print(f"   Travel time: {route.estimatedTravelTime:.1f} seconds")
			
			# Generate route data for display
			route_data = self.generate_route_data_for_proposed_route(train_id, line, destination_block, arrival_time, route)
			
			# Populate the new train information table - this shows the PROPOSED route
			self.populate_new_train_info_table([route_data])
			
			# Update the route visualization on the map
			self.update_route_visualization(route_data)
			
			# Store the route info for when Accept Route is pressed
			self.pending_route_info = {
				'train_id': train_id,
				'line': line,
				'destination_block': destination_block,
				'route_type': 'SAFEST_PATH',
				'start_block': 1,  # Default for new trains
				'is_new_train': train_id not in self.ctc_system.trains,
				'calculated_route': route  # Store the calculated route
			}
			
		except ValueError as e:
			StyledMessageBox.warning(self, "Route Error", f"Invalid destination block: {e}")
			print(f"Error generating route: {e}")

	def generate_route_data_for_proposed_route(self, train_id, line, destination_block, arrival_time, route):
		"""Generate route data for a proposed route (train may not exist yet)"""
		# Check if train already exists
		if train_id in self.ctc_system.trains:
			train = self.ctc_system.trains[train_id]
			current_section = self.get_section_for_block(train.line, train.currentBlock)
			current_block = str(self.get_block_number(train.currentBlock))
			on_track = "Yes"  # Existing train is on track
			# Check speed using TBTG naming convention (camelCase) with fallback
			speed_kmh = getattr(train, 'speedKmh', getattr(train, 'speed', 0))
			moving = "Yes" if speed_kmh > 0 else "No"
		else:
			# New train - not on track yet
			current_section = "Yard"
			current_block = "Yard"
			on_track = "No"  # NOT on track until route is accepted
			moving = "No"  # Not moving
		
		# Get destination section
		dest_block_info = self.trackReader.get_block_info(line, destination_block)
		dest_section = dest_block_info.section if dest_block_info else "Unknown"
		
		# Use requested arrival time if provided, otherwise calculate ETA from route
		if arrival_time and arrival_time.strip():
			display_eta = arrival_time.strip()
		elif route and route.estimatedTravelTime < float('inf'):
			# Calculate actual clock time ETA
			from datetime import datetime, timedelta
			current_time = getattr(self, 'current_time', None)
			if current_time:
				try:
					current_hour, current_minute = map(int, current_time.split(':'))
					current_datetime = _get_simulation_time().replace(hour=current_hour, minute=current_minute, second=0, microsecond=0)
				except:
					current_datetime = _get_simulation_time()
			else:
				current_datetime = _get_simulation_time()
			eta_datetime = current_datetime + timedelta(seconds=route.estimatedTravelTime)
			display_eta = eta_datetime.strftime("%H:%M")
		else:
			display_eta = "Blocked"
		
		# Calculate departure time for new train info table
		departure_time = ""
		if display_eta and display_eta != "Blocked":
			try:
				from datetime import datetime, time, timedelta
				eta_hour, eta_minute = map(int, display_eta.split(':'))
				today = _get_simulation_time().date()
				eta_datetime = datetime.combine(today, time(eta_hour, eta_minute))
				
				# Use the route's calculated travel time if available
				if route and route.estimatedTravelTime < float('inf'):
					travel_minutes = int(route.estimatedTravelTime / 60)
					departure_datetime = eta_datetime - timedelta(minutes=travel_minutes)
					departure_time = departure_datetime.strftime("%H:%M")
				else:
					# Fallback to precise calculation for new trains
					if train_id not in self.ctc_system.trains:
						travel_time_seconds = self.calculate_precise_travel_time(train_id, destination_block)
						if travel_time_seconds > 0:
							departure_datetime = eta_datetime - timedelta(seconds=travel_time_seconds)
							departure_time = departure_datetime.strftime("%H:%M")
						else:
							# Final fallback to 30 minutes
							departure_datetime = eta_datetime - timedelta(minutes=30)
							departure_time = departure_datetime.strftime("%H:%M")
					else:
						# Use default 30 minutes for existing trains without route
						departure_datetime = eta_datetime - timedelta(minutes=30)
						departure_time = departure_datetime.strftime("%H:%M")
			except Exception as e:
				print(f"Error calculating departure time: {e}")
				departure_time = "TBD"

		return {
			"train_id": train_id,
			"on_track": on_track,
			"moving": moving,
			"line": line,
			"location_section": current_section,
			"location_block": current_block,
			"dest_section": dest_section,
			"dest_block": str(destination_block),
			"departure_time": departure_time,
			"eta": display_eta
		}

	def generate_route_data_from_calculated_route(self, train_id, route, arrival_time):
		"""Generate route data from a calculated route for display"""
		train = self.ctc_system.trains[train_id]
		current_section = self.get_section_for_block(train.line, train.currentBlock)
		current_block = str(train.currentBlock)
		
		# Get destination section
		dest_block_info = self.trackReader.get_block_info(route.line, route.destination_block)
		dest_section = dest_block_info.section if dest_block_info else "Unknown"
		
		# Calculate ETA based on route total time
		if route.estimatedTravelTime < float('inf'):
			# Calculate actual clock time ETA
			from datetime import datetime, timedelta
			current_time = getattr(self, 'current_time', None)
			if current_time:
				try:
					current_hour, current_minute = map(int, current_time.split(':'))
					current_datetime = _get_simulation_time().replace(hour=current_hour, minute=current_minute, second=0, microsecond=0)
				except:
					current_datetime = _get_simulation_time()
			else:
				current_datetime = _get_simulation_time()
			eta_datetime = current_datetime + timedelta(seconds=route.estimatedTravelTime)
			calculated_eta = eta_datetime.strftime("%H:%M")
		else:
			calculated_eta = "Blocked"
		
		# Use requested arrival time if provided, otherwise use calculated ETA
		display_eta = arrival_time if arrival_time else calculated_eta
		
		return {
			"train_id": train_id,
			"on_track": "●",
			"moving": "●" if train.speedKmh > 0 else "○",
			"line": train.line,
			"location_section": current_section,
			"location_block": current_block,
			"dest_section": dest_section,
			"dest_block": str(route.destination_block),
			"eta": display_eta
		}

	def generate_placeholder_route(self, train_id, line, section, block, arrival_time):
		"""Generate a real route using RouteManager instead of placeholder data"""
		from datetime import datetime, timedelta
		
		# Check if train exists to get current location
		if train_id in self.ctc_system.trains:
			train = self.ctc_system.trains[train_id]
			current_section = self.get_section_for_block(train.line, train.currentBlock)
			current_block = str(self.get_block_number(train.currentBlock))
			on_track = "●"
			moving = "●"
		else:
			current_section = "Yard"
			current_block = "Yard"
			on_track = "○"
			moving = "○"

		# Generate actual route using CTCSystem.calculate_route
		try:
			# Convert arrival_time string to datetime
			scheduled_arrival = None
			if arrival_time:
				hour, minute = map(int, arrival_time.split(':'))
				scheduled_arrival = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
			
			# Generate real route instead of placeholder
			route = self.ctc_system.calculate_route(train_id, block, scheduled_arrival=scheduled_arrival)
			
			if route and hasattr(route, 'scheduledDeparture'):
				departure_time = route.scheduledDeparture.strftime('%H:%M')
			else:
				# Fallback to calculated departure time
				departure_time = self.calculate_departure_time(train_id, block, arrival_time)
			
			# Log successful route generation
			if route:
				print(f"UI: Generated real route {route.routeID} for train {train_id} to block {block}")
			else:
				print(f"UI: Route generation failed for train {train_id} to block {block} - using display data only")
		
		except Exception as e:
			print(f"UI: Error generating route for train {train_id}: {e} - using display data only")
			departure_time = self.calculate_departure_time(train_id, block, arrival_time)

		return {
			"train_id": train_id,
			"on_track": on_track,
			"moving": moving,
			"line": line,
			"location_section": current_section,
			"location_block": current_block,
			"dest_section": section,
			"dest_block": str(block),
			"departure_time": departure_time,
			"eta": arrival_time if arrival_time else "5:30"
		}

	def calculate_departure_time(self, train_id, destination_block, arrival_time):
		"""Calculate departure time based on arrival time using precise speed limits and door times"""
		try:
			from datetime import datetime, time, timedelta
			from ..Core.routing_engine import RouteType
			
			if not arrival_time:
				return ""
				
			# Parse arrival time
			hour, minute = map(int, arrival_time.split(':'))
			
			# Calculate precise travel time using speed limits and door times
			travel_time_seconds = self.calculate_precise_travel_time(train_id, destination_block)
			
			if travel_time_seconds <= 0:
				return ""  # Route not possible
			
			# Calculate departure time = arrival time - travel time
			# Use today's date for the calculation
			today = _get_simulation_time().date()
			arrival_datetime = datetime.combine(today, time(hour, minute))
			departure_datetime = arrival_datetime - timedelta(seconds=travel_time_seconds)
			
			# Handle day boundary crossing - if departure is before current time, assume next day arrival
			current_time = getattr(self, 'current_time', None)
			if current_time:
				try:
					current_hour, current_minute = map(int, current_time.split(':'))
					current_datetime = datetime.combine(today, time(current_hour, current_minute))
					
					# If departure time is in the past, move arrival to next day
					if departure_datetime < current_datetime:
						arrival_datetime += timedelta(days=1)
						departure_datetime = arrival_datetime - timedelta(seconds=travel_time_seconds)
				except:
					pass  # Continue with original calculation if current time parsing fails
			
			return departure_datetime.strftime("%H:%M")
			
		except Exception as e:
			print(f"Error calculating departure time: {e}")
			return ""

	def calculate_precise_travel_time(self, train_id, destination_block):
		"""Delegate travel time calculation to CTC System"""
		return self.ctc_system.calculate_travel_time_for_train(train_id, destination_block)

	def is_station_block(self, line, block_num):
		"""Determine if a block is a station that requires door time"""
		try:
			block_info = self.trackReader.get_block_info(line, block_num)
			if not block_info:
				return False
			
			# Consider a block a station if:
			# 1. It has infrastructure (switches, crossings, etc.)
			# 2. It's in certain sections that are known stations
			# 3. It has a speed limit suggesting it's a stop area
			
			# Simple heuristic: blocks with lower speed limits are likely stations
			if block_info.speed_limit_kmh <= 25:  # 25 km/h or less suggests station area
				return True
			
			# Additional heuristics can be added based on track layout data
			return False
			
		except Exception:
			return False  # Default to no door time if uncertain

	def update_route_visualization(self, route_data):
		"""Update the track visualization to show the generated route"""
		# For now, just mark that the track needs to be redrawn
		# In full implementation, this would highlight the route path on the map
		self.trackNeedsRedraw = True
		
		# Update the route track visualization
		if hasattr(self, 'route_track_widget'):
			# Create sample route path for visualization
			# This would be replaced with actual route calculation
			QTimer.singleShot(100, self.update_route_track_display)

	def update_route_track_display(self):
		"""Update the route track display with the generated route"""
		# In a full implementation, this would show the actual route path
		# For now, just ensure the track visualization is updated
		if self.trackNeedsRedraw:
			self.create_track_visualization()

	# Original Event handlers
	def line_selected(self, line, checked):
		"""Handle line selection"""
		if checked:
			self.selected_display_line = line
			self.track_needs_redraw = True

	def generate_train_id(self):
		"""Generate a train ID automatically"""
		line = self.dispatch_line_combo.currentText()
		train_id = self.ctc_system.generate_train_id(line)
		self.train_id_entry.setText(train_id)

	def update_station_lists(self):
		"""Update station dropdowns when line changes"""
		line = self.dispatch_line_combo.currentText()
		stations = self.trackReader.get_all_stations(line)

		station_names = [s['station_name'] for s in stations]

		self.from_station_combo.clear()
		self.from_station_combo.addItems(station_names)

		self.to_station_combo.clear()
		self.to_station_combo.addItems(station_names)

		if station_names:
			self.from_station_combo.setCurrentText(station_names[0])
			self.to_station_combo.setCurrentText(station_names[-1])


	def dispatch_train(self):
		"""Dispatch a new train using the train manager with auto-generated ID"""
		# Get route information
		from_station = self.from_station_combo.currentText()
		to_station = self.to_station_combo.currentText()
		line = self.dispatch_line_combo.currentText()

		# Plan route using the consolidated track display helper
		track_display = CTCTrackDisplayHelper(self.trackReader, self.ctcSystem)
		route_result = track_display.plan_route_simple(from_station, to_station)

		if not route_result['success']:
			StyledMessageBox.critical(self, "Routing Error", route_result['error'])
			return

		# Create train using train manager with auto-generated ID
		train_id = self.ctc_system.add_train(
			line, route_result['blocks'][0],
			route_result['blocks'][-1], route_result['blocks']
		)
		
		# Update the state manager with the new train
		train = self.ctc_system.get_train(train_id) if hasattr(self.ctc_system, 'get_train') else self.ctc_system.trains.get(train_id)
		if train:
			self.display_manager.update_train_state(train_id, train)

		# Update route preview
		self.route_text.clear()
		self.route_text.append(f"Train {train_id} dispatch requested!\n")
		self.route_text.append(f"Route: {from_station} → {to_station}")
		self.route_text.append(f"Line: {line} Line")
		self.route_text.append(f"Start Block: {route_result['blocks'][0]}")
		self.route_text.append(f"Destination Block: {route_result['blocks'][-1]}")
		self.route_text.append(f"Total Blocks: {len(route_result['blocks'])}")

		self.track_needs_redraw = True
		StyledMessageBox.information(self, "Success", f"Train {train_id} dispatched successfully!")


	def initialize_block_table(self):
		"""Initialize the block table with all blocks"""
		self.allBlocksData = []
		self.blockToRowMap = {}

		self.block_info_table.setSortingEnabled(False)
		self.block_info_table.setUpdatesEnabled(False)

		row_index = 0
		for line in self.selected_lines:
			blocks = self.trackReader.lines.get(line, [])
			for block in blocks:
				block_data = {
					"line": line,
					"block_number": block.block_number,
					"section": block.section,
					"block": str(block.block_number).zfill(4),
					"speed": str(int(block.speed_limit_kmh * 0.621371)),
					"stop": block.station.name if block.has_station and block.station else "",
					"switch": "●" if block.has_switch else "",
					"crossing": "●" if block.has_crossing else ""
				}
				self.allBlocksData.append(block_data)
				self.blockToRowMap[(line, block.block_number)] = row_index
				row_index += 1

		self.block_info_table.setRowCount(len(self.allBlocksData))

		for row, block_data in enumerate(self.allBlocksData):
			self.block_info_table.setItem(row, 0, QTableWidgetItem(block_data["line"]))
			self.block_info_table.setItem(row, 1, QTableWidgetItem("●"))  # Filled circle = open
			self.block_info_table.setItem(row, 2, QTableWidgetItem(""))    # Occupying Train
			self.block_info_table.setItem(row, 3, QTableWidgetItem(block_data["section"]))
			self.block_info_table.setItem(row, 4, QTableWidgetItem(block_data["block"]))
			self.block_info_table.setItem(row, 5, QTableWidgetItem(block_data["speed"]))
			self.block_info_table.setItem(row, 6, QTableWidgetItem(block_data["stop"]))
			self.block_info_table.setItem(row, 7, QTableWidgetItem(block_data["switch"]))
			self.block_info_table.setItem(row, 8, QTableWidgetItem(block_data["crossing"]))

		self.block_info_table.setUpdatesEnabled(True)
		self.block_info_table.setSortingEnabled(True)
		self.block_info_table.sortItems(0, Qt.AscendingOrder)

	def create_track_visualization(self):
		"""Create track visualization using the track visualization component"""
		if not self.trackNeedsRedraw:
			return

		# Update the track visualization with appropriate layout
		use_auto = self.selectedDisplayLine in ["Red", "Green"]  # Only use auto-layout for individual Red/Green
		self.trackVisualization.update_display(
			self.selectedDisplayLine,
			self.ctc_system.trains,
			self.display_manager.get_maintenance_closures(),
			use_auto_layout=use_auto
		)
		
		self.trackNeedsRedraw = False
	
	def update_route_track_visualization(self):
		"""Update the route track widget in the Route Train tab"""
		# Update the route visualization if it exists
		if hasattr(self, 'route_track_visualization'):
			use_auto = self.selectedDisplayLine in ["Red", "Green"]
			self.route_track_visualization.update_display(
				self.selectedDisplayLine,
				self.ctc_system.trains,
				self.display_manager.get_maintenance_closures(),
				use_auto_layout=use_auto
			)


	def _initial_compact_sizing(self, table):
		"""Set initial compact column sizes for a table"""
		# Check if this is the block info table by column count and headers
		if (table.columnCount() == 9 and 
			table.horizontalHeaderItem(0) and 
			table.horizontalHeaderItem(0).text() == 'Line'):
			# Set proper widths for block table columns to accommodate 20pt font
			compact_widths = [140, 90, 180, 110, 90, 170, 90, 110, 110]  # Updated for 20pt font
			for col, width in enumerate(compact_widths):
				if col < table.columnCount():
					table.setColumnWidth(col, width)
		else:
			# For other tables, use auto-sizing but make compact
			table.resizeColumnsToContents()
			for col in range(table.columnCount()):
				current_width = table.columnWidth(col)
				new_width = max(50, int(current_width * 0.85))
				table.setColumnWidth(col, new_width)

	def _on_column_resized(self, logical_index, old_size, new_size):
		"""Track when user manually resizes columns"""
		self._user_adjusted_columns.add(logical_index)


	def update_open_close_button(self):
		"""Update the open/close button text based on selected block"""
		selected_items = self.block_info_table.selectedItems()
		if selected_items:
			# Get the selected row
			row = selected_items[0].row()
			open_item = self.block_info_table.item(row, 1)  # Open? column
			if open_item:
				is_open = open_item.text() == "●"  # Filled circle means open
				if is_open:
					self.open_block_btn.setText("Close Block")
				else:
					self.open_block_btn.setText("Open Block")
		else:
			self.open_block_btn.setText("Close Block")  # Default

	def handle_open_close_block(self):
		"""Handle open/close block button click - navigate to maintenance tab"""
		selected_items = self.block_info_table.selectedItems()
		if selected_items:
			# Get the selected row info
			row = selected_items[0].row()
			line_item = self.block_info_table.item(row, 0)
			block_item = self.block_info_table.item(row, 4)
			
			if line_item and block_item:
				line = line_item.text()
				block_num = int(block_item.text())
				
				# Store the auto-population data and set flag
				self._auto_populate_data = {'line': line, 'block': block_num}
				self._auto_populating = True
				
				# Switch to maintenance tab first (index 2)
				self.tab_widget.setCurrentIndex(2)
				
				# Use QTimer with longer delay and reset flag after population
				from PyQt5.QtCore import QTimer
				QTimer.singleShot(200, self.execute_auto_population)
		else:
			# No selection, switch to maintenance tab anyway
			self.tab_widget.setCurrentIndex(2)

	def execute_auto_population(self):
		"""Execute auto-population with stored data"""
		# Execute auto population
		if hasattr(self, '_auto_populate_data') and self._auto_populate_data:
			line = self._auto_populate_data['line']
			block = self._auto_populate_data['block']
			# Auto-populating maintenance tab
			self.populate_maintenance_tab(line, block)
			# Clear the data
			self._auto_populate_data = None

	def populate_maintenance_tab(self, line: str, block: int):
		"""Populate the maintenance tab with selected block info"""
		# Populate maintenance tab
		
		# Set the state manager selection (this will trigger the signal)
		self.display_manager.set_selected_block(line, block)
		
		# Also directly populate the form to ensure it works
		has_combos = hasattr(self, 'close_line_combo') and hasattr(self, 'close_section_combo') and hasattr(self, 'close_block_combo')
		print(f"DEBUG: Has combo boxes: {has_combos}")
		
		if has_combos:
			print(f"DEBUG: Setting line combo to {line}")
			# Set the line
			line_index = self.close_line_combo.findText(line)
			print(f"DEBUG: Line index found: {line_index}")
			if line_index >= 0:
				self.close_line_combo.setCurrentIndex(line_index)
				
				# Update sections for the selected line
				self.update_close_sections()
				
				# Find and set the section for this block
				section = self.get_section_for_block(line, block)
				print(f"DEBUG: Section for block {block}: {section}")
				if section:
					section_index = self.close_section_combo.findText(section)
					print(f"DEBUG: Section index found: {section_index}")
					if section_index >= 0:
						self.close_section_combo.setCurrentIndex(section_index)
						
						# Update blocks for the selected section
						self.update_close_blocks()
						
						# Set the specific block
						block_str = str(block).zfill(4)  # Format with leading zeros to match combo format
						print(f"DEBUG: Looking for block string: {block_str}")
						block_index = self.close_block_combo.findText(block_str)
						print(f"DEBUG: Block index found: {block_index}")
						if block_index >= 0:
							self.close_block_combo.setCurrentIndex(block_index)
							print("DEBUG: Auto-population successful")
		else:
			print("DEBUG: Required combo boxes not found")


	# State Manager Signal Handlers
	def on_train_selected(self, train_id: str):
		"""Handle train selection across all tabs"""
		if train_id:
			# Update train table selection if it exists
			if hasattr(self, 'train_info_table'):
				self.update_train_table_selection(train_id)
			if hasattr(self, 'current_trains_table'):
				self.update_current_trains_selection(train_id)
			
			# Note: Track visualization highlighting could be implemented in the future
			# if hasattr(self, 'trackVisualization'):
			#     self.trackVisualization.highlight_train(train_id)
				
			# Switch to train management tab if requested
			# This could be extended to switch tabs automatically

	def on_block_selected(self, line: str, block: int):
		"""Handle block selection across all tabs"""
		# Note: Track visualization highlighting could be implemented in the future
		# if hasattr(self, 'trackVisualization'):
		#     self.trackVisualization.highlight_block(line, block)
			
		# Pre-populate maintenance controls if maintenance tab elements exist
		if hasattr(self, 'close_line_combo') and hasattr(self, 'close_section_combo') and hasattr(self, 'close_block_combo'):
			# Set the line
			line_index = self.close_line_combo.findText(line)
			if line_index >= 0:
				self.close_line_combo.setCurrentIndex(line_index)
				
				# Update sections for the selected line
				self.update_close_sections()
				
				# Find and set the section for this block
				section = self.get_section_for_block(line, block)
				if section:
					section_index = self.close_section_combo.findText(section)
					if section_index >= 0:
						self.close_section_combo.setCurrentIndex(section_index)
						
						# Update blocks for the selected section
						self.update_close_blocks()
						
						# Set the specific block
						block_str = str(block).zfill(4)  # Format with leading zeros to match combo format
						print(f"DEBUG: Looking for block string: {block_str}")
						block_index = self.close_block_combo.findText(block_str)
						print(f"DEBUG: Block index found: {block_index}")
						if block_index >= 0:
							self.close_block_combo.setCurrentIndex(block_index)
							print("DEBUG: Auto-population successful")
				
		# Update block info table selection
		if hasattr(self, 'block_info_table'):
			self.update_block_table_selection(line, block)

	def on_state_changed(self):
		"""Handle general state changes"""
		# Update UI to reflect current state
		self.update_train_info_table()
		self.update_warnings_display()
		# Force track redraw to show updated state
		if hasattr(self, 'trackVisualization'):
			self.track_needs_redraw = True

	def on_trains_updated(self):
		"""Handle train state changes - triggered when trains are added, removed, or routed"""
		# Train state has changed
		# Force immediate table update to show new/updated trains
		self.update_train_info_table()
		if hasattr(self, 'current_trains_table'):
			all_train_data = self.display_manager.get_train_info_for_display(
				trains=self.ctc_system.trains,
				train_suggested_speeds=self.ctc_system.trainSuggestedSpeeds
			)
			self.update_current_trains_table(all_train_data)
		# Force track redraw to show updated trains
		if hasattr(self, 'trackVisualization'):
			self.track_needs_redraw = True

	def on_warnings_updated(self):
		"""Handle warning state changes"""
		# Warnings have changed
		# Update warnings table immediately
		self.update_warnings_table()

	def on_maintenance_updated(self):
		"""Handle maintenance closure state changes"""
		# Maintenance state has changed
		# Update all UI components that depend on maintenance closures
		self.update_scheduled_closures_display()  # Update table
		self.trackNeedsRedraw = True  # Force track visualization redraw
		self.update_warnings_display()  # Update warnings (may include maintenance)
		print("DEBUG: Maintenance state updated - triggering UI refresh")
		# Force immediate track visualization update
		if hasattr(self, 'trackVisualization'):
			self.create_track_visualization()

	def on_throughput_updated(self, throughput_data):
		"""Handle throughput updates from display manager
		
		Args:
			throughput_data: Dict containing throughput metrics with keys:
				- 'per_line': Dict with per-line throughput data (Blue, Red, Green)
				- 'total': Total hourly throughput rate
				- 'timestamp': Timestamp of update
				OR legacy format:
				- 'current': Current throughput value
				- 'hourly': Hourly throughput rate
				- 'history': List of throughput history entries
		"""
		if throughput_data:
			# Check if we have per-line data (new format)
			if 'per_line' in throughput_data:
				# Use the actual per-line data from the CTC system
				line_data = throughput_data['per_line']
				self.update_throughput(line_data)
			elif 'hourly' in throughput_data:
				# Legacy format - fall back to equal distribution
				# Create per-line data structure (placeholder until backend provides line-specific data)
				line_data = {
					'Blue': throughput_data['hourly'] // 3,
					'Red': throughput_data['hourly'] // 3,
					'Green': throughput_data['hourly'] // 3
				}
				self.update_throughput(line_data)

	# Helper methods for UI updates
	def update_train_table_selection(self, train_id: str):
		"""Update train table to show selected train"""
		if hasattr(self, 'train_info_table'):
			for row in range(self.train_info_table.rowCount()):
				item = self.train_info_table.item(row, 0)  # Train ID column
				if item and item.text() == train_id:
					self.train_info_table.selectRow(row)
					break

	def update_current_trains_selection(self, train_id: str):
		"""Update current trains table to show selected train"""
		if hasattr(self, 'current_trains_table'):
			for row in range(self.current_trains_table.rowCount()):
				item = self.current_trains_table.item(row, 0)  # Train ID column
				if item and item.text() == train_id:
					self.current_trains_table.selectRow(row)
					break

	def update_block_table_selection(self, line: str, block: int):
		"""Update block info table to show selected block"""
		if hasattr(self, 'block_info_table'):
			for row in range(self.block_info_table.rowCount()):
				line_item = self.block_info_table.item(row, 0)  # Line column
				block_item = self.block_info_table.item(row, 4)  # Block column
				if (line_item and line_item.text() == line and 
					block_item and block_item.text() == str(block)):
					self.block_info_table.selectRow(row)
					break

	def update_warnings_display(self):
		"""Update warnings display from display manager"""
		if hasattr(self, 'warnings_table'):
			warnings = self.display_manager.get_warnings(
				failure_manager=self.failure_manager,
				track_status=self.ctc_system.trackStatus,
				railway_crossings=self.ctc_system.railwayCrossings
			)
			self.warnings_table.setRowCount(len(warnings))
			
			for row, warning in enumerate(warnings):
				# Display warning information
				self.warnings_table.setItem(row, 0, QTableWidgetItem(warning.get('type', '')))
				self.warnings_table.setItem(row, 1, QTableWidgetItem(warning.get('message', '')))
				# Add timestamp if available
				if 'timestamp' in warning:
					import datetime
					ts = datetime.datetime.fromtimestamp(warning['timestamp'])
					self.warnings_table.setItem(row, 2, QTableWidgetItem(ts.strftime('%H:%M:%S')))

	def get_block_section(self, block_id, line=None):
		"""Get section information for a block"""
		try:
			if block_id != 'Unknown':
				if line:
					# Use line-aware method when line is provided
					block = self.ctc_system.get_block_by_line(line, int(block_id))
				else:
					# Fallback to original method for backward compatibility
					block = self.ctc_system.get_block(int(block_id))
				if block:
					return block.section
		except (ValueError, AttributeError):
			# Train data format error - return default
			return 'Unknown'
		return 'Unknown'

	def update_scheduled_closures_display(self):
		"""Update the scheduled closures and openings table"""
		if hasattr(self, 'scheduled_closures_table'):
			# Use CTC system delegation for scheduled closures
			maintenance_data = self.ctc_system.get_maintenance_schedule_for_ui()
			scheduled = maintenance_data.get('scheduled_closures', [])
			# Filter to only show active scheduled and active closures
			active_scheduled = [s for s in scheduled if s['status'] in ['scheduled', 'active']]
			
			# Create entries - show scheduled closures, active closures, and scheduled openings
			table_entries = []
			for closure in active_scheduled:
				if closure['status'] == 'scheduled':
					# Show the scheduled closure
					block_id = closure.get('block_id', closure.get('block_number', 'Unknown'))
					line = closure['line']
					section = self.get_block_section(block_id, line)
					table_entries.append({
						'line': closure['line'],
						'section': section,
						'block_number': block_id,
						'type': 'Closure', 
						'scheduled_time': closure.get('time', closure.get('scheduled_time', 'Unknown')),
						'status': closure['status'],
						'closure_id': closure['id']
					})
				elif closure['status'] == 'active':
					# Block is currently closed, show when it will automatically open
					block_id = closure['block_number']
					line = closure['line']
					section = self.get_block_section(block_id, line)
					table_entries.append({
						'line': closure['line'],
						'section': section,
						'block_number': block_id,
						'type': 'Opening',
						'scheduled_time': closure['end_time'],
						'status': 'automatic',  # Not scheduled, but automatic
						'closure_id': closure['id']
					})
			
			# Add scheduled closures from communication handler
			if hasattr(self.communication_handler, 'scheduledClosures'):
				for block, time in self.communication_handler.scheduledClosures:
					block_id = getattr(block, 'blockID', getattr(block, 'block_number', 'Unknown'))
					line = getattr(block, 'line', 'Unknown')
					section = getattr(block, 'section', 'Unknown')
					table_entries.append({
						'line': line,
						'section': section,
						'block_number': block_id,
						'type': 'Closure',
						'scheduled_time': time.strftime('%H:%M') if hasattr(time, 'strftime') else str(time),
						'status': 'scheduled',
						'closure_id': f"closure_{block_id}_{line}"
					})
			
			# Add scheduled openings from communication handler
			if hasattr(self.communication_handler, 'scheduledOpenings'):
				for block, time in self.communication_handler.scheduledOpenings:
					block_id = getattr(block, 'blockID', getattr(block, 'block_number', 'Unknown'))
					line = getattr(block, 'line', 'Unknown')
					section = getattr(block, 'section', 'Unknown')
					table_entries.append({
						'line': line,
						'section': section,
						'block_number': block_id,
						'type': 'Opening',
						'scheduled_time': time.strftime('%H:%M') if hasattr(time, 'strftime') else str(time),
						'status': 'scheduled',
						'closure_id': f"opening_{block_id}_{line}"
					})
			
			# Sort by scheduled time (convert to comparable format)
			def get_sort_key(entry):
				scheduled_time = entry['scheduled_time']
				if hasattr(scheduled_time, 'strftime'):
					# It's a datetime object
					return scheduled_time.strftime('%H:%M')
				else:
					# It's already a string
					return str(scheduled_time)
			
			table_entries.sort(key=get_sort_key)
			
			self.scheduled_closures_table.setRowCount(len(table_entries))
			
			for row, entry in enumerate(table_entries):
				# Line
				line_item = QTableWidgetItem(entry['line'])
				# Store the closure ID as item data for easy retrieval
				line_item.setData(Qt.UserRole, entry['closure_id'])
				self.scheduled_closures_table.setItem(row, 0, line_item)
				
				# Section
				self.scheduled_closures_table.setItem(row, 1, QTableWidgetItem(entry['section']))
				
				# Block
				self.scheduled_closures_table.setItem(row, 2, QTableWidgetItem(str(entry['block_number'])))
				
				# Type (Closure or Opening)
				type_item = QTableWidgetItem(entry['type'])
				
				if entry['type'] == 'Closure':
					type_item.setForeground(QColor('red'))
				else:  # Opening
					type_item.setForeground(QColor('green'))
				
				self.scheduled_closures_table.setItem(row, 3, type_item)
				
				# Scheduled Time
				scheduled_time = entry['scheduled_time']
				if hasattr(scheduled_time, 'strftime'):
					time_str = scheduled_time.strftime('%H:%M')
				else:
					time_str = str(scheduled_time)
				self.scheduled_closures_table.setItem(row, 4, QTableWidgetItem(time_str))
				
				# Status
				if entry['status'] == 'automatic':
					status_text = 'Auto Open'
					status_item = QTableWidgetItem(status_text)
					status_item.setForeground(QColor('blue'))
				else:
					status_text = entry['status'].title()
					status_item = QTableWidgetItem(status_text)
					if entry['status'] == 'active':
						status_item.setForeground(QColor('red'))
					elif entry['status'] == 'scheduled':
						status_item.setForeground(QColor('darkorange'))
				
				font = QFont()
				font.setBold(True)
				status_item.setFont(font)
				self.scheduled_closures_table.setItem(row, 5, status_item)

	def cancel_selected_scheduled_closure(self):
		"""Cancel the selected scheduled closure"""
		if hasattr(self, 'scheduled_closures_table'):
			current_row = self.scheduled_closures_table.currentRow()
			if current_row >= 0:
				# Get the closure ID from the stored item data
				line_item = self.scheduled_closures_table.item(current_row, 0)
				block_item = self.scheduled_closures_table.item(current_row, 2)
				type_item = self.scheduled_closures_table.item(current_row, 3)
				
				if line_item and block_item and type_item:
					# Get the closure ID from the item data
					closure_id = line_item.data(Qt.UserRole)
					line = line_item.text()
					try:
						block_number = int(block_item.text())
					except ValueError:
						StyledMessageBox.warning(self, "Error", f"Invalid block number: {block_item.text()}")
						return
					action_type = type_item.text()
					print(f"Debug: Cancelling {action_type} for {line} Line Block {block_number}, closure_id={closure_id}")
					
					if action_type == "Opening":
						# Handle opening cancellation
						if closure_id.startswith("opening_"):
							# This is a scheduled opening from communication handler
							opening_to_cancel = None
							if hasattr(self.communication_handler, 'scheduledOpenings'):
								print(f"Debug: Found {len(self.communication_handler.scheduledOpenings)} scheduled openings")
								for block, time in self.communication_handler.scheduledOpenings:
									block_id = getattr(block, 'blockID', getattr(block, 'block_number', 'Unknown'))
									block_line = getattr(block, 'line', 'Unknown')
									print(f"Debug: Checking opening - Block {block_id} on {block_line} line")
									if block_line == line and block_id == block_number:
										opening_to_cancel = (block, time)
										print(f"Debug: Found matching opening to cancel")
										break
							else:
								print("Debug: No scheduledOpenings attribute found")
							
							if opening_to_cancel:
								# Confirm cancellation
								reply = StyledMessageBox.question(
									self, 
									"Confirm Cancellation",
									f"Are you sure you want to cancel the scheduled opening for {line} Line Block {block_number}?",
									QMessageBox.Yes | QMessageBox.No
								)
								
								if reply == QMessageBox.Yes:
									self.communication_handler.scheduledOpenings.remove(opening_to_cancel)
									StyledMessageBox.information(self, "Success", f"Scheduled opening for Block {block_number} cancelled")
									# Clear the table and refresh it
									self.scheduled_closures_table.setRowCount(0)
									self.update_scheduled_closures_display()
									print(f"Debug: Cancelled opening for {line} Line Block {block_number}")
							else:
								StyledMessageBox.warning(self, "Error", "Could not find the selected scheduled opening.")
						else:
							# This is an automatic opening from an active closure - cannot be cancelled independently
							StyledMessageBox.warning(self, "Error", "Cannot cancel automatic opening. Cancel the associated closure instead.")
					
					else:  # Closure
						# Handle closure cancellation using the stored closure ID
						if closure_id.startswith("closure_"):
							# This is a closure from communication handler
							closure_to_cancel = None
							if hasattr(self.communication_handler, 'scheduledClosures'):
								for block, time in self.communication_handler.scheduledClosures:
									block_id = getattr(block, 'blockID', getattr(block, 'block_number', 'Unknown'))
									block_line = getattr(block, 'line', 'Unknown')
									if block_line == line and block_id == block_number:
										closure_to_cancel = (block, time)
										break
							
							if closure_to_cancel:
								# Confirm cancellation
								reply = StyledMessageBox.question(
									self, 
									"Confirm Cancellation",
									f"Are you sure you want to cancel the scheduled closure for {line} Line Block {block_number}?",
									QMessageBox.Yes | QMessageBox.No
								)
								
								if reply == QMessageBox.Yes:
									self.communication_handler.scheduledClosures.remove(closure_to_cancel)
									StyledMessageBox.information(self, "Success", f"Scheduled closure for Block {block_number} cancelled")
									# Clear the table and refresh it
									self.scheduled_closures_table.setRowCount(0)
									self.update_scheduled_closures_display()
									print(f"Debug: Cancelled closure for {line} Line Block {block_number}")
							else:
								StyledMessageBox.warning(self, "Error", "Could not find the selected scheduled closure.")
						else:
							# This is a closure from failure manager - use the proper ID
							# Confirm cancellation first
							reply = StyledMessageBox.question(
								self, 
								"Confirm Cancellation",
								f"Are you sure you want to cancel the scheduled closure for {line} Line Block {block_number}?\nThis will cancel both the closure and opening.",
								QMessageBox.Yes | QMessageBox.No
							)
							
							if reply == QMessageBox.Yes:
								# Actually cancel it now
								result = self.failure_manager.cancel_scheduled_closure(closure_id)
								if result['success']:
									StyledMessageBox.information(self, "Success", result['message'])
									# Clear the table and refresh it
									self.scheduled_closures_table.setRowCount(0)
									self.update_scheduled_closures_display()
									print(f"Debug: Cancelled closure for {line} Line Block {block_number}")
								else:
									StyledMessageBox.warning(self, "Error", result['message'])
			else:
				StyledMessageBox.information(self, "No Selection", "Please select a scheduled closure/opening to cancel.")
		else:
			StyledMessageBox.warning(self, "Error", "Scheduled closures table not available.")

	# Tab Management
	def on_tab_changed(self, index):
		"""Handle tab change - reset page states"""
		# Add a flag to prevent reset during programmatic navigation with auto-population
		if not hasattr(self, '_auto_populating'):
			self._auto_populating = False
		
		# Only reset if this is a manual tab change (not auto-population)
		if not self._auto_populating:
			# Clear state manager selections when switching tabs manually
			if hasattr(self, 'state_manager'):
				self.display_manager.set_selected_train("")
				self.display_manager.set_selected_block("", 0)
			
			# Reset specific tab states based on the tab index
			if index == 0:  # Main tab
				self.reset_main_tab()
			elif index == 1:  # Route Train tab
				self.reset_route_train_tab()
				# Always re-initialize dropdowns when accessing Route Train tab
				print("[DEBUG] Accessing Route Train tab - initializing dropdowns")
				self.initialize_route_dropdowns()
			elif index == 2:  # Open/Close Block tab
				self.reset_maintenance_tab()
			
			# Only reset the flag if this was a manual tab change
			self._auto_populating = False

	def reset_main_tab(self):
		"""Reset the main tab to its default state"""
		# Clear any selections in tables
		if hasattr(self, 'train_info_table'):
			self.train_info_table.clearSelection()
		if hasattr(self, 'warnings_table'):
			self.warnings_table.clearSelection()
		if hasattr(self, 'block_info_table'):
			self.block_info_table.clearSelection()

	def reset_route_train_tab(self):
		"""Reset the route train tab to its default state"""
		# Clear train ID input and reset validation styling
		if hasattr(self, 'route_train_id_entry'):
			self.route_train_id_entry.clear()
			self.route_train_id_entry.setStyleSheet("")  # Clear any validation styling
		
		# Clear train info table
		if hasattr(self, 'route_train_info_table'):
			for col in range(self.route_train_info_table.columnCount()):
				self.route_train_info_table.setItem(0, col, QTableWidgetItem(""))
		
		# Clear new train info table
		if hasattr(self, 'new_train_info_table'):
			self.new_train_info_table.setRowCount(0)
		
		# Clear current trains table selection
		if hasattr(self, 'current_trains_table'):
			self.current_trains_table.clearSelection()
		
		# Reset destination selection
		if hasattr(self, 'dest_line_combo') and hasattr(self, 'dest_section_combo') and hasattr(self, 'dest_block_combo'):
			self.dest_line_combo.setCurrentIndex(0)
			# Don't clear dropdowns - they will be re-populated by the tab change handler
		
		# Clear arrival time
		if hasattr(self, 'arrival_time_entry'):
			self.arrival_time_entry.clear()
		
		# Reset selection flags
		if hasattr(self, 'destination_selected'):
			self.destination_selected = False
		if hasattr(self, 'time_selected'):
			self.time_selected = False
		
		# Clear pending route info
		if hasattr(self, 'pending_route_info'):
			delattr(self, 'pending_route_info')

	def reset_maintenance_tab(self):
		"""Reset the maintenance tab to its default state"""
		# Reset line, section, block selections to first item
		if hasattr(self, 'close_line_combo') and self.close_line_combo.count() > 0:
			self.close_line_combo.setCurrentIndex(0)
			self.update_close_sections()
		
		# Clear time entry
		if hasattr(self, 'close_time_entry'):
			self.close_time_entry.clear()
		
		# Clear table selections
		if hasattr(self, 'close_block_table'):
			self.close_block_table.clearSelection()
		if hasattr(self, 'scheduled_closures_table'):
			self.scheduled_closures_table.clearSelection()

		
		# Clear table selections if they exist
		if hasattr(self, 'train_error_table'):
			self.train_error_table.clearSelection()
		if hasattr(self, 'affected_trains_table'):
			self.affected_trains_table.clearSelection()
		if hasattr(self, 'success_trains_table'):
			self.success_trains_table.clearSelection()
		if hasattr(self, 'unable_trains_table'):
			self.unable_trains_table.clearSelection()

	def closeEvent(self, event):
		"""Handle application close"""
		self.running = False
		if self.updateWorker:
			self.updateWorker.stop()
		event.accept()


# Integration functions
def create_ctc_interface():
	"""Factory function to create CTC Interface instance"""
	return CTCInterface()


def send_to_ctc(ctc_interface, message):
	"""Send message from Wayside Controller to CTC Interface"""
	ctc_interface.train_manager.receive_message(message)


def get_from_ctc(ctc_interface):
	"""Get message from CTC Interface to Wayside Controller"""
	return ctc_interface.train_manager.get_outgoing_message()


if __name__ == "__main__":
	# For testing the interface independently
	app = QApplication(sys.argv)
	ctc = CTCInterface()
	ctc.show()
	sys.exit(app.exec_())