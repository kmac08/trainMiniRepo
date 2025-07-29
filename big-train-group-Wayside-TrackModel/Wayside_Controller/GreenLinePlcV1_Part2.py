"""
Green Line PLC 2 - Blocks 76-150
=================================
PLC program for Green Line blocks 76-150 including:
- Switch control for blocks 76, 85 (based on Excel file)
- Speed hazard management for sections N-U
- Advanced switch logic from original implementation

Switches from Excel file:
- Block 76: SWITCH (76-77;77-101)
- Block 85: SWITCH (85-86; 100-85)

Author: Systems and Project Engineering Student
"""

def main(block_occupancy, speed, authority, switches_actual, 
         traffic_lights_actual, crossings_actual, block_numbers):
    """
    Main Green Line PLC 2 loop that manages blocks 76-150.
    
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
    switches = [False] * 2       # 2 switches in this PLC section
    traffic_lights = [False] * 6 # Traffic lights for switch entrances
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
            76: 0,  # SWITCH (76-77;77-101)
            85: 1   # SWITCH (85-86; 100-85)
        }
        
        # Map traffic lights to block entrances for each switch connection
        traffic_light_mapping = {
            # Switch at block 76: (76-77;77-101)
            76: 0,   # Entrance to block 76 from block 75
            77: 1,   # Entrance to block 77 from block 76
            101: 2,  # Entrance to block 101 from block 77
            
            # Switch at block 85: (85-86; 100-85)
            85: 3,   # Entrance to block 85 from block 84
            86: 4,   # Entrance to block 86 from block 85
            100: 5   # Entrance to block 100 from block 85
        }
        
        # Apply mappings based on block_numbers array
        for i in range(len(block_numbers)):
            block_num = block_numbers[i]
            
            # Only handle blocks in our range (76-150)
            if block_num < 76 or block_num > 150:
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

    def N_occupied():
        """Check if section N (blocks 77-85) is occupied."""
        for i in range(77, 86):
            if i < len(block_occupancy) and block_occupancy[i]:
                return True
        return False
    
    def Q_occupied():
        """Check if section Q (blocks 98-100) is occupied."""
        for i in range(98, 101):
            if i < len(block_occupancy) and block_occupancy[i]:
                return True
        return False
    
    def M_occupied():
        """Check if section M (blocks 74-76) is occupied."""
        for i in range(74, 77):
            if i < len(block_occupancy) and block_occupancy[i]:
                return True
        return False
    
    def OPQ_occupied():
        """Check if sections O, P, Q (blocks 86-100) are occupied."""
        for i in range(86, 101):
            if i < len(block_occupancy) and block_occupancy[i]:
                return True
        return False
    
    def set_Q_hazard(truth_val):
        """Set speed hazard for section Q (blocks 98-100)."""
        for i in range(98, 101):
            if i < len(speed_hazard):
                speed_hazard[i] = truth_val
    
    def set_M_hazard(truth_val):
        """Set speed hazard for section M (blocks 74-76)."""
        for i in range(74, 77):
            if i < len(speed_hazard):
                speed_hazard[i] = truth_val
    
    def J_is_hazard():
        """Check if section J (blocks 58-62) has hazards."""
        for i in range(58, 63):
            if i < len(speed_hazard) and speed_hazard[i] == False:
                return False
        return True
    
    def set_J_hazard(truth_val):
        """Set speed hazard for section J (blocks 58-62)."""
        for i in range(58, 63):
            if i < len(speed_hazard):
                speed_hazard[i] = truth_val
        
    def reset_hazard():
        """Reset all speed hazards to False."""
        for i in range(0, len(speed_hazard)):
            speed_hazard[i] = False

    J_hazard = J_is_hazard()
    
    reset_hazard()

    # Sections I - M (blocks 36-77) - speed hazard management
    for i in range(36, 77):
        if i < len(speed_hazard):
            speed_hazard[i] = False
        if i < len(block_occupancy) and block_occupancy[i] == True:
            # trailing 4 blocks so other trains don't get too close
            for z in range(36, 77):
                if z < len(block_numbers) and block_numbers[z] == i:
                    if z < len(speed_hazard):
                        speed_hazard[z] = True

    if J_hazard == True:
        set_J_hazard(True)
    
    # Sections O - Q (blocks 86-100) - speed hazard management
    for i in range(86, 101):
        if i < len(speed_hazard):
            speed_hazard[i] = False
        if i < len(block_occupancy) and block_occupancy[i] == True:
            # trailing 4 blocks so other trains don't get too close
            for z in range(86, 101):
                if z < len(block_numbers) and block_numbers[z] == i:
                    if z < len(speed_hazard):
                        speed_hazard[z] = True

    # Sections S - U (blocks 105-117) - speed hazard management
    for i in range(105, 117):
        if i < len(speed_hazard):
            speed_hazard[i] = False
        if i < len(block_occupancy) and block_occupancy[i] == True:
            # trailing 4 blocks so other trains don't get too close
            for z in range(105, 117):
                if z < len(block_numbers) and block_numbers[z] == i:
                    if z < len(speed_hazard):
                        speed_hazard[z] = True

    # Advanced switch logic based on Excel file connections and original implementation
    
    # Switch at block 76: (76-77;77-101) and Switch at block 85: (85-86; 100-85)
    # This implements the sophisticated logic from the original PLC
    
    if N_occupied() == False and OPQ_occupied() == False:
        # Normal flow: 76-77 and 85-86
        switches[0] = False  # Block 76: 76-77 connection
        switches[1] = True   # Block 85: 85-86 connection
        traffic_lights[0] = True   # Block 76 entrance (from block 75)
        traffic_lights[1] = False  # Block 77 entrance (from block 76)
        traffic_lights[3] = True   # Block 85 entrance (from block 84)
        traffic_lights[4] = False  # Block 86 entrance (from block 85)

        set_M_hazard(False)

    elif (N_occupied() == True and not (76 < len(block_occupancy) and block_occupancy[76])) or OPQ_occupied() == True:
        # Alternate routing when section N is occupied
        switches[0] = True   # Block 76: 77-101 connection
        traffic_lights[0] = False  # Block 76 entrance (from block 75)
        traffic_lights[1] = True   # Block 77 entrance (from block 76)
        traffic_lights[2] = True   # Block 101 entrance (from block 77)
        set_M_hazard(True)

        if N_occupied() == True and not (100 < len(block_occupancy) and block_occupancy[100]):
            # Route through 100-85 connection
            switches[1] = False  # Block 85: 100-85 connection
            traffic_lights[3] = False  # Block 85 entrance (from block 84)
            traffic_lights[4] = True   # Block 86 entrance (from block 85)
            traffic_lights[5] = True   # Block 100 entrance (to block 85)

        elif N_occupied() == False:
            # Normal 85-86 connection
            switches[1] = True   # Block 85: 85-86 connection
            traffic_lights[3] = True   # Block 85 entrance (from block 84)
            traffic_lights[4] = False  # Block 86 entrance (from block 85)
            traffic_lights[5] = False  # Block 100 entrance (alternate route off)

    # Apply speed hazards to speed and authority
    speed_hazard_to_speed_authority()
    
    # Map all track objects to their physical locations
    map_track_objects()