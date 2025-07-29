# CTCVisualDisplay Class Documentation

## Overview
The CTCVisualDisplay class (`ctc_display.py`) provides methods to create visual representations of track layout for the dispatcher interface. Designed to be clear and intuitive for non-technical users.

## Attributes

### Color Scheme
- `COLORS` (Dict[str, str]): Color scheme designed for clarity and accessibility
  - `track_normal`: Dark gray for regular track (#333333)
  - `track_maintenance`: Red for closed sections (#FF6B6B)
  - `station`: Blue for stations (#4DABF7)
  - `switch`: Green for switches (#69DB7C)
  - `crossing`: Yellow for crossings (#FFD43B)
  - `train`: Pink for trains (#FF8CC8)
  - `authority`: Light green for authority zones (#C3FAD5)
  - `background`: Light gray background (#F8F9FA)
  - `grid`: Grid lines (#DEE2E6)

### Instance Attributes
- `track_reader` (TrackLayoutReader): Track layout data source

## Methods

### Core Visualization Methods
- `create_line_diagram(line: str, active_trains: Optional[Dict[int, str]], maintenance_sections: Optional[List[str]], zoom_section: Optional[str]) -> plt.Figure`: Create a visual diagram of a track line
- `create_system_overview(active_trains: Dict[str, Dict[int, str]], maintenance: Dict[str, List[str]]) -> plt.Figure`: Create an overview of all three lines for the dispatcher's main screen

### Drawing Helper Methods
- `_draw_station(ax, x: float, y: float, name: str)`: Draw a station symbol
- `_draw_switch(ax, x: float, y: float)`: Draw a switch symbol
- `_draw_crossing(ax, x: float, y: float)`: Draw a railway crossing symbol
- `_draw_train(ax, x: float, y: float, train_id: str)`: Draw a train symbol
- `_add_legend(ax)`: Add a legend to the diagram
- `_create_empty_diagram(message: str) -> plt.Figure`: Create an empty diagram with a message

## Method Details

### create_line_diagram
Creates a detailed visual diagram of a specific track line with the following features:
- **Track segments**: Drawn proportional to actual block lengths
- **Infrastructure**: Stations, switches, and crossings clearly marked
- **Trains**: Current train positions with IDs
- **Maintenance**: Highlighted sections under maintenance
- **Elevation profile**: Visual representation of track elevation changes
- **Section dividers**: Clear boundaries between track sections
- **Legend**: Color-coded legend for all symbols

**Parameters:**
- `line`: Line name ("Blue", "Red", or "Green")
- `active_trains`: Dict of {block_number: train_id} for current train positions
- `maintenance_sections`: List of section letters closed for maintenance
- `zoom_section`: Optional section letter to focus on specific area

**Returns:** matplotlib figure ready for display

### create_system_overview
Creates a high-level overview showing all three lines simultaneously:
- **Line statistics**: Block count, station count, switch count, active trains
- **Maintenance indicators**: Clear warnings for lines under maintenance
- **System-wide status**: Comprehensive view for dispatcher decision-making

**Parameters:**
- `active_trains`: Dict of {line: {block_number: train_id}} for all lines
- `maintenance`: Dict of {line: [section_letters]} for maintenance closures

**Returns:** matplotlib figure with three-panel overview

## Visual Design Philosophy

### Accessibility
- High contrast colors for clear visibility
- Large, bold text for train and block numbers
- Distinct symbols for different infrastructure types
- Color-blind friendly color palette

### Clarity
- Proportional scaling based on actual track dimensions
- Consistent symbol placement and sizing
- Logical layout following actual track geometry
- Clear separation between different information layers

### User Experience
- Intuitive symbols that match real-world appearances
- Consistent color coding throughout all displays
- Informative legends and labels
- Scalable displays that work at different zoom levels

## Integration Notes
- Designed for integration with CTC Office GUI applications
- Returns matplotlib figures that can be embedded in various GUI frameworks
- Real-time updates supported by regenerating displays with current data
- Click handlers can be added to interact with specific blocks or trains
- Supports both full-line views and zoomed section views
- Optimized for display on dispatcher workstations with standard monitors

## Display Recommendations

### For Real-time Operation
1. Update displays every 2-5 seconds for train movements
2. Immediate updates for maintenance status changes
3. Use create_line_diagram() for detailed operational views
4. Use create_system_overview() for high-level monitoring

### For User Interface Integration
1. Embed figures in scrollable containers for large track layouts
2. Provide zoom controls for detailed inspection
3. Add click handlers using matplotlib event handling
4. Consider toolbar integration for display options (show/hide elements)
5. Implement print functionality for hardcopy documentation