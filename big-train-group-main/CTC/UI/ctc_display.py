"""
CTC Visual Display Helper
=========================
Provides methods to create visual representations of track layout
for the dispatcher interface. Designed to be clear and intuitive
for non-technical users.
"""

from Track_Reader.track_reader import TrackLayoutReader
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from typing import Dict, List, Optional
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

    def __init__(self, track_reader: TrackLayoutReader):
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


# === Example Usage ===
if __name__ == "__main__":
    # Initialize systems
    reader = TrackLayoutReader("../Track_Reader/Track Layout & Vehicle Data vF2.xlsx")
    visual = CTCVisualDisplay(reader)

    # Example 1: Display Blue Line with trains and maintenance
    active_trains = {5: "T101", 10: "T102", 15: "T103"}
    maintenance_sections = ["B"]

    fig1 = visual.create_line_diagram(
        "Blue",
        active_trains=active_trains,
        maintenance_sections=maintenance_sections
    )
    # In real application: fig1.show() or embed in GUI

    # Example 2: System overview for dispatcher's main screen
    all_trains = {
        "Blue": {5: "T101", 10: "T102"},
        "Red": {25: "T201", 50: "T202"},
        "Green": {9: "T301", 75: "T302"}
    }
    all_maintenance = {
        "Blue": ["B"],
        "Red": [],
        "Green": ["F", "G"]
    }

    fig2 = visual.create_system_overview(
        active_trains=all_trains,
        maintenance=all_maintenance
    )
    # In real application: fig2.show() or embed in GUI

    print("Visual displays created successfully!")
    print("\nFor integration with CTC Office GUI:")
    print("1. Use create_line_diagram() for detailed track views")
    print("2. Use create_system_overview() for dispatcher's main dashboard")
    print("3. Update displays in real-time as trains move and status changes")
    print("4. Click handlers can use block numbers to get detailed info")