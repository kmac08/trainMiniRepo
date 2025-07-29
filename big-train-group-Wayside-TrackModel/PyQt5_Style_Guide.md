# PyQt5 Style Guide

## Color Palette
- **Background**: White (`#ffffff`)
- **Text**: Black (`#000000`)
- **Borders**: Medium gray (`#808080`)
- **Button backgrounds**: Light gray (`#E0E0E0`)
- **Hover states**: Darker gray (`#D0D0D0`)
- **Success/Green**: `#4CAF50` (Start buttons)
- **Warning/Orange**: `#FF9800` (Pause buttons)
- **Error/Red**: `#f44336` (Stop/Emergency buttons)
- **Selection/Blue**: `#3399FF` (Table selections)

## Font Standards
- **Default**: 18pt Arial (Updated for better readability - used for all UI controls and table content)
- **Headers**: 16pt Arial Bold (Updated for better readability - used for table headers and section titles)
- **Large headers**: 20pt-24pt Arial Bold (Used for main page titles and important displays)
- **Large displays**: 30pt-64pt Arial Bold (Time displays, critical status information)
- **Monospace**: 'Courier New' 16pt (Message displays, updated for better readability)

## Common Widget Styles

### Buttons
```python
QPushButton { 
    color: black; 
    background-color: #E0E0E0; 
    border: 1px solid #808080; 
    padding: 6px 12px; 
    font-size: 18pt; 
    font-weight: bold;
    min-height: 20px;
}
QPushButton:hover { background-color: #D0D0D0; }
QPushButton:pressed { background-color: #C0C0C0; }
```

### Input Fields
```python
QLineEdit { 
    color: black; 
    background-color: white; 
    border: 1px solid #808080; 
    padding: 4px; 
    font-size: 18pt;
}
```

### Tables
```python
QTableWidget { 
    color: black; 
    background-color: white; 
    border: 1px solid #808080; 
    gridline-color: #C0C0C0; 
    font-size: 18pt;
}
QTableWidget::item:selected { 
    background-color: #3399FF; 
    color: white; 
}
```

### Group Boxes
```python
QGroupBox { 
    color: black; 
    background-color: white; 
    border: 2px solid #808080; 
    font-size: 16pt;
    font-weight: bold; 
    padding-top: 10px; 
    margin-top: 6px; 
}
```

## Application Setup
```python
app.setStyleSheet("""
    QWidget { font-size: 18pt; }
    QPushButton { font-size: 18pt; }
    QLabel { font-size: 18pt; }
    QGroupBox { font-size: 16pt; font-weight: bold; }
""")
```

Use these patterns for consistent UI design across all modules.

## Font Implementation Guidelines

### Size Categories:
- **Default text** (18pt): Body text, input fields, table content, buttons, dropdowns
- **Headers** (16pt): Section titles, table headers, dialog titles  
- **Large headers** (20-24pt): Main page titles, important displays
- **Large displays** (30pt+): Time displays, critical status information

### Implementation:
Use explicit `setFont()` calls rather than stylesheets for reliable font application:
```python
# Default controls (buttons, inputs, table content)
widget.setFont(QFont("Arial", 18))

# Headers (table headers, section titles)
header_label.setFont(QFont("Arial", 16, QFont.Bold))

# Tables
table.setFont(QFont("Arial", 18))
table.horizontalHeader().setFont(QFont("Arial", 16, QFont.Bold))

# Large headers (main titles)
title_label.setFont(QFont("Arial", 20, QFont.Bold))
```