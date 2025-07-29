"""
Red Line PLC System
==================
PLC program for Red Line track operations including:
- Switch control for blocks 9, 15, 27, 32, 38, 43, 52
- Directional traffic management
- Speed hazard management for sections ABC and FGHIJ
- Railway crossing control at block 47
- Yard operations

Author: Systems and Project Engineering Student
"""

def main(block_occupancy, speed, authority, switches_actual, 
         traffic_lights_actual, crossings_actual, block_numbers):
    """
    Main Red Line PLC loop that manages all track operations.
    
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
    switches = [False] * 7       # Red line has 7 switches
    traffic_lights = [False] * 10
    crossings = [False] * 2

    def speed_hazard_to_speed_authority():
        """Apply speed hazards to speed and authority commands."""
        for i in range(len(speed_hazard)):
            for z in range(len(block_numbers)):
                if speed_hazard[i] == True & block_numbers[z] == i:
                    speed[i] = 0
                    authority[i] = 0
    
    def map_track_objects():
        """Map track objects to their physical locations."""
        # Map switches to their indices based on Red Line switch blocks
        switch_mapping = {
            9: 0,   # Yard switch at block 9
            15: 1,  # Block 15 ↔ Block 16; Block 1 ↔ Block 16
            27: 2,  # Block 27 ↔ Block 28; Block 27 ↔ Block 76
            32: 3,  # Block 32 ↔ Block 33; Block 33 ↔ Block 72
            38: 4,  # Block 38 ↔ Block 39; Block 38 ↔ Block 71
            43: 5,  # Block 43 ↔ Block 44; Block 44 ↔ Block 67
            52: 6   # Block 52 ↔ Block 53; Block 52 ↔ Block 66
        }
        
        # Map traffic lights to block entrances for each switch connection
        traffic_light_mapping = {
            # Switch at block 9: Yard connections
            9: 0,    # Yard entrance
            
            # Switch at block 15: Block 15 ↔ Block 16; Block 1 ↔ Block 16
            15: 1,   # Entrance to block 15
            16: 2,   # Entrance to block 16 from block 15
            1: 3,    # Entrance to block 1
            
            # Switch at block 27: Block 27 ↔ Block 28; Block 27 ↔ Block 76
            27: 4,   # Entrance to block 27
            28: 5,   # Entrance to block 28 from block 27
            76: 6,   # Entrance to block 76 from block 27
            
            # Additional traffic lights for other switches
            32: 7,   # Switch at block 32
            38: 8,   # Switch at block 38
            43: 9    # Switch at block 43
        }
        
        # Map crossings to their indices
        crossing_mapping = {
            47: 0  # RAILWAY CROSSING at block 47 maps to crossings[0]
        }
        
        # Apply mappings based on block_numbers array
        for i in range(len(block_numbers)):
            block_num = i
            
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
            if block_occupancy[i] == True:
                return True
        return False
    
    def ABC_occupied():
        """Check if sections A, B, C (blocks 1-9) are occupied."""
        for i in range(1, 10):
            if block_occupancy[i] == True:
                return True
        return False
    
    def set_N_speed_hazard(truth_value):
        """Set speed hazard for section N (blocks 64-66)."""
        for i in range(64, 67):
            if i < len(speed_hazard):
                speed_hazard[i] = truth_value

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
    switches[1] = True
    up_through_H = False
    
    # Reset all hazards
    reset_hazard()

    # Determine direction based on train positions
    if block_occupancy[16] == True and not block_occupancy[17]:
        up_through_H = False
    
    if block_occupancy[52] == True and not block_occupancy[51]:
        up_through_H = True

    # Set switches and traffic lights based on direction
    if up_through_H == True:
        switches[2] = True   # Block 27 switch
        switches[3] = False  # Block 32 switch
        switches[4] = True   # Block 38 switch
        switches[5] = False  # Block 43 switch

        traffic_lights[5] = True
        traffic_lights[6] = False
        traffic_lights[7] = True
        traffic_lights[8] = False
        traffic_lights[9] = False
    else:
        switches[2] = False  # Block 27 switch
        switches[3] = True   # Block 32 switch
        switches[4] = False  # Block 38 switch
        switches[5] = True   # Block 43 switch

        traffic_lights[5] = False
        traffic_lights[6] = True
        traffic_lights[7] = False
        traffic_lights[8] = True
        traffic_lights[9] = True

    # Set speed hazards based on direction and occupancy
    if up_through_H == False:
        # sections FGHIJ - trailing hazards
        for i in range(20, 53):
            if block_occupancy[i] == True:
                for j in range(1, 5):
                    if (i - j) >= 0 and (i - j) < len(speed_hazard):
                        speed_hazard[i - j] = True
    else:
        # sections FGHIJ - leading hazards
        for i in range(20, 53):
            if block_occupancy[i] == True:
                for j in range(1, 5):
                    if (i + j) < len(speed_hazard):
                        speed_hazard[i + j] = True

    # Yard control - only let train out of yard if clear
    if FGHIJ_occupied() == True or ABC_occupied() == True:
        speed_hazard[0] = True
    else:
        speed_hazard[0] = False

    # Section management - prioritize trains in sections ABC
    if FGHIJ_occupied() == False:
        switches[6] = True  # Block 52 switch
        set_A_speed_hazard(False)

        if ABC_occupied() == True:
            set_N_speed_hazard(True)
        else:
            set_N_speed_hazard(False)
    # Do not let other trains go on to the section
    elif FGHIJ_occupied() == True and not block_occupancy[66] and not block_occupancy[1]:
        switches[6] = False  # Block 52 switch
        switches[1] = True   # Block 15 switch
        set_A_speed_hazard(True)
        set_N_speed_hazard(True)

    # Railway crossing control at block 47
    crossings[0] = False  # Default is up
    for i in range(0, 3):
        if ((47 - i) >= 0 and block_occupancy[47 - i]) or ((47 + i) < len(block_occupancy) and block_occupancy[47 + i]):
            crossings[0] = True  # Put the crossing down
            break

    # Apply speed hazards to speed and authority
    speed_hazard_to_speed_authority()
    
    # Map all track objects to their physical locations
    map_track_objects()