# TBTG Python Coding Standard Instructions

## Overview
All code in this project must follow the TBTG Python Coding Standards as specified in "TBTG Python Coding Standard.rtf".

## Naming Conventions

### 1. Classes
- **Format**: PascalCase
- **Example**: `TrainController`, `CTCInterface`, `MaintenanceManager`

### 2. Instance Attributes/Properties
- **Format**: camelCase
- **Example**: `self.trainSpeed`, `self.currentBlock`, `self.destinationBlock`

### 3. Methods/Functions
- **Format**: snake_case
- **Example**: `def start_engine(self):`, `def calculate_speed(self):`

### 4. Variables (local and module-level)
- **Format**: snake_case
- **Example**: `train_speed = 100`, `block_number = 5`

### 5. Constants
- **Format**: UPPERCASE with underscores
- **Example**: `MAX_SPEED = 300`, `DEFAULT_AUTHORITY = 3`

## Code Formatting

### Indentation
- **Default**: Use **TAB** characters for indentation
- **Raspberry Pi**: Use **4 spaces** for indentation
- **Consistency**: Maintain consistent indentation throughout each file

### Comments and Documentation
- **Single-line comments**: Use `#` followed by space
- **Multi-line comments/docstrings**: Use `"""`
- **Example**:
  ```python
  # Calculate train speed based on track conditions
  def calculate_speed(self):
      """
      Calculate the suggested speed for a train based on current track conditions.
      
      Returns:
          float: Suggested speed in km/h
      """
      pass
  ```

### Error Handling
- Use try-except blocks for error handling
- **Example**:
  ```python
  try:
      speed = int(user_input)
  except ValueError:
      print("Invalid speed input")
  ```

## Refactoring Checklist

When refactoring existing code:

1. **Convert class names** to PascalCase
2. **Convert instance attributes** from snake_case to camelCase
3. **Convert method names** to snake_case
4. **Convert local variables** to snake_case
5. **Convert constants** to UPPERCASE
6. **Update indentation** to use tabs (or 4 spaces for Raspberry Pi)
7. **Review comments** for proper formatting
8. **Ensure docstrings** use triple quotes

## Important Notes

- These standards differ from PEP 8 in several key areas (mixed naming conventions, tab indentation)
- Maintain consistency within each file
- When in doubt, refer to the original "TBTG Python Coding Standard.rtf" document
- All new code must follow these standards from the start

## Code Review Points

- Verify naming conventions are followed correctly
- Check indentation consistency
- Ensure proper comment formatting
- Validate error handling patterns
- Confirm docstring format compliance