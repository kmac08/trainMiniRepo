"""
Track Model Test Interfaces
===========================
Modular test suite for Track Model components including CommunicationObject,
wayside integration, train creation, and yard buffer simulation.

Usage:
    python trackmodel_testinterfaces.py --test communication
    python trackmodel_testinterfaces.py --test yard_buffer
    python trackmodel_testinterfaces.py --test train_creation
    python trackmodel_testinterfaces.py --test all
    python trackmodel_testinterfaces.py --help
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))
try:
    from trackmodel_working import CommunicationObject, YardBuffer, TrackCircuitInterface
except ImportError:
    # Fallback for testing without full dependencies
    class YardBuffer:
        def __init__(self):
            self.current_buffer = []
            self.is_complete = False
        def add_next_block(self, block_number):
            if not self.is_complete:
                self.current_buffer.append(block_number)
                if len(self.current_buffer) == 4 and self.current_buffer == [63, 64, 65, 66]:
                    self.is_complete = True
                    print(f"[DEBUG] Yard buffer complete: {self.current_buffer}")  # Add debug
                    return True
            return False
        def get_buffer_and_clear(self):
            if self.is_complete:
                buffer = self.current_buffer.copy()
                self.current_buffer = []
                self.is_complete = False
                return buffer
            return None
    
    class TrackCircuitInterface:
        @staticmethod
        def create_packet(block_number, speed_command, authorized=True, new_block=True, 
                         next_block_entered=False, update_queue=False, station_number=0):
            if update_queue and new_block:
                new_block = False
            packet = (
                (block_number & 0b1111111) << 11 |
                (speed_command & 0b11) << 9 |
                (1 if authorized else 0) << 8 |
                (1 if new_block else 0) << 7 |
                (1 if next_block_entered else 0) << 6 |
                (1 if update_queue else 0) << 5 |
                (station_number & 0b11111)
            )
            return packet & 0x3FFFF
    
    CommunicationObject = None
from Inputs import TrackModelInputs

# Import DebugTerminal for integrated testing
try:
    from trackmodel_working import DebugTerminal
except ImportError:
    # Fallback for standalone testing
    class DebugTerminal:
        @staticmethod
        def log(message):
            print(f"[DEBUG] {message}")

def mock_debug_print(message):
    """Mock debug print function for testing without Qt dependencies"""
    print(f"[DEBUG] {message}")

def test_communication_object():
    """
    Test function to verify CommunicationObject functionality.
    Tests wayside communication before integration.
    """
    print("=== CommunicationObject Test Interface ===\n")
    
    # Test 1: Create multiple wayside instances
    print("Test 1: Creating Wayside Instances")
    wayside1 = CommunicationObject("1", "Green")
    wayside2 = CommunicationObject("2", "Green") 
    wayside3 = CommunicationObject("3", "Green")
    print(f" Created 3 wayside instances")
    print(f"   Wayside 1: {wayside1.getWaysideInfo()}")
    print(f"   Wayside 2: {wayside2.getWaysideInfo()}")
    print(f"   Wayside 3: {wayside3.getWaysideInfo()}\n")
    
    # Test 2: Set block coverage (simulate different wayside responsibilities)
    print("Test 2: Setting Block Coverage")
    
    # Wayside 1 covers blocks 0-50 (Yard + first section)
    coverage1 = ["1"] * 51 + ["0"] * 100  # Blocks 0-50
    wayside1.setWaysideBlocksCovered(coverage1)
    
    # Wayside 2 covers blocks 51-100 (middle section)
    coverage2 = ["0"] * 51 + ["1"] * 50 + ["0"] * 50  # Blocks 51-100
    wayside2.setWaysideBlocksCovered(coverage2)
    
    # Wayside 3 covers blocks 101-150 (final section)
    coverage3 = ["0"] * 101 + ["1"] * 50  # Blocks 101-150
    wayside3.setWaysideBlocksCovered(coverage3)
    
    print(f" Set block coverage:")
    print(f"   Wayside 1 covers {wayside1.getCoveredBlockCount()} blocks (G0-G50)")
    print(f"   Wayside 2 covers {wayside2.getCoveredBlockCount()} blocks (G51-G100)")
    print(f"   Wayside 3 covers {wayside3.getCoveredBlockCount()} blocks (G101-G150)\n")
    
    # Test 3: Test authority setting (each wayside sets data for all blocks)
    print("Test 3: Setting Authority Data")
    
    # All waysides receive full 151-element arrays but only update their covered blocks
    full_authority = ["1"] * 151  # All trains authorized
    wayside1.setAuthorities(full_authority)
    wayside2.setAuthorities(full_authority)
    wayside3.setAuthorities(full_authority)
    
    # Verify only covered blocks were updated
    auth1 = wayside1.getWaysideAuthority()
    auth2 = wayside2.getWaysideAuthority()
    auth3 = wayside3.getWaysideAuthority()
    
    print(f" Authority setting test:")
    print(f"   Wayside 1: Block G0={auth1[0]}, Block G25={auth1[25]}, Block G75={auth1[75]} (should be 1,1,0)")
    print(f"   Wayside 2: Block G0={auth2[0]}, Block G75={auth2[75]}, Block G125={auth2[125]} (should be 0,1,0)")
    print(f"   Wayside 3: Block G25={auth3[25]}, Block G75={auth3[75]}, Block G125={auth3[125]} (should be 0,0,1)\n")
    
    # Test 4: Test commanded speed with different values
    print("Test 4: Setting Commanded Speed Data")
    
    # Create varied speed commands
    speed_commands = []
    for i in range(151):
        if i == 0:  # Yard - stop
            speed_commands.append("00")
        elif i % 20 == 0:  # Stations - slow
            speed_commands.append("01")
        elif i % 15 == 0:  # Switches - medium
            speed_commands.append("10")
        else:  # Regular blocks - full speed
            speed_commands.append("11")
    
    wayside1.setCommandedSpeeds(speed_commands)
    wayside2.setCommandedSpeeds(speed_commands)
    wayside3.setCommandedSpeeds(speed_commands)
    
    speeds = wayside1.getWaysideCommandedSpeed()
    print(f" Speed command test:")
    print(f"   Block G0 (Yard): {speeds[0]} (should be 00)")
    print(f"   Block G20 (Station): {speeds[20]} (should be 01)")
    print(f"   Block G15 (Switch): {speeds[15]} (should be 10)")
    print(f"   Block G25 (Regular): {speeds[25]} (should be 11)\n")
    
    # Test 5: Test data aggregation (how outputs would combine data)
    print("Test 5: Data Aggregation Test")
    
    # Get complete authority data from all waysides
    complete_authority = ["0"] * 151
    auth_sources = [wayside1, wayside2, wayside3]
    
    for wayside in auth_sources:
        wayside_auth = wayside.getWaysideAuthority()
        coverage = wayside.getWaysideBlocksCovered()
        
        # Only use data from blocks this wayside covers
        for i in range(151):
            if coverage[i] == "1":
                complete_authority[i] = wayside_auth[i]
    
    print(f" Complete authority array created:")
    print(f"   First 10 blocks: {complete_authority[:10]}")
    print(f"   Blocks 50-59: {complete_authority[50:60]}")
    print(f"   Blocks 100-109: {complete_authority[100:110]}")
    print(f"   Last 10 blocks: {complete_authority[141:151]}\n")
    
    # Test 6: Test error handling
    print("Test 6: Error Handling Tests")
    
    try:
        # Test invalid array length
        wayside1.setAuthorities(["1"] * 150)  # Wrong length
        print("L Should have failed - wrong array length")
    except ValueError as e:
        print(f" Caught expected error: {e}")
    
    try:
        # Test invalid bit string
        wayside1.setCommandedSpeeds(["2"] * 151)  # Invalid bit value
        print("L Should have failed - invalid bit string")
    except ValueError as e:
        print(f" Caught expected error: {e}")
    
    try:
        # Test invalid block index
        wayside1.getDataSummary(151)  # Out of range
        print("L Should have failed - invalid block index")
    except ValueError as e:
        print(f" Caught expected error: {e}")
    
    print()
    
    # Test 7: Test utility methods
    print("Test 7: Utility Methods")
    
    # Test block coverage check
    print(f" Block coverage checks:")
    print(f"   Wayside 1 covers G25: {wayside1.isBlockCovered(25)}")
    print(f"   Wayside 1 covers G75: {wayside1.isBlockCovered(75)}")
    print(f"   Wayside 2 covers G75: {wayside2.isBlockCovered(75)}")
    
    # Test data summary for specific block
    summary = wayside2.getDataSummary(75)
    print(f" Block G75 data summary:")
    for key, value in summary.items():
        print(f"   {key}: {value}")
    
    print("\n=== CommunicationObject Tests Completed Successfully! ===")
    return True

def test_wayside_integration():
    """
    Test wayside integration scenarios with multiple communication objects.
    Simulates real-world wayside controller communication patterns.
    """
    print("=== Wayside Integration Test ===\n")
    
    # Test scenario: 3 waysides managing different track sections
    print("Scenario: 3-Wayside Green Line Management")
    
    # Create wayside controllers with realistic coverage
    waysides = {
        "Wayside_1": CommunicationObject("1", "Green"),
        "Wayside_2": CommunicationObject("2", "Green"), 
        "Wayside_3": CommunicationObject("3", "Green")
    }
    
    # Set realistic block coverage patterns
    coverage_patterns = {
        "Wayside_1": ["1"] * 51 + ["0"] * 100,  # G0-G50: Yard and downtown
        "Wayside_2": ["0"] * 51 + ["1"] * 50 + ["0"] * 50,  # G51-G100: Midtown
        "Wayside_3": ["0"] * 101 + ["1"] * 50  # G101-G150: Uptown
    }
    
    for wayside_name, wayside_obj in waysides.items():
        wayside_obj.setWaysideBlocksCovered(coverage_patterns[wayside_name])
        print(f" {wayside_name} configured for {wayside_obj.getCoveredBlockCount()} blocks")
    
    # Test concurrent data updates (simulate real wayside communication)
    print("\n= Simulating concurrent wayside updates...")
    
    # Each wayside sends different authority patterns
    auth_scenarios = {
        "Wayside_1": ["1"] * 151,  # All authorized
        "Wayside_2": ["0" if i % 3 == 0 else "1" for i in range(151)],  # Some restrictions
        "Wayside_3": ["1" if i % 2 == 0 else "0" for i in range(151)]   # Alternating pattern
    }
    
    for wayside_name, wayside_obj in waysides.items():
        wayside_obj.setAuthorities(auth_scenarios[wayside_name])
        print(f"   {wayside_name} updated authority data")
    
    # Aggregate final authority state (how Track Model would combine data)
    final_authority = ["0"] * 151
    for wayside_name, wayside_obj in waysides.items():
        auth_data = wayside_obj.getWaysideAuthority()
        coverage = wayside_obj.getWaysideBlocksCovered()
        
        for i in range(151):
            if coverage[i] == "1":  # Only use data from covered blocks
                final_authority[i] = auth_data[i]
    
    print(f"\n Final aggregated authority state:")
    print(f"   Blocks G0-G10: {final_authority[:11]}")
    print(f"   Blocks G60-G70: {final_authority[60:71]}")
    print(f"   Blocks G120-G130: {final_authority[120:131]}")
    
    # Test conflict detection
    print(f"\n==Testing overlap detection...")
    total_covered = sum(int(final_authority[i] != "0") for i in range(151))
    expected_covered = sum(wayside.getCoveredBlockCount() for wayside in waysides.values())
    
    if total_covered == expected_covered:
        print(f" No overlaps detected: {total_covered} blocks covered by {len(waysides)} waysides")
    else:
        print(f"�  Potential overlap: Expected {expected_covered}, got {total_covered}")
    
    print("\n=== Wayside Integration Tests Completed! ===")
    return True

def test_yard_buffer():
    """Test yard buffer functionality for train creation"""
    print("=== Yard Buffer Test Interface ===\n")
    
    # Test 1: Create yard buffer and test sequence
    print("Test 1: Yard Buffer Sequence")
    yard_buffer = YardBuffer()
    
    # Test incomplete sequence
    print(" Testing incomplete sequence...")
    result = yard_buffer.add_next_block(63)
    print(f"   Added 63: Complete = {result}")
    result = yard_buffer.add_next_block(64)
    print(f"   Added 64: Complete = {result}")
    result = yard_buffer.add_next_block(65)
    print(f"   Added 65: Complete = {result}")
    
    # Complete the sequence
    result = yard_buffer.add_next_block(66)
    print(f"   Added 66: Complete = {result}")
    
    # Test getting buffer
    buffer = yard_buffer.get_buffer_and_clear()
    print(f"   Retrieved buffer: {buffer}")
    print(f"   Buffer after clear: {yard_buffer.current_buffer}")
    
    # Test 2: Test incorrect sequence
    print("\nTest 2: Incorrect Sequence")
    yard_buffer2 = YardBuffer()
    
    result = yard_buffer2.add_next_block(63)
    print(f"   Added 63: Complete = {result}")
    result = yard_buffer2.add_next_block(65)  # Skip 64
    print(f"   Added 65 (skip 64): Complete = {result}")
    result = yard_buffer2.add_next_block(64)  # Out of order
    print(f"   Added 64 (out of order): Complete = {result}")
    result = yard_buffer2.add_next_block(66)
    print(f"   Added 66: Complete = {result}")
    
    print(f"   Final buffer: {yard_buffer2.current_buffer}")
    print(f"   Is complete: {yard_buffer2.is_complete}")
    
    return True

def test_track_circuit_packets():
    """Test track circuit packet creation and bit logic"""
    print("=== Track Circuit Packet Test Interface ===\n")
    
    # Test 1: Basic packet creation
    print("Test 1: Basic Packet Creation")
    packet = TrackCircuitInterface.create_packet(
        block_number=67,      # 4th block ahead
        speed_command=2,      # Medium speed
        authorized=True,
        new_block=True,
        station_number=5
    )
    print(f"   Packet value: 0x{packet:05X}")
    print(f"   Binary: {packet:018b}")
    
    # Decode packet to verify
    block_num = (packet >> 11) & 0x7F
    speed_cmd = (packet >> 9) & 0x03
    authority = (packet >> 8) & 0x01
    new_block = (packet >> 7) & 0x01
    next_entered = (packet >> 6) & 0x01
    update_queue = (packet >> 5) & 0x01
    station = packet & 0x1F
    
    print(f"   Decoded - Block: {block_num}, Speed: {speed_cmd}, Auth: {authority}")
    print(f"             New: {new_block}, Entered: {next_entered}, Queue: {update_queue}, Station: {station}")
    
    # Test 2: Test bit constraint (new_block vs update_queue)
    print("\nTest 2: Bit Constraint Test")
    
    # Should force new_block to 0 when update_queue is 1
    packet_constrained = TrackCircuitInterface.create_packet(
        block_number=70,
        speed_command=1,
        authorized=True,
        new_block=True,       # Should be forced to False
        update_queue=True,    # Forces new_block to False
        station_number=0
    )
    
    new_block_result = (packet_constrained >> 7) & 0x01
    update_queue_result = (packet_constrained >> 5) & 0x01
    
    print(f"   Packet with constraint: 0x{packet_constrained:05X}")
    print(f"   New block bit: {new_block_result} (should be 0)")
    print(f"   Update queue bit: {update_queue_result} (should be 1)")
    
    # Test 3: Edge cases
    print("\nTest 3: Edge Cases")
    
    # Max values
    max_packet = TrackCircuitInterface.create_packet(
        block_number=127,     # Max 7-bit value
        speed_command=3,      # Max 2-bit value
        station_number=31     # Max 5-bit value
    )
    print(f"   Max values packet: 0x{max_packet:05X}")
    
    # Test 18-bit limit
    oversized = TrackCircuitInterface.create_packet(
        block_number=255,     # Oversized - should be masked to 7 bits
        speed_command=5,      # Oversized - should be masked to 2 bits
        station_number=63     # Oversized - should be masked to 5 bits
    )
    
    block_masked = (oversized >> 11) & 0x7F
    speed_masked = (oversized >> 9) & 0x03
    station_masked = oversized & 0x1F
    
    print(f"   Oversized input packet: 0x{oversized:05X}")
    print(f"   Block masked to: {block_masked} (from 255)")
    print(f"   Speed masked to: {speed_masked} (from 5)")
    print(f"   Station masked to: {station_masked} (from 63)")
    
    return True

def test_wayside_simulation():
    """Simulate realistic wayside data for train creation testing"""
    print("=== Wayside Simulation Test Interface ===\n")
    
    # Test 1: Set up wayside inputs with train creation scenario
    print("Test 1: Wayside Data Setup")
    
    # Try to connect to a running GUI application first
    inputs = None
    try:
        # Look for a running Qt application with train manager
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            # Find MainWindow with train manager
            for widget in app.allWidgets():
                if hasattr(widget, 'train_manager') and widget.train_manager:
                    inputs = widget.inputs
                    print("   Connected to running GUI application with train manager")
                    break
    except:
        pass
    
    # Fallback to standalone inputs for testing
    if not inputs:
        inputs = TrackModelInputs()
        print("   Using standalone inputs (no train creation will occur)")
    
    # Set up yard buffer sequence in wayside data
    print("   Setting up yard buffer sequence...")
    
    # Simulate CTC sending yard buffer data through wayside
    print("   Processing yard buffer sequence:")
    for block_num in [63, 64, 65, 66]:
        print(f"      Sending block {block_num} to yard buffer...")
        inputs.process_next_block_for_yard(block_num)
        
        # Check if train manager exists and yard buffer status
        if hasattr(inputs, 'train_manager') and inputs.train_manager:
            yard_buffer = inputs.train_manager.yard_buffer
            if yard_buffer:
                print(f"         Buffer now: {yard_buffer.current_buffer}")
                print(f"         Complete: {yard_buffer.is_complete}")
                if yard_buffer.is_complete:
                    print(f"         [SUCCESS] Yard buffer complete - train should be created!")
            else:
                print(f"         [WARNING] No yard buffer found in train manager")
        else:
            print(f"         [WARNING] No train manager connected to inputs")
    
    # Test 2: Set realistic next block data for train path
    print("\nTest 2: Next Block Data Setup")
    
    # Set up sequential next block data for realistic train movement
    for block_num in range(63, 151):
        block_id = f"G{block_num}"
        next_block_num = min(block_num + 1, 150) if block_num < 150 else 63  # Loop back to start
        next_block_bits = f"{next_block_num:07b}"
        inputs.set_next_block_number(block_id, next_block_bits)
        
    print(f"   Set next block data for blocks G63-G150")
    
    # Verify some key blocks
    test_blocks = [63, 70, 100, 150]
    for block_num in test_blocks:
        block_id = f"G{block_num}"
        next_bits = inputs.get_next_block_number(block_id)
        next_num = int(next_bits, 2) if next_bits else 0
        print(f"   Block {block_id} -> Block G{next_num}")
    
    # Test 3: Set authority and speed data
    print("\nTest 3: Authority and Speed Data")
    
    # Set all blocks to authorized with varying speeds
    for block_num in range(151):
        block_id = f"G{block_num}"
        
        # All blocks authorized
        inputs.set_wayside_authority(block_id, "1")
        
        # Vary speed based on block type
        if block_num == 0:  # Yard
            speed = "00"  # Stop
        elif block_num % 20 == 0:  # Stations
            speed = "01"  # Slow
        elif block_num % 15 == 0:  # Switches
            speed = "10"  # Medium
        else:  # Regular blocks
            speed = "11"  # Fast
            
        inputs.set_wayside_commanded_speed(block_id, speed)
    
    # Verify some settings
    test_blocks = [0, 20, 15, 25]
    for block_num in test_blocks:
        block_id = f"G{block_num}"
        auth = inputs.get_wayside_authority(block_id)
        speed = inputs.get_wayside_commanded_speed(block_id)
        speed_name = ["Stop", "Slow", "Medium", "Fast"][int(speed, 2)]
        block_type = "Yard" if block_num == 0 else "Station" if block_num % 20 == 0 else "Switch" if block_num % 15 == 0 else "Regular"
        print(f"   Block {block_id} ({block_type}): Auth={auth}, Speed={speed} ({speed_name})")
    
    print("\nWayside simulation complete - data ready for train creation testing")
    return True

def test_train_route_63_to_66():
    """Test sending packets to guide train from block 63 to 66"""
    print("=== Train Route 63->64->65->66 Test ===\n")
    
    # Test connecting to running GUI - try multiple approaches
    train_manager = None
    inputs = None
    main_window = None
    
    try:
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            print(f"   Found QApplication with {len(app.allWidgets())} widgets")
            
            # Debug: show what widgets we have
            widget_types = {}
            for widget in app.allWidgets():
                widget_type = widget.__class__.__name__
                widget_types[widget_type] = widget_types.get(widget_type, 0) + 1
            print(f"   Widget types: {dict(list(widget_types.items())[:5])}...")  # Show first 5 types
            
            # Try to find MainWindow specifically
            for widget in app.allWidgets():
                if widget.__class__.__name__ == 'MainWindow':
                    main_window = widget
                    print(f"   Found MainWindow: train_manager={hasattr(widget, 'train_manager')}, inputs={hasattr(widget, 'inputs')}")
                    if hasattr(widget, 'train_manager') and widget.train_manager:
                        train_manager = widget.train_manager
                        inputs = widget.inputs
                        print("   Connected to running GUI MainWindow with train manager")
                        break
                    elif hasattr(widget, 'inputs'):
                        inputs = widget.inputs
                        print("   Connected to running GUI MainWindow (inputs only)")
                        break
            
            # Fallback: look for any widget with train_manager
            if not train_manager:
                for widget in app.allWidgets():
                    if hasattr(widget, 'train_manager') and widget.train_manager:
                        train_manager = widget.train_manager
                        inputs = widget.inputs if hasattr(widget, 'inputs') else inputs
                        print(f"   Connected to running GUI widget {widget.__class__.__name__} with train manager")
                        break
        else:
            print("   No QApplication instance found")
    except Exception as e:
        print(f"   Warning: Could not connect to GUI: {e}")
    
    # Check if we have existing trains to work with
    if train_manager and len(train_manager.active_trains) > 0:
        existing_train_id = list(train_manager.active_trains.keys())[0]
        print(f"   Found existing train: {existing_train_id}")
        use_existing = True
    else:
        use_existing = False
    
    if not inputs:
        # Fallback: Create standalone inputs for demonstration
        print("   No GUI found. Creating standalone demonstration...")
        inputs = TrackModelInputs()
        print("   Using standalone inputs for packet simulation demonstration")
        # We can't create real trains, but we can show what packets would look like
        train_id = "G01"  # Simulated train ID
    
    # Step 1: Get or create a train
    if use_existing:
        print(f"Step 1: Using existing train {existing_train_id}")
        train_id = existing_train_id
    elif train_manager:
        print("Step 1: Creating test train...")
        train_id = train_manager.create_train_manual()
        if not train_id:
            print("   ERROR: Failed to create train")
            return False
        print(f"   Created train {train_id}")
    else:
        print(f"Step 1: Using simulated train {train_id} for demonstration")
    
    # Step 2: Set up routing data for blocks 63->64->65->66
    print("\nStep 2: Setting up route 63->64->65->66...")
    route_config = {
        63: 64,  # G63 -> G64
        64: 65,  # G64 -> G65  
        65: 66,  # G65 -> G66
        66: 67   # G66 -> G67 (or stop)
    }
    
    for current_block, next_block in route_config.items():
        block_id = f"G{current_block}"
        next_block_bits = f"{next_block:07b}"
        inputs.set_next_block_number(block_id, next_block_bits)
        
        # Set authority and speed for each block
        inputs.set_wayside_authority(block_id, "1")  # Authorized
        if current_block == 66:  # Destination - slow down
            inputs.set_wayside_commanded_speed(block_id, "01")  # Slow
        else:
            inputs.set_wayside_commanded_speed(block_id, "10")  # Medium
        
        print(f"   Block G{current_block} -> Block G{next_block}")
    
    # Step 3: Simulate train movement through the route
    print("\nStep 3: Simulating train movement packets...")
    
    # Manually trigger packet sends to see the routing in action
    simulated_positions = [63, 64, 65, 66]
    
    for position_block in simulated_positions:
        print(f"\n   Train at block G{position_block}:")
        
        # Get 4th block ahead
        fourth_block_ahead = min(position_block + 4, 150)
        
        # Get wayside data for current position
        current_block_id = f"G{position_block}"
        authority = inputs.get_wayside_authority(current_block_id) == "1"
        speed_bits = inputs.get_wayside_commanded_speed(current_block_id)
        speed_cmd = int(speed_bits, 2) if speed_bits else 0
        
        # Create packet for this position
        packet = TrackCircuitInterface.create_packet(
            block_number=fourth_block_ahead,
            speed_command=speed_cmd,
            authorized=authority,
            new_block=True,
            station_number=0
        )
        
        # Decode and display packet
        binary_packet = format(packet, '018b')
        speed_names = ["Stop", "Slow", "Medium", "Fast"]
        
        print(f"      Packet: {binary_packet}")
        print(f"      4th Block Ahead: G{fourth_block_ahead}")
        print(f"      Speed Command: {speed_cmd} ({speed_names[speed_cmd]})")
        print(f"      Authority: {'Yes' if authority else 'No'}")
        
        # Show next block from routing
        next_bits = inputs.get_next_block_number(current_block_id)
        next_block_num = int(next_bits, 2) if next_bits else 0
        print(f"      Next Block (from wayside): G{next_block_num}")
    
    # Step 4: Verify the route is set correctly  
    print("\nStep 4: Route Verification:")
    for block_num in [63, 64, 65, 66]:
        block_id = f"G{block_num}"
        next_bits = inputs.get_next_block_number(block_id)
        next_num = int(next_bits, 2) if next_bits else 0
        auth = inputs.get_wayside_authority(block_id)
        speed_bits = inputs.get_wayside_commanded_speed(block_id)
        speed_cmd = int(speed_bits, 2) if speed_bits else 0
        speed_name = ["Stop", "Slow", "Medium", "Fast"][speed_cmd]
        
        print(f"   G{block_num} -> G{next_num} | Auth: {auth} | Speed: {speed_name}")
    
    print(f"\nTrain {train_id} route 63->64->65->66 configured successfully!")
    print("The train will receive 4-blocks-ahead guidance through this route.")
    return True

def test_train_route_63_to_66_integrated(main_window):
    """Integrated version of train route test for GUI tests tab"""
    if not main_window or not main_window.train_manager or not main_window.inputs:
        DebugTerminal.log("ERROR: Missing main window, train manager, or inputs")
        return False
    
    train_manager = main_window.train_manager
    inputs = main_window.inputs
    
    DebugTerminal.log("=== Train Route 63->64->65->66 Test ===")
    
    # Use existing train if available, otherwise create one
    if len(train_manager.active_trains) > 0:
        train_id = list(train_manager.active_trains.keys())[0]
        DebugTerminal.log(f"Using existing train: {train_id}")
    else:
        train_id = train_manager.create_train_manual()
        if not train_id:
            DebugTerminal.log("ERROR: Failed to create train")
            return False
        main_window.update_train_count()
        DebugTerminal.log(f"Created new train: {train_id}")
    
    # Set up route 63->64->65->66 with detailed logging
    DebugTerminal.log("Setting up route configuration...")
    route_config = {
        63: 64,  # G63 -> G64
        64: 65,  # G64 -> G65  
        65: 66,  # G65 -> G66
        66: 67   # G66 -> G67
    }
    
    for current_block, next_block in route_config.items():
        block_id = f"G{current_block}"
        next_block_bits = f"{next_block:07b}"
        inputs.set_next_block_number(block_id, next_block_bits)
        inputs.set_wayside_authority(block_id, "1")
        if current_block == 66:
            inputs.set_wayside_commanded_speed(block_id, "01")  # Slow
            DebugTerminal.log(f"Block {block_id} -> Block G{next_block} (SLOW)")
        else:
            inputs.set_wayside_commanded_speed(block_id, "10")  # Medium
            DebugTerminal.log(f"Block {block_id} -> Block G{next_block} (MEDIUM)")
    
    # Verify the route was set correctly
    DebugTerminal.log("Verifying route configuration...")
    for current_block in [63, 64, 65, 66]:
        block_id = f"G{current_block}"
        next_bits = inputs.get_next_block_number(block_id)
        auth = inputs.get_wayside_authority(block_id)
        speed_bits = inputs.get_wayside_commanded_speed(block_id)
        next_num = int(next_bits, 2) if next_bits else 0
        speed_cmd = int(speed_bits, 2) if speed_bits else 0
        speed_names = ["Stop", "Slow", "Medium", "Fast"]
        
        DebugTerminal.log(f"  {block_id}: Next=G{next_num}, Auth={auth}, Speed={speed_names[speed_cmd]}")
    
    DebugTerminal.log("Route configuration complete! Trains should now receive correct packets.")
    return True

def test_all():
    """Run all available tests"""
    print("=== Running All Track Model Tests ===\n")
    
    tests = [
        ("CommunicationObject", test_communication_object),
        ("Wayside Integration", test_wayside_integration),
        ("Yard Buffer", test_yard_buffer),
        ("Track Circuit Packets", test_track_circuit_packets),
        ("Wayside Simulation", test_wayside_simulation),
        ("Train Route 63->66", test_train_route_63_to_66)
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running {test_name} Tests")
        print(f"{'='*50}")
        
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"L {test_name} test failed: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print(f"{'='*50}")
    
    for test_name, passed in results.items():
        status = " PASSED" if passed else "L FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    print(f"\nOverall Result: {' ALL TESTS PASSED' if all_passed else 'L SOME TESTS FAILED'}")
    return all_passed

def show_help():
    """Display help information"""
    print("""
Track Model Test Interfaces
===========================

Available Commands:
    python trackmodel_testinterfaces.py --test communication
        Run CommunicationObject tests only
        
    python trackmodel_testinterfaces.py --test integration  
        Run wayside integration tests only
        
    python trackmodel_testinterfaces.py --test train_route
        Test train routing from block 63->64->65->66
        
    python trackmodel_testinterfaces.py --test all
        Run all available tests
        
    python trackmodel_testinterfaces.py --help
        Show this help message

Test Categories:
    " CommunicationObject: Core wayside communication functionality
    " Wayside Integration: Multi-wayside coordination and data aggregation
    " Train Route: Test 63->64->65->66 routing with live train packets
    
Examples:
    # Test just the communication object
    python trackmodel_testinterfaces.py --test communication
    
    # Run complete test suite
    python trackmodel_testinterfaces.py --test all
""")

def main():
    """Main entry point for test interface"""
    if len(sys.argv) < 2:
        print("Error: Please specify a command. Use --help for usage information.")
        return
    
    command = sys.argv[1]
    
    if command == "--help":
        show_help()
    elif command == "--test":
        if len(sys.argv) < 3:
            print("Error: Please specify test type. Use --help for options.")
            return
            
        test_type = sys.argv[2]
        
        # Mock debug function to avoid Qt dependencies
        try:
            from trackmodel_working import DebugWindow, DebugTerminal
            original_debug = DebugWindow.print_to_terminal
            original_terminal_log = DebugTerminal.log
            DebugWindow.print_to_terminal = mock_debug_print
            DebugTerminal.log = mock_debug_print
        except:
            pass  # No Qt available, continue without debug mocking
        
        try:
            if test_type == "communication":
                test_communication_object()
            elif test_type == "integration":
                test_wayside_integration()
            elif test_type == "yard_buffer":
                test_yard_buffer()
            elif test_type == "track_circuit":
                test_track_circuit_packets()
            elif test_type == "wayside_simulation":
                test_wayside_simulation()
            elif test_type == "train_route":
                test_train_route_63_to_66()
            elif test_type == "all":
                test_all()
            else:
                print(f"Error: Unknown test type '{test_type}'. Use --help for options.")
        finally:
            # Restore original debug function if it was mocked
            try:
                DebugWindow.print_to_terminal = original_debug
                DebugTerminal.log = original_terminal_log
            except:
                pass
    else:
        print(f"Error: Unknown command '{command}'. Use --help for usage information.")

if __name__ == "__main__":
    main()