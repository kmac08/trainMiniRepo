import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime

# Add the parent directory to sys.path to import CTC modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from CTC.Core.block import Block


class TestBlock(unittest.TestCase):
    """Test cases for Block class focusing on block closing/opening and occupation"""
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        # Create mock track block data
        self.mock_track_data = Mock()
        self.mock_track_data.block_number = 1
        self.mock_track_data.length_m = 100.0
        self.mock_track_data.grade_percent = 2.5
        self.mock_track_data.speed_limit_kmh = 55
        self.mock_track_data.has_switch = True
        self.mock_track_data.has_crossing = False
        self.mock_track_data.has_station = True
        self.mock_track_data.line = "Green"
        self.mock_track_data.section = "A"
        self.mock_track_data.elevation_m = 10.0
        self.mock_track_data.direction = 1
        self.mock_track_data.is_underground = False
        self.mock_track_data.station = Mock()
        self.mock_track_data.switch = Mock()
        
        # Create Block instance
        self.block = Block(self.mock_track_data)
    
    def tearDown(self):
        """Clean up after each test"""
        self.block = None
    
    def test_block_initialization(self):
        """Test proper block initialization from track data"""
        self.assertEqual(self.block.blockID, 1)
        self.assertEqual(self.block.block_number, 1)
        self.assertEqual(self.block.length, 100.0)
        self.assertEqual(self.block.grade, 2.5)
        self.assertEqual(self.block.speedLimit, 55)
        self.assertTrue(self.block.is_open)
        self.assertFalse(self.block.switchPosition)
        self.assertTrue(self.block.switchPresent)
        self.assertFalse(self.block.crossingPresent)
        self.assertTrue(self.block.circuitPresent)
        self.assertEqual(self.block.line, "Green")
        self.assertEqual(self.block.section, "A")
    
    def test_update_occupation(self):
        """Test block occupation when train enters and exits, including error cases"""
        mock_train = Mock()
        mock_train.train_id = "TEST001"
        
        # Test normal train addition
        self.block.add_train(mock_train)
        self.assertEqual(self.block.get_occupying_train(), mock_train)
        self.assertEqual(self.block.occupied, True)

        # Test normal train removal
        self.block.remove_train()
        self.assertEqual(self.block.get_occupying_train(), None)
        self.assertEqual(self.block.occupied, False)
        
        # Test adding train to already occupied block (error case)
        # First train
        first_train = Mock()
        first_train.train_id = "FIRST_TRAIN"
        self.block.add_train(first_train)
        
        # Second train - should give an error message but not change occupancy
        second_train = Mock()
        second_train.train_id = "SECOND_TRAIN"
        self.block.add_train(second_train)
        
        # First train should still be occupying the block
        self.assertEqual(self.block.get_occupying_train(), first_train)
    
    def test_block_open_close_operations(self):
        """Test comprehensive block open/close operations with safety checks"""
        # Test basic opening block
        self.block.set_block_open(True)
        self.assertTrue(self.block.is_open)

        # Test closing empty block - should succeed
        self.block.set_block_open(False)
        self.assertFalse(self.block.is_open)
        
        # Test opening again
        self.block.set_block_open(True)
        self.assertTrue(self.block.is_open)
        
        # Test opening an already open block (idempotent)
        self.assertTrue(self.block.is_open)
        self.block.set_block_open(True)
        self.assertTrue(self.block.is_open)
        
        # Test safety check: closing block when occupied - should prevent closure
        mock_train = Mock()
        mock_train.train_id = "SAFETY_TEST"
        self.block.add_train(mock_train)
        
        initial_state = self.block.is_open
        self.block.set_block_open(False)
        # Block should prevent closure when occupied for safety
        self.assertEqual(self.block.is_open, initial_state)  # Should remain open
        
        # Train should still be present (not removed for safety)
        self.assertEqual(self.block.get_occupying_train(), mock_train)
        
        # Clear the train and try again - should succeed
        self.block.remove_train()
        self.block.set_block_open(False)
        self.assertFalse(self.block.is_open)
        
        # Test reopening closed block
        self.block.set_block_open(True)
        self.assertTrue(self.block.is_open)
    
    def test_block_authority_calculation(self):
        """Test block authority calculation based on block conditions"""
        # Test operational block (open and not failed)
        self.block.set_block_open(True)
        self.block.set_block_failed(False)
        self.assertTrue(self.block.block_operational())
        
        # Operational block should grant authority
        authority = self.block.calculate_safe_authority()
        self.assertEqual(authority, 1)  # Authority granted
        
        # Test closed block
        self.block.set_block_open(False)
        self.assertFalse(self.block.block_operational())
        authority = self.block.calculate_safe_authority()
        self.assertEqual(authority, 0)  # No authority
        
        # Test failed block (even if open)
        self.block.set_block_open(True)
        self.block.set_block_failed(True)
        self.assertFalse(self.block.block_operational())
        authority = self.block.calculate_safe_authority()
        self.assertEqual(authority, 0)  # No authority
        
        # Test occupied block
        self.block.set_block_open(True)
        self.block.set_block_failed(False)
        self.block.occupied = True
        authority = self.block.calculate_safe_authority()
        self.assertEqual(authority, 0)  # No authority for occupied block
    
    def test_block_speed_calculation(self):
        """Test block speed calculation based on next block occupation"""
        # Set up operational block with authority
        self.block.set_block_open(True)
        self.block.set_block_failed(False)
        self.block.occupied = False
        self.block.maintenance_mode = False
        
        # Create mock next blocks
        next_block_1 = Mock()
        next_block_2 = Mock()
        
        # Test case 1: No next blocks (end of sequence) - should return 1/3 speed
        speed = self.block.calculate_suggested_speed()
        self.assertEqual(speed, 1)  # 1/3 speed when no next block
        
        # Test case 2: Next block is occupied - should return 1/3 speed
        next_block_1.occupied = True
        next_block_2.occupied = False
        speed = self.block.calculate_suggested_speed(next_block_1, next_block_2)
        self.assertEqual(speed, 1)  # 1/3 speed when next block occupied
        
        # Test case 3: Next block clear, second block occupied - should return 2/3 speed
        next_block_1.occupied = False
        next_block_2.occupied = True
        speed = self.block.calculate_suggested_speed(next_block_1, next_block_2)
        self.assertEqual(speed, 2)  # 2/3 speed when second block occupied
        
        # Test case 4: Both next blocks clear - should return full speed
        next_block_1.occupied = False
        next_block_2.occupied = False
        speed = self.block.calculate_suggested_speed(next_block_1, next_block_2)
        self.assertEqual(speed, 3)  # Full speed when both blocks clear
        
        # Test case 5: Next block clear but no second block - should return 2/3 speed
        next_block_1.occupied = False
        speed = self.block.calculate_suggested_speed(next_block_1, None)
        self.assertEqual(speed, 2)  # 2/3 speed when no block 2 positions ahead
        
        # Test case 6: No authority - should return 0 regardless of next blocks
        self.block.occupied = True  # Make block occupied to deny authority
        speed = self.block.calculate_suggested_speed(next_block_1, next_block_2)
        self.assertEqual(speed, 0)  # No speed when no authority
    
    def test_switch_control(self):
        """Test switch control and information retrieval"""
        # Test block with switch - set positions and verify
        self.assertTrue(self.block.switchPresent)
        
        # Test setting switch position to True (reverse)
        self.block.set_switch_position(True)
        result = self.block.get_switch_info()
        self.assertTrue(result)
        
        # Test setting switch position to False (normal)
        self.block.set_switch_position(False)
        result = self.block.get_switch_info()
        self.assertFalse(result)
        
        # Test block without switch
        self.block._switchPresent = False
        result = self.block.get_switch_info()
        self.assertFalse(result)
    
    def test_setCrossing_status(self):
        """Test activating railway crossing"""
        # Need to modify the private variable since crossingPresent is now read-only
        self.block._crossingPresent = True
        self.block.setCrossing_status(True)
        self.assertTrue(self.block.crossingStatus)

        # Test if there is not crossing status (set crossing status shouldn't do anything)
        self.block._crossingPresent = False
        self.block.setCrossing_status(True)
        self.assertFalse(self.block.crossingStatus)
    
    
    def test_add_train_to_closed_block(self):
        """Test adding train to closed block"""
        self.block.is_open = False
        mock_train = Mock()
        
        # Block implementation doesn't prevent trains from entering closed blocks
        # This would be handled at a higher level (CTC system)
        self.block.add_train(mock_train)
        
        # Train is added even to closed block
        self.assertEqual(self.block.get_occupying_train(), mock_train)
    
    def test_remove_train_present(self):
        """Test removing train that is present in block"""
        mock_train = Mock()
        mock_train.train_id = "TEST001"
        self.block.add_train(mock_train)
        
        self.block.remove_train()
        
        self.assertIsNone(self.block.get_occupying_train())
    
    def test_remove_train_not_present(self):
        """Test removing train that is not in block"""
        # Try to remove train when none present - should just log warning
        self.block.remove_train()
        self.assertIsNone(self.block.get_occupying_train())
    
    
    @patch('CTC.Core.block._get_simulation_time')
    def test_block_closure_scheduling(self, mock_time):
        """Test comprehensive block closure scheduling functionality"""
        mock_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        
        # Test scheduling a closure with time mocking
        closure_time = datetime(2024, 1, 1, 12, 0, 0)
        result = self.block.schedule_closure(closure_time)
        
        # Check result
        self.assertTrue(result['success'])
        
        # Check that closure was scheduled
        self.assertIsNotNone(self.block.scheduledClosure)
        self.assertEqual(self.block.scheduledClosure['closure_time'], closure_time)
        self.assertEqual(self.block.scheduledClosure['type'], 'maintenance')
        
        # Test scheduling a future closure (without time mocking dependency)
        future_time = datetime(2024, 12, 25, 14, 30, 0)
        result2 = self.block.schedule_closure(future_time)
        self.assertTrue(result2['success'])
        self.assertIsNotNone(self.block.scheduledClosure)
        self.assertEqual(self.block.scheduledClosure['closure_time'], future_time)
        self.assertEqual(self.block.scheduledClosure['type'], 'maintenance')
        
        # Test scheduling second closure should overwrite the first
        future_time2 = datetime(2024, 12, 26, 10, 0, 0)
        result3 = self.block.schedule_closure(future_time2)
        self.assertTrue(result3['success'])
        self.assertEqual(self.block.scheduledClosure['closure_time'], future_time2)
        
        # Test clearing scheduled closure
        result4 = self.block.clear_scheduled_closure()
        self.assertTrue(result4['success'])
        self.assertIsNone(self.block.scheduledClosure)
        
        # Test validation: Cannot schedule closure when block is occupied
        mock_train = Mock()
        mock_train.train_id = "OCCUPIED_TEST"
        self.block.add_train(mock_train)
        
        occupied_closure_time = datetime(2024, 12, 27, 9, 0, 0)
        result_occupied = self.block.schedule_closure(occupied_closure_time)
        self.assertFalse(result_occupied['success'])
        self.assertIn('currently occupied', result_occupied['message'])
        self.assertIsNone(self.block.scheduledClosure)  # Should not have scheduled
        
        # Clear the train for next tests
        self.block.remove_train()
        
        # Test validation: Cannot schedule closure when it would conflict with scheduled occupations
        scheduled_occupations = [
            datetime(2024, 12, 28, 10, 0, 0),
            datetime(2024, 12, 28, 14, 0, 0),
            datetime(2024, 12, 28, 18, 0, 0)
        ]
        self.block.update_scheduled_occupancy(scheduled_occupations)
        
        # Try to schedule closure at exact time of scheduled occupation - should fail
        conflicting_closure_time = datetime(2024, 12, 28, 14, 0, 0)
        result_conflict = self.block.schedule_closure(conflicting_closure_time)
        self.assertFalse(result_conflict['success'])
        self.assertIn('scheduled occupation', result_conflict['message'])
        self.assertIsNone(self.block.scheduledClosure)  # Should not have scheduled
        
        # Try to schedule closure before scheduled occupation time - should fail
        before_occupation_closure = datetime(2024, 12, 28, 8, 0, 0)
        result_before = self.block.schedule_closure(before_occupation_closure)
        self.assertFalse(result_before['success'])
        self.assertIn('scheduled occupation', result_before['message'])
        
        # Test successful closure scheduling after all scheduled occupations - should succeed
        after_all_occupations_closure = datetime(2024, 12, 28, 20, 0, 0)
        result_after_all = self.block.schedule_closure(after_all_occupations_closure)
        self.assertTrue(result_after_all['success'])
        self.assertIsNotNone(self.block.scheduledClosure)
        self.assertEqual(self.block.scheduledClosure['closure_time'], after_all_occupations_closure)
        
        # Clear scheduled occupations and closure for clean state  
        self.block.update_scheduled_occupancy([])
        self.block.clear_scheduled_closure()
    
    def test_infrastructure_properties(self):
        """Test access to infrastructure properties"""
        # Test station access
        if self.block.station:
            self.assertIsNotNone(self.block.station)
        
        # Test switch access
        if self.block.switch:
            self.assertIsNotNone(self.block.switch)
    
    def test_block_metrics_collection(self):
        """Test collection of block performance metrics"""
        # Test initial authority and speed
        authority = self.block.calculate_safe_authority()
        speed = self.block.calculate_suggested_speed()
        
        self.assertIsInstance(authority, int)
        self.assertIsInstance(speed, int)
        self.assertIn(authority, [0, 1])
        self.assertIn(speed, [0, 1, 2, 3])
    
    @patch('CTC.Core.block._get_simulation_time')
    def test_is_closed_at_time_checking(self, mock_time):
        """Test is_closed_at_time for time-based closure checking"""
        # Set current simulation time
        current_time = datetime(2024, 12, 25, 14, 30, 0)
        mock_time.return_value = current_time
        
        # Test block open with no scheduled closures
        self.block.is_open = True
        self.block.scheduledClosures = []
        result = self.block.is_closed_at_time(current_time)
        self.assertFalse(result)  # Should not be closed

        # Test block that is currently closed
        self.block.is_open = False
        result = self.block.is_closed_at_time(current_time)
        self.assertTrue(result)  # Should be closed
        
        # Test block that is currently open
        self.block.is_open = True
        result = self.block.is_closed_at_time(current_time)
        self.assertFalse(result)  # Should not be closed
    
    def test_prevent_close_occupied_block_safety(self):
        """Test safety prevention of closing occupied blocks"""
        # Setup occupied block
        mock_train = Mock()
        mock_train.train_id = "SAFETY_TEST"
        self.block.add_train(mock_train)
        
        # Attempt to close occupied block should fail
        initial_state = self.block.is_open
        self.block.set_block_open(False)
        
        # Safety check: block should remain open
        self.assertEqual(self.block.is_open, initial_state)
        
        # Train should still be present (not removed for safety)
        self.assertEqual(self.block.get_occupying_train(), mock_train)
        
        # Clear the train and try again - should succeed
        self.block.remove_train()
        self.block.set_block_open(False)
        self.assertFalse(self.block.is_open)
    
    def test_schedule_opening_validation(self):
        """Test schedule_opening method with validation logic"""
        # Test scheduling opening without closure should fail
        opening_time = datetime(2024, 12, 25, 16, 0, 0)
        result = self.block.schedule_opening(opening_time)
        self.assertFalse(result['success'])
        self.assertIn('not scheduled for closure', result['message'])
        
        # Schedule a closure first
        closure_time = datetime(2024, 12, 25, 14, 0, 0)
        closure_result = self.block.schedule_closure(closure_time)
        self.assertTrue(closure_result['success'])
        
        # Test scheduling opening before closure should fail
        early_opening = datetime(2024, 12, 25, 13, 0, 0)
        result = self.block.schedule_opening(early_opening)
        self.assertFalse(result['success'])
        self.assertIn('must be after closure time', result['message'])
        
        # Test scheduling valid opening should succeed
        valid_opening = datetime(2024, 12, 25, 16, 0, 0)
        result = self.block.schedule_opening(valid_opening)
        self.assertTrue(result['success'])
        self.assertIsNotNone(self.block.scheduledOpening)
        self.assertEqual(self.block.scheduledOpening['opening_time'], valid_opening)
        
        # Test scheduling second opening should overwrite the first
        second_opening = datetime(2024, 12, 25, 18, 0, 0)
        result = self.block.schedule_opening(second_opening)
        self.assertTrue(result['success'])  # Should succeed (overwrite)
        self.assertIsNotNone(self.block.scheduledOpening)
        self.assertEqual(self.block.scheduledOpening['opening_time'], second_opening)  # Should be the new time
    
    def test_connectivity_methods(self):
        """Test block connectivity and routing methods"""
        # Set up connected blocks
        self.block._connected_blocks = [2, 3, 4]
        self.block._has_yard_connection = False
        
        # Test get_connected_blocks
        connected = self.block.get_connected_blocks()
        self.assertEqual(connected, [2, 3, 4])
        
        # Test is_connected_to
        self.assertTrue(self.block.is_connected_to(2))
        self.assertTrue(self.block.is_connected_to(3))
        self.assertFalse(self.block.is_connected_to(5))
        
        # Test leads_to_yard
        self.assertFalse(self.block.leads_to_yard())
        
        # Test with yard connection
        self.block._has_yard_connection = True
        self.assertTrue(self.block.leads_to_yard())
        
        # Test get_next_valid_blocks (basic functionality)
        next_blocks = self.block.get_next_valid_blocks()
        self.assertIsInstance(next_blocks, list)
        # Should return connected blocks that are operational
        for block_id in next_blocks:
            self.assertIn(block_id, [2, 3, 4])
    
    def test_information_methods(self):
        """Test block information and diagnostic methods"""
        # Test get_infrastructure_info
        info = self.block.get_infrastructure_info()
        self.assertIsInstance(info, dict)
        
        # Verify basic keys are in infrastructure info
        basic_keys = ['blockID', 'length', 'grade', 'line', 'section']
        for key in basic_keys:
            self.assertIn(key, info)
        
        # Verify values match block properties
        self.assertEqual(info['blockID'], self.block.blockID)
        self.assertEqual(info['length'], self.block.length)
        self.assertEqual(info['grade'], self.block.grade)
        self.assertEqual(info['line'], self.block.line)
        self.assertEqual(info['section'], self.block.section)
        
        # Check speed limit is present (could be speed_limit or speedLimit)
        self.assertTrue('speed_limit' in info or 'speedLimit' in info)
        
        # Test string representations
        str_repr = str(self.block)
        self.assertIsInstance(str_repr, str)
        self.assertIn("Block", str_repr)
        self.assertIn("1", str_repr)  # Block ID should be in string
        
        repr_str = repr(self.block)
        self.assertIsInstance(repr_str, str)
        self.assertIn("Block", repr_str)
    
    @patch('CTC.Core.block._get_simulation_time')
    def test_time_based_processing_methods(self, mock_time):
        """Test time-based processing methods for scheduled operations"""
        current_time = datetime(2024, 12, 25, 15, 0, 0)
        mock_time.return_value = current_time
        
        # Test process_scheduled_closure when no closure is scheduled
        self.block.scheduledClosure = None
        result = self.block.process_scheduled_closure(current_time)
        self.assertFalse(result)  # No action taken
        
        # Schedule a closure for the current time
        closure_time = datetime(2024, 12, 25, 15, 0, 0)
        self.block.schedule_closure(closure_time)
        self.assertTrue(self.block.is_open)  # Should be open initially
        
        # Process the scheduled closure - should close the block
        result = self.block.process_scheduled_closure(current_time)
        self.assertTrue(result)  # Action was taken
        self.assertFalse(self.block.is_open)  # Block should now be closed
        
        # Test process_scheduled_opening when no opening is scheduled
        self.block.scheduledOpening = None
        result = self.block.process_scheduled_opening(current_time)
        self.assertFalse(result)  # No action taken
        
        # Schedule an opening
        opening_time = datetime(2024, 12, 25, 16, 0, 0)
        opening_result = self.block.schedule_opening(opening_time)
        self.assertTrue(opening_result['success'])
        
        # Process opening before the scheduled time - should not open
        early_time = datetime(2024, 12, 25, 15, 30, 0)
        result = self.block.process_scheduled_opening(early_time)
        self.assertFalse(result)  # No action taken
        self.assertFalse(self.block.is_open)  # Should remain closed
        
        # Process opening at the scheduled time - should open the block
        mock_time.return_value = opening_time
        result = self.block.process_scheduled_opening(opening_time)
        self.assertTrue(result)  # Action was taken
        self.assertTrue(self.block.is_open)  # Block should now be open

    @patch('CTC.Core.block._get_simulation_time')
    def test_can_close_safely(self, mock_time):
        """Test comprehensive safety checks before closing block for maintenance"""
        current_time = datetime(2024, 12, 25, 12, 0, 0)
        mock_time.return_value = current_time
        
        # Test 1: Block safe to close - should succeed
        self.block.is_open = True
        self.block.occupied = False
        self.block.scheduledOccupations = []
        
        result = self.block.can_close_safely()
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], 'Block 1 can be safely closed')
        self.assertIsNone(result['conflict_type'])
        self.assertEqual(result['earliest_safe_time'], current_time)
        
        # Test 2: Block currently occupied - should fail
        mock_train = Mock()
        mock_train.train_id = "SAFETY_TEST"
        self.block.add_train(mock_train)
        
        result = self.block.can_close_safely()
        self.assertFalse(result['success'])
        self.assertIn('currently occupied', result['message'])
        self.assertEqual(result['conflict_type'], 'current_occupation')
        self.assertIsNone(result['earliest_safe_time'])
        
        # Clear train for next tests
        self.block.remove_train()
        
        # Test 3: Block already closed - should fail
        self.block.is_open = False
        
        result = self.block.can_close_safely()
        self.assertFalse(result['success'])
        self.assertIn('already closed', result['message'])
        self.assertEqual(result['conflict_type'], 'already_closed')
        self.assertIsNone(result['earliest_safe_time'])
        
        # Reopen block for next tests
        self.block.is_open = True
        
        # Test 4: Block with scheduled occupations - should fail and suggest safe time
        scheduled_times = [
            datetime(2024, 12, 25, 14, 0, 0),
            datetime(2024, 12, 25, 16, 0, 0),
            datetime(2024, 12, 25, 18, 0, 0)
        ]
        self.block.update_scheduled_occupancy(scheduled_times)
        
        # Check at current time (before scheduled occupations)
        result = self.block.can_close_safely(current_time)
        self.assertFalse(result['success'])
        self.assertIn('scheduled occupation', result['message'])
        self.assertEqual(result['conflict_type'], 'scheduled_occupation')
        self.assertIn('14:00', result['message'])  # Should mention earliest conflict
        
        # Verify earliest safe time is after all occupations plus buffer
        expected_safe_time = datetime(2024, 12, 25, 18, 5, 0)  # Last occupation + 5 min
        self.assertEqual(result['earliest_safe_time'], expected_safe_time)
        
        # Test 5: Check at time between scheduled occupations
        check_time = datetime(2024, 12, 25, 15, 0, 0)
        result = self.block.can_close_safely(check_time)
        self.assertFalse(result['success'])
        self.assertEqual(result['conflict_type'], 'scheduled_occupation')
        # Should identify next conflict at 16:00
        self.assertIn('16:00', result['message'])
        
        # Test 6: Check at time after all scheduled occupations - should succeed
        safe_check_time = datetime(2024, 12, 25, 19, 0, 0)
        result = self.block.can_close_safely(safe_check_time)
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], 'Block 1 can be safely closed')
        self.assertIsNone(result['conflict_type'])
        self.assertEqual(result['earliest_safe_time'], safe_check_time)
        
        # Clear scheduled occupations
        self.block.update_scheduled_occupancy([])
        
        # Test 7: Custom check_time parameter with open, unoccupied block
        future_time = datetime(2024, 12, 26, 10, 0, 0)
        result = self.block.can_close_safely(future_time)
        self.assertTrue(result['success'])
        self.assertEqual(result['earliest_safe_time'], future_time)


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestBlock)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)