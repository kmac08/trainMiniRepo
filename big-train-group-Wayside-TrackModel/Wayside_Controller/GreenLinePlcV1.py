"""
Simple Pass-through PLC Program
===============================
This PLC automatically passes CTC suggestions directly to outputs:
- commandedSpeed = suggestedSpeed
- commandedAuthority = suggestedAuthority

Author: Systems and Project Engineering Student
"""

def main( block_occupancy, speed, authority, switches_actual, 
         traffic_lights_actual, crossings_actual, block_numbers):
    """
    Main PLC loop that passes CTC suggestions directly to outputs.
    """
    speed_hazard = [False] * 151  # Initialize speed hazard list for all blocks
    switches = [False] * 6
    traffic_lights = [False] * 14  # Updated to handle all switch entrance lights
    crossings = [False] * 1

    def speed_hazard_to_speed_authority():
        for i in range(len(speed_hazard)):
            for z in range(len(block_numbers)):
                if speed_hazard[i]== True & block_numbers[z] == i:
                    speed[i] = 0
                    authority[i] = 0
    
    def map_track_objects():
        # Map switches to their indices based on the correct switch blocks from Track Reader
        switch_mapping = {
            12: 0,  # Switch at block 12
            29: 1,  # Switch at block 29
            58: 2,  # Switch at block 58 (yard connection)
            62: 3,  # Switch at block 62 (yard connection)
            76: 4,  # Switch at block 76 (used in main logic)
            85: 5   # Switch at block 85 (used in main logic)
        }
        
        # Map traffic lights to block entrances for each switch connection
        traffic_light_mapping = {
            # Switch at block 12: Block 12 ↔ Block 13; Block 1 ↔ Block 13
            12: 0,   # Entrance to block 12 from block 11
            13: 1,   # Entrance to block 13 from block 12
            1: 2,    # Entrance to block 1 from block 2
            
            # Switch at block 29: Block 29 ↔ Block 30; Block 29 ↔ Block 150
            29: 3,   # Entrance to block 29 from block 28
            30: 4,   # Entrance to block 30 from block 29
            150: 5,  # Entrance to block 150 from block 29
            
            # Switch at block 58: Block 57 → Yard (block 0)
            58: 6,   # Entrance to yard switch at block 58 from block 57
            
            # Switch at block 62: Yard ← Block 63 (yard to block 62)
            62: 7,   # Entrance to block 62 from yard
            
            # Switch at block 76: Block 76 ↔ Block 77; Block 77 ↔ Block 101
            76: 8,   # Entrance to block 76 from block 75 - used in main logic
            77: 9,   # Entrance to block 77 from block 76 - used in main logic
            101: 10, # Entrance to block 101 from block 77
            
            # Switch at block 85: Block 85 ↔ Block 86; Block 100 ↔ Block 85
            85: 11,  # Entrance to block 85 from block 84 - used in main logic
            86: 12,  # Entrance to block 86 from block 85 - used in main logic
            100: 13  # Entrance to block 100 from block 85
        }
        
        # Map crossings to their indices
        crossing_mapping = {
            19: 0  # RAILWAY CROSSING at block 19 maps to crossings[0]
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


    def N_occupied():
        for i in range(77, 86):
            if block_occupancy[i]:
                return True
        return False
    
    def Q_occupied():
        for i in range(98, 101):
            if block_occupancy[i]:
                return True
        return False
    
    def M_occupied():
        for i in range(74, 77):
            if block_occupancy[i]:
                return True
        return False
    
    def OPQ_occupied():
        for i in range(86, 101):
            if block_occupancy[i]:
                return True
        return False
    
    def set_Q_hazard(truth_val):
        for i in range(98, 101):
            speed_hazard[i] = truth_val
    
    def set_M_hazard(truth_val):
        for i in range(74, 77):
            speed_hazard[i] = truth_val
    
    def J_is_hazard():
        for i in range(58, 63):
            if speed_hazard[i] == False:
                return False
        return True
    
    def set_J_hazard(truth_val):
        for i in range(58, 63):
            speed_hazard[i] = truth_val
        
    def reset_hazard():
        for i in range(0, len(speed_hazard)):
            speed_hazard[i] = False

    J_hazard = J_is_hazard()
    
    reset_hazard()

    # Sections I - M
    for i in range(36, 77):
        speed_hazard[i] = False
        if block_occupancy[i]== True:
            # trailing 4 blocks so other trains don't get too close
            for z in range(36,77):
                if block_numbers[z] == i:
                    speed_hazard[z] = True

    if J_hazard == True:
        set_J_hazard(True)
    
    # Sections O - Q
    for i in range(86, 101):
        speed_hazard[i] = False
        if block_occupancy[i]== True:
            # trailing 4 blocks so other trains don't get too close
            for z in range(86,101):
                if block_numbers[z] == i:
                    speed_hazard[z] = True
        

    # Sections S -  U
    for i in range(105, 117):
        speed_hazard[i] = False
        if block_occupancy[i]== True:
            # trailing 4 blocks so other trains don't get too close
            for z in range(105,117):
                if block_numbers[z] == i:
                    speed_hazard[z] = True
            
        
    
    if N_occupied() == False and OPQ_occupied() == False:
        switches[4] = False
        switches[5] = True
        traffic_lights[8] = True   # Block 76 entrance (from block 75)
        traffic_lights[9] = False  # Block 77 entrance (from block 76)
        traffic_lights[11] = True  # Block 85 entrance (from block 84)
        traffic_lights[12] = False # Block 86 entrance (from block 85)

        # set_Q_hazard(False)
        set_M_hazard(False)

        # if trains are at both ends of section N, give priority over trains at section M
        # if Q_occupied() and M_occupied():
        #     set_Q_hazard(True) # stops trains at Q

    elif (N_occupied() == True and not block_occupancy[76]) or OPQ_occupied() == True:
        switches[4] = True
        traffic_lights[8] = False  # Block 76 entrance (from block 75)
        traffic_lights[9] = True   # Block 77 entrance (from block 76)
        set_M_hazard(True)

        if N_occupied() == True and not block_occupancy[100]:
            switches[5] = False
            traffic_lights[11] = False # Block 85 entrance (from block 84)
            traffic_lights[12] = True  # Block 86 entrance (from block 85)

            # stop other trains from entering section N
            # set_Q_hazard(True)
        elif N_occupied() == False:
            switches[5] = True
            traffic_lights[11] = True  # Block 85 entrance (from block 84)
            traffic_lights[12] = False # Block 86 entrance (from block 85)


    # check 3 blocks behind crossing and block of crossing (4 total blocks)
    crossings[0] = False # Default is up
    for i in range(4):
        if block_occupancy[19 - i]: # block 19 is the railroad crossing
            crossings[0] = True # Put the crossing down

    speed_hazard_to_speed_authority()
    map_track_objects()
        

            

    

