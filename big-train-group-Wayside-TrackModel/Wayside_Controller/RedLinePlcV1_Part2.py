"""
Red Line PLC 2 - Blocks 39-76
==============================
PLC program for Red Line blocks 39-76 including:
- Switch control for blocks 43, 52 (based on Excel file)
- Railway crossing control at block 47
- Speed hazard management for sections G-N
- Directional traffic management

Switches from Excel file:
- Block 43: SWITCH (43-44; 44-67); UNDERGROUND
- Block 52: SWITCH (52-53; 52-66)

Author: Systems and Project Engineering Student
"""

def main(block_occupancy, speed, authority, switches_actual, 
         traffic_lights_actual, crossings_actual, block_numbers):
    """
    Main Red Line PLC 2 loop that manages blocks 39-76.
    
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
    switches = [False] * 2       # 2 switches in this PLC section
    traffic_lights = [False] * 6 # Traffic lights for switch entrances
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
            43: 0,  # SWITCH (43-44; 44-67)
            52: 1   # SWITCH (52-53; 52-66)
        }
        
        # Map traffic lights to block entrances for each switch connection
        traffic_light_mapping = {
            # Switch at block 43: (43-44; 44-67)
            43: 0,   # Entrance to block 43 from block 42
            44: 1,   # Entrance to block 44 from block 43
            67: 2,   # Entrance to block 67 from block 44
            
            # Switch at block 52: (52-53; 52-66)
            52: 3,   # Entrance to block 52 from block 51
            53: 4,   # Entrance to block 53 from block 52
            66: 5    # Entrance to block 66 from block 52
        }
        
        # Map crossings to their indices
        crossing_mapping = {
            47: 0  # RAILWAY CROSSING at block 47 maps to crossings[0]
        }
        
        # Apply mappings based on block_numbers array
        for i in range(len(block_numbers)):
            block_num = block_numbers[i]
            
            # Only handle blocks in our range (39-76)
            if block_num < 39 or block_num > 76:
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
    
    def GHIJ_occupied():
        """Check if sections G, H, I, J (blocks 39-52) are occupied."""
        for i in range(39, 53):
            if i < len(block_occupancy) and block_occupancy[i]:
                return True
        return False
    
    def KLM_occupied():
        """Check if sections K, L, M (blocks 53-66) are occupied."""
        for i in range(53, 67):
            if i < len(block_occupancy) and block_occupancy[i]:
                return True
        return False
    
    def N_occupied():
        """Check if section N (blocks 67-76) is occupied."""
        for i in range(67, 77):
            if i < len(block_occupancy) and block_occupancy[i]:
                return True
        return False
    
    def set_N_speed_hazard(truth_value):
        """Set speed hazard for section N (blocks 67-76)."""
        for i in range(67, 77):
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
    if 52 < len(block_occupancy) and block_occupancy[52] == True and not (51 < len(block_occupancy) and block_occupancy[51]):
        up_through_H = True

    # Switch control logic based on Excel file connections
    
    # Switch at block 43: (43-44; 44-67)
    # Direction-based control
    if up_through_H == True:
        switches[0] = False  # 43-44 then 44-67 connection (bypass route)
        traffic_lights[0] = True   # Block 43 entrance
        traffic_lights[1] = True   # Block 44 entrance
        traffic_lights[2] = True   # Block 67 entrance
    else:
        switches[0] = True   # 43-44 connection (normal route)
        traffic_lights[0] = True   # Block 43 entrance
        traffic_lights[1] = True   # Block 44 entrance
        traffic_lights[2] = False  # Block 67 entrance
    
    # Switch at block 52: (52-53; 52-66)
    # Section management based control
    if FGHIJ_occupied() == False:
        switches[1] = True   # 52-66 connection (return route)
        traffic_lights[3] = True   # Block 52 entrance
        traffic_lights[4] = False  # Block 53 entrance
        traffic_lights[5] = True   # Block 66 entrance
        
        if ABC_occupied() == True:
            set_N_speed_hazard(True)
        else:
            set_N_speed_hazard(False)
    else:
        # Do not let other trains go on to the section
        if not (66 < len(block_occupancy) and block_occupancy[66]) and not (1 < len(block_occupancy) and block_occupancy[1]):
            switches[1] = False  # 52-53 connection (normal route)
            traffic_lights[3] = True   # Block 52 entrance
            traffic_lights[4] = True   # Block 53 entrance
            traffic_lights[5] = False  # Block 66 entrance
            set_N_speed_hazard(True)

    # Speed hazard management for sections G-N (blocks 39-76)
    
    if up_through_H == False:
        # Normal direction - trailing hazards for sections GHIJ
        for i in range(39, 53):
            if i < len(block_occupancy) and block_occupancy[i] == True:
                for j in range(1, 5):
                    hazard_block = i - j
                    if hazard_block >= 39 and hazard_block < len(speed_hazard):
                        speed_hazard[hazard_block] = True
    else:
        # Reverse direction - leading hazards for sections GHIJ
        for i in range(39, 53):
            if i < len(block_occupancy) and block_occupancy[i] == True:
                for j in range(1, 5):
                    hazard_block = i + j
                    if hazard_block < 53 and hazard_block < len(speed_hazard):
                        speed_hazard[hazard_block] = True

    # Speed hazards for sections K-N (blocks 53-76)
    for i in range(53, 77):
        if i < len(block_occupancy) and block_occupancy[i] == True:
            # Set trailing hazards for 4 blocks behind
            for j in range(1, 5):
                hazard_block = i - j
                if hazard_block >= 53 and hazard_block < len(speed_hazard):
                    speed_hazard[hazard_block] = True

    # Railway crossing control at block 47
    crossings[0] = False  # Default is up
    # Check 3 blocks before and after crossing (7 total blocks)
    for i in range(-3, 4):
        check_block = 47 + i
        if check_block >= 0 and check_block < len(block_occupancy) and block_occupancy[check_block]:
            crossings[0] = True  # Put the crossing down
            break

    # Apply speed hazards to speed and authority
    speed_hazard_to_speed_authority()
    
    # Map all track objects to their physical locations
    map_track_objects()