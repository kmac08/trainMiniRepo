import unittest
from unittest.mock import patch, Mock
import sys
import os
from datetime import datetime, timedelta

# Add the parent directory to sys.path to import CTC modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from CTC.Core.route import Route
from CTC.Core.route_manager import RouteManager
from CTC.Core.block import Block
from CTC.Core.ctc_system import CTCSystem
from Track_Reader.track_reader import TrackLayoutReader



@patch('CTC.Core.ctc_system._get_simulation_time')
@patch('CTC.Core.route._get_simulation_time')
@patch('CTC.Core.route_manager._get_simulation_time')
class TestRoute(unittest.TestCase):
    """Test cases for Route class focusing on route generation and validation"""
    
    def setUp(self):
        """Set up test fixtures before each test method"""        
        # Set up real TrackReader with actual Excel data
        excel_path = os.path.join(os.path.dirname(__file__), '..', '..', 'Track_Reader', 'Track Layout & Vehicle Data vF2.xlsx')
        self.track_reader = TrackLayoutReader(excel_path, ["Green"])
        
        # Create real blocks using connected sequence
        start_block_data = self.track_reader.get_block_by_number(1, "Green")   # PIONEER station
        end_block_data = self.track_reader.get_block_by_number(14, "Green")     # EDGEBROOK station
        intermediate_block_data = self.track_reader.get_block_by_number(13, "Green")  # Block between PIONEER and EDGEBROOK
        
        self.start_block = Block(start_block_data)
        self.end_block = Block(end_block_data) 
        self.intermediate_block = Block(intermediate_block_data)
        
        # Mock CTCSystem to avoid master interface dependency
        with patch('CTC.Core.ctc_system._get_simulation_time') as mock_time:
            mock_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
            self.ctc_system = CTCSystem(track_reader=self.track_reader)
        
        # Create RouteManager instance for validation
        self.route_manager = RouteManager(track_reader=self.track_reader)
        
        # Test data
        # Fixed test time instead of datetime.now()
        self.test_arrival_time = datetime(2024, 1, 1, 13, 0, 0)
    
    def tearDown(self):
        """Clean up after each test"""
        # Reset block states to prevent test interference
        self._reset_blocks_to_operational()
    
    def _reset_blocks_to_operational(self):
        """Helper method to reset all test blocks to operational state"""
        for block in [self.start_block, self.intermediate_block, self.end_block]:
            block.set_block_open(True)
            block.set_block_failed(False)
            block.occupied = False
            block.maintenance_mode = False
    
    def test_route_initialization(self, mock_route_manager_time, mock_route_time, mock_ctc_time):
        """Test proper route initialization"""
        route = Route()
        
        self.assertIsNone(route.routeID)
        self.assertIsNone(route.startBlock)
        self.assertIsNone(route.endBlock)
        self.assertEqual(route.blockSequence, [])
        self.assertEqual(route.estimatedTravelTime, 0.0)
        self.assertEqual(route.authoritySequence, [])
        self.assertEqual(route.speedSequence, [])
        self.assertEqual(route.currentBlockIndex, 0)
        self.assertFalse(route.isActive)
        self.assertEqual(route.routeType, 'NORMAL')
        self.assertEqual(route.priority, 1)

    def test_create_route_invalid_blocks(self, mock_route_manager_time, mock_route_time, mock_ctc_time):
        """Test route creation with invalid blocks"""
        route = Route()

        try:
            route.create_route([None, self.end_block], self.test_arrival_time)
        except:
            pass
        self.assertIsNone(route.startBlock)

        route2 = Route()

        try:
            route2.create_route([self.start_block, None], self.test_arrival_time)
        except:
            pass
        self.assertIsNone(route2.endBlock)
    
    def test_create_route_same_start_end(self, mock_route_manager_time, mock_route_time, mock_ctc_time):
        """Test route creation with same start and end block using pre-calculated sequence"""
        route = Route()
        
        # Provide single-block sequence
        single_block_sequence = [self.start_block]
        
        route.create_route(
            single_block_sequence,
            self.test_arrival_time
        )
        
        # Check that the provided sequence was used
        self.assertEqual(len(route.blockSequence), 1)
        self.assertEqual(route.blockSequence[0], self.start_block)
    
    def test_create_route_no_sequence_raises_error(self, mock_route_manager_time, mock_route_time, mock_ctc_time):
        """Test route creation without block sequence raises ValueError"""
        route = Route()
        
        # Should raise ValueError when empty block_sequence provided
        with self.assertRaises(ValueError) as context:
            route.create_route(
                [],  # empty block sequence
                self.test_arrival_time
            )
        
        self.assertIn("Route creation requires non-empty block sequence", str(context.exception))
    
    def test_create_route_success(self, mock_route_manager_time, mock_route_time, mock_ctc_time):
        """Test Creation of a route with a complex sequence"""
        route = Route()

        # Create blocks for the connected sequence 4,3,2,1,13,14,15
        block_4_data = Block(self.track_reader.get_block_by_number(4, "Green"))
        block_3_data = Block(self.track_reader.get_block_by_number(3, "Green"))
        block_2_data = Block(self.track_reader.get_block_by_number(2, "Green"))
        block_1_data = Block(self.track_reader.get_block_by_number(1, "Green"))
        block_13_data = Block(self.track_reader.get_block_by_number(13, "Green"))
        block_14_data = Block(self.track_reader.get_block_by_number(14, "Green"))
        block_15_data = Block(self.track_reader.get_block_by_number(15, "Green"))
        
        connected_sequence = [
            block_4_data, block_3_data, block_2_data,
            block_1_data, block_13_data, block_14_data, block_15_data
        ]
        
        route.create_route(
            connected_sequence,
            self.test_arrival_time
        )

        self.assertEqual(len(route.blockSequence), 7)
        self.assertEqual(route.blockSequence[0], block_4_data)
        self.assertEqual(route.blockSequence[1], block_3_data)
        self.assertEqual(route.blockSequence[2], block_2_data)
        self.assertEqual(route.blockSequence[3], block_1_data)
        self.assertEqual(route.blockSequence[4], block_13_data)
        self.assertEqual(route.blockSequence[5], block_14_data)
        self.assertEqual(route.blockSequence[6], block_15_data)
        self.assertEqual(route.startBlock, block_4_data)
        self.assertEqual(route.endBlock, block_15_data)

    def test_update_location_valid_block(self, mock_route_manager_time, mock_route_time, mock_ctc_time):
        """Test updating train location to valid block in route"""
        route = Route()
        
        # Create route properly using create_route method
        block_sequence = [
            self.start_block, 
            self.intermediate_block, 
            self.end_block
        ]
        route.create_route(block_sequence, self.test_arrival_time)
        route.currentBlockIndex = 0
        
        result = route.update_location(self.intermediate_block)
        
        self.assertTrue(result)
        self.assertEqual(route.get_block_sequence()[route.currentBlockIndex], self.intermediate_block)
        self.assertEqual(route.get_next_block(), self.end_block)
    
        """Test updating location to block not in route"""
        # Create new route for this test
        route2 = Route()
        route2.create_route([self.start_block, self.end_block], self.test_arrival_time)
        
        invalid_block = Mock()
        invalid_block.blockID = 999
        
        result = route2.update_location(invalid_block)
        self.assertFalse(result)
    
        """Test handling of backward movement in route"""
        # Create new route for this test
        route3 = Route()
        route3.create_route([
            self.start_block, 
            self.intermediate_block, 
            self.end_block
        ], self.test_arrival_time)
        route3.currentBlockIndex = 2  # At end block
        
        # Try to move back to intermediate block
        result = route3.update_location(self.intermediate_block)
        
        # Should fail (trains cannot move backwards)
        self.assertFalse(result)
        self.assertEqual(route3.currentBlockIndex, 2)  # Should remain at end block

    def test_get_next_block(self, mock_route_manager_time, mock_route_time, mock_ctc_time):
        """Test getting next block in route sequence"""
        route = Route()
        
        # Create route properly using create_route method
        block_sequence = [
            self.start_block, 
            self.intermediate_block, 
            self.end_block
        ]
        route.create_route(block_sequence, self.test_arrival_time)
        route.currentBlockIndex = 0
        
        next_block = route.get_next_block()
        self.assertEqual(next_block, self.intermediate_block)
    
        """Test getting next block when at end of route"""
        route.currentBlockIndex = 2  # At end
        
        next_block = route.get_next_block()
        self.assertIsNone(next_block)
    
        """Test getting next block with empty route"""
        empty_route = Route()
        next_block = empty_route.get_next_block()
        self.assertIsNone(next_block)
    
    def test_calculate_authority_speed(self, mock_route_manager_time, mock_route_time, mock_ctc_time):
        """Comprehensive test of authority and speed calculation for various block conditions"""
        
        # === Test 1: All blocks operational (baseline) ===
        route = Route()
        # Create route properly using create_route method
        block_sequence = [self.start_block, self.intermediate_block, self.end_block]
        route.create_route(block_sequence, self.test_arrival_time)
        
        # Ensure all blocks are in clean operational state
        for block in route.blockSequence:
            block.set_block_open(True)
            block.set_block_failed(False)
            block.occupied = False
            block.maintenance_mode = False
        
        authority, speed = route.calculate_authority_speed()
        
        # Basic structure validation
        self.assertIsInstance(authority, list)
        self.assertIsInstance(speed, list)
        self.assertEqual(len(authority), len(route.blockSequence))
        self.assertEqual(len(speed), len(route.blockSequence))
        
        # All blocks should have authority (operational and not occupied)
        self.assertEqual(authority[0], 1, "Start block should have authority")
        self.assertEqual(authority[1], 1, "Intermediate block should have authority")
        self.assertEqual(authority[2], 1, "End block should have authority")
        
        # Speed should be: full speed for first block, 2/3 for second (no block 2 positions ahead), 1/3 for end (no next)
        self.assertEqual(speed[0], 3, "Start block should have full speed (2 clear blocks ahead)")
        self.assertEqual(speed[1], 2, "Intermediate block should have 2/3 speed (no block 2 positions ahead)")
        self.assertEqual(speed[2], 1, "End block should have 1/3 speed (no next blocks)")
        
        # === Test 2: Occupied block in middle ===
        self.intermediate_block.occupied = True
        
        authority, speed = route.calculate_authority_speed()
        
        # Authority: based only on current block conditions
        self.assertEqual(authority[0], 1, "Start block should have authority (not occupied)")
        self.assertEqual(authority[1], 0, "Intermediate block should have NO authority (occupied)")
        self.assertEqual(authority[2], 1, "End block should have authority (not occupied)")
        
        # Speed: based on next block occupation
        self.assertEqual(speed[0], 1, "Start block should have 1/3 speed (next block occupied)")
        self.assertEqual(speed[1], 0, "Intermediate block should have 0 speed (no authority)")
        self.assertEqual(speed[2], 1, "End block should have 1/3 speed (no next blocks)")
        
        # === Test 3: Failed block ===
        self.intermediate_block.occupied = False  # Clear occupation
        self.intermediate_block.set_block_failed(True)
        
        authority, speed = route.calculate_authority_speed()
        
        self.assertEqual(authority[0], 1, "Start block should have authority (operational)")
        self.assertEqual(authority[1], 0, "Failed block should have NO authority")
        self.assertEqual(authority[2], 1, "End block should have authority (operational)")
        
        self.assertEqual(speed[0], 3, "Start block should have full speed (next block clear)")
        self.assertEqual(speed[1], 0, "Failed block should have 0 speed (no authority)")
        self.assertEqual(speed[2], 1, "End block should have 1/3 speed (no next blocks)")
        
        # === Test 4: Closed block ===
        self.intermediate_block.set_block_failed(False)  # Clear failure
        self.intermediate_block.set_block_open(False)    # Close block
        
        authority, speed = route.calculate_authority_speed()
        
        self.assertEqual(authority[0], 1, "Start block should have authority (open)")
        self.assertEqual(authority[1], 0, "Closed block should have NO authority")
        self.assertEqual(authority[2], 1, "End block should have authority (open)")
        
        self.assertEqual(speed[0], 3, "Start block should have full speed (next block clear)")
        self.assertEqual(speed[1], 0, "Closed block should have 0 speed (no authority)")
        self.assertEqual(speed[2], 1, "End block should have 1/3 speed (no next blocks)")
        
        # === Test 5: Maintenance mode ===
        self.intermediate_block.set_block_open(True)     # Reopen block
        self.intermediate_block.maintenance_mode = True  # Set maintenance
        
        authority, speed = route.calculate_authority_speed()
        
        self.assertEqual(authority[0], 1, "Start block should have authority (not in maintenance)")
        self.assertEqual(authority[1], 0, "Block in maintenance should have NO authority")
        self.assertEqual(authority[2], 1, "End block should have authority (not in maintenance)")
        
        self.assertEqual(speed[0], 3, "Start block should have full speed (next block clear)")
        self.assertEqual(speed[1], 0, "Maintenance block should have 0 speed (no authority)")
        self.assertEqual(speed[2], 1, "End block should have 1/3 speed (no next blocks)")
        
        # === Test 6: Multiple block issues ===
        # Reset intermediate block and set end block to have issues
        self.intermediate_block.maintenance_mode = False
        self.end_block.occupied = True
        
        authority, speed = route.calculate_authority_speed()
        
        self.assertEqual(authority[0], 1, "Start block should have authority")
        self.assertEqual(authority[1], 1, "Intermediate block should have authority") 
        self.assertEqual(authority[2], 0, "End block should have NO authority (occupied)")
        
        self.assertEqual(speed[0], 2, "Start block should have 2/3 speed (second block ahead occupied)")
        self.assertEqual(speed[1], 1, "Intermediate block should have 1/3 speed (next block occupied)")
        self.assertEqual(speed[2], 0, "End block should have 0 speed (no authority)")
        
        # === Test 7: Edge case - Single block route ===
        single_route = Route()
        single_route.create_route([self.start_block], self.test_arrival_time)
        
        # Ensure start block is operational
        self.start_block.set_block_open(True)
        self.start_block.set_block_failed(False)
        self.start_block.occupied = False
        self.start_block.maintenance_mode = False
        
        authority, speed = single_route.calculate_authority_speed()
        
        self.assertEqual(len(authority), 1)
        self.assertEqual(len(speed), 1)
        self.assertEqual(authority[0], 1, "Single block should have authority if operational")
        self.assertEqual(speed[0], 1, "Single block should have 1/3 speed (no next blocks)")
        
        # === Test 8: Edge case - All blocks have issues ===
        all_issues_route = Route()
        all_issues_route.create_route([self.start_block, self.intermediate_block, self.end_block], self.test_arrival_time)
        
        # Set all blocks to have different issues
        self.start_block.occupied = True
        self.intermediate_block.set_block_failed(True)
        self.end_block.set_block_open(False)
        
        authority, speed = all_issues_route.calculate_authority_speed()
        
        # All blocks should have no authority due to their respective issues
        self.assertEqual(authority[0], 0, "Occupied block should have no authority")
        self.assertEqual(authority[1], 0, "Failed block should have no authority")
        self.assertEqual(authority[2], 0, "Closed block should have no authority")
        
        # All blocks should have no speed due to no authority
        self.assertEqual(speed[0], 0, "Block with no authority should have 0 speed")
        self.assertEqual(speed[1], 0, "Block with no authority should have 0 speed")
        self.assertEqual(speed[2], 0, "Block with no authority should have 0 speed")
        
        # Clean up for other tests
        self._reset_blocks_to_operational()
    
    def test_calculate_route_distance(self, mock_route_manager_time, mock_route_time, mock_ctc_time):
        """Test calculation of total route distance"""
        route = Route()
        
        # Create route properly using create_route method
        block_sequence = [
            self.start_block, 
            self.intermediate_block, 
            self.end_block
        ]
        route.create_route(block_sequence, self.test_arrival_time)
        
        # Test using the existing method that calculates route distance between two blocks
        distance = route.calculate_route_distance(1, 14)  # From first to last block (passes through block 13)

        # The last block is 2 blocks away from the first block
        self.assertEqual(distance, 2)

        """Test distance calculation for empty route"""
        empty_route = Route()
        
        distance = empty_route.calculate_route_distance(1, 5)
        self.assertEqual(distance, 0)
    
    def test_get_remaining_blocks(self, mock_route_manager_time, mock_route_time, mock_ctc_time):
        """Test getting remaining blocks in route"""
        route = Route()
        
        # Create route properly using create_route method
        block_sequence = [
            self.start_block,    # 100m
            self.intermediate_block,  # 120m
            self.end_block       # 150m
        ]
        route.create_route(block_sequence, self.test_arrival_time)
        route.currentBlockIndex = 1  # At intermediate block
        
        remaining_blocks = route.get_remaining_blocks()
        
        # Should include current block + remaining blocks
        expected_count = 2  # intermediate and end blocks
        self.assertEqual(len(remaining_blocks), expected_count)
        self.assertEqual(remaining_blocks[0], self.intermediate_block)
        self.assertEqual(remaining_blocks[1], self.end_block)
    
    def test_travel_time_estimation(self, mock_route_manager_time, mock_route_time, mock_ctc_time):
        """Test travel time estimation using existing methods"""
        mock_route_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        route = Route()
        
        # Create route properly using create_route method
        block_sequence = [
            self.start_block, 
            self.intermediate_block, 
            self.end_block
        ]
        route.create_route(block_sequence, self.test_arrival_time)
        
        # Test that estimated arrival is calculated properly
        route.isActive = True
        route.currentBlockIndex = 0
        estimated_arrival = route.get_estimated_arrival()

        timeDiff = 8 + 7.7/0.67 + 7.7/0.33

        expected_arrival = mock_route_time.return_value + timedelta(seconds=timeDiff)
        time_diff = abs((estimated_arrival - expected_arrival).total_seconds())
        self.assertLessEqual(time_diff, 0.1, f"Time difference {time_diff} exceeds 0.1 second tolerance")
    
    def test_route_priority_handling(self, mock_route_manager_time, mock_route_time, mock_ctc_time):
        """Test route priority assignment and comparison"""
        mock_route_manager_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        mock_route_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        mock_ctc_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        route = Route()
        
        # Test normal priority
        self.assertEqual(route.priority, 1)
        
        # Test high priority route
        emergency_route = Route()
        emergency_route.routeType = 'EMERGENCY'
        emergency_route.priority = 3
        
        self.assertGreater(emergency_route.priority, route.priority)
    
    def test_route_status_tracking(self, mock_route_manager_time, mock_route_time, mock_ctc_time):
        """Test route status and timing tracking"""
        route = Route()
        
        # Test activation using existing method
        route.activate_route("train_123")
        self.assertTrue(route.isActive)
        self.assertEqual(route.trainID, "train_123")
        
        # Test deactivation using existing method
        route.deactivate_route()
        self.assertFalse(route.isActive)
        self.assertIsNotNone(route.actualArrival)

if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestRoute)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)