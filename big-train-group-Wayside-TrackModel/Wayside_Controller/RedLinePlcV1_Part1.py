"""
Red Line PLC 1 - Blocks 1-38
=============================
PLC program for Red Line blocks 1-38 including:
- Switch control for blocks 9, 15, 27, 32, 38 (based on Excel file)
- Directional traffic management
- Speed hazard management for sections A-F
- Yard operations

Switches from Excel file:
- Block 9: SWITCH TO/FROM YARD (9-yard)
- Block 15: SWITCH (15-16; 1-16)
- Block 27: SWITCH (27-28; 27-76); UNDERGROUND
- Block 32: SWITCH (32-33; 33-72); UNDERGROUND
- Block 38: SWITCH (38-39; 38-71); UNDERGROUND

Author: Systems and Project Engineering Student
"""

def main(block_occupancy, speed, authority, switches_actual, 
         traffic_lights_actual, crossings_actual, block_numbers):
    """
    Main Red Line PLC 1 loop that manages blocks 1-38.
    
    Args:
        block_occupancy: List of block occupancy states
        speed: List of speed commands for each block
        authority: List of authority commands for each block
        switches_actual: Actual switch positions
        traffic_lights_actual: Actual traffic light states
        crossings_actual: Actual crossing states
        block_numbers: Block number mapping array
    """
    speed_hazard = [False] * 77  # Initialize speed hazard list for all Red Line blocks
    switches = [False] * 5       # 5 switches in this PLC section
    traffic_lights = [False] * 12 # Traffic lights for switch entrances
    crossings = [False] * 0      # No crossings in this section

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
            9: 0,   # SWITCH TO/FROM YARD (9-yard)
            15: 1,  # SWITCH (15-16; 1-16)
            27: 2,  # SWITCH (27-28; 27-76)
            32: 3,  # SWITCH (32-33; 33-72)
            38: 4   # SWITCH (38-39; 38-71)
        }
        
        # Map traffic lights to block entrances for each switch connection
        traffic_light_mapping = {
            # Switch at block 9: TO/FROM YARD (9-yard)
            9: 0,    # Yard entrance/exit at block 9
            
            # Switch at block 15: (15-16; 1-16)
            15: 1,   # Entrance to block 15 from block 14
            16: 2,   # Entrance to block 16 from block 15
            1: 3,    # Entrance to block 1 from block 2
            
            # Switch at block 27: (27-28; 27-76)
            27: 4,   # Entrance to block 27 from block 26
            28: 5,   # Entrance to block 28 from block 27
            76: 6,   # Entrance to block 76 from block 27
            
            # Switch at block 32: (32-33; 33-72)
            32: 7,   # Entrance to block 32 from block 31
            33: 8,   # Entrance to block 33 from block 32
            72: 9,   # Entrance to block 72 from block 33
            
            # Switch at block 38: (38-39; 38-71)
            38: 10,  # Entrance to block 38 from block 37
            39: 11   # Entrance to block 39 from block 38
            # Note: Block 71 entrance handled by PLC 2
        }
        
        # Apply mappings based on block_numbers array
        for i in range(len(block_numbers)):
            block_num = block_numbers[i]
            
            # Only handle blocks in our range (1-38)
            if block_num < 1 or block_num > 38:
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

    def FGHIJ_occupied():
        """Check if sections F, G, H, I, J (blocks 16-52) are occupied."""
        for i in range(16, 53):
            if i < len(block_occupancy) and block_occupancy[i]:
                return True
        return False
    
    def ABC_occupied():
        """Check if sections A, B, C (blocks 1-9) are occupied."""
        for i in range(1, 10):
            if i < len(block_occupancy) and block_occupancy[i]:
                return True
        return False
    
    def DEF_occupied():
        """Check if sections D, E, F (blocks 10-38) are occupied."""
        for i in range(10, 39):
            if i < len(block_occupancy) and block_occupancy[i]:
                return True
        return False
    
    def set_A_speed_hazard(truth_value):
        """Set speed hazard for section A (blocks 1-3)."""
        for i in range(1, 4):
            if i < len(speed_hazard):
                speed_hazard[i] = truth_value

    def reset_hazard():
        """Reset all speed hazards to False."""
        for i in range(0, len(speed_hazard)):
            speed_hazard[i] = False

    # Initialize directional control
    up_through_H = False
    
    # Reset all hazards
    reset_hazard()

    # Determine direction based on train positions
    if 16 < len(block_occupancy) and block_occupancy[16] == True and not (17 < len(block_occupancy) and block_occupancy[17]):
        up_through_H = False
    
    # Switch control logic based on Excel file connections
    
    # Switch at block 9: TO/FROM YARD (9-yard)
    # Control based on line occupancy
    if ABC_occupied() or DEF_occupied() or FGHIJ_occupied():
        switches[0] = False  # Don't allow yard operations when line is busy
        traffic_lights[0] = False  # Yard entrance restricted
    else:
        switches[0] = True   # Allow yard operations
        traffic_lights[0] = True   # Yard entrance allowed
    
    # Switch at block 15: (15-16; 1-16)
    # Default: 15-16 connection
    switches[1] = True   # True = 15-16, False = 1-16
    traffic_lights[1] = True   # Block 15 entrance
    traffic_lights[2] = True   # Block 16 entrance
    traffic_lights[3] = False  # Block 1 entrance (alternate route)
    
    # Switch at block 27: (27-28; 27-76)
    # Direction-based control
    if up_through_H == True:
        switches[2] = True   # 27-76 connection (bypass route)
        traffic_lights[4] = True   # Block 27 entrance
        traffic_lights[5] = False  # Block 28 entrance
        traffic_lights[6] = True   # Block 76 entrance
    else:
        switches[2] = False  # 27-28 connection (normal route)
        traffic_lights[4] = True   # Block 27 entrance
        traffic_lights[5] = True   # Block 28 entrance
        traffic_lights[6] = False  # Block 76 entrance
    
    # Switch at block 32: (32-33; 33-72)
    # Direction-based control
    if up_through_H == True:
        switches[3] = False  # 32-33 connection then 33-72
        traffic_lights[7] = True   # Block 32 entrance
        traffic_lights[8] = True   # Block 33 entrance
        traffic_lights[9] = True   # Block 72 entrance
    else:
        switches[3] = True   # 32-33 connection (normal route)
        traffic_lights[7] = True   # Block 32 entrance
        traffic_lights[8] = True   # Block 33 entrance
        traffic_lights[9] = False  # Block 72 entrance
    
    # Switch at block 38: (38-39; 38-71)
    # Direction-based control
    if up_through_H == True:
        switches[4] = True   # 38-71 connection (bypass route)
        traffic_lights[10] = True   # Block 38 entrance
        traffic_lights[11] = False  # Block 39 entrance
    else:
        switches[4] = False  # 38-39 connection (normal route)
        traffic_lights[10] = True   # Block 38 entrance
        traffic_lights[11] = True   # Block 39 entrance

    # Speed hazard management for sections A-F (blocks 1-38)
    
    if up_through_H == False:
        # Normal direction - trailing hazards
        for i in range(1, 39):
            if i < len(block_occupancy) and block_occupancy[i] == True:
                for j in range(1, 5):
                    hazard_block = i - j
                    if hazard_block >= 1 and hazard_block < len(speed_hazard):
                        speed_hazard[hazard_block] = True
    else:
        # Reverse direction - leading hazards
        for i in range(1, 39):
            if i < len(block_occupancy) and block_occupancy[i] == True:
                for j in range(1, 5):
                    hazard_block = i + j
                    if hazard_block < 39 and hazard_block < len(speed_hazard):
                        speed_hazard[hazard_block] = True

    # Yard control - only let train out of yard if clear
    if ABC_occupied() == True or DEF_occupied() == True:
        speed_hazard[0] = True
    else:
        speed_hazard[0] = False

    # Section management - prioritize trains in sections ABC
    if DEF_occupied() == False:
        set_A_speed_hazard(False)
    else:
        set_A_speed_hazard(True)

    # Apply speed hazards to speed and authority
    speed_hazard_to_speed_authority()
    
    # Map all track objects to their physical locations
    map_track_objects()