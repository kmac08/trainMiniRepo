"""
Green Line PLC 1 - Blocks 1-75
===============================
PLC program for Green Line blocks 1-75 including:
- Switch control for blocks 12, 29, 58, 62 (based on Excel file)
- Railway crossing control at block 19
- Speed hazard management for sections A-M
- Yard operations

Switches from Excel file:
- Block 12: SWITCH (12-13; 1-13)
- Block 29: SWITCH (29-30; 29-150) 
- Block 58: SWITCH TO YARD (57-yard)
- Block 62: SWITCH FROM YARD (Yard-63)

Author: Systems and Project Engineering Student
"""

def main(block_occupancy, speed, authority, switches_actual, 
         traffic_lights_actual, crossings_actual, block_numbers):
    """
    Main Green Line PLC 1 loop that manages blocks 1-75.
    
    Args:
        block_occupancy: List of block occupancy states
        speed: List of speed commands for each block
        authority: List of authority commands for each block
        switches_actual: Actual switch positions
        traffic_lights_actual: Actual traffic light states
        crossings_actual: Actual crossing states
        block_numbers: Block number mapping array
    """
    speed_hazard = [False] * 151  # Initialize speed hazard list for all blocks
    switches = [False] * 4       # 4 switches in this PLC section
    traffic_lights = [False] * 8 # Traffic lights for switch entrances
    crossings = [False] * 1      # 1 crossing in this section

    def speed_hazard_to_speed_authority():
        """Apply speed hazards to speed and authority commands."""
        for i in range(len(speed_hazard)):
            for z in range(len(block_numbers)):
                if speed_hazard[i] == True and block_numbers[z] == i:
                    speed[i] = 0
                    authority[i] = 0
    
    def map_track_objects():
        """Map track objects to their physical locations based on Excel file."""
        # Map switches to their indices based on Excel file data
        switch_mapping = {
            12: 0,  # SWITCH (12-13; 1-13)
            29: 1,  # SWITCH (29-30; 29-150)
            58: 2,  # SWITCH TO YARD (57-yard)
            62: 3   # SWITCH FROM YARD (Yard-63)
        }
        
        # Map traffic lights to block entrances for each switch connection
        traffic_light_mapping = {
            # Switch at block 12: (12-13; 1-13)
            12: 0,   # Entrance to block 12 from block 11
            13: 1,   # Entrance to block 13 from block 12
            1: 2,    # Entrance to block 1 from block 2
            
            # Switch at block 29: (29-30; 29-150)
            29: 3,   # Entrance to block 29 from block 28
            30: 4,   # Entrance to block 30 from block 29
            150: 5,  # Entrance to block 150 from block 29
            
            # Switch at block 58: TO YARD (57-yard)
            58: 6,   # Entrance to yard switch at block 58 from block 57
            
            # Switch at block 62: FROM YARD (Yard-63)
            62: 7    # Entrance to block 62 from yard
        }
        
        # Map crossings to their indices
        crossing_mapping = {
            19: 0  # RAILWAY CROSSING at block 19 maps to crossings[0]
        }
        
        # Apply mappings based on block_numbers array
        for i in range(len(block_numbers)):
            block_num = block_numbers[i]
            
            # Only handle blocks in our range (1-75)
            if block_num < 1 or block_num > 75:
                continue
            
            # Map switches
            if block_num in switch_mapping:
                switch_index = switch_mapping[block_num]
                if switch_index < len(switches_actual):
                    switches_actual[switch_index] = switches[switch_index]
            
            # Map traffic lights  
            if block_num in traffic_light_mapping:
                light_index = traffic_light_mapping[block_num]
                if light_index < len(traffic_lights_actual):
                    traffic_lights_actual[light_index] = traffic_lights[light_index]
            
            # Map crossings
            if block_num in crossing_mapping:
                crossing_index = crossing_mapping[block_num]
                if crossing_index < len(crossings_actual):
                    crossings_actual[crossing_index] = crossings[crossing_index]

    def A_to_D_occupied():
        """Check if sections A-D (blocks 1-36) are occupied."""
        for i in range(1, 37):
            if i < len(block_occupancy) and block_occupancy[i]:
                return True
        return False
    
    def E_to_H_occupied():
        """Check if sections E-H (blocks 37-57) are occupied."""
        for i in range(37, 58):
            if i < len(block_occupancy) and block_occupancy[i]:
                return True
        return False
    
    def I_to_M_occupied():
        """Check if sections I-M (blocks 58-75) are occupied."""
        for i in range(58, 76):
            if i < len(block_occupancy) and block_occupancy[i]:
                return True
        return False
    
    def set_section_hazard(start_block, end_block, truth_val):
        """Set speed hazard for a range of blocks."""
        for i in range(start_block, end_block + 1):
            if i < len(speed_hazard):
                speed_hazard[i] = truth_val
    
    def reset_hazard():
        """Reset all speed hazards to False."""
        for i in range(0, len(speed_hazard)):
            speed_hazard[i] = False

    # Reset all hazards
    reset_hazard()

    # Switch control logic based on Excel file connections
    
    # Switch at block 12: (12-13; 1-13)
    # Default: 12-13 connection (normal state)
    switches[0] = False  # False = 12-13, True = 1-13
    traffic_lights[0] = True   # Block 12 entrance
    traffic_lights[1] = True   # Block 13 entrance  
    traffic_lights[2] = False  # Block 1 entrance (alternate route)
    
    # Switch at block 29: (29-30; 29-150)
    # Default: 29-30 connection (normal state)
    switches[1] = False  # False = 29-30, True = 29-150
    traffic_lights[3] = True   # Block 29 entrance
    traffic_lights[4] = True   # Block 30 entrance
    traffic_lights[5] = False  # Block 150 entrance (alternate route)
    
    # Switch at block 58: TO YARD (57-yard)
    # Control based on yard occupancy and traffic
    if block_occupancy[0]:  # If yard is occupied
        switches[2] = False  # Don't allow entry to yard
        traffic_lights[6] = False  # Block 58 entrance restricted
    else:
        switches[2] = True   # Allow entry to yard
        traffic_lights[6] = True   # Block 58 entrance allowed
    
    # Switch at block 62: FROM YARD (Yard-63)
    # Control based on line occupancy
    if A_to_D_occupied() or E_to_H_occupied():
        switches[3] = False  # Don't allow exit from yard
        traffic_lights[7] = False  # Block 62 entrance restricted
    else:
        switches[3] = True   # Allow exit from yard
        traffic_lights[7] = True   # Block 62 entrance allowed

    # Speed hazard management for sections A-M (blocks 1-75)
    
    # Sections A-D (blocks 1-36) - trailing hazards
    for i in range(1, 37):
        if i < len(block_occupancy) and block_occupancy[i]:
            # Set trailing hazards for 4 blocks behind
            for j in range(1, 5):
                hazard_block = i - j
                if hazard_block >= 1 and hazard_block < len(speed_hazard):
                    speed_hazard[hazard_block] = True

    # Sections E-H (blocks 37-57) - trailing hazards  
    for i in range(37, 58):
        if i < len(block_occupancy) and block_occupancy[i]:
            # Set trailing hazards for 4 blocks behind
            for j in range(1, 5):
                hazard_block = i - j
                if hazard_block >= 37 and hazard_block < len(speed_hazard):
                    speed_hazard[hazard_block] = True

    # Sections I-M (blocks 58-75) - trailing hazards
    for i in range(58, 76):
        if i < len(block_occupancy) and block_occupancy[i]:
            # Set trailing hazards for 4 blocks behind
            for j in range(1, 5):
                hazard_block = i - j
                if hazard_block >= 58 and hazard_block < len(speed_hazard):
                    speed_hazard[hazard_block] = True

    # Railway crossing control at block 19
    crossings[0] = False  # Default is up
    # Check 3 blocks before and after crossing (7 total blocks)
    for i in range(-3, 4):
        check_block = 19 + i
        if check_block >= 0 and check_block < len(block_occupancy) and block_occupancy[check_block]:
            crossings[0] = True  # Put the crossing down
            break

    # Yard management - don't let trains out if line is busy
    if A_to_D_occupied() or E_to_H_occupied():
        speed_hazard[0] = True  # Stop trains at yard
    else:
        speed_hazard[0] = False

    # Apply speed hazards to speed and authority
    speed_hazard_to_speed_authority()
    
    # Map all track objects to their physical locations
    map_track_objects()