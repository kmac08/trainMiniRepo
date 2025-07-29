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
from collections import defaultdict, deque
import math


class TrackTopologyAnalyzer:
    """
    Analyzes track topology to identify linear sections, branches, loops, and yard connections.
    """
    
    def __init__(self, blocks):
        self.blocks = blocks
        self.block_dict = {block.block_number: block for block in blocks}
        self.graph = self._build_connection_graph()
        
    def _build_connection_graph(self):
        """Build undirected graph from connected_blocks data"""
        graph = defaultdict(set)
        
        for block in self.blocks:
            if hasattr(block, 'connected_blocks') and block.connected_blocks:
                for connected_num in block.connected_blocks:
                    if connected_num != 0:  # Exclude yard connections
                        graph[block.block_number].add(connected_num)
                        graph[connected_num].add(block.block_number)
        
        return graph
    
    def classify_nodes(self):
        """Classify nodes by their connectivity degree"""
        classification = {
            'linear': [],      # degree = 2 (middle of track segments)
            'junctions': [],   # degree > 2 (switches and convergence points)  
            'terminals': [],   # degree = 1 (track endpoints)
            'yard_blocks': []  # connects to yard (block 0)
        }
        
        for block in self.blocks:
            block_num = block.block_number
            degree = len(self.graph[block_num])
            
            # Check for yard connection
            if hasattr(block, 'has_yard_connection') and block.has_yard_connection:
                classification['yard_blocks'].append(block_num)
            
            # Classify by degree
            if degree == 1:
                classification['terminals'].append(block_num)
            elif degree == 2:
                classification['linear'].append(block_num)
            elif degree > 2:
                classification['junctions'].append(block_num)
        
        return classification
    
    def detect_cycles(self):
        """Detect cycles (loops) in the track graph using DFS"""
        visited = set()
        cycles = []
        
        def dfs_cycle_detection(node, parent, path):
            visited.add(node)
            path.append(node)
            
            for neighbor in self.graph[node]:
                if neighbor == parent:
                    continue
                    
                if neighbor in path:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                elif neighbor not in visited:
                    dfs_cycle_detection(neighbor, node, path[:])
            
            path.pop()
        
        for block_num in self.graph:
            if block_num not in visited:
                dfs_cycle_detection(block_num, None, [])
        
        return cycles
    
    def extract_track_segments(self):
        """Extract track segments (paths between junctions/terminals)"""
        classification = self.classify_nodes()
        key_nodes = set(classification['junctions'] + classification['terminals'] + classification['yard_blocks'])
        
        segments = []
        visited_edges = set()
        
        for start_node in key_nodes:
            for neighbor in self.graph[start_node]:
                edge = tuple(sorted([start_node, neighbor]))
                if edge in visited_edges:
                    continue
                
                # Trace segment from key node to next key node
                segment = [start_node]
                current = neighbor
                prev = start_node
                
                while current not in key_nodes and current in self.graph:
                    segment.append(current)
                    visited_edges.add(tuple(sorted([prev, current])))
                    
                    # Find next node (should only be one for linear segments)
                    next_nodes = [n for n in self.graph[current] if n != prev]
                    if len(next_nodes) != 1:
                        break
                    
                    prev = current
                    current = next_nodes[0]
                
                segment.append(current)
                visited_edges.add(tuple(sorted([prev, current])))
                
                if len(segment) > 1:
                    segments.append(segment)
        
        return segments


class TrackLayoutEngine:
    """
    Creates intelligent track positioning using graph-based layout algorithms.
    """
    
    def __init__(self):
        self.yard_position = None
        
    def create_line_layout(self, blocks, line_name, track_y, yard_x=500):
        """Create realistic track layout for a line using topology analysis"""
        if not blocks:
            return {}
        
        # Analyze track topology
        analyzer = TrackTopologyAnalyzer(blocks)
        classification = analyzer.classify_nodes()
        cycles = analyzer.detect_cycles()
        segments = analyzer.extract_track_segments()
        
        # Set yard position (shared between lines) - BETTER POSITIONED
        self.yard_position = {'x': yard_x, 'y': track_y + 100}  # More space from track
        
        # Determine layout strategy based on topology
        if cycles:
            # Has loops - use loop-based layout
            return self._create_loop_layout(blocks, analyzer, track_y, line_name)
        elif len(classification['junctions']) > 0:
            # Has branches - use branch-based layout  
            return self._create_branch_layout(blocks, analyzer, track_y, line_name)
        else:
            # Linear track - use simple linear layout
            return self._create_linear_layout(blocks, analyzer, track_y, line_name)
    
    def _create_loop_layout(self, blocks, analyzer, track_y, line_name):
        """Create layout for tracks with loops"""
        positions = {}
        cycles = analyzer.detect_cycles()
        classification = analyzer.classify_nodes()
        
        # Start with the largest cycle
        main_cycle = max(cycles, key=len) if cycles else []
        
        if main_cycle:
            # Position main loop as circle/oval - IMPROVED POSITIONING AND SIZE
            center_x = 400 if line_name == "Red" else 600  # Better spacing
            center_y = track_y
            radius = min(120, max(80, len(main_cycle) * 3))  # Larger radius for better spacing
            
            for i, block_num in enumerate(main_cycle[:-1]):  # Exclude duplicate end node
                angle = (i / (len(main_cycle) - 1)) * 2 * np.pi
                x = center_x + radius * np.cos(angle)
                y = center_y + radius * np.sin(angle)
                positions[block_num] = {'x': x, 'y': y}
        
        # Position remaining blocks
        remaining_blocks = [b for b in blocks if b.block_number not in positions]
        self._position_remaining_blocks(remaining_blocks, positions, analyzer, track_y)
        
        # Position yard connections
        self._position_yard_connections(blocks, positions, analyzer)
        
        return positions
    
    def _create_branch_layout(self, blocks, analyzer, track_y, line_name):
        """Create layout for tracks with branches"""
        positions = {}
        classification = analyzer.classify_nodes()
        segments = analyzer.extract_track_segments()
        
        # Find main trunk (longest segment or segment with most connections)
        main_segment = max(segments, key=len) if segments else []
        
        # Position main trunk horizontally - INCREASED SPACING
        start_x = 100
        if main_segment:
            for i, block_num in enumerate(main_segment):
                x = start_x + i * 35  # Increased from 15 to 35 for better readability
                positions[block_num] = {'x': x, 'y': track_y}
        
        # Position branches vertically offset from main trunk - INCREASED OFFSET
        branch_y_offset = 80  # Increased from 40 to 80 for better separation
        branch_count = 0
        
        for segment in segments:
            if segment == main_segment:
                continue
                
            # Find connection point to positioned blocks
            connection_point = None
            for block_num in segment:
                if block_num in positions:
                    connection_point = positions[block_num]
                    break
            
            if connection_point:
                # Position branch offset from connection point
                branch_y = track_y + (branch_y_offset * (1 if branch_count % 2 == 0 else -1))
                branch_start_x = connection_point['x']
                
                for i, block_num in enumerate(segment):
                    if block_num not in positions:
                        x = branch_start_x + i * 35  # Increased spacing for branches too
                        positions[block_num] = {'x': x, 'y': branch_y}
                
                branch_count += 1
        
        # Position remaining blocks
        remaining_blocks = [b for b in blocks if b.block_number not in positions]
        self._position_remaining_blocks(remaining_blocks, positions, analyzer, track_y)
        
        # Position yard connections
        self._position_yard_connections(blocks, positions, analyzer)
        
        return positions
    
    def _create_linear_layout(self, blocks, analyzer, track_y, line_name):
        """Create layout for linear tracks"""
        positions = {}
        
        # Sort blocks using topology order
        sorted_blocks = self._sort_blocks_topologically(blocks, analyzer)
        
        # Position blocks linearly - INCREASED SPACING
        start_x = 100
        for i, block in enumerate(sorted_blocks):
            x = start_x + i * 35  # Increased from 15 to 35 for better readability
            positions[block.block_number] = {'x': x, 'y': track_y}
        
        # Position yard connections
        self._position_yard_connections(blocks, positions, analyzer)
        
        return positions
    
    def _sort_blocks_topologically(self, blocks, analyzer):
        """Sort blocks using actual connectivity"""
        if not blocks:
            return []
        
        # Start from a terminal or arbitrary block
        classification = analyzer.classify_nodes()
        start_candidates = classification['terminals'] + classification['yard_blocks']
        
        if start_candidates:
            start_block_num = start_candidates[0]
        else:
            start_block_num = min(block.block_number for block in blocks)
        
        # BFS traversal
        visited = set()
        result = []
        queue = deque([start_block_num])
        
        while queue:
            current_num = queue.popleft()
            if current_num in visited:
                continue
                
            visited.add(current_num)
            # Find block object
            current_block = analyzer.block_dict.get(current_num)
            if current_block:
                result.append(current_block)
            
            # Add unvisited neighbors
            for neighbor in analyzer.graph[current_num]:
                if neighbor not in visited:
                    queue.append(neighbor)
        
        # Add any remaining blocks
        for block in blocks:
            if block not in result:
                result.append(block)
        
        return result
    
    def _position_remaining_blocks(self, remaining_blocks, positions, analyzer, track_y):
        """Position blocks that weren't placed by main layout algorithm"""
        if not remaining_blocks:
            return
        
        # Find rightmost positioned block
        max_x = max((pos['x'] for pos in positions.values()), default=100)
        
        # Place remaining blocks to the right, but ensure they fit within canvas (max 1300)
        current_x = max_x + 80  # More space from positioned blocks
        max_canvas_x = 1300  # Leave margin from 1400 limit
        spacing = min(40, (max_canvas_x - current_x) / max(len(remaining_blocks), 1))  # Increased minimum spacing
        
        for block in remaining_blocks:
            if current_x <= max_canvas_x:
                positions[block.block_number] = {'x': current_x, 'y': track_y}
                current_x += spacing
            else:
                # If we run out of space, stack blocks vertically with better spacing
                positions[block.block_number] = {'x': max_canvas_x, 'y': track_y + (current_x - max_canvas_x) * 0.5}
    
    def _position_yard_connections(self, blocks, positions, analyzer):
        """Position yard connections appropriately"""
        yard_blocks = []
        for block in blocks:
            if hasattr(block, 'has_yard_connection') and block.has_yard_connection:
                yard_blocks.append(block.block_number)
        
        if yard_blocks and self.yard_position:
            # Find average position of yard-connected blocks
            yard_connected_positions = [positions[b] for b in yard_blocks if b in positions]
            if yard_connected_positions:
                avg_x = sum(pos['x'] for pos in yard_connected_positions) / len(yard_connected_positions)
                # Update yard position to be near the yard-connected blocks
                self.yard_position['x'] = avg_x


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
        """Draw Red and Green lines using actual connected_blocks topology"""
        # Get actual track data
        red_blocks = self.track_reader.lines.get("Red", [])
        green_blocks = self.track_reader.lines.get("Green", [])

        if not red_blocks and not green_blocks:
            ax.text(250, 150, 'No Red/Green Line Data Available', ha='center', va='center', fontsize=23)
            return

        # Build connections from connected_blocks data
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

        # Build connections from connected_blocks data instead of sequential assumptions
        block_to_section = {}
        
        # Map blocks to sections for Green line
        for block in green_blocks:
            block_to_section[block.block_number] = block.section
        
        # Build Green connections using connected_blocks
        for block in green_blocks:
            if hasattr(block, 'connected_blocks') and block.connected_blocks:
                curr_section = block.section
                for connected_block_num in block.connected_blocks:
                    if connected_block_num != 0 and connected_block_num in block_to_section:
                        next_section = block_to_section[connected_block_num]
                        if curr_section != next_section:  # Only connect different sections
                            if (curr_section, next_section) not in green_connections and (next_section, curr_section) not in green_connections:
                                green_connections.append((curr_section, next_section))

        # Map blocks to sections for Red line
        block_to_section = {}
        for block in red_blocks:
            block_to_section[block.block_number] = block.section
        
        # Build Red connections using connected_blocks
        for block in red_blocks:
            if hasattr(block, 'connected_blocks') and block.connected_blocks:
                curr_section = block.section
                for connected_block_num in block.connected_blocks:
                    if connected_block_num != 0 and connected_block_num in block_to_section:
                        next_section = block_to_section[connected_block_num]
                        if curr_section != next_section:  # Only connect different sections
                            if (curr_section, next_section) not in red_connections and (next_section, curr_section) not in red_connections:
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
        Draw Red & Green lines with completely redesigned approach for maximum visibility
        """
        # Clear previous interactive elements 
        self.interactive_elements = {}
        
        # Much larger canvas for better spacing
        ax.set_xlim(0, 1600)
        ax.set_ylim(0, 900)
        ax.set_facecolor('#F8F9FA')  # Light gray background for better contrast
        
        # Get block data
        red_blocks = self.track_reader.lines.get("Red", [])
        green_blocks = self.track_reader.lines.get("Green", [])
        
        # Draw lines with completely new approach
        self._draw_redesigned_track_line(ax, red_blocks, trains, maintenance_closures, 
                                       line_name="Red", line_color='#DC2626', track_y=650)
        
        self._draw_redesigned_track_line(ax, green_blocks, trains, maintenance_closures,
                                       line_name="Green", line_color='#16A34A', track_y=350)
        
        # Add redesigned legend
        self._draw_redesigned_legend(ax)
        
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
        Auto-generate a clean, interactive track layout from track data using connected_blocks.
        Creates a schematic representation optimized for readability and interaction.
        
        Returns: Dictionary with layout information
        """
        if line_name in self.layout_cache:
            return self.layout_cache[line_name]
            
        blocks = self.track_reader.lines.get(line_name, [])
        if not blocks:
            return {}
            
        # Use connected_blocks data to create proper track topology layout
        sorted_blocks = self._sort_blocks_by_topology(blocks) if hasattr(self, '_sort_blocks_by_topology') else sorted(blocks, key=lambda b: b.block_number)
        
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
    
    def _sort_blocks_by_topology(self, blocks):
        """
        Sort blocks using connected_blocks data to create proper track topology order
        """
        if not blocks:
            return []
        
        # Check if blocks have connected_blocks data
        has_connected_data = any(hasattr(block, 'connected_blocks') and block.connected_blocks for block in blocks)
        
        if not has_connected_data:
            # Fallback to numerical sorting
            return sorted(blocks, key=lambda b: b.block_number)
        
        # Build adjacency graph from connected_blocks data
        block_dict = {block.block_number: block for block in blocks}
        visited = set()
        topology_order = []
        
        # Start from block with lowest number that has connections
        start_block = min((b for b in blocks if hasattr(b, 'connected_blocks') and b.connected_blocks), 
                         key=lambda b: b.block_number, default=blocks[0])
        
        # Depth-first traversal following connected_blocks
        def dfs_traverse(block):
            if block.block_number in visited:
                return
            
            visited.add(block.block_number)
            topology_order.append(block)
            
            # Follow connections in sorted order for consistency
            if hasattr(block, 'connected_blocks') and block.connected_blocks:
                connected_nums = sorted([num for num in block.connected_blocks if num != 0])
                for next_num in connected_nums:
                    if next_num in block_dict and next_num not in visited:
                        dfs_traverse(block_dict[next_num])
        
        # Start traversal
        dfs_traverse(start_block)
        
        # Add any unvisited blocks (disconnected components)
        for block in sorted(blocks, key=lambda b: b.block_number):
            if block.block_number not in visited:
                topology_order.append(block)
        
        return topology_order
    
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
        Draw track map using actual connected_blocks topology for accurate visualization.
        """
        blocks = self.track_reader.lines.get(line_name, [])
        if not blocks:
            ax.text(200, 100, f'No {line_name} Line Data Available', ha='center', va='center', fontsize=23)
            return
            
        line_colors = {'Blue': '#2196F3', 'Red': '#F44336', 'Green': '#4CAF50'}
        line_color = line_colors.get(line_name, '#666666')
        
        # Clear previous interactive elements for this line
        self.interactive_elements = {}
        
        # Check if blocks have connected_blocks data
        has_connected_data = any(hasattr(block, 'connected_blocks') and block.connected_blocks for block in blocks)
        
        if has_connected_data:
            # Draw using connected_blocks topology
            self._draw_topology_based_map(ax, line_name, blocks, trains, maintenance_closures, line_color)
        else:
            # Fallback to old method
            layout = self.generate_auto_layout(line_name)
            self._draw_layout_based_map(ax, layout, line_name, trains, maintenance_closures, line_color)
    
    def _draw_topology_based_map(self, ax, line_name, blocks, trains, maintenance_closures, line_color):
        """Draw map using actual connected_blocks data to show proper track topology"""
        
        # Build block positions using force-directed layout based on connections
        block_positions = self._calculate_topology_positions(blocks)
        
        # Set axis limits based on calculated positions
        if block_positions:
            min_x = min(pos['x'] for pos in block_positions.values()) - 50
            max_x = max(pos['x'] for pos in block_positions.values()) + 50
            min_y = min(pos['y'] for pos in block_positions.values()) - 50
            max_y = max(pos['y'] for pos in block_positions.values()) + 50
            ax.set_xlim(min_x, max_x)
            ax.set_ylim(min_y, max_y)
        
        # Draw connections first (behind blocks)
        connection_lines = set()  # Avoid duplicate lines
        for block in blocks:
            if hasattr(block, 'connected_blocks') and block.connected_blocks:
                current_pos = block_positions.get(block.block_number)
                if not current_pos:
                    continue
                    
                for connected_num in block.connected_blocks:
                    if connected_num == 0:  # Skip yard connections for now
                        continue
                    
                    connected_pos = block_positions.get(connected_num)
                    if not connected_pos:
                        continue
                    
                    # Create unique identifier for this connection (avoid duplicates)
                    conn_id = tuple(sorted([block.block_number, connected_num]))
                    if conn_id not in connection_lines:
                        connection_lines.add(conn_id)
                        
                        # Draw connection line - THICKER FOR BETTER VISIBILITY
                        ax.plot([current_pos['x'], connected_pos['x']], 
                               [current_pos['y'], connected_pos['y']], 
                               color=line_color, linewidth=6, alpha=0.7, zorder=1)
        
        # Draw blocks
        for block in blocks:
            pos = block_positions.get(block.block_number)
            if not pos:
                continue
                
            x, y = pos['x'], pos['y']
            
            # Determine block color
            if block.block_number in maintenance_closures.get(line_name, []):
                block_color = '#FF5555'  # Maintenance
            elif block.has_station:
                block_color = '#FFD700'  # Station
            elif block.has_switch:
                block_color = '#FF8C00'  # Switch
            else:
                block_color = line_color
            
            # Draw block as circle - INCREASED SIZE for better visibility
            block_circle = patches.Circle((x, y), 15, facecolor=block_color, 
                                        edgecolor='black', linewidth=2, zorder=2)
            ax.add_patch(block_circle)
            
            # Add block number - INCREASED FONT SIZE
            ax.text(x, y, str(block.block_number), ha='center', va='center',
                   fontsize=12, fontweight='bold', color='white' if block_color != '#FFD700' else 'black', zorder=3)
            
            # Add station label if present - IMPROVED POSITIONING AND SIZE
            if block.has_station and block.station:
                ax.text(x, y - 25, block.station.name, ha='center', va='center',
                       fontsize=12, fontweight='bold',
                       bbox=dict(boxstyle="round,pad=0.3", facecolor='#FFFACD', alpha=0.9), zorder=3)
            
            # Add switch marker if present - INCREASED SIZE
            if block.has_switch:
                ax.plot(x, y + 20, 'D', markersize=10, color='#FF4500', 
                       markeredgecolor='black', markeredgewidth=2, zorder=3)
        
        # Draw yard connections
        for block in blocks:
            if hasattr(block, 'has_yard_connection') and block.has_yard_connection:
                pos = block_positions.get(block.block_number)
                if pos:
                    # Draw yard box near this block
                    yard_x = pos['x']
                    yard_y = pos['y'] - 30
                    
                    yard_rect = patches.Rectangle((yard_x - 20, yard_y - 12), 40, 24,
                                                facecolor='lightgray', edgecolor='black', linewidth=2, zorder=2)
                    ax.add_patch(yard_rect)
                    ax.text(yard_x, yard_y, 'YARD', ha='center', va='center', 
                           fontsize=11, fontweight='bold', zorder=3)
                    
                    # Connect to block - THICKER CONNECTION LINE
                    ax.plot([yard_x, pos['x']], [yard_y + 12, pos['y'] - 15],
                           color=line_color, linewidth=4, alpha=0.7, zorder=1)
        
        # Draw trains
        for train_id, train in trains.items():
            if train.line == line_name and hasattr(train, 'currentBlock'):
                pos = block_positions.get(train.currentBlock)
                if pos:
                    # Draw train near block - LARGER AND BETTER POSITIONED
                    train_rect = patches.Rectangle((pos['x'] - 15, pos['y'] + 25), 30, 12,
                                                 facecolor='#8A2BE2', edgecolor='white', linewidth=2, zorder=3)
                    ax.add_patch(train_rect)
                    ax.text(pos['x'], pos['y'] + 31, getattr(train, 'id', 'T'), ha='center', va='center',
                           color='white', fontsize=11, fontweight='bold', zorder=4)
        
        # Title
        if block_positions:
            title_x = (min_x + max_x) / 2
            title_y = max_y - 20
            ax.text(title_x, title_y, f'{line_name.upper()} LINE - TOPOLOGY VIEW',
                   ha='center', va='center', fontsize=18, fontweight='bold', color=line_color)
    
    def _calculate_topology_positions(self, blocks):
        """Calculate block positions using force-directed layout based on connected_blocks"""
        import math
        import random
        
        # Initialize random positions
        positions = {}
        for block in blocks:
            positions[block.block_number] = {
                'x': random.uniform(0, 400),
                'y': random.uniform(0, 300)
            }
        
        # Force-directed layout iterations
        for iteration in range(100):
            forces = {block_num: {'x': 0, 'y': 0} for block_num in positions.keys()}
            
            # Repulsive forces between all blocks
            for i, block1_num in enumerate(positions.keys()):
                for block2_num in list(positions.keys())[i+1:]:
                    pos1 = positions[block1_num]
                    pos2 = positions[block2_num]
                    
                    dx = pos2['x'] - pos1['x']
                    dy = pos2['y'] - pos1['y']
                    distance = math.sqrt(dx*dx + dy*dy) + 0.1  # Avoid division by zero
                    
                    # Repulsive force
                    force = 1000 / (distance * distance)
                    fx = force * dx / distance
                    fy = force * dy / distance
                    
                    forces[block1_num]['x'] -= fx
                    forces[block1_num]['y'] -= fy
                    forces[block2_num]['x'] += fx
                    forces[block2_num]['y'] += fy
            
            # Attractive forces between connected blocks
            for block in blocks:
                if hasattr(block, 'connected_blocks') and block.connected_blocks:
                    pos1 = positions.get(block.block_number)
                    if not pos1:
                        continue
                        
                    for connected_num in block.connected_blocks:
                        if connected_num == 0:  # Skip yard
                            continue
                        pos2 = positions.get(connected_num)
                        if not pos2:
                            continue
                        
                        dx = pos2['x'] - pos1['x']
                        dy = pos2['y'] - pos1['y']
                        distance = math.sqrt(dx*dx + dy*dy) + 0.1
                        
                        # Attractive force
                        force = distance * 0.01
                        fx = force * dx / distance
                        fy = force * dy / distance
                        
                        forces[block.block_number]['x'] += fx
                        forces[block.block_number]['y'] += fy
                        forces[connected_num]['x'] -= fx
                        forces[connected_num]['y'] -= fy
            
            # Apply forces with damping
            damping = 0.9
            for block_num in positions.keys():
                positions[block_num]['x'] += forces[block_num]['x'] * damping
                positions[block_num]['y'] += forces[block_num]['y'] * damping
        
        return positions
    
    def _draw_layout_based_map(self, ax, layout, line_name, trains, maintenance_closures, line_color):
        """Fallback method using the old layout system"""
        if not layout:
            ax.text(200, 100, f'No {line_name} Line Data Available', ha='center', va='center', fontsize=23)
            return
        
        # Set axis limits with proper padding
        bounds = layout['bounds']
        ax.set_xlim(bounds['min_x'] - 30, bounds['max_x'] + 30)
        ax.set_ylim(bounds['min_y'] - 20, bounds['max_y'] + 20)
        
        # Draw continuous track segments
        for i, segment in enumerate(layout['track_segments']):
            segment_blocks = segment['blocks']
            is_maintenance = any(block in maintenance_closures.get(line_name, []) for block in segment_blocks)
            segment_color = '#FF5555' if is_maintenance else line_color
            
            ax.plot([segment['start_x'], segment['end_x']], 
                   [segment['y'], segment['y']], 
                   color=segment_color, linewidth=segment['height'], 
                   solid_capstyle='round', alpha=0.9)
        
        # Draw infrastructure
        for station in layout['stations']:
            platform_rect = patches.FancyBboxPatch(
                (station['x'] - station['width']/2, station['y'] - station['height']/2),
                station['width'], station['height'],
                boxstyle="round,pad=3",
                facecolor='#FFD700', edgecolor='#B8860B', linewidth=2
            )
            ax.add_patch(platform_rect)
            ax.text(station['x'], station['y'], station['name'],
                   ha='center', va='center', fontsize=13, fontweight='bold', color='#8B4513')
        
        for switch in layout['switches']:
            diamond = patches.RegularPolygon(
                (switch['x'], switch['y']), 4, radius=switch['size'],
                orientation=np.pi/4, facecolor='#FF8C00', edgecolor='#FF4500', linewidth=3
            )
            ax.add_patch(diamond)
            ax.text(switch['x'], switch['y'], str(switch['block_number']),
                   ha='center', va='center', fontsize=14, fontweight='bold', color='white')
        
        # Draw trains
        for train_id, train in trains.items():
            if train.line == line_name and hasattr(train, 'currentBlock'):
                if train.currentBlock in layout['blocks']:
                    block_data = layout['blocks'][train.currentBlock]
                    train_rect = patches.FancyBboxPatch(
                        (block_data['x'], block_data['y']),
                        30, 12, boxstyle="round,pad=2",
                        facecolor='#8A2BE2', edgecolor='white', linewidth=2
                    )
                    ax.add_patch(train_rect)
                    ax.text(block_data['x'] + 15, block_data['y'] + 6, train.id,
                           ha='center', va='center', color='white', fontsize=14, fontweight='bold')
        
        # Title
        ax.text(bounds['max_x']/2, bounds['max_y'] - 10, f'{line_name.upper()} LINE',
               ha='center', va='center', fontsize=20, fontweight='bold', color=line_color)
                   
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

    def _draw_blue_style_line(self, ax, blocks, trains, maintenance_closures, line_name, line_color, track_y):
        """Draw Red or Green line using Blue line design style with proper topology"""
        if not blocks:
            ax.text(600, track_y, f'No {line_name} Line Data Available', ha='center', va='center', fontsize=20)
            return

        # Create topology-based layout that fits on screen
        if line_name == "Red":
            block_positions = self._create_red_line_topology(blocks, track_y)
        elif line_name == "Green":
            block_positions = self._create_green_line_topology(blocks, track_y)
        else:
            # Fallback for other lines
            sorted_blocks = sorted(blocks, key=lambda b: b.block_number)
            block_positions = self._calculate_smart_positions(sorted_blocks, 100, track_y, 15)
        
        # Draw yard connections first
        self._draw_yard_connections(ax, blocks, block_positions, line_color)
        
        # Draw all track connections
        self._draw_topology_connections(ax, blocks, block_positions, line_color)
        
        # Draw all blocks with Blue line styling
        for block in blocks:
            if block.block_number not in block_positions:
                continue
                
            pos = block_positions[block.block_number]
            x, y = pos['x'], pos['y']
            
            # Determine block color (Blue line style)
            if block.block_number in maintenance_closures.get(line_name, []):
                block_color = '#FF5555'  # Maintenance
            else:
                block_color = line_color
            
            # Draw the block as a circle (better for topology view)
            block_circle = patches.Circle((x, y), 6, facecolor=block_color, 
                                        edgecolor='black', linewidth=1, alpha=0.9)
            ax.add_patch(block_circle)
            
            # Add block number for key blocks
            if block.block_number % 20 == 0 or block.has_station or block.has_switch:
                ax.text(x, y - 15, str(block.block_number),
                       ha='center', va='center', fontsize=8, color='black',
                       bbox=dict(boxstyle="round,pad=0.1", facecolor='white', alpha=0.8))
            
            # Add station marker and name (Blue line style)
            if block.has_station and block.station:
                # Station marker ring around block
                station_circle = patches.Circle((x, y), 9, facecolor='none', 
                                              edgecolor='#FFD700', linewidth=3)
                ax.add_patch(station_circle)
                # Station name for major stations only
                if any(word in block.station.name.upper() for word in ['STATION SQUARE', 'CENTRAL', 'DOWNTOWN', 'CASTLE']):
                    ax.text(x, y + 20, block.station.name,
                           ha='center', va='center', fontsize=9, fontweight='bold',
                           bbox=dict(boxstyle="round,pad=0.2", facecolor='#FFFACD', alpha=0.9))
            
            # Add switch marker (Blue line style)
            if block.has_switch:
                ax.plot(x, y, 'D', markersize=8, color='#FF8C00', 
                       markeredgecolor='#FF4500', markeredgewidth=2)
        
        # Add trains with Blue line styling
        for train_id, train in trains.items():
            if train.line == line_name and hasattr(train, 'currentBlock') and train.currentBlock in block_positions:
                pos = block_positions[train.currentBlock]
                train_x, train_y = pos['x'], pos['y']
                
                # Train as small rectangle
                train_rect = patches.Rectangle((train_x-8, train_y+12), 16, 8,
                                             facecolor='#8A2BE2', edgecolor='white', linewidth=2)
                ax.add_patch(train_rect)
                ax.text(train_x, train_y+16, getattr(train, 'id', getattr(train, 'trainID', 'T')), 
                       ha='center', va='center', color='white', fontsize=8, fontweight='bold')

        # Title
        title_x = 600 if line_name == "Red" else 600
        ax.text(title_x, track_y + 100, f'{line_name.upper()} LINE', fontsize=16, fontweight='bold', color=line_color)

    def _calculate_smart_positions(self, sorted_blocks, start_x, track_y, block_width):
        """Calculate block positions using connected_blocks data for smart layout"""
        positions = {}
        current_x = start_x
        
        # Check if we have connected_blocks data
        has_connected_data = any(hasattr(block, 'connected_blocks') and block.connected_blocks for block in sorted_blocks)
        
        if not has_connected_data:
            # Fallback to simple linear layout
            for block in sorted_blocks:
                positions[block.block_number] = {'x': current_x, 'y': track_y}
                current_x += block_width + 3
            return positions
        
        # Use connected_blocks to create better layout
        placed_blocks = set()
        
        # Start with the first block
        if sorted_blocks:
            first_block = sorted_blocks[0]
            positions[first_block.block_number] = {'x': current_x, 'y': track_y}
            placed_blocks.add(first_block.block_number)
            current_x += block_width + 3
        
        # Place connected blocks in sequence
        remaining_blocks = [b for b in sorted_blocks if b.block_number not in placed_blocks]
        
        while remaining_blocks:
            placed_any = False
            
            for block in remaining_blocks[:]:
                if hasattr(block, 'connected_blocks') and block.connected_blocks:
                    # Check if any connected block is already placed
                    for connected_num in block.connected_blocks:
                        if connected_num in placed_blocks and connected_num != 0:
                            # Place this block next to the connected one
                            positions[block.block_number] = {'x': current_x, 'y': track_y}
                            placed_blocks.add(block.block_number)
                            remaining_blocks.remove(block)
                            current_x += block_width + 3
                            placed_any = True
                            break
                
                if placed_any:
                    break
            
            # If no connections found, place next block in sequence
            if not placed_any and remaining_blocks:
                block = remaining_blocks.pop(0)
                positions[block.block_number] = {'x': current_x, 'y': track_y}
                placed_blocks.add(block.block_number)
                current_x += block_width + 3
        
        return positions

    def _draw_blue_style_connections(self, ax, sorted_blocks, block_positions, line_color):
        """Draw connections between blocks using Blue line style"""
        drawn_connections = set()
        
        for block in sorted_blocks:
            if not hasattr(block, 'connected_blocks') or not block.connected_blocks:
                continue
                
            current_pos = block_positions.get(block.block_number)
            if not current_pos:
                continue
                
            for connected_num in block.connected_blocks:
                if connected_num == 0:  # Skip yard connections
                    continue
                    
                connected_pos = block_positions.get(connected_num)
                if not connected_pos:
                    continue
                
                # Avoid duplicate connections
                conn_key = tuple(sorted([block.block_number, connected_num]))
                if conn_key in drawn_connections:
                    continue
                drawn_connections.add(conn_key)
                
                # Draw connection only if blocks are not adjacent (avoid clutter)
                x_diff = abs(connected_pos['x'] - current_pos['x'])
                if x_diff > 30:  # Only draw non-adjacent connections
                    ax.plot([current_pos['x'] + 12, connected_pos['x'] + 12], 
                           [current_pos['y'], connected_pos['y']], 
                           color=line_color, linewidth=6, alpha=0.6, linestyle='--')

    def _draw_blue_style_sections(self, ax, sorted_blocks, block_positions, line_color, track_y):
        """Draw section labels using Blue line style"""
        sections = {}
        for block in sorted_blocks:
            if block.section not in sections:
                sections[block.section] = []
            sections[block.section].append(block)
        
        # Draw section labels for major sections only
        section_names = sorted(sections.keys())
        sections_to_show = section_names[::max(1, len(section_names) // 6)]  # Max 6 sections
        
        for section_name in sections_to_show:
            section_blocks = sections[section_name]
            if section_blocks:
                # Find average position of blocks in this section
                valid_positions = [block_positions[b.block_number] for b in section_blocks 
                                 if b.block_number in block_positions]
                if valid_positions:
                    section_x = sum(pos['x'] for pos in valid_positions) / len(valid_positions)
                    section_y = track_y + 40  # Below the track
                    
                    ax.text(section_x, section_y, f"Section {section_name}",
                           ha='center', va='center', fontsize=11, fontweight='bold',
                           bbox=dict(boxstyle="round,pad=0.3", facecolor='#F0F0F0', 
                                    edgecolor=line_color, linewidth=1, alpha=0.9))

    def _draw_red_green_legend(self, ax):
        """Draw comprehensive legend for Red & Green lines"""
        # Position legend at bottom
        legend_x = 50
        legend_y = 50
        legend_width = 1100
        legend_height = 100
        
        # Legend background
        legend_bg = patches.Rectangle((legend_x - 10, legend_y - 10), legend_width, legend_height, 
                                    facecolor='#F8F8F8', edgecolor='black', linewidth=1, alpha=0.9)
        ax.add_patch(legend_bg)
        
        # Title
        ax.text(legend_x + legend_width/2, legend_y + legend_height - 20, 'TRACK LEGEND', 
               ha='center', va='center', fontsize=16, fontweight='bold')
        
        # Legend items
        items = [
            ('Red Line', '#F44336', 'line'),
            ('Green Line', '#4CAF50', 'line'),
            ('Station', '#FFD700', 'circle'),
            ('Switch', '#FF8C00', 'diamond'),
            ('Train', '#8A2BE2', 'square'),
            ('Maintenance', '#FF5555', 'line'),
            ('Yard', 'lightgray', 'rect')
        ]
        
        for i, (label, color, shape) in enumerate(items):
            x_pos = legend_x + 30 + (i * 150)
            y_pos = legend_y + 30
            
            if shape == 'line':
                ax.plot([x_pos, x_pos + 20], [y_pos, y_pos], color=color, linewidth=6)
            elif shape == 'circle':
                ax.plot(x_pos + 10, y_pos, 'o', markersize=8, color=color, 
                       markeredgecolor='#B8860B', markeredgewidth=2)
            elif shape == 'diamond':
                ax.plot(x_pos + 10, y_pos, 'D', markersize=7, color=color, 
                       markeredgecolor='#FF4500', markeredgewidth=1)
            elif shape == 'square':
                ax.plot(x_pos + 10, y_pos, 's', markersize=7, color=color, 
                       markeredgecolor='black', markeredgewidth=1)
            elif shape == 'rect':
                rect = patches.Rectangle((x_pos + 5, y_pos - 4), 10, 8, 
                                       facecolor=color, edgecolor='black', linewidth=1)
                ax.add_patch(rect)
            
            ax.text(x_pos + 10, y_pos - 15, label, ha='center', va='center', fontsize=10)

    def _create_red_line_topology(self, blocks, track_y):
        """Create Red line topology using realistic track layout based on connections"""
        if not blocks:
            return {}
        
        # Use the new topology-based layout engine
        layout_engine = TrackLayoutEngine()
        return layout_engine.create_line_layout(blocks, "Red", track_y, yard_x=500)

    def _create_green_line_topology(self, blocks, track_y):
        """Create Green line topology using realistic track layout based on connections"""
        if not blocks:
            return {}
        
        # Use the new topology-based layout engine
        layout_engine = TrackLayoutEngine()
        return layout_engine.create_line_layout(blocks, "Green", track_y, yard_x=500)

    def _draw_yard_connections(self, ax, blocks, block_positions, line_color):
        """Draw yard connections from blocks that connect to yard"""
        for block in blocks:
            if hasattr(block, 'has_yard_connection') and block.has_yard_connection:
                pos = block_positions.get(block.block_number)
                if pos:
                    # Draw small yard symbol near block
                    yard_x = pos['x'] - 20
                    yard_y = pos['y'] + 20
                    
                    yard_rect = patches.Rectangle((yard_x - 8, yard_y - 4), 16, 8,
                                                facecolor='lightgray', edgecolor='black', linewidth=1)
                    ax.add_patch(yard_rect)
                    ax.text(yard_x, yard_y, 'YD', ha='center', va='center', 
                           fontsize=7, fontweight='bold')
                    
                    # Connect to block
                    ax.plot([yard_x + 8, pos['x'] - 6], [yard_y, pos['y']],
                           color=line_color, linewidth=2, alpha=0.7)

    def _draw_topology_connections(self, ax, blocks, block_positions, line_color):
        """Draw track connections based on connected_blocks data"""
        drawn_connections = set()
        
        for block in blocks:
            if not hasattr(block, 'connected_blocks') or not block.connected_blocks:
                continue
                
            current_pos = block_positions.get(block.block_number)
            if not current_pos:
                continue
                
            for connected_num in block.connected_blocks:
                if connected_num == 0:  # Skip yard connections
                    continue
                    
                connected_pos = block_positions.get(connected_num)
                if not connected_pos:
                    continue
                
                # Avoid duplicate connections
                conn_key = tuple(sorted([block.block_number, connected_num]))
                if conn_key in drawn_connections:
                    continue
                drawn_connections.add(conn_key)
                
                # Draw connection line
                ax.plot([current_pos['x'], connected_pos['x']], 
                       [current_pos['y'], connected_pos['y']], 
                       color=line_color, linewidth=3, alpha=0.6, zorder=1)

    # NEW REDESIGNED VISUALIZATION METHODS
    
    def _draw_redesigned_track_line(self, ax, blocks, trains, maintenance_closures, line_name, line_color, track_y):
        """Balanced track visualization showing topology with readable infrastructure"""
        if not blocks:
            return
        
        # Use topology-based layout to show actual track structure
        if line_name == "Red":
            block_positions = self._create_red_line_topology(blocks, track_y)
        elif line_name == "Green":
            block_positions = self._create_green_line_topology(blocks, track_y)
        else:
            sorted_blocks = sorted(blocks, key=lambda b: b.block_number)
            block_positions = self._calculate_smart_positions(sorted_blocks, 100, track_y, 25)
        
        # Draw track connections to show structure
        self._draw_balanced_connections(ax, blocks, block_positions, line_color)
        
        # Draw blocks with improved visibility
        self._draw_balanced_blocks(ax, blocks, block_positions, line_color, maintenance_closures, line_name)
        
        # Draw enhanced infrastructure
        self._draw_balanced_infrastructure(ax, blocks, block_positions, track_y, line_color)
        
        # Draw yard connections
        self._draw_balanced_yard_connections(ax, blocks, block_positions, line_color)
        
        # Draw trains if present
        self._draw_balanced_trains(ax, trains, block_positions, line_name)
        
        # Add appropriately sized line title
        if block_positions:
            positions_list = list(block_positions.values())
            avg_x = sum(pos['x'] for pos in positions_list) / len(positions_list)
            ax.text(avg_x, track_y + 60, f'{line_name.upper()} LINE', 
                   ha='center', va='center', fontsize=16, fontweight='bold', 
                   color=line_color, bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.9))

    def _create_track_segments(self, blocks):
        """Create logical track segments for cleaner visualization"""
        segments = []
        
        # Group blocks into logical segments (stations, major junctions, etc.)
        current_segment = []
        
        sorted_blocks = sorted(blocks, key=lambda b: b.block_number)
        
        for block in sorted_blocks:
            current_segment.append(block)
            
            # End segment at stations or switches (major landmarks)
            if block.has_station or block.has_switch or len(current_segment) >= 20:
                if current_segment:
                    segments.append(current_segment)
                    current_segment = []
        
        # Add remaining blocks
        if current_segment:
            segments.append(current_segment)
        
        return segments

    def _draw_track_backbone(self, ax, segments, line_color, track_y):
        """Draw main track as thick continuous lines"""
        x_start = 100
        segment_width = 200  # Much wider segments
        
        for i, segment in enumerate(segments):
            if not segment:
                continue
                
            # Calculate segment position
            x_pos = x_start + (i * segment_width)
            
            # Draw thick track line for this segment
            ax.plot([x_pos, x_pos + segment_width - 50], [track_y, track_y], 
                   color=line_color, linewidth=20, solid_capstyle='round', alpha=0.8)
            
            # Add subtle segment separator
            if i > 0:
                ax.axvline(x=x_pos - 25, color='gray', linestyle='--', alpha=0.3, linewidth=1)

    def _draw_prominent_stations(self, ax, stations, track_y, line_name):
        """Draw large, prominent station markers"""
        if not stations:
            return
            
        # Position stations along the track
        x_positions = [200, 400, 800, 1200, 1400]  # Fixed prominent positions
        
        for i, station in enumerate(stations[:5]):  # Show up to 5 major stations
            if i >= len(x_positions):
                break
                
            x = x_positions[i]
            
            # Large station circle
            station_circle = patches.Circle((x, track_y), 30, 
                                          facecolor='#FFD700', edgecolor='black', 
                                          linewidth=4, zorder=10)
            ax.add_patch(station_circle)
            
            # Station symbol
            ax.text(x, track_y, 'S', ha='center', va='center', 
                   fontsize=20, fontweight='bold', color='black', zorder=11)
            
            # Station name with large, readable text
            ax.text(x, track_y - 50, station.station.name, ha='center', va='center',
                   fontsize=16, fontweight='bold', 
                   bbox=dict(boxstyle="round,pad=0.5", facecolor='white', 
                            edgecolor='black', linewidth=2), zorder=11)

    def _draw_prominent_switches(self, ax, switches, track_y, line_color):
        """Draw large, visible switch markers"""
        if not switches:
            return
            
        # Position switches at logical points
        x_positions = [300, 600, 1000, 1300]
        
        for i, switch in enumerate(switches[:4]):  # Show up to 4 major switches
            if i >= len(x_positions):
                break
                
            x = x_positions[i]
            
            # Large switch diamond
            ax.plot(x, track_y + 40, 'D', markersize=25, color='#FF8C00', 
                   markeredgecolor='black', markeredgewidth=3, zorder=10)
            
            # Switch label
            ax.text(x, track_y + 70, f'SW{i+1}', ha='center', va='center',
                   fontsize=14, fontweight='bold',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.9))

    def _draw_prominent_yard(self, ax, yard_blocks, track_y, line_color):
        """Draw large, visible yard connection"""
        if not yard_blocks:
            return
            
        # Position yard at the end
        yard_x = 1500
        yard_y = track_y
        
        # Large yard rectangle
        yard_rect = patches.Rectangle((yard_x - 60, yard_y - 40), 120, 80,
                                    facecolor='#D1D5DB', edgecolor='black', 
                                    linewidth=3, zorder=10)
        ax.add_patch(yard_rect)
        
        # Yard label
        ax.text(yard_x, yard_y, 'YARD', ha='center', va='center',
               fontsize=18, fontweight='bold', color='black', zorder=11)
        
        # Connection line to main track
        ax.plot([1400, yard_x - 60], [track_y, yard_y], 
               color=line_color, linewidth=8, alpha=0.7, zorder=9)

    def _draw_prominent_trains(self, ax, trains, blocks, track_y, line_name):
        """Draw large, visible train markers"""
        for train_id, train in trains.items():
            if train.line == line_name and hasattr(train, 'currentBlock'):
                # Position train roughly based on block number
                train_x = 200 + ((train.currentBlock % 100) * 10)  # Simple positioning
                
                # Large train rectangle
                train_rect = patches.Rectangle((train_x - 25, track_y + 50), 50, 20,
                                             facecolor='#8B5CF6', edgecolor='white', 
                                             linewidth=3, zorder=12)
                ax.add_patch(train_rect)
                
                # Train ID
                ax.text(train_x, track_y + 60, getattr(train, 'id', 'T'), 
                       ha='center', va='center', fontsize=16, fontweight='bold', 
                       color='white', zorder=13)
                
                # Block number below train
                ax.text(train_x, track_y + 35, f'B{train.currentBlock}', 
                       ha='center', va='center', fontsize=12, fontweight='bold',
                       bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.9))

    def _draw_redesigned_legend(self, ax):
        """Draw balanced legend with clear but appropriately sized symbols"""
        # Reasonable legend size at bottom
        legend_x = 150
        legend_y = 50
        legend_width = 1200
        legend_height = 80
        
        # Legend background
        legend_bg = patches.Rectangle((legend_x - 10, legend_y - 10), legend_width, legend_height, 
                                    facecolor='white', edgecolor='black', linewidth=2, alpha=0.95)
        ax.add_patch(legend_bg)
        
        # Appropriately sized title
        ax.text(legend_x + legend_width/2, legend_y + legend_height - 20, 'TRACK LEGEND', 
               ha='center', va='center', fontsize=14, fontweight='bold')
        
        # Legend items with reasonable sizing
        items = [
            ('Red Line', '#DC2626', 'line'),
            ('Green Line', '#16A34A', 'line'),
            ('Station', '#FFD700', 'station'),
            ('Switch', '#FF8C00', 'switch'),
            ('Train', '#8B5CF6', 'train'),
            ('Yard', '#D1D5DB', 'yard')
        ]
        
        # Single row of legend items
        for i, (label, color, shape) in enumerate(items):
            x_pos = legend_x + 30 + (i * 190)  # Reasonable spacing
            y_pos = legend_y + 35
            
            if shape == 'line':
                # Track lines - medium thickness
                ax.plot([x_pos, x_pos + 25], [y_pos, y_pos], 
                       color=color, linewidth=6, solid_capstyle='round')
            elif shape == 'station':
                # Station symbol - moderate size
                ax.add_patch(patches.Circle((x_pos + 12, y_pos), 8, 
                           facecolor=color, edgecolor='black', linewidth=2))
                station_ring = patches.Circle((x_pos + 12, y_pos), 12, facecolor='none', 
                                            edgecolor='#B8860B', linewidth=2)
                ax.add_patch(station_ring)
            elif shape == 'switch':
                # Switch diamond - moderate size
                ax.plot(x_pos + 12, y_pos, 'D', markersize=10, color=color, 
                       markeredgecolor='black', markeredgewidth=2)
            elif shape == 'train':
                # Train rectangle - moderate size
                ax.add_patch(patches.Rectangle((x_pos + 4, y_pos - 5), 16, 10,
                           facecolor=color, edgecolor='white', linewidth=2))
                ax.text(x_pos + 12, y_pos, 'T', ha='center', va='center',
                       fontsize=8, fontweight='bold', color='white')
            elif shape == 'yard':
                # Yard rectangle - moderate size
                ax.add_patch(patches.Rectangle((x_pos + 4, y_pos - 6), 16, 12,
                           facecolor=color, edgecolor='black', linewidth=1))
                ax.text(x_pos + 12, y_pos, 'YD', ha='center', va='center',
                       fontsize=7, fontweight='bold', color='black')
            
            # Readable labels - reasonable size
            ax.text(x_pos + 12, y_pos - 15, label, ha='center', va='center', 
                   fontsize=11, fontweight='bold', color='black')

    # BALANCED VISUALIZATION METHODS - RESTORING TRACK STRUCTURE
    
    def _draw_balanced_connections(self, ax, blocks, block_positions, line_color):
        """Draw track connections showing actual topology"""
        drawn_connections = set()
        
        for block in blocks:
            if not hasattr(block, 'connected_blocks') or not block.connected_blocks:
                continue
                
            current_pos = block_positions.get(block.block_number)
            if not current_pos:
                continue
                
            for connected_num in block.connected_blocks:
                if connected_num == 0:  # Skip yard connections
                    continue
                    
                connected_pos = block_positions.get(connected_num)
                if not connected_pos:
                    continue
                
                # Avoid duplicate connections
                conn_key = tuple(sorted([block.block_number, connected_num]))
                if conn_key in drawn_connections:
                    continue
                drawn_connections.add(conn_key)
                
                # Draw track connection line - medium thickness
                ax.plot([current_pos['x'], connected_pos['x']], 
                       [current_pos['y'], connected_pos['y']], 
                       color=line_color, linewidth=4, alpha=0.7, zorder=1)

    def _draw_balanced_blocks(self, ax, blocks, block_positions, line_color, maintenance_closures, line_name):
        """Draw blocks with better visibility but not overwhelming"""
        for block in blocks:
            pos = block_positions.get(block.block_number)
            if not pos:
                continue
                
            x, y = pos['x'], pos['y']
            
            # Determine block color
            if block.block_number in maintenance_closures.get(line_name, []):
                block_color = '#FF5555'  # Maintenance
            elif block.has_station:
                block_color = '#FFD700'  # Station
            elif block.has_switch:
                block_color = '#FF8C00'  # Switch
            else:
                block_color = line_color
            
            # Draw block as circle - moderate size
            block_circle = patches.Circle((x, y), 8, facecolor=block_color, 
                                        edgecolor='black', linewidth=1.5, zorder=2)
            ax.add_patch(block_circle)
            
            # Add block number for key blocks only - moderate font size
            if (block.block_number % 10 == 0 or block.has_station or block.has_switch or 
                block.block_number in [1, len(blocks)]):  # Start, end, and key blocks
                ax.text(x, y, str(block.block_number), ha='center', va='center',
                       fontsize=9, fontweight='bold', 
                       color='white' if block_color != '#FFD700' else 'black', zorder=3)

    def _draw_balanced_infrastructure(self, ax, blocks, block_positions, track_y, line_color):
        """Draw infrastructure with appropriate sizing and positioning"""
        for block in blocks:
            if not block.has_station and not block.has_switch:
                continue
                
            pos = block_positions.get(block.block_number)
            if not pos:
                continue
                
            x, y = pos['x'], pos['y']
            
            # Station markers
            if block.has_station and block.station:
                # Moderate-sized station ring
                station_ring = patches.Circle((x, y), 12, facecolor='none', 
                                            edgecolor='#B8860B', linewidth=2, zorder=4)
                ax.add_patch(station_ring)
                
                # Station name with reasonable text size
                ax.text(x, y - 20, block.station.name, ha='center', va='center',
                       fontsize=10, fontweight='bold',
                       bbox=dict(boxstyle="round,pad=0.2", facecolor='#FFFACD', 
                                edgecolor='#B8860B', alpha=0.9), zorder=5)
            
            # Switch markers
            if block.has_switch:
                # Moderate-sized switch diamond
                ax.plot(x, y + 15, 'D', markersize=8, color='#FF4500', 
                       markeredgecolor='black', markeredgewidth=1.5, zorder=4)

    def _draw_balanced_trains(self, ax, trains, block_positions, line_name):
        """Draw trains with appropriate visibility"""
        for train_id, train in trains.items():
            if train.line == line_name and hasattr(train, 'currentBlock'):
                pos = block_positions.get(train.currentBlock)
                if pos:
                    x, y = pos['x'], pos['y']
                    
                    # Moderate-sized train rectangle
                    train_rect = patches.Rectangle((x - 12, y + 20), 24, 10,
                                                 facecolor='#8B5CF6', edgecolor='white', 
                                                 linewidth=2, zorder=6)
                    ax.add_patch(train_rect)
                    
                    # Train ID with appropriate text size
                    ax.text(x, y + 25, getattr(train, 'id', 'T'), ha='center', va='center',
                           color='white', fontsize=9, fontweight='bold', zorder=7)

    def _draw_balanced_yard_connections(self, ax, blocks, block_positions, line_color):
        """Draw yard connections with appropriate sizing"""
        for block in blocks:
            if hasattr(block, 'has_yard_connection') and block.has_yard_connection:
                pos = block_positions.get(block.block_number)
                if pos:
                    x, y = pos['x'], pos['y']
                    
                    # Moderate yard box
                    yard_x = x + 25
                    yard_y = y
                    
                    yard_rect = patches.Rectangle((yard_x - 15, yard_y - 8), 30, 16,
                                                facecolor='#D1D5DB', edgecolor='black', 
                                                linewidth=2, zorder=4)
                    ax.add_patch(yard_rect)
                    ax.text(yard_x, yard_y, 'YARD', ha='center', va='center', 
                           fontsize=8, fontweight='bold', zorder=5)
                    
                    # Connection line
                    ax.plot([x + 8, yard_x - 15], [y, yard_y], 
                           color=line_color, linewidth=3, alpha=0.7, zorder=3)