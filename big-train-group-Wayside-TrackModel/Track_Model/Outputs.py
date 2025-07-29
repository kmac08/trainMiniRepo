def get_authority_bit():
    """
    Get the authority bit for track output
    
    Returns:
        String '0' or '1' representing authority
    """
    # Dummy value: 1 (active authority)
    return '1'

def get_commanded_speed_bits():
    """
    Get the commanded speed bits for track output
    
    Returns:
        String of 2 bits representing commanded speed
    """
    # Dummy value: 2 (binary '10'), 2 bits
    return '10'

def get_next_block_bits():
    """
    Get the next block bits for track output
    
    Returns:
        String of 7 bits representing next blocks
    """
    # Dummy value: 7 bits, e.g. 1010101
    return '1010101'

def get_update_previous_bit():
    """
    Get the update previous bit for track output
    
    Returns:
        String '0' or '1' representing whether the previous block should be updated
    """
    # Dummy value: 0 (not updating previous)
    return '0'

def get_next_station_bits():
    """
    Get the next station bits for track output
    
    Returns:
        String of 5 bits representing the next station ID
    """
    # Dummy value: 5 bits, e.g. 11010
    return '11010'

def get_16bit_track_model_output(train_id=None):
    """
    Generate a 16-bit output string for track model communication
    
    Format:
    - Authority (1 bit)
    - Commanded Speed (2 bits) 
    - Next Block #s (7 bits)
    - Update Previous Bit (1 bit)
    - Next Station # (5 bits)
    
    Args:
        train_id: Optional ID of train to generate output for
        
    Returns:
        String of 16 bits
    """
    bits = (
        get_authority_bit() +
        get_commanded_speed_bits() +
        get_next_block_bits() +
        get_update_previous_bit() +
        get_next_station_bits()
    )
    # Ensure the string is exactly 16 bits
    return bits[:16].ljust(16, '0')

def get_train_specific_output(train_id, authority, commanded_speed, next_block, update_previous, next_station):
    """
    Generate train-specific 16-bit output
    
    Args:
        train_id: ID of the train
        authority: Boolean indicating if train has authority to move
        commanded_speed: Speed value (0-3)
        next_block: Next block number (0-127)
        update_previous: Boolean indicating if previous block should be updated
        next_station: Next station ID (0-31)
        
    Returns:
        String of 16 bits
    """
    # Authority (1 bit)
    authority_bit = '1' if authority else '0'
    
    # Commanded Speed (2 bits)
    speed_bits = f"{commanded_speed & 0x03:02b}"
    
    # Next Block (7 bits)
    block_bits = f"{next_block & 0x7F:07b}"
    
    # Update Previous (1 bit)
    update_bit = '1' if update_previous else '0'
    
    # Next Station (5 bits)
    station_bits = f"{next_station & 0x1F:05b}"
    
    # Combine all bits
    output = authority_bit + speed_bits + block_bits + update_bit + station_bits
    
    return output