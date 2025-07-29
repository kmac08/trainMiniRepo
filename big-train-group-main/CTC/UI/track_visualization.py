"""
CTC UI - Track Visualization
===========================
Handles all track visualization components for the CTC interface.
Separated from main UI for better modularity.
"""

import time
import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as patches
from PyQt5.QtWidgets import QWidget
from datetime import datetime


class TrackVisualization:
    """
    Manages track visualization components for the CTC interface.
    Handles matplotlib integration and track drawing.
    """

    def __init__(self, track_reader):
        self.track_reader = track_reader
        self.figure = None
        self.canvas = None
        self.widget = None
        self.layout_cache = {}  # Cache for auto-generated layouts
        self.interactive_elements = {}  # Store clickable elements for future interaction
        self.click_callback = None  # Callback function for click events
        
    def create_widget(self):
        """Create the track visualization widget"""
        # Much larger figure size for better visibility
        self.figure = Figure(figsize=(16, 10), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.widget = self.canvas
        
        # Disable mouse click events to make charts non-editable
        # self.canvas.mpl_connect('button_press_event', self._on_click)
        
        return self.widget
        
    def set_click_callback(self, callback):
        """Set callback function for track element clicks"""
        self.click_callback = callback
        
    def _on_click(self, event):
        """Handle mouse click events on the track visualization"""
        if event.inaxes is None or self.click_callback is None:
            return
            
        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return
            
        # Check if click is within any interactive elements
        for element_id, element_data in self.interactive_elements.items():
            if self._point_in_element(x, y, element_data):
                self.click_callback(element_data['type'], element_data)
                break
                
    def _point_in_element(self, x, y, element):
        """Check if a point is within an interactive element's bounds"""
        return (element['x'] <= x <= element['x'] + element['width'] and
                element['y'] <= y <= element['y'] + element['height'])
        
    def update_display(self, selected_line, trains, maintenance_closures, use_auto_layout=True):
        """Update the track visualization display"""
        if not self.figure:
            return
            
        # Clear previous plot
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # Set light background color to match track theme
        ax.set_facecolor('#FFFFFF')
        
        # Choose visualization method based on available lines
        available_lines = list(self.track_reader.lines.keys())
        
        if use_auto_layout:
            # Use new auto-generated boxy layout
            if selected_line == "Red & Green":
                # Show both Red and Green lines in a simplified, clean format
                self.draw_simplified_red_green_map(ax, trains, maintenance_closures)
                ax.set_aspect('equal')
                ax.axis('off')
            else:
                # Single line view
                self.draw_auto_generated_map(ax, selected_line, trains, maintenance_closures)
                ax.set_aspect('equal')
                ax.axis('off')
        else:
            # Use simple clean layout - automatically choose based on available lines
            if len(available_lines) == 1:
                # Single line loaded - show that line
                line_name = available_lines[0]
                if line_name == "Blue":
                    self.draw_blue_line(ax, trains, maintenance_closures)
                else:
                    self.draw_auto_generated_map(ax, line_name, trains, maintenance_closures)
            elif len(available_lines) == 2 and "Red" in available_lines and "Green" in available_lines:
                # Red and Green together
                self.draw_simplified_red_green_map(ax, trains, maintenance_closures)
            elif selected_line == "Blue" and "Blue" in available_lines:
                self.draw_blue_line(ax, trains, maintenance_closures)
            elif selected_line == "Red & Green":
                self.draw_simplified_red_green_map(ax, trains, maintenance_closures)
            else:
                # Default to auto-generated layout for other cases
                if selected_line in available_lines:
                    self.draw_auto_generated_map(ax, selected_line, trains, maintenance_closures)
                else:
                    # Fallback - show first available line
                    self.draw_auto_generated_map(ax, available_lines[0], trains, maintenance_closures)
                
            # Set axis properties
            ax.set_aspect('equal')
            ax.axis('off')
        
        self.canvas.draw()
        
    def draw_red_green_lines(self, ax, trains, maintenance_closures):
        """Draw Red and Green lines using actual track layout data"""
        # Get actual track data
        red_blocks = self.track_reader.lines.get("Red", [])
        green_blocks = self.track_reader.lines.get("Green", [])

        if not red_blocks and not green_blocks:
            ax.text(250, 150, 'No Red/Green Line Data Available', ha='center', va='center', fontsize=23)
            return

        # Build connections from actual track data
        green_connections = []
        red_connections = []

        # Create section positions dynamically based on actual sections
        green_sections = sorted(set(block.section for block in green_blocks))
        red_sections = sorted(set(block.section for block in red_blocks))

        # Generate positions for sections in a circular/network layout
        green_section_positions = {}
        red_section_positions = {}

        # Layout green sections
        num_green = len(green_sections)
        if num_green > 0:
            for i, section in enumerate(green_sections):
                angle = (i / num_green) * 2 * np.pi
                if i % 4 == 0:  # Upper loop
                    x = 200 + 120 * np.cos(angle)
                    y = 250 + 60 * np.sin(angle)
                elif i % 4 == 1:  # Lower left loop
                    x = 100 + 60 * np.cos(angle)
                    y = 150 + 40 * np.sin(angle)
                elif i % 4 == 2:  # Lower right loop
                    x = 300 + 60 * np.cos(angle)
                    y = 120 + 40 * np.sin(angle)
                else:  # Connections
                    x = 200 + 150 * np.cos(angle)
                    y = 180 + 80 * np.sin(angle)
                green_section_positions[section] = (x, y)

        # Layout red sections
        num_red = len(red_sections)
        if num_red > 0:
            for i, section in enumerate(red_sections):
                angle = (i / num_red) * 2 * np.pi
                if i < num_red // 3:  # Main upper loop
                    x = 250 + 80 * np.cos(angle)
                    y = 180 + 30 * np.sin(angle)
                elif i < 2 * num_red // 3:  # Lower left loop
                    x = 120 + 50 * np.cos(angle)
                    y = 100 + 30 * np.sin(angle)
                else:  # Lower right loop
                    x = 180 + 40 * np.cos(angle)
                    y = 90 + 25 * np.sin(angle)
                red_section_positions[section] = (x, y)

        # Build connections from track data
        for i in range(len(green_blocks) - 1):
            curr_section = green_blocks[i].section
            next_section = green_blocks[i + 1].section
            if curr_section in green_section_positions and next_section in green_section_positions:
                if (curr_section, next_section) not in green_connections:
                    green_connections.append((curr_section, next_section))

        for i in range(len(red_blocks) - 1):
            curr_section = red_blocks[i].section
            next_section = red_blocks[i + 1].section
            if curr_section in red_section_positions and next_section in red_section_positions:
                if (curr_section, next_section) not in red_connections:
                    red_connections.append((curr_section, next_section))

        # Draw Green line
        green_color = '#4CAF50'
        for section1, section2 in green_connections:
            if section1 in green_section_positions and section2 in green_section_positions:
                x1, y1 = green_section_positions[section1]
                x2, y2 = green_section_positions[section2]
                ax.plot([x1, x2], [y1, y2], color=green_color, linewidth=4, alpha=0.8)

        # Draw section markers for green line with maintenance indication
        for section in green_sections:
            if section in green_section_positions:
                x, y = green_section_positions[section]
                # Check if any blocks in this section are closed for maintenance
                section_blocks = [b.block_number for b in green_blocks if b.section == section]
                has_closed_blocks = any(block in maintenance_closures.get("Green", []) for block in section_blocks)

                color = 'red' if has_closed_blocks else green_color
                ax.text(x, y, section, ha='center', va='center',
                       fontsize=13, fontweight='bold',
                       bbox=dict(boxstyle="circle,pad=0.3", facecolor='white',
                                edgecolor=color, linewidth=2))

        # Draw Red line
        red_color = '#F44336'
        for section1, section2 in red_connections:
            if section1 in red_section_positions and section2 in red_section_positions:
                x1, y1 = red_section_positions[section1]
                x2, y2 = red_section_positions[section2]
                ax.plot([x1, x2], [y1, y2], color=red_color, linewidth=4, alpha=0.8)

        # Draw section markers for red line with maintenance indication
        for section in red_sections:
            if section in red_section_positions:
                x, y = red_section_positions[section]
                # Check if any blocks in this section are closed for maintenance
                section_blocks = [b.block_number for b in red_blocks if b.section == section]
                has_closed_blocks = any(block in maintenance_closures.get("Red", []) for block in section_blocks)

                color = 'red' if has_closed_blocks else red_color
                ax.text(x, y, section, ha='center', va='center',
                       fontsize=13, fontweight='bold',
                       bbox=dict(boxstyle="circle,pad=0.3", facecolor='white',
                                edgecolor=color, linewidth=2))

        # Add trains from actual train data
        for train_id, train in trains.items():
            if train.line in ['Red', 'Green']:
                block_info = self.track_reader.get_block_info(train.line, train.currentBlock)
                if block_info:
                    positions = green_section_positions if train.line == "Green" else red_section_positions
                    if block_info.section in positions:
                        x, y = positions[block_info.section]
                        # Draw train
                        train_rect = patches.Rectangle((x-10, y-6), 20, 12,
                                                     facecolor='purple', edgecolor='white', linewidth=2)
                        ax.add_patch(train_rect)
                        ax.text(x, y, train.id, ha='center', va='center',
                               color='white', fontsize=14, fontweight='bold')

        # Add title
        ax.text(200, 320, 'RED & GREEN LINE', fontsize=23, fontweight='bold')

    def draw_blue_line(self, ax, trains, maintenance_closures):
        """Draw Blue line with proper switch handling and improved readability"""
        blue_blocks = self.track_reader.lines.get("Blue", [])
        blue_color = '#2196F3'

        if not blue_blocks:
            ax.text(250, 150, 'No Blue Line Data Available', ha='center', va='center', fontsize=23)
            return

        # Sort blocks by block number for logical ordering
        sorted_blocks = sorted(blue_blocks, key=lambda b: b.block_number)
        
        # Improved layout parameters for better readability
        main_track_y = 150  # Y position for main line (blocks 1-5, 6-10)
        alt_track_y = 100   # Y position for alternate line (blocks 11-15)
        track_start_x = 100
        block_width = 30  # Even larger blocks for better visibility
        
        # Draw yard at the start with better labeling
        yard_x = 50
        yard_rect = patches.Rectangle((yard_x-20, main_track_y-15), 40, 30, 
                                    facecolor='lightgray', edgecolor='black', linewidth=2)
        ax.add_patch(yard_rect)
        ax.text(yard_x, main_track_y, 'YARD', ha='center', va='center', fontsize=13, fontweight='bold')
        
        # Draw connection from yard to track
        ax.plot([yard_x + 20, track_start_x], [main_track_y, main_track_y], 
               color=blue_color, linewidth=10, alpha=0.8)
        
        # Blue line has a fork at block 5: blocks 6-10 go straight, blocks 11-15 go on alternate path
        # Then they rejoin after block 15 to continue to downtown
        block_positions = {}  # Store position of each block for later reference
        
        # Draw blocks 1-5 (before the fork)
        current_x = track_start_x
        for block in sorted_blocks:
            if block.block_number <= 5:
                block_positions[block.block_number] = {'x': current_x, 'y': main_track_y}
                current_x += block_width + 2
        
        # Save position after block 5 for the fork
        fork_x = current_x - block_width - 2
        
        # Draw blocks 6-10 (main branch)
        main_branch_x = current_x
        for block in sorted_blocks:
            if 6 <= block.block_number <= 10:
                block_positions[block.block_number] = {'x': main_branch_x, 'y': main_track_y}
                main_branch_x += block_width + 2
        
        # Draw blocks 11-15 (alternate branch)
        alt_branch_x = current_x
        for block in sorted_blocks:
            if 11 <= block.block_number <= 15:
                block_positions[block.block_number] = {'x': alt_branch_x, 'y': alt_track_y}
                alt_branch_x += block_width + 2
        
        # Continue with remaining blocks after the branches
        rejoin_x = max(main_branch_x, alt_branch_x) + 20  # Space after branches
        current_x = rejoin_x
        
        # Removed hardcoded rejoin connections - let the actual track data define connections
        
        for block in sorted_blocks:
            if block.block_number > 15:
                block_positions[block.block_number] = {'x': current_x, 'y': main_track_y}
                current_x += block_width + 2
        
        # Now draw all the blocks
        for block in sorted_blocks:
            if block.block_number not in block_positions:
                continue
                
            pos = block_positions[block.block_number]
            x = pos['x']
            y = pos['y']
            
            # Determine block color based on maintenance
            if block.block_number in maintenance_closures.get("Blue", []):
                block_color = '#FF5555'  # Maintenance
            else:
                block_color = blue_color
            
            # Draw the block
            ax.plot([x, x + block_width - 2], [y, y],
                   color=block_color, linewidth=12, solid_capstyle='butt', alpha=0.9)
            
            # Add block number for every block (small text)
            ax.text(x + block_width/2, y - 15, str(block.block_number),
                   ha='center', va='center', fontsize=10, color='black',
                   bbox=dict(boxstyle="round,pad=0.05", facecolor='white', alpha=0.8))
            
            # Add station marker and name if present
            if block.has_station and block.station:
                # Station marker
                ax.plot(x + block_width/2, y, 'o', markersize=10, color='#FFD700', 
                       markeredgecolor='#B8860B', markeredgewidth=2)
                # Station name above track
                ax.text(x + block_width/2, y + 25, block.station.name,
                       ha='center', va='center', fontsize=16, fontweight='bold',
                       bbox=dict(boxstyle="round,pad=0.2", facecolor='#FFFACD', alpha=0.9))
            
            # Add switch marker if present
            if block.has_switch:
                ax.plot(x + block_width/2, y, 'D', markersize=8, color='#FF8C00', 
                       markeredgecolor='#FF4500', markeredgewidth=2)
                
                # Draw connection lines for switch at block 5
                if block.block_number == 5:
                    # Draw diverging connections from block 5 to blocks 6 and 11
                    if 6 in block_positions and 11 in block_positions:
                        # Connection to block 6 (straight)
                        pos6 = block_positions[6]
                        ax.plot([x + block_width, pos6['x']], 
                               [y, pos6['y']], 
                               color=blue_color, linewidth=8, alpha=0.7)
                        
                        # Connection to block 11 (branch down)
                        pos11 = block_positions[11]
                        ax.plot([x + block_width/2, pos11['x']], 
                               [y, pos11['y']], 
                               color=blue_color, linewidth=8, alpha=0.7)
        
        # Add section labels
        sections = {}
        for block in sorted_blocks:
            if block.section not in sections:
                sections[block.section] = []
            sections[block.section].append(block)
        
        # Draw section labels
        for section_name, section_blocks in sections.items():
            if section_blocks:
                # Find average position of blocks in this section
                section_x = sum(block_positions[b.block_number]['x'] for b in section_blocks) / len(section_blocks)
                section_y = main_track_y + 50  # Below the track
                
                ax.text(section_x, section_y, f"Section {section_name}",
                       ha='center', va='center', fontsize=13, fontweight='bold',
                       bbox=dict(boxstyle="round,pad=0.3", facecolor='#E6F3FF', 
                                edgecolor=blue_color, linewidth=2))
        
        # Add trains with accurate positioning
        for train_id, train in trains.items():
            if train.line == 'Blue' and train.currentBlock in block_positions:
                pos = block_positions[train.currentBlock]
                train_x = pos['x'] + block_width/2
                train_y = pos['y']
                
                # Train as rounded rectangle
                train_rect = patches.FancyBboxPatch((train_x-10, train_y-6), 20, 12,
                                                   boxstyle="round,pad=2",
                                                   facecolor='#8A2BE2', edgecolor='white', linewidth=2)
                ax.add_patch(train_rect)
                ax.text(train_x, train_y, getattr(train, 'id', getattr(train, 'trainID', getattr(train, 'train_id', 'T'))), ha='center', va='center',
                       color='white', fontsize=14, fontweight='bold')

        # # Add destination labels at the ends
        # if sorted_blocks:
        #     # Start destination (YARD already drawn)
        #     # End destination
        #     end_x = current_x + 50
        #     ax.text(end_x, main_track_y, 'DOWNTOWN', ha='center', va='center',
        #            fontsize=13, fontweight='bold',
        #            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgray', alpha=0.9))

        # Title
        ax.text(current_x/2, main_track_y + 80, 'BLUE LINE', fontsize=20, fontweight='bold', color=blue_color)
        
        # Add legend
        self._draw_blue_line_legend(ax, current_x)
        
        # Set clean axis limits
        ax.set_xlim(0, current_x + 100)
        ax.set_ylim(30, 250)  # Fixed Y limits for consistent view with legend

    def _draw_blue_line_legend(self, ax, max_x):
        """Draw legend for the Blue line map"""
        # Position legend at bottom left
        legend_x = 50
        legend_y = 50
        legend_width = 300
        legend_height = 40
        
        # Legend background
        legend_bg = patches.Rectangle((legend_x - 10, legend_y - 10), legend_width, legend_height, 
                                    facecolor='#F8F8F8', edgecolor='black', linewidth=1, alpha=0.9)
        ax.add_patch(legend_bg)
        
        # Legend items
        items = [
            ('Track', '#2196F3', 'line'),
            ('Station', '#FFD700', 'circle'),
            ('Switch', '#FF8C00', 'diamond'),
            ('Train', '#8A2BE2', 'square'),
            ('Maintenance', '#FF5555', 'line')
        ]
        
        for i, (label, color, shape) in enumerate(items):
            x_pos = legend_x + (i * 55)
            y_pos = legend_y + 10
            
            if shape == 'line':
                ax.plot([x_pos, x_pos + 15], [y_pos, y_pos], color=color, linewidth=6)
            elif shape == 'circle':
                ax.plot(x_pos + 7, y_pos, 'o', markersize=8, color=color, 
                       markeredgecolor='#B8860B', markeredgewidth=2)
            elif shape == 'diamond':
                ax.plot(x_pos + 7, y_pos, 'D', markersize=7, color=color, 
                       markeredgecolor='#FF4500', markeredgewidth=1)
            elif shape == 'square':
                ax.plot(x_pos + 7, y_pos, 's', markersize=7, color=color, 
                       markeredgecolor='black', markeredgewidth=1)
            
            ax.text(x_pos + 7, y_pos - 10, label, ha='center', va='center', fontsize=10)

    def draw_simplified_red_green_map(self, ax, trains, maintenance_closures):
        """
        Draw a clean Red & Green line map with proper blocks and switches.
        """
        # Clear previous interactive elements 
        self.interactive_elements = {}
        
        # Set canvas size
        ax.set_xlim(0, 1400)
        ax.set_ylim(0, 600)
        
        # Get block data
        red_blocks = self.track_reader.lines.get("Red", [])
        green_blocks = self.track_reader.lines.get("Green", [])
        
        # Draw improved Red Line
        self._draw_improved_red_line(ax, red_blocks, trains, maintenance_closures)
        
        # Draw improved Green Line
        self._draw_improved_green_line(ax, green_blocks, trains, maintenance_closures)
        
        # Add simple legend
        self._draw_simple_legend(ax)
        
    def _draw_improved_red_line(self, ax, red_blocks, trains, maintenance_closures):
        """Draw Red line with visible blocks and proper section labels"""
        if not red_blocks:
            return
            
        red_color = '#F44336'
        red_y = 450
        
        # Sort blocks
        sorted_blocks = sorted(red_blocks, key=lambda b: b.block_number)
        track_start_x = 100
        block_width = 12  # Visible block size
        
        # Group into sections
        sections = {}
        for block in sorted_blocks:
            if block.section not in sections:
                sections[block.section] = []
            sections[block.section].append(block)
        
        block_positions = {}
        current_x = track_start_x
        
        # Store section positions for grouped labeling
        section_groups = []
        
        # Draw each section
        for section_idx, section_name in enumerate(sorted(sections.keys())):
            section_blocks = sections[section_name]
            
            # Store section info for grouped labeling
            section_start_x = current_x
            
            # Draw blocks in this section
            for i, block in enumerate(section_blocks):
                block_x = current_x + i * block_width
                block_positions[block.block_number] = {'x': block_x, 'y': red_y}
                
                # Determine block color
                if block.block_number in maintenance_closures.get("Red", []):
                    block_color = '#FF5555'
                elif block.has_station:
                    block_color = '#FF8888'  # Lighter red for stations
                elif block.has_switch:
                    block_color = '#FFAA88'  # Orange-ish for switches
                else:
                    block_color = red_color
                
                # Draw block
                ax.plot([block_x, block_x + block_width - 2], [red_y, red_y],
                       color=block_color, linewidth=10, solid_capstyle='butt', alpha=0.9)
                
                # Add block number for key blocks
                if block.block_number % 10 == 0 or block.has_station or block.has_switch:
                    ax.text(block_x + block_width/2, red_y - 8, str(block.block_number),
                           ha='center', va='center', fontsize=10, color='black')
                
                # Add station marker
                if block.has_station and block.station:
                    ax.plot(block_x + block_width/2, red_y, 'o', markersize=8, 
                           color='#FFD700', markeredgecolor='#B8860B', markeredgewidth=1)
                
                # Add switch marker
                if block.has_switch:
                    ax.plot(block_x + block_width/2, red_y, 'D', markersize=7, 
                           color='#FF8C00', markeredgecolor='#FF4500', markeredgewidth=1)
            
            # Store section group info
            section_groups.append({
                'name': section_name,
                'start_x': section_start_x,
                'end_x': current_x + len(section_blocks) * block_width,
                'blocks': section_blocks
            })
            
            current_x += len(section_blocks) * block_width + 15  # Gap between sections
        
        # Draw grouped section labels (like Green line)
        section_label_groups = [
            (['A', 'B', 'C'], 0, 2),
            (['D', 'E', 'F'], 3, 5),
            (['G', 'H', 'I'], 6, 8),
            (['J', 'K', 'L'], 9, 11),
            (['M', 'N', 'O'], 12, 14),
            (['P', 'Q', 'R'], 15, 17),
            (['S', 'T'], 18, 19)
        ]
        
        for sections_in_group, start_idx, end_idx in section_label_groups:
            # Find the sections that exist in this group
            existing_sections = [sg for sg in section_groups if sg['name'] in sections_in_group]
            if existing_sections:
                # Calculate center position for this group
                group_start_x = existing_sections[0]['start_x']
                group_end_x = existing_sections[-1]['end_x']
                group_center_x = (group_start_x + group_end_x) / 2
                
                # Create label text
                if len(existing_sections) == 1:
                    label_text = f"Section {existing_sections[0]['name']}"
                else:
                    label_text = f"Sections {existing_sections[0]['name']}-{existing_sections[-1]['name']}"
                
                # Draw grouped label
                ax.text(group_center_x, red_y + 20, label_text,
                       ha='center', va='center', fontsize=16, fontweight='bold',
                       bbox=dict(boxstyle="round,pad=0.3", facecolor='#FFE5E5', 
                               edgecolor=red_color, linewidth=1, alpha=0.9))
        
        # Show key station names (selected to avoid overlap)
        key_stations = []
        for block in sorted_blocks:
            if block.has_station and block.station and block.block_number in block_positions:
                # Only include major stations
                if any(word in block.station.name.upper() for word in ['SHADYSIDE', 'HERRON', 'SWISSVILLE', 'STEEL', 'STATION SQUARE', 'SOUTH HILLS']):
                    pos = block_positions[block.block_number]
                    key_stations.append({
                        'name': block.station.name,
                        'x': pos['x'] + block_width/2,
                        'y': pos['y']
                    })
        
        # Draw selected station names with alternating positions
        for i, station in enumerate(key_stations):
            label_y = station['y'] - 25 - (i % 2) * 15  # Alternate between two heights
            ax.text(station['x'], label_y, station['name'],
                   ha='center', va='center', fontsize=10,
                   bbox=dict(boxstyle="round,pad=0.2", facecolor='#FFFACD', alpha=0.9))
        
        # Draw yard connection for Red line
        # Block 9 has bidirectional connection to yard
        if 9 in block_positions:
            pos = block_positions[9]
            yard_x = pos['x'] + block_width/2
            yard_y = pos['y'] + 30
            
            # Draw yard box
            yard_rect = patches.Rectangle((yard_x - 25, yard_y - 8), 50, 16,
                                        facecolor='lightgray', edgecolor='black', linewidth=1)
            ax.add_patch(yard_rect)
            ax.text(yard_x, yard_y, 'YARD', ha='center', va='center', 
                   fontsize=10, fontweight='bold')
            
            # Connect to track with bidirectional arrows
            ax.plot([yard_x, yard_x], [pos['y'], yard_y - 8],
                   color=red_color, linewidth=3, alpha=0.7)
            # Bidirectional arrows
            ax.plot(yard_x - 3, yard_y - 6, '^', markersize=6, color=red_color)
            ax.plot(yard_x + 3, pos['y'] + 4, 'v', markersize=6, color=red_color)
        
        # Add trains
        for train_id, train in trains.items():
            if train.line == 'Red' and train.currentBlock in block_positions:
                pos = block_positions[train.currentBlock]
                train_x = pos['x'] + block_width/2
                train_y = pos['y']
                
                # Draw train
                train_rect = patches.Rectangle((train_x-8, train_y-5), 16, 10,
                                             facecolor='#8A2BE2', edgecolor='white', linewidth=1)
                ax.add_patch(train_rect)
                ax.text(train_x, train_y, getattr(train, 'id', getattr(train, 'trainID', getattr(train, 'train_id', 'T'))), ha='center', va='center',
                       color='white', fontsize=10, fontweight='bold')
        
        # Title
        ax.text(600, red_y + 60, 'RED LINE', fontsize=23, fontweight='bold', color=red_color)
    
    def _draw_improved_green_line(self, ax, green_blocks, trains, maintenance_closures):
        """Draw Green line with proper loop structure"""
        if not green_blocks:
            return
            
        green_color = '#4CAF50'
        green_y = 200
        
        # Sort blocks
        sorted_blocks = sorted(green_blocks, key=lambda b: b.block_number)
        track_start_x = 100
        block_width = 10  # Slightly smaller than Red line
        
        block_positions = {}
        
        # Draw main line before fork (blocks 1-13)
        current_x = track_start_x
        for block in sorted_blocks:
            if block.block_number <= 13:
                block_positions[block.block_number] = {'x': current_x, 'y': green_y}
                
                # Block color
                if block.block_number in maintenance_closures.get("Green", []):
                    block_color = '#FF5555'
                elif block.has_station:
                    block_color = '#88DD88'  # Light green for stations
                elif block.has_switch:
                    block_color = '#DDAA88'  # Orange-ish for switches
                else:
                    block_color = green_color
                
                ax.plot([current_x, current_x + block_width - 1], [green_y, green_y],
                       color=block_color, linewidth=10, solid_capstyle='butt', alpha=0.9)
                
                # Block numbers for switch block
                if block.has_switch:
                    ax.text(current_x + block_width/2, green_y - 8, str(block.block_number),
                           ha='center', va='center', fontsize=10, color='black')
                    ax.plot(current_x + block_width/2, green_y, 'D', markersize=7, 
                           color='#FF8C00', markeredgecolor='#FF4500', markeredgewidth=1)
                
                current_x += block_width
        
        # Fork position
        fork_x = current_x
        
        # Draw loop structure
        loop_top_y = green_y - 60
        loop_bottom_y = green_y + 60
        loop_start_x = fork_x + 30
        loop_width = 400
        
        # Top branch of loop (blocks 14-63)
        current_x = loop_start_x
        for block in sorted_blocks:
            if 14 <= block.block_number <= 63:
                block_positions[block.block_number] = {'x': current_x, 'y': loop_top_y}
                
                # Block color
                if block.block_number in maintenance_closures.get("Green", []):
                    block_color = '#FF5555'
                elif block.has_station:
                    block_color = '#88DD88'
                elif block.has_switch:
                    block_color = '#DDAA88'
                else:
                    block_color = green_color
                
                ax.plot([current_x, current_x + block_width - 1], [loop_top_y, loop_top_y],
                       color=block_color, linewidth=10, solid_capstyle='butt', alpha=0.9)
                
                # Show some block numbers
                if block.block_number % 20 == 0 or block.has_station:
                    ax.text(current_x + block_width/2, loop_top_y - 8, str(block.block_number),
                           ha='center', va='center', fontsize=9, color='black')
                
                current_x += block_width * 0.8  # Compress loop blocks
        
        # Bottom branch of loop (blocks 64-100)
        current_x = loop_start_x + loop_width
        for block in sorted_blocks:
            if 64 <= block.block_number <= 100:
                block_positions[block.block_number] = {'x': current_x, 'y': loop_bottom_y}
                
                # Block color
                if block.block_number in maintenance_closures.get("Green", []):
                    block_color = '#FF5555'
                elif block.has_station:
                    block_color = '#88DD88'
                elif block.has_switch:
                    block_color = '#DDAA88'
                else:
                    block_color = green_color
                
                ax.plot([current_x, current_x + block_width - 1], [loop_bottom_y, loop_bottom_y],
                       color=block_color, linewidth=10, solid_capstyle='butt', alpha=0.9)
                
                # Show some block numbers
                if block.block_number % 20 == 0:
                    ax.text(current_x + block_width/2, loop_bottom_y + 8, str(block.block_number),
                           ha='center', va='center', fontsize=9, color='black')
                
                current_x -= block_width * 0.8  # Right to left
        
        # Main line after loop (blocks 101+)
        current_x = loop_start_x + loop_width + 30
        for block in sorted_blocks:
            if block.block_number >= 101:
                block_positions[block.block_number] = {'x': current_x, 'y': green_y}
                
                # Block color
                if block.block_number in maintenance_closures.get("Green", []):
                    block_color = '#FF5555'
                elif block.has_station:
                    block_color = '#88DD88'
                elif block.has_switch:
                    block_color = '#DDAA88'
                else:
                    block_color = green_color
                
                ax.plot([current_x, current_x + block_width - 1], [green_y, green_y],
                       color=block_color, linewidth=10, solid_capstyle='butt', alpha=0.9)
                
                current_x += block_width
        
        # Draw connections
        # Fork to loop
        ax.plot([fork_x, fork_x, loop_start_x], [green_y, loop_top_y, loop_top_y],
               color=green_color, linewidth=6, alpha=0.8)
        ax.plot([fork_x, fork_x, loop_start_x], [green_y, loop_bottom_y, loop_bottom_y],
               color=green_color, linewidth=6, alpha=0.8)
        
        # Loop end connection
        loop_end_x = loop_start_x + loop_width
        ax.plot([loop_end_x, loop_end_x], [loop_top_y, loop_bottom_y],
               color=green_color, linewidth=6, alpha=0.8)
        
        # Rejoin to main
        main_continue_x = loop_end_x + 30
        ax.plot([loop_end_x, loop_end_x, main_continue_x], [loop_top_y, green_y, green_y],
               color=green_color, linewidth=6, alpha=0.8)
        ax.plot([loop_end_x, loop_end_x, main_continue_x], [loop_bottom_y, green_y, green_y],
               color=green_color, linewidth=6, alpha=0.8)
        
        # Express route (dashed)
        ax.plot([fork_x, main_continue_x], [green_y, green_y],
               color=green_color, linewidth=4, alpha=0.5, linestyle='--')
        
        # Draw section labels
        sections = {}
        for block in sorted_blocks:
            if block.section not in sections:
                sections[block.section] = []
            sections[block.section].append(block)
        
        # Label key sections
        section_labels = [
            ('A-C', track_start_x + 60, green_y + 20),
            ('D-G', loop_start_x + 150, loop_top_y - 25),
            ('H-K', loop_start_x + 150, loop_bottom_y + 25),
            ('L-O', main_continue_x + 100, green_y + 20)
        ]
        
        for label, x, y in section_labels:
            ax.text(x, y, f"Sections {label}", ha='center', va='center',
                   fontsize=16, fontweight='bold',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor='#E8F5E9',
                           edgecolor=green_color, linewidth=1, alpha=0.9))
        
        # Add station markers (without labels to avoid clutter)
        for block in sorted_blocks:
            if block.has_station and block.station and block.block_number in block_positions:
                pos = block_positions[block.block_number]
                ax.plot(pos['x'] + block_width/2, pos['y'], 'o', markersize=6,
                       color='#FFD700', markeredgecolor='#B8860B', markeredgewidth=1)
        
        # Add only a few key station names
        key_green_stations = [
            ('CASTLE SHANNON', 19),
            ('MT LEBANON', 39),
            ('CENTRAL', 48),
            ('STATION SQUARE', 124)
        ]
        
        for station_name, block_num in key_green_stations:
            if block_num in block_positions:
                pos = block_positions[block_num]
                label_y = pos['y'] - 20 if pos['y'] != green_y else pos['y'] + 20
                ax.text(pos['x'] + block_width/2, label_y, station_name,
                       ha='center', va='center', fontsize=10,
                       bbox=dict(boxstyle="round,pad=0.2", facecolor='#FFFACD', alpha=0.9))
        
        # Draw yard connections for Green line
        # Block 58 has TO_ONLY connection to yard, Block 62 has FROM_ONLY from yard
        yard_blocks = {58: 'TO YARD', 62: 'FROM YARD'}
        for block_num, yard_label in yard_blocks.items():
            if block_num in block_positions:
                pos = block_positions[block_num]
                yard_x = pos['x'] + block_width/2
                yard_y = pos['y'] - 30 if pos['y'] == loop_top_y else pos['y'] + 30
                
                # Draw yard box
                yard_rect = patches.Rectangle((yard_x - 20, yard_y - 8), 40, 16,
                                            facecolor='lightgray', edgecolor='black', linewidth=1)
                ax.add_patch(yard_rect)
                ax.text(yard_x, yard_y, 'YARD', ha='center', va='center', 
                       fontsize=10, fontweight='bold')
                
                # Connect to track with directional indicator
                if yard_label == 'TO YARD':
                    ax.plot([yard_x, yard_x], [pos['y'], yard_y + 8],
                           color=green_color, linewidth=3, alpha=0.7)
                    # Arrow pointing to yard
                    ax.plot(yard_x, yard_y + 6, 'v', markersize=8, color=green_color)
                else:  # FROM YARD
                    ax.plot([yard_x, yard_x], [yard_y - 8, pos['y']],
                           color=green_color, linewidth=3, alpha=0.7)
                    # Arrow pointing from yard
                    ax.plot(yard_x, yard_y - 6, '^', markersize=8, color=green_color)
        
        # Add trains
        for train_id, train in trains.items():
            if train.line == 'Green' and train.currentBlock in block_positions:
                pos = block_positions[train.currentBlock]
                train_x = pos['x'] + block_width/2
                train_y = pos['y']
                
                # Draw train
                train_rect = patches.Rectangle((train_x-8, train_y-5), 16, 10,
                                             facecolor='#8A2BE2', edgecolor='white', linewidth=1)
                ax.add_patch(train_rect)
                ax.text(train_x, train_y, getattr(train, 'id', getattr(train, 'trainID', getattr(train, 'train_id', 'T'))), ha='center', va='center',
                       color='white', fontsize=10, fontweight='bold')
        
        # Title
        ax.text(600, green_y - 120, 'GREEN LINE', fontsize=23, fontweight='bold', color=green_color)
    
    def _draw_simple_legend(self, ax):
        """Draw simple, uncluttered legend"""
        legend_x = 50
        legend_y = 100
        
        # Background
        legend_bg = patches.Rectangle((legend_x - 10, legend_y - 10), 400, 60, 
                                    facecolor='#F8F8F8', edgecolor='black', linewidth=1, alpha=0.9)
        ax.add_patch(legend_bg)
        
        # Title
        ax.text(legend_x + 190, legend_y + 35, 'LEGEND', ha='center', va='center',
               fontsize=16, fontweight='bold')
        
        # Simple items
        items = [
            ('Normal Track', '#2196F3', 'line'),
            ('Maintenance', '#FF5555', 'line'),
            ('Train', '#8A2BE2', 'square'),
            ('Station', '#FFD700', 'circle')
        ]
        
        for i, (label, color, shape) in enumerate(items):
            x_pos = legend_x + (i * 90)
            y_pos = legend_y + 15
            
            if shape == 'line':
                ax.plot([x_pos, x_pos + 20], [y_pos, y_pos], color=color, linewidth=4)
            elif shape == 'square':
                ax.plot(x_pos + 10, y_pos, 's', markersize=6, color=color, markeredgecolor='black')
            elif shape == 'circle':
                ax.plot(x_pos + 10, y_pos, 'o', markersize=6, color=color, markeredgecolor='#B8860B')
            
            ax.text(x_pos + 10, y_pos - 15, label, ha='center', va='center', fontsize=14)
               
    def _draw_red_line_with_branches(self, ax, red_blocks, trains, maintenance_closures):
        """Draw Red Line with proper branching based on switches"""
        red_has_maintenance = any(block.block_number in maintenance_closures.get("Red", []) 
                                 for block in red_blocks)
        red_color = '#FF5555' if red_has_maintenance else '#F44336'
        
        # Red line base level - positioned in upper portion with extensive spacing
        red_y = 900
        
        # Main Red line trunk (left to right) with massive spacing
        trunk_start_x = 150
        trunk_end_x = 2200
        
        # Draw individual blocks as distinct segments with much larger size
        sorted_blocks = sorted(red_blocks, key=lambda b: b.block_number)
        block_width = max(40, (trunk_end_x - trunk_start_x) / len(sorted_blocks))  # Minimum 40px width
        
        for i, block in enumerate(sorted_blocks):
            block_start_x = trunk_start_x + (i * block_width)
            block_end_x = block_start_x + block_width - 2  # Small gap between blocks
            
            # Determine block color based on maintenance and properties
            if block.block_number in maintenance_closures.get("Red", []):
                block_color = '#CC0000'  # Maintenance - darker red for better distinction
            elif block.is_underground:
                block_color = '#8B4513'  # Underground - brown
            elif block.has_station:
                block_color = '#0066CC'  # Station block - blue
            elif block.has_switch:
                block_color = '#FF6600'  # Switch block - orange
            else:
                block_color = '#DD3333'  # Normal red - lighter than maintenance
            
            # Draw block segment - much thicker and more visible
            ax.plot([block_start_x, block_end_x], [red_y, red_y], 
                   color=block_color, linewidth=16, solid_capstyle='butt', alpha=0.9)
            
            # Add block number for every 10th block, plus stations and switches
            if i % 10 == 0 or block.has_station or block.has_switch:
                ax.text(block_start_x + block_width/2, red_y - 15, str(block.block_number),
                       ha='center', va='center', fontsize=9, color='black',
                       bbox=dict(boxstyle="round,pad=0.05", facecolor='white', alpha=0.8))
        
        # Add station markers only (no text labels to avoid clutter)
        red_stations_data = []
        for block in red_blocks:
            if block.has_station and block.station:
                red_stations_data.append({
                    'name': block.station.name,
                    'block': block.block_number,
                    'underground': block.is_underground
                })
        
        # Sort stations by block number for proper ordering
        red_stations_data.sort(key=lambda x: x['block'])
        
        # Position Red station markers aligned with station blocks
        if red_stations_data:
            for i, station in enumerate(red_stations_data):
                # Find the actual block position for this station
                station_block = None
                for j, block in enumerate(sorted_blocks):
                    if block.has_station and block.station and block.station.name == station['name']:
                        station_block = block
                        break
                
                if station_block:
                    # Calculate exact position based on block position
                    block_index = sorted_blocks.index(station_block)
                    x_pos = trunk_start_x + (block_index * block_width) + (block_width / 2)
                    
                    # Station marker positioned exactly on the blue station block
                    marker_color = '#FFD700' if not station['underground'] else '#FFA500'
                    ax.plot(x_pos, red_y, 'o', markersize=12, color=marker_color, 
                           markeredgecolor='#B8860B', markeredgewidth=2)
                    
                    # Station name label positioned clearly above with extensive spacing
                    label_y = red_y + 50 + (i % 3) * 25  # Much more staggered heights
                    ax.text(x_pos, label_y, station['name'], ha='center', va='center',
                           fontsize=13, fontweight='bold', color='black', rotation=0,
                           bbox=dict(boxstyle="round,pad=0.2", facecolor='#FFFACD', 
                                   edgecolor='#B8860B', linewidth=2, alpha=0.9))
        
        # Add section labels for Red line with comprehensive coverage
        red_sections = sorted(set(block.section for block in red_blocks))
        if red_sections:
            # Show more sections evenly distributed
            sections_to_show = red_sections[::max(1, len(red_sections) // 10)]  # Max 10 sections
            available_width = trunk_end_x - trunk_start_x - 300
            section_spacing = available_width / max(len(sections_to_show) - 1, 1)
            
            for i, section in enumerate(sections_to_show[:10]):  # Max 10 labels
                x_pos = trunk_start_x + 150 + (i * section_spacing)
                if x_pos < trunk_end_x - 200:  # Keep within bounds with much more margin
                    ax.text(x_pos, red_y + 150, f"Sec {section}", ha='center', va='center',
                           fontsize=13, fontweight='bold', color='#8B0000',
                           bbox=dict(boxstyle="round,pad=0.2", facecolor='#FFE4E1', 
                                   edgecolor='#8B0000', linewidth=2))
        
        # Red line branching is now handled by actual switch data above
        
        # Switch markers positioned exactly on orange switch blocks with real connections
        for i, block in enumerate(sorted_blocks):
            if block.has_switch and block.switch:
                switch_x = trunk_start_x + (i * block_width) + (block_width / 2)
                
                # Draw switch marker on the orange block
                ax.plot(switch_x, red_y, 'D', markersize=12, color='#FF6600', 
                       markeredgecolor='#FF4500', markeredgewidth=2)
                
                # Draw actual track connections based on switch data
                for connection in block.switch.connections:
                    from_block = connection.from_block
                    to_block = connection.to_block
                    
                    # Find positions of connected blocks
                    from_pos = None
                    to_pos = None
                    
                    # Find position of from_block
                    if isinstance(from_block, int):
                        for j, other_block in enumerate(sorted_blocks):
                            if other_block.block_number == from_block:
                                from_pos = trunk_start_x + (j * block_width) + (block_width / 2)
                                break
                    elif from_block == "yard":
                        from_pos = switch_x - 60  # Yard position (approximate)
                    
                    # Find position of to_block
                    if isinstance(to_block, int):
                        for j, other_block in enumerate(sorted_blocks):
                            if other_block.block_number == to_block:
                                to_pos = trunk_start_x + (j * block_width) + (block_width / 2)
                                break
                    elif to_block == "yard":
                        to_pos = switch_x + 60  # Yard position (approximate)
                    
                    # Draw connection line if both positions are found
                    if from_pos is not None and to_pos is not None and from_pos != to_pos:
                        # Calculate offset for parallel tracks
                        y_offset = 15 if abs(to_pos - from_pos) > block_width else 0
                        
                        # Draw connecting track segment
                        ax.plot([from_pos, to_pos], 
                               [red_y + y_offset, red_y + y_offset], 
                               color='#DD3333', linewidth=6, alpha=0.7, linestyle='--')
                        
                        # Draw connector to main track
                        if y_offset > 0:
                            ax.plot([switch_x, switch_x], [red_y, red_y + y_offset], 
                                   color='#DD3333', linewidth=6, alpha=0.7)
                   
        # Add trains on Red line
        for train_id, train in trains.items():
            if train.line == 'Red':
                # Place train at position based on block number
                train_x = trunk_start_x + 100 + ((train.currentBlock % 50) * 15)  
                train_x = min(max(train_x, trunk_start_x + 50), trunk_end_x - 50)  # Keep in bounds
                ax.plot(train_x, red_y, 's', markersize=12, color='#8A2BE2', 
                       markeredgecolor='black', markeredgewidth=2)
                ax.text(train_x, red_y, train.id, ha='center', va='center',
                       color='white', fontsize=14, fontweight='bold')
        
        # Store Red line interactive elements
        self.interactive_elements['red_main'] = {
            'type': 'track_segment',
            'x': trunk_start_x, 'y': red_y - 4, 'width': trunk_end_x - trunk_start_x, 'height': 8,
            'line': 'Red', 'blocks': [b.block_number for b in red_blocks],
            'is_maintenance': red_has_maintenance
        }
        
    def _draw_green_line_with_branches(self, ax, green_blocks, trains, maintenance_closures):
        """Draw Green Line with proper branching and loop structure"""
        green_has_maintenance = any(block.block_number in maintenance_closures.get("Green", []) 
                                   for block in green_blocks)
        green_color = '#FF5555' if green_has_maintenance else '#4CAF50'
        
        # Green line base level - positioned in lower portion with extensive spacing
        green_y = 500
        
        # Main Green line with loop structure - massive spacing
        main_start_x = 150
        loop_start_x = 500
        loop_end_x = 1500
        main_end_x = 2200
        
        # Draw loop structure with extensive spacing
        loop_top_y = green_y + 120
        loop_bottom_y = green_y - 120
        
        # Draw individual Green blocks on main segments
        green_sorted = sorted(green_blocks, key=lambda b: b.block_number)
        
        # Left main line blocks with much larger size
        left_blocks = green_sorted[:20]  # First 20 blocks
        block_width = 40  # Much larger default block width
        top_block_width = 35  # Default for top loop
        bottom_block_width = 35  # Default for bottom loop  
        right_block_width = 40  # Default for right main line
        if left_blocks:
            block_width = max(40, (loop_start_x - main_start_x) / len(left_blocks))  # Minimum 40px
            for i, block in enumerate(left_blocks):
                block_start_x = main_start_x + (i * block_width)
                block_end_x = block_start_x + block_width - 2
                
                # Block color based on properties
                if block.block_number in maintenance_closures.get("Green", []):
                    block_color = '#FF5555'
                elif block.is_underground:
                    block_color = '#8B4513'  # Brown
                elif block.has_station:
                    block_color = '#4169E1'  # Blue
                elif block.has_switch:
                    block_color = '#FF8C00'  # Orange
                else:
                    block_color = green_color
                
                ax.plot([block_start_x, block_end_x], [green_y, green_y], 
                       color=block_color, linewidth=16, solid_capstyle='butt', alpha=0.9)
                
                # Block numbers for important blocks
                if i % 8 == 0 or block.has_station or block.has_switch:
                    ax.text(block_start_x + block_width/2, green_y - 15, str(block.block_number),
                           ha='center', va='center', fontsize=9, color='black',
                           bbox=dict(boxstyle="round,pad=0.05", facecolor='white', alpha=0.8))
        
        # Top loop blocks with larger size
        top_blocks = green_sorted[20:70]  # Middle blocks
        if top_blocks:
            top_block_width = max(35, (loop_end_x - loop_start_x) / len(top_blocks))  # Minimum 35px
            for i, block in enumerate(top_blocks):
                block_start_x = loop_start_x + (i * top_block_width)
                block_end_x = block_start_x + top_block_width - 2
                
                if block.block_number in maintenance_closures.get("Green", []):
                    block_color = '#CC0000'  # Maintenance - dark red
                elif block.is_underground:
                    block_color = '#8B4513'
                elif block.has_station:
                    block_color = '#0066CC'
                elif block.has_switch:
                    block_color = '#FF6600'
                else:
                    block_color = '#22AA22'  # Normal green
                
                ax.plot([block_start_x, block_end_x], [loop_top_y, loop_top_y], 
                       color=block_color, linewidth=16, solid_capstyle='butt', alpha=0.9)
        
        # Bottom loop blocks with larger size
        bottom_blocks = green_sorted[70:120]  # Later blocks
        if bottom_blocks:
            bottom_block_width = max(35, (loop_end_x - loop_start_x) / len(bottom_blocks))  # Minimum 35px
            for i, block in enumerate(bottom_blocks):
                block_start_x = loop_start_x + (i * bottom_block_width)
                block_end_x = block_start_x + bottom_block_width - 2
                
                if block.block_number in maintenance_closures.get("Green", []):
                    block_color = '#CC0000'  # Maintenance - dark red
                elif block.is_underground:
                    block_color = '#8B4513'
                elif block.has_station:
                    block_color = '#0066CC'
                elif block.has_switch:
                    block_color = '#FF6600'
                else:
                    block_color = '#22AA22'  # Normal green
                
                ax.plot([block_start_x, block_end_x], [loop_bottom_y, loop_bottom_y], 
                       color=block_color, linewidth=16, solid_capstyle='butt', alpha=0.9)
        
        # Right main line blocks with larger size
        right_blocks = green_sorted[120:]  # Final blocks
        if right_blocks:
            right_block_width = max(40, (main_end_x - loop_end_x) / max(len(right_blocks), 1))  # Minimum 40px
            for i, block in enumerate(right_blocks):
                block_start_x = loop_end_x + (i * right_block_width)
                block_end_x = block_start_x + right_block_width - 2
                
                if block.block_number in maintenance_closures.get("Green", []):
                    block_color = '#CC0000'  # Maintenance - dark red
                elif block.is_underground:
                    block_color = '#8B4513'
                elif block.has_station:
                    block_color = '#0066CC'
                elif block.has_switch:
                    block_color = '#FF6600'
                else:
                    block_color = '#22AA22'  # Normal green
                
                ax.plot([block_start_x, block_end_x], [green_y, green_y], 
                       color=block_color, linewidth=16, solid_capstyle='butt', alpha=0.9)
        
        # Draw connecting lines between loop sections  
        ax.plot([loop_start_x, loop_start_x], [green_y, loop_top_y], 
               color=green_color, linewidth=8, alpha=0.9)
        ax.plot([loop_start_x, loop_start_x], [green_y, loop_bottom_y], 
               color=green_color, linewidth=8, alpha=0.9)
        ax.plot([loop_end_x, loop_end_x], [green_y, loop_top_y], 
               color=green_color, linewidth=8, alpha=0.9)
        ax.plot([loop_end_x, loop_end_x], [green_y, loop_bottom_y], 
               color=green_color, linewidth=8, alpha=0.9)
        # Bottom arc of loop  
        ax.plot([loop_start_x, loop_end_x], [loop_bottom_y, loop_bottom_y], 
               color=green_color, linewidth=8, solid_capstyle='round', alpha=0.9)
        # Connecting segments
        ax.plot([loop_start_x, loop_start_x], [green_y, loop_top_y], 
               color=green_color, linewidth=8, alpha=0.9)
        ax.plot([loop_start_x, loop_start_x], [green_y, loop_bottom_y], 
               color=green_color, linewidth=8, alpha=0.9)
        ax.plot([loop_end_x, loop_end_x], [green_y, loop_top_y], 
               color=green_color, linewidth=8, alpha=0.9)
        ax.plot([loop_end_x, loop_end_x], [green_y, loop_bottom_y], 
               color=green_color, linewidth=8, alpha=0.9)
        
        # Add Green line station markers only (no text labels)
        green_stations_data = []
        for block in green_blocks:
            if block.has_station and block.station:
                green_stations_data.append({
                    'name': block.station.name,
                    'block': block.block_number,
                    'underground': block.is_underground
                })
        
        # Sort and remove duplicates (some stations appear multiple times)
        seen_names = set()
        unique_stations = []
        for station in sorted(green_stations_data, key=lambda x: x['block']):
            if station['name'] not in seen_names:
                unique_stations.append(station)
                seen_names.add(station['name'])
        
        # Position station markers aligned with actual station blocks
        if unique_stations:
            for i, station in enumerate(unique_stations):
                # Find the actual block for this station in different segments
                station_positioned = False
                
                # Check left main line blocks
                for j, block in enumerate(left_blocks):
                    if block.has_station and block.station and block.station.name == station['name']:
                        block_index = j
                        x_pos = main_start_x + (block_index * block_width) + (block_width / 2)
                        y_pos = green_y
                        
                        # Station marker positioned exactly on the blue station block
                        marker_color = '#FFD700' if not station['underground'] else '#FFA500'
                        ax.plot(x_pos, y_pos, 'o', markersize=12, color=marker_color, 
                               markeredgecolor='#B8860B', markeredgewidth=2)
                        
                        # Station name label positioned clearly above with extensive spacing
                        label_y = y_pos + 50 + (i % 3) * 25
                        ax.text(x_pos, label_y, station['name'], ha='center', va='center',
                               fontsize=13, fontweight='bold', color='black', rotation=0,
                               bbox=dict(boxstyle="round,pad=0.2", facecolor='#F0FFFF', 
                                       edgecolor='#006400', linewidth=2, alpha=0.9))
                        station_positioned = True
                        break
                
                if not station_positioned:
                    # Check top loop blocks
                    for j, block in enumerate(top_blocks):
                        if block.has_station and block.station and block.station.name == station['name']:
                            block_index = j
                            x_pos = loop_start_x + (block_index * block_width) + (block_width / 2)
                            y_pos = loop_top_y
                            
                            marker_color = '#FFD700' if not station['underground'] else '#FFA500'
                            ax.plot(x_pos, y_pos, 'o', markersize=12, color=marker_color, 
                                   markeredgecolor='#B8860B', markeredgewidth=2)
                            
                            label_y = y_pos + 25 + (i % 3) * 10
                            ax.text(x_pos, label_y, station['name'], ha='center', va='center',
                                   fontsize=10, fontweight='bold', color='black', rotation=0,
                                   bbox=dict(boxstyle="round,pad=0.1", facecolor='#F0FFFF', 
                                           edgecolor='#006400', linewidth=1, alpha=0.9))
                            station_positioned = True
                            break
                
                if not station_positioned:
                    # Check bottom loop blocks
                    for j, block in enumerate(bottom_blocks):
                        if block.has_station and block.station and block.station.name == station['name']:
                            block_index = j
                            x_pos = loop_start_x + (block_index * block_width) + (block_width / 2)
                            y_pos = loop_bottom_y
                            
                            marker_color = '#FFD700' if not station['underground'] else '#FFA500'
                            ax.plot(x_pos, y_pos, 'o', markersize=12, color=marker_color, 
                                   markeredgecolor='#B8860B', markeredgewidth=2)
                            
                            label_y = y_pos - 25 - (i % 3) * 10  # Below for bottom loop
                            ax.text(x_pos, label_y, station['name'], ha='center', va='center',
                                   fontsize=10, fontweight='bold', color='black', rotation=0,
                                   bbox=dict(boxstyle="round,pad=0.1", facecolor='#F0FFFF', 
                                           edgecolor='#006400', linewidth=1, alpha=0.9))
                            station_positioned = True
                            break
        
        # Add section labels for Green line with comprehensive coverage
        green_sections = sorted(set(block.section for block in green_blocks))
        if green_sections:
            # Distribute sections around the loop structure more evenly
            sections_to_show = green_sections[::max(1, len(green_sections) // 12)]  # Max 12 sections
            
            for i, section in enumerate(sections_to_show[:12]):  # Max 12 labels
                section_mod = i % 4
                if section_mod == 0:  # Left main line
                    x_pos = main_start_x + 80 + (i // 4) * 60
                    y_pos = green_y - 60
                elif section_mod == 1:  # Top loop
                    x_pos = loop_start_x + 150 + (i // 4) * 200
                    y_pos = loop_top_y + 35
                elif section_mod == 2:  # Bottom loop
                    x_pos = loop_start_x + 200 + (i // 4) * 180
                    y_pos = loop_bottom_y - 35
                else:  # Right main line
                    x_pos = loop_end_x + 50 + (i // 4) * 50
                    y_pos = green_y - 60
                
                # Keep within bounds with extensive spacing
                if main_start_x + 100 < x_pos < main_end_x - 100:
                    ax.text(x_pos, y_pos, f"Sec {section}", ha='center', va='center',
                           fontsize=13, fontweight='bold', color='#006400',
                           bbox=dict(boxstyle="round,pad=0.2", facecolor='#F0FFF0', 
                                   edgecolor='#006400', linewidth=2))
        
        # Add switch markers for Green line positioned on orange switch blocks with real connections
        all_green_blocks = left_blocks + top_blocks + bottom_blocks + right_blocks
        for block_group, y_position in [(left_blocks, green_y), (top_blocks, loop_top_y), 
                                       (bottom_blocks, loop_bottom_y), (right_blocks, green_y)]:
            for i, block in enumerate(block_group):
                if block.has_switch and block.switch:
                    if block_group == left_blocks:
                        switch_x = main_start_x + (i * block_width) + (block_width / 2)
                    elif block_group == top_blocks:
                        switch_x = loop_start_x + (i * top_block_width) + (top_block_width / 2)
                    elif block_group == bottom_blocks:
                        switch_x = loop_start_x + (i * bottom_block_width) + (bottom_block_width / 2)
                    else:  # right_blocks
                        switch_x = loop_end_x + (i * right_block_width) + (right_block_width / 2)
                    
                    # Draw switch marker
                    ax.plot(switch_x, y_position, 'D', markersize=12, color='#FF6600', 
                           markeredgecolor='#FF4500', markeredgewidth=2)
                    
                    # Draw actual track connections based on switch data
                    for connection in block.switch.connections:
                        from_block = connection.from_block
                        to_block = connection.to_block
                        
                        # Find positions of connected blocks within all green blocks
                        from_pos = None
                        to_pos = None
                        from_y = None
                        to_y = None
                        
                        # Search for from_block position
                        if isinstance(from_block, int):
                            for j, other_block in enumerate(all_green_blocks):
                                if other_block.block_number == from_block:
                                    # Determine which segment this block is in
                                    if other_block in left_blocks:
                                        from_pos = main_start_x + (left_blocks.index(other_block) * block_width) + (block_width / 2)
                                        from_y = green_y
                                    elif other_block in top_blocks:
                                        from_pos = loop_start_x + (top_blocks.index(other_block) * top_block_width) + (top_block_width / 2)
                                        from_y = loop_top_y
                                    elif other_block in bottom_blocks:
                                        from_pos = loop_start_x + (bottom_blocks.index(other_block) * bottom_block_width) + (bottom_block_width / 2)
                                        from_y = loop_bottom_y
                                    elif other_block in right_blocks:
                                        from_pos = loop_end_x + (right_blocks.index(other_block) * right_block_width) + (right_block_width / 2)
                                        from_y = green_y
                                    break
                        elif from_block == "yard":
                            from_pos = switch_x
                            from_y = y_position - 40  # Yard below
                        
                        # Search for to_block position
                        if isinstance(to_block, int):
                            for j, other_block in enumerate(all_green_blocks):
                                if other_block.block_number == to_block:
                                    # Determine which segment this block is in
                                    if other_block in left_blocks:
                                        to_pos = main_start_x + (left_blocks.index(other_block) * block_width) + (block_width / 2)
                                        to_y = green_y
                                    elif other_block in top_blocks:
                                        to_pos = loop_start_x + (top_blocks.index(other_block) * top_block_width) + (top_block_width / 2)
                                        to_y = loop_top_y
                                    elif other_block in bottom_blocks:
                                        to_pos = loop_start_x + (bottom_blocks.index(other_block) * bottom_block_width) + (bottom_block_width / 2)
                                        to_y = loop_bottom_y
                                    elif other_block in right_blocks:
                                        to_pos = loop_end_x + (right_blocks.index(other_block) * right_block_width) + (right_block_width / 2)
                                        to_y = green_y
                                    break
                        elif to_block == "yard":
                            to_pos = switch_x
                            to_y = y_position - 40  # Yard below
                        
                        # Draw connection if both positions found and they're different
                        if (from_pos is not None and to_pos is not None and 
                            from_y is not None and to_y is not None and 
                            (from_pos != to_pos or from_y != to_y)):
                            
                            # Draw connecting track segment
                            ax.plot([from_pos, to_pos], [from_y, to_y], 
                                   color='#22AA22', linewidth=6, alpha=0.7, linestyle='--')
                            
                            # Draw connection to switch if needed
                            if from_pos != switch_x or from_y != y_position:
                                ax.plot([switch_x, from_pos], [y_position, from_y], 
                                       color='#22AA22', linewidth=4, alpha=0.6)
                            if to_pos != switch_x or to_y != y_position:
                                ax.plot([switch_x, to_pos], [y_position, to_y], 
                                       color='#22AA22', linewidth=4, alpha=0.6)
        
        # Add yard connections
        yard_x = 750
        ax.plot([yard_x, yard_x], [loop_bottom_y, loop_bottom_y - 20], 
               color=green_color, linewidth=6, alpha=0.7)
        ax.text(yard_x, loop_bottom_y - 35, 'YARD', ha='center', va='center',
               fontsize=13, fontweight='bold', color='black',
               bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgray', alpha=0.9))
        
        # Add trains on Green line
        for train_id, train in trains.items():
            if train.line == 'Green':
                # Distribute trains across different parts of the loop
                block_mod = train.currentBlock % 100
                if block_mod < 25:  # Left main line
                    train_x = main_start_x + 50 + (block_mod * 6)
                    train_y = green_y
                elif block_mod < 50:  # Top loop
                    train_x = loop_start_x + ((block_mod - 25) * (loop_end_x - loop_start_x) / 25)
                    train_y = loop_top_y
                elif block_mod < 75:  # Bottom loop
                    train_x = loop_start_x + ((block_mod - 50) * (loop_end_x - loop_start_x) / 25)
                    train_y = loop_bottom_y
                else:  # Right main line
                    train_x = loop_end_x + ((block_mod - 75) * 4)
                    train_y = green_y
                
                # Keep train in bounds
                train_x = min(max(train_x, main_start_x + 30), main_end_x - 30)
                
                ax.plot(train_x, train_y, 's', markersize=12, color='#8A2BE2', 
                       markeredgecolor='black', markeredgewidth=2)
                ax.text(train_x, train_y, getattr(train, 'id', getattr(train, 'trainID', getattr(train, 'train_id', 'T'))), ha='center', va='center',
                       color='white', fontsize=14, fontweight='bold')
        
        # Store Green line interactive elements
        self.interactive_elements['green_main'] = {
            'type': 'track_segment',
            'x': main_start_x, 'y': green_y - 4, 'width': main_end_x - main_start_x, 'height': 8,
            'line': 'Green', 'blocks': [b.block_number for b in green_blocks],
            'is_maintenance': green_has_maintenance
        }

    def generate_auto_layout(self, line_name):
        """
        Auto-generate a clean, interactive track layout from track data.
        Creates a schematic representation optimized for readability and interaction.
        
        Returns: Dictionary with layout information
        """
        if line_name in self.layout_cache:
            return self.layout_cache[line_name]
            
        blocks = self.track_reader.lines.get(line_name, [])
        if not blocks:
            return {}
            
        # Sort blocks by block number for sequential layout
        sorted_blocks = sorted(blocks, key=lambda b: b.block_number)
        
        # Create more spacious layout with better proportions
        layout = {
            'blocks': {},
            'track_segments': [],  # Continuous track segments for cleaner lines
            'stations': [],
            'switches': [],
            'crossings': [],
            'interactive_zones': [],  # Areas for future mouse interaction
            'bounds': {'min_x': 0, 'max_x': 0, 'min_y': 0, 'max_y': 150}
        }
        
        # More spacious dimensions for clarity
        segment_length = 80  # Longer segments for fewer visual breaks
        track_height = 8     # Thicker track lines
        base_y = 75
        
        # Group consecutive blocks into segments for cleaner visualization
        current_x = 50
        current_segment = []
        segment_start_x = current_x
        
        for i, block in enumerate(sorted_blocks):
            # Start new segment if this block has infrastructure or we have 5+ blocks
            should_start_new_segment = (
                len(current_segment) >= 5 or  # Max 5 blocks per segment
                block.has_station or block.has_switch or block.has_crossing or
                (i > 0 and (sorted_blocks[i-1].has_station or sorted_blocks[i-1].has_switch))
            )
            
            if should_start_new_segment and current_segment:
                # Finish current segment
                self._add_track_segment(layout, current_segment, segment_start_x, current_x, base_y, track_height)
                current_segment = []
                segment_start_x = current_x
            
            # Add block to current segment
            current_segment.append(block)
            
            # Store block data for interactive zones
            layout['blocks'][block.block_number] = {
                'x': current_x,
                'y': base_y - track_height/2,
                'width': segment_length,
                'height': track_height,
                'section': block.section,
                'block': block
            }
            
            # Add infrastructure elements with better positioning
            if block.has_station and block.station:
                layout['stations'].append({
                    'block_number': block.block_number,
                    'name': block.station.name,
                    'x': current_x + segment_length/2,
                    'y': base_y - 35,  # Above the track
                    'side': block.station.side,
                    'width': max(80, len(block.station.name) * 8),  # Dynamic width
                    'height': 20
                })
                
            if block.has_switch and block.switch:
                layout['switches'].append({
                    'block_number': block.block_number,
                    'x': current_x + segment_length/2,
                    'y': base_y,  # On the track
                    'connections': block.switch.connections,
                    'type': block.switch.switch_type,
                    'size': 12  # Larger for better visibility
                })
                
            if block.has_crossing:
                layout['crossings'].append({
                    'block_number': block.block_number,
                    'x': current_x + segment_length/2,
                    'y': base_y + 25,  # Below the track
                    'size': 10
                })
            
            # Add interactive zone for future mouse events
            layout['interactive_zones'].append({
                'block_number': block.block_number,
                'x': current_x,
                'y': base_y - 20,
                'width': segment_length,
                'height': 40,
                'type': 'block'
            })
            
            current_x += segment_length + 20  # More spacing between segments
            
        # Add final segment if exists
        if current_segment:
            self._add_track_segment(layout, current_segment, segment_start_x, current_x, base_y, track_height)
            
        # Update bounds with more padding
        layout['bounds']['max_x'] = current_x + 50
        layout['bounds']['max_y'] = base_y + 80
        layout['bounds']['min_y'] = base_y - 80
        
        # Cache the layout
        self.layout_cache[line_name] = layout
        return layout
    
    def _add_track_segment(self, layout, blocks, start_x, end_x, y, height):
        """Add a continuous track segment to the layout"""
        if not blocks:
            return
            
        # Find if any blocks in this segment are important (have infrastructure)
        has_infrastructure = any(b.has_station or b.has_switch or b.has_crossing for b in blocks)
        
        layout['track_segments'].append({
            'start_x': start_x,
            'end_x': end_x - 20,  # Don't include the spacing
            'y': y,
            'height': height,
            'blocks': [b.block_number for b in blocks],
            'section': blocks[0].section,
            'has_infrastructure': has_infrastructure,
            'start_block': blocks[0].block_number,
            'end_block': blocks[-1].block_number
        })

    def draw_auto_generated_map(self, ax, line_name, trains, maintenance_closures):
        """
        Draw clean, uncluttered track map optimized for readability and interaction.
        """
        layout = self.generate_auto_layout(line_name)
        if not layout:
            ax.text(200, 100, f'No {line_name} Line Data Available', ha='center', va='center', fontsize=23)
            return
            
        line_colors = {'Blue': '#2196F3', 'Red': '#F44336', 'Green': '#4CAF50'}
        line_color = line_colors.get(line_name, '#666666')
        
        # Clear previous interactive elements for this line
        self.interactive_elements = {}
        
        # Set axis limits with proper padding
        bounds = layout['bounds']
        ax.set_xlim(bounds['min_x'] - 30, bounds['max_x'] + 30)
        ax.set_ylim(bounds['min_y'] - 20, bounds['max_y'] + 20)
        
        # Draw continuous track segments (much cleaner than individual blocks)
        for i, segment in enumerate(layout['track_segments']):
            # Check if any blocks in segment are under maintenance
            segment_blocks = segment['blocks']
            is_maintenance = any(block in maintenance_closures.get(line_name, []) for block in segment_blocks)
            segment_color = '#FF5555' if is_maintenance else line_color
            
            # Draw thick, continuous track line
            ax.plot([segment['start_x'], segment['end_x']], 
                   [segment['y'], segment['y']], 
                   color=segment_color, linewidth=segment['height'], 
                   solid_capstyle='round', alpha=0.9)
            
            # Store interactive element for track segment
            segment_id = f"{line_name}_segment_{i}"
            self.interactive_elements[segment_id] = {
                'type': 'track_segment',
                'x': segment['start_x'],
                'y': segment['y'] - segment['height']/2,
                'width': segment['end_x'] - segment['start_x'],
                'height': segment['height'],
                'blocks': segment_blocks,
                'section': segment['section'],
                'line': line_name,
                'is_maintenance': is_maintenance
            }
            
            # Only label important segments (with stations/switches), and only if segment is long enough
            segment_length = segment['end_x'] - segment['start_x']
            if segment['has_infrastructure'] and segment_length > 60:
                # Only show section name, not individual block numbers
                ax.text((segment['start_x'] + segment['end_x']) / 2, 
                       segment['y'] - 20, 
                       f"Section {segment['section']}", 
                       ha='center', va='center', fontsize=14, 
                       alpha=0.8, color='black',
                       bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.7))
                   
        # Draw stations prominently above track
        for station in layout['stations']:
            # Larger, more visible station marker
            station_width = station['width']
            station_height = station['height']
            
            # Station platform as rounded rectangle
            platform_rect = patches.FancyBboxPatch(
                (station['x'] - station_width/2, station['y'] - station_height/2),
                station_width, station_height,
                boxstyle="round,pad=3",
                facecolor='#FFD700', edgecolor='#B8860B', linewidth=2
            )
            ax.add_patch(platform_rect)
            
            # Station name with better typography
            ax.text(station['x'], station['y'], station['name'],
                   ha='center', va='center', fontsize=13, fontweight='bold',
                   color='#8B4513')
                   
        # Draw switches as larger, more visible elements
        for switch in layout['switches']:
            # Larger switch diamond
            diamond_size = switch['size']
            diamond = patches.RegularPolygon(
                (switch['x'], switch['y']), 4, radius=diamond_size,
                orientation=np.pi/4, facecolor='#FF8C00', edgecolor='#FF4500', linewidth=3
            )
            ax.add_patch(diamond)
            
            # Switch number instead of generic "SW"
            ax.text(switch['x'], switch['y'], str(switch['block_number']),
                   ha='center', va='center', fontsize=14, fontweight='bold',
                   color='white')
                   
        # Draw railway crossings prominently
        for crossing in layout['crossings']:
            # Larger, more visible crossing
            x, y = crossing['x'], crossing['y']
            size = crossing['size']
            ax.plot([x-size, x+size], [y-size, y+size], color='#DC143C', linewidth=4)
            ax.plot([x-size, x+size], [y+size, y-size], color='#DC143C', linewidth=4)
            
            # Circle background for better visibility
            circle = patches.Circle((x, y), size+2, facecolor='white', edgecolor='#DC143C', linewidth=2)
            ax.add_patch(circle)
                   
        # Draw trains prominently
        for train_id, train in trains.items():
            if train.line == line_name and hasattr(train, 'currentBlock'):
                if train.currentBlock in layout['blocks']:
                    block_data = layout['blocks'][train.currentBlock]
                    
                    # Larger, more visible train
                    train_width = 30
                    train_height = 12
                    train_x = block_data['x'] + (block_data['width'] - train_width) / 2
                    train_y = block_data['y'] - 8
                    
                    # Train as rounded rectangle
                    train_rect = patches.FancyBboxPatch(
                        (train_x, train_y),
                        train_width, train_height,
                        boxstyle="round,pad=2",
                        facecolor='#8A2BE2', edgecolor='white', linewidth=2
                    )
                    ax.add_patch(train_rect)
                    
                    # Train ID
                    ax.text(train_x + train_width/2, train_y + train_height/2,
                           train.id, ha='center', va='center',
                           color='white', fontsize=14, fontweight='bold')
                           
        # Simple, clean title
        ax.text(bounds['max_x']/2, bounds['max_y'] - 10, f'{line_name.upper()} LINE',
               ha='center', va='center', fontsize=20, fontweight='bold', color=line_color)
               
        # Minimal legend at bottom
        legend_y = bounds['min_y'] + 10
        legend_items = []
        
        if layout['stations']:
            legend_items.append(('Station', '#FFD700'))
        if layout['switches']:
            legend_items.append(('Switch', '#FF8C00'))
        if layout['crossings']:
            legend_items.append(('Crossing', '#DC143C'))
            
        # Draw compact legend
        legend_x = bounds['min_x'] + 20
        for i, (label, color) in enumerate(legend_items):
            x_offset = i * 80
            # Simple colored square
            legend_rect = patches.Rectangle((legend_x + x_offset, legend_y), 12, 8, 
                                          facecolor=color, edgecolor='black', linewidth=1)
            ax.add_patch(legend_rect)
            ax.text(legend_x + x_offset + 18, legend_y + 4, label, 
                   fontsize=16, va='center', color='black')
                   
    def _draw_legend(self, ax):
        """Draw comprehensive legend for all track symbols"""
        # Legend position - positioned to avoid track overlap
        legend_x = 50
        legend_y = 150
        
        # Much larger legend background to prevent text overlap
        from matplotlib.patches import Rectangle
        legend_bg = Rectangle((legend_x - 30, legend_y - 30), 1550, 120, 
                            facecolor='#F8F8F8', edgecolor='black', linewidth=2, alpha=0.95)
        ax.add_patch(legend_bg)
        
        # Title positioned properly
        ax.text(legend_x + 760, legend_y + 70, 'TRACK LEGEND', ha='center', va='center',
               fontsize=20, fontweight='bold', color='black')
        
        # Track types - single row with MUCH wider spacing
        track_items = [
            ('Normal', '#DD3333'),
            ('Station', '#0066CC'), 
            ('Switch', '#FF6600'),
            ('Underground', '#8B4513'),
            ('Maintenance', '#CC0000')
        ]
        
        # Infrastructure symbols - single row with wide spacing
        symbol_items = [
            ('Station Marker', '#FFD700', 'circle'),
            ('Switch Point', '#FF8C00', 'diamond'),
            ('Train', '#8A2BE2', 'square'),
            ('Yard', '#D3D3D3', 'rect')
        ]
        
        # Row 1: Track Types with VERY wide spacing to prevent overlap
        ax.text(legend_x + 20, legend_y + 45, 'TRACK TYPES:', ha='left', va='center',
               fontsize=14, fontweight='bold', color='black')
        
        for i, (label, color) in enumerate(track_items):
            x_pos = legend_x + 150 + (i * 300)  # Even wider spacing: 300px
            y_pos = legend_y + 50
            
            # Track line sample
            ax.plot([x_pos, x_pos + 25], [y_pos, y_pos], 
                   color=color, linewidth=6, solid_capstyle='butt')
            # Label with extra space
            ax.text(x_pos + 35, y_pos, label, ha='left', va='center',
                   fontsize=16, color='black', fontweight='bold')
        
        # Row 2: Infrastructure with even wider spacing
        ax.text(legend_x + 20, legend_y + 20, 'INFRASTRUCTURE:', ha='left', va='center',
               fontsize=14, fontweight='bold', color='black')
        
        for i, (label, color, shape) in enumerate(symbol_items):
            x_pos = legend_x + 150 + (i * 370)  # Maximum spacing: 370px
            y_pos = legend_y + 25
            
            # Symbol with proper sizing
            if shape == 'circle':
                ax.plot(x_pos + 12, y_pos, 'o', markersize=10, color=color, 
                       markeredgecolor='#B8860B', markeredgewidth=2)
            elif shape == 'diamond':
                ax.plot(x_pos + 12, y_pos, 'D', markersize=10, color=color, 
                       markeredgecolor='#FF4500', markeredgewidth=2)
            elif shape == 'square':
                ax.plot(x_pos + 12, y_pos, 's', markersize=10, color=color, 
                       markeredgecolor='black', markeredgewidth=2)
            elif shape == 'rect':
                rect = Rectangle((x_pos + 6, y_pos - 5), 12, 10, 
                               facecolor=color, edgecolor='black', linewidth=2)
                ax.add_patch(rect)
            
            # Label with plenty of space
            ax.text(x_pos + 30, y_pos, label, ha='left', va='center',
                   fontsize=16, color='black', fontweight='bold')

    def _draw_clean_legend(self, ax):
        """Draw a completely redesigned, readable legend"""
        # Position legend at bottom with ample space
        legend_x = 100
        legend_y = 50
        legend_width = 2200
        legend_height = 180
        
        # Clean legend background
        from matplotlib.patches import Rectangle
        legend_bg = Rectangle((legend_x - 20, legend_y - 20), legend_width, legend_height, 
                            facecolor='#FAFAFA', edgecolor='#333333', linewidth=3, alpha=0.95)
        ax.add_patch(legend_bg)
        
        # Clear title with proper spacing
        ax.text(legend_x + legend_width/2, legend_y + legend_height - 30, 'TRACK LEGEND', 
               ha='center', va='center', fontsize=23, fontweight='bold', color='#333333')
        
        # Track types section
        track_items = [
            ('Normal Track', '#DD3333'),
            ('Station Block', '#0066CC'), 
            ('Switch Block', '#FF6600'),
            ('Underground', '#8B4513'),
            ('Maintenance', '#CC0000')
        ]
        
        # Infrastructure symbols section
        symbol_items = [
            ('Station', '#FFD700', 'circle'),
            ('Switch', '#FF6600', 'diamond'),
            ('Train', '#8A2BE2', 'square'),
            ('Yard', '#D3D3D3', 'rect')
        ]
        
        # Track types row with massive spacing
        ax.text(legend_x + 20, legend_y + 100, 'TRACK BLOCKS:', ha='left', va='center',
               fontsize=23, fontweight='bold', color='#333333')
        
        for i, (label, color) in enumerate(track_items):
            x_pos = legend_x + 200 + (i * 400)  # Huge spacing: 400px
            y_pos = legend_y + 100
            
            # Track line sample - longer and thicker
            ax.plot([x_pos, x_pos + 40], [y_pos, y_pos], 
                   color=color, linewidth=8, solid_capstyle='round')
            # Label with massive spacing
            ax.text(x_pos + 50, y_pos, label, ha='left', va='center',
                   fontsize=14, color='#333333', fontweight='bold')
        
        # Infrastructure symbols row with massive spacing
        ax.text(legend_x + 20, legend_y + 50, 'INFRASTRUCTURE:', ha='left', va='center',
               fontsize=23, fontweight='bold', color='#333333')
        
        for i, (label, color, shape) in enumerate(symbol_items):
            x_pos = legend_x + 200 + (i * 500)  # Even more massive spacing: 500px
            y_pos = legend_y + 50
            
            # Symbols - larger and clearer
            if shape == 'circle':
                ax.plot(x_pos + 20, y_pos, 'o', markersize=14, color=color, 
                       markeredgecolor='#B8860B', markeredgewidth=3)
            elif shape == 'diamond':
                ax.plot(x_pos + 20, y_pos, 'D', markersize=14, color=color, 
                       markeredgecolor='#FF4500', markeredgewidth=3)
            elif shape == 'square':
                ax.plot(x_pos + 20, y_pos, 's', markersize=14, color=color, 
                       markeredgecolor='black', markeredgewidth=3)
            elif shape == 'rect':
                rect = Rectangle((x_pos + 10, y_pos - 8), 20, 16, 
                               facecolor=color, edgecolor='black', linewidth=3)
                ax.add_patch(rect)
            
            # Labels with massive spacing
            ax.text(x_pos + 45, y_pos, label, ha='left', va='center',
                   fontsize=14, color='#333333', fontweight='bold')