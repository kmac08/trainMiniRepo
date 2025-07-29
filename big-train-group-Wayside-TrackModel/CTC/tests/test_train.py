import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime, timedelta

# Add the parent directory to sys.path to import CTC modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from CTC.Core.train import Train
from CTC.Core.block import Block
from CTC.Core.route import Route


class TestTrain(unittest.TestCase):
    """Test cases for Train class focusing on train state management"""
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        # Create mock block
        self.mock_block = Mock(spec=Block)
        self.mock_block.blockID = 1
        self.mock_block.line = "Green"
        self.mock_block.length = 100.0
        self.mock_block.speedLimit = 55
        self.mock_block.grade = 2.0
        
        # Create mock next block
        self.mock_next_block = Mock(spec=Block)
        self.mock_next_block.blockID = 2
        self.mock_next_block.line = "Green"
        self.mock_next_block.length = 120.0
        self.mock_next_block.speedLimit = 50
        self.mock_next_block.grade = 0.0
        
        # Create Train instance
        self.train = Train(
            trainID=1001,
            currentBlock=self.mock_block
        )
        
        # Test data
        self.test_train_id = "TEST001"
    
    def tearDown(self):
        """Clean up after each test"""
        self.train = None
    
    def test_train_initialization(self):
        """Test proper train initialization"""
        self.assertEqual(self.train.trainID, 1001)
        self.assertEqual(self.train.currentBlock, self.mock_block)
        self.assertIsNone(self.train.nextBlock)
        self.assertEqual(self.train.grade, 0.0)
        self.assertEqual(self.train.authority, 0)
        self.assertEqual(self.train.suggestedSpeed, 0)
        self.assertIsNone(self.train.route)
        self.assertTrue(self.train.is_active)
        self.assertEqual(self.train.line, "")
    
    def test_update_location_new_block(self):
        """Test updating train location to new block"""
        self.train.update_location(self.mock_next_block)
        self.assertEqual(self.train.currentBlock, self.mock_next_block)
    
    def test_update_route(self):
        """Test updating train's route assignment"""
        mock_route = Mock(spec=Route)
        mock_route.routeID = "ROUTE_123"
        mock_route.isActive = True
        mock_route.blockSequence = None  # No blocks in route

        # Check that no route is returned when none is assigned
        self.assertIsNone(self.train.get_route())

        self.train.update_route(mock_route)
        self.assertEqual(self.train.get_route(), mock_route)
    
    def test_get_speed_limit(self):
        """Test getting speed limit from current block"""
        speed_limit = self.train.get_speed_limit()
        
        self.assertEqual(speed_limit, self.mock_block.speedLimit)

        self.train.update_location(self.mock_next_block)
        self.assertEqual(self.train.get_speed_limit(), self.mock_next_block.speedLimit)
    
    def test_speed_calculations_and_states(self):
        """Test speed calculations, conversions, and state transitions"""
        # Test speed 0 (stop)
        self.train.update_suggested_speed(0)
        self.assertEqual(self.train.get_speed_mph(), 0.0)
        
        # Test speed 1 (1/3 speed limit)
        self.train.update_suggested_speed(1)
        expected_mph = (55 * 0.621371) / 3.0  # 55 km/h converted to mph then divided by 3
        self.assertAlmostEqual(self.train.get_speed_mph(), expected_mph, places=2)
        
        # Test speed 2 (2/3 speed limit) 
        self.train.update_suggested_speed(2)
        expected_mph = (55 * 0.621371 * 2.0) / 3.0
        self.assertAlmostEqual(self.train.get_speed_mph(), expected_mph, places=2)
        
        # Test speed 3 (full speed limit)
        self.train.update_suggested_speed(3)
        expected_mph = 55 * 0.621371
        self.assertAlmostEqual(self.train.get_speed_mph(), expected_mph, places=2)
    
    def test_get_location(self):
        """Test getting current location"""
        self.train.update_location(self.mock_block)
        location = self.train.get_location()
        self.assertEqual(location, self.mock_block)

        self.train.update_location(self.mock_next_block)
        location = self.train.get_location()
        self.assertEqual(location, self.mock_next_block)
    
    def test_update_movement_history(self):
        """Test updating movement history for emergency detection"""
        # First update
        self.train.update_movement_history(self.mock_block.blockID)
        
        # Should initialize movement history
        self.assertEqual(self.train.movement_history['block'], self.mock_block.blockID)
        self.assertEqual(self.train.movement_history['count'], 1)
        self.assertIsNotNone(self.train.movement_history['last_update'])
        
        # Second update in same block
        self.train.update_movement_history(self.mock_block.blockID)

        self.assertEqual(self.train.movement_history['count'], 2)

    def test_update_movement_history_new_block(self):
        """Test movement history when changing blocks"""
        # First update
        self.train.update_movement_history(self.mock_block.blockID)
        initial_count = self.train.movement_history['count']
        
        # Move to new block
        self.train.update_location(self.mock_next_block)
        self.train.update_movement_history(self.mock_next_block.blockID)
        
        # Should reset count for new block
        self.assertEqual(self.train.movement_history['block'], self.mock_next_block.blockID)
        self.assertEqual(self.train.movement_history['count'], 1)
    
    def test_is_stationary_too_long_basic(self):
        """Test basic stationary detection without time constraints"""
        # Should not be considered stationary without history
        is_stationary = self.train.is_stationary_too_long()
        self.assertFalse(is_stationary)
        
        # Initialize movement history
        self.train.update_movement_history(self.mock_block.blockID)
        
        # Test immediately after update (should not be stationary too long)
        is_stationary = self.train.is_stationary_too_long()
        self.assertFalse(is_stationary)

        # Simulate multiple updates in same block with time_threshold=0 to ignore time
        for _ in range(10):
            self.train.update_movement_history(self.mock_block.blockID)

        # Should detect emergency condition when time_threshold is 0
        is_stationary = self.train.is_stationary_too_long(threshold=10, time_threshold=0)
        self.assertTrue(is_stationary)
    
    def test_time_based_stationary_detection_comprehensive(self):
        """Test comprehensive time-based stationary detection functionality"""
        from datetime import datetime, timedelta
        import time
        
        # Test 1: Initial state - should have first_stationary_time field
        self.assertIn('first_stationary_time', self.train.movement_history)
        self.assertIsNone(self.train.movement_history['first_stationary_time'])
        
        # Test 2: First update - train enters block
        self.train.update_movement_history(self.mock_block.blockID)
        self.assertIsNone(self.train.movement_history['first_stationary_time'])
        self.assertEqual(self.train.movement_history['count'], 1)
        
        # Test 3: Second update - train becomes stationary (count=2)
        self.train.update_movement_history(self.mock_block.blockID)
        self.assertIsNotNone(self.train.movement_history['first_stationary_time'])
        first_stationary_time = self.train.movement_history['first_stationary_time']
        self.assertEqual(self.train.movement_history['count'], 2)
        
        # Test 4: Third update - meets count threshold but insufficient time
        self.train.update_movement_history(self.mock_block.blockID)
        self.assertEqual(self.train.movement_history['count'], 3)
        
        # Should NOT be flagged as stationary too long (insufficient time since very little time has passed)
        self.assertFalse(self.train.is_stationary_too_long(threshold=3, time_threshold=60))
        
        # Test with time_threshold=0 (ignores time completely) - should still work
        self.assertTrue(self.train.is_stationary_too_long(threshold=3, time_threshold=0))
        
        # Test 5: Wait and then check that enough time has passed for detection
        # Use a very small time threshold (1 second) and sleep to ensure time passes
        time.sleep(1.1)  # Sleep slightly more than 1 second
        
        # Should NOW be flagged as stationary too long (sufficient time: >1 second ≥ 1 second)
        self.assertTrue(self.train.is_stationary_too_long(threshold=3, time_threshold=1))
        
        # Test 6: Movement resets time tracking
        self.train.update_movement_history(self.mock_next_block.blockID)
        self.assertIsNone(self.train.movement_history['first_stationary_time'])
        self.assertEqual(self.train.movement_history['count'], 1)
        
        # Test 7: Train becomes stationary in new block with new timestamp
        self.train.update_movement_history(self.mock_next_block.blockID)
        new_stationary_time = self.train.movement_history['first_stationary_time']
        self.assertIsNotNone(new_stationary_time)
        self.assertNotEqual(new_stationary_time, first_stationary_time)
        
        # Test 8: Reset movement history includes first_stationary_time
        self.train.reset_movement_history()
        self.assertIn('first_stationary_time', self.train.movement_history)
        self.assertIsNone(self.train.movement_history['first_stationary_time'])
        
        # Test 9: Missing time data returns False even with sufficient count
        self.train.movement_history['count'] = 5
        self.train.movement_history['block'] = self.mock_block.blockID
        self.train.movement_history['last_update'] = datetime.now()
        self.train.movement_history['first_stationary_time'] = None
        self.assertFalse(self.train.is_stationary_too_long(threshold=3))
    
    def test_train_activation_deactivation(self):
        """Test train activation and deactivation"""
        # Initially active
        self.assertTrue(self.train.is_active)
        
        # Deactivate
        self.train.is_active = False
        self.assertFalse(self.train.is_active)
        
        # Reactivate
        self.train.is_active = True
        self.assertTrue(self.train.is_active)
    
    def test_property_assignments(self):
        """Test assignment and tracking of various train properties"""
        # Test authority assignment (valid values are 0 or 1)
        new_authority = 1
        self.train.update_authority(new_authority)
        self.assertEqual(self.train.authority, new_authority)
        
        # Test suggested speed assignment
        new_suggested_speed = 2
        self.train.update_suggested_speed(new_suggested_speed)
        self.assertEqual(self.train.suggestedSpeed, new_suggested_speed)
        
        # Test grade tracking from block information
        self.train.grade = self.mock_block.grade
        self.assertEqual(self.train.grade, 2.0)
        
        # Test next block assignment
        self.train.nextBlock = self.mock_next_block
        self.assertEqual(self.train.nextBlock, self.mock_next_block)
        self.assertNotEqual(self.train.nextBlock, self.train.currentBlock)
        
        # Test line assignment
        self.train.line = "Green"
        self.assertEqual(self.train.line, "Green")
    
    def test_train_string_representation(self):
        """Test string representation of train"""
        self.train.line = "Green"
        train_str = str(self.train)
        
        # Should contain key information
        self.assertIn("1001", train_str)  # Train ID

    def test_authority_and_speed_updates(self):
        """Test update_authority and update_suggested_speed methods with boundary conditions"""
        # Test authority updates - valid values are 0 (stop) and 1 (proceed)
        # Test valid authority values
        self.train.update_authority(0)
        self.assertEqual(self.train.authority, 0)
        
        self.train.update_authority(1)
        self.assertEqual(self.train.authority, 1)
        
        # Test invalid positive authority values get clamped to 1
        self.train.update_authority(5)
        self.assertEqual(self.train.authority, 1)
        
        self.train.update_authority(1000)
        self.assertEqual(self.train.authority, 1)
        
        # Test negative value gets clamped to 0
        self.train.update_authority(-1)
        self.assertEqual(self.train.authority, 0)
        
        # Test speed updates - valid values are 0, 1, 2, 3
        # Test valid speed values
        for speed in [0, 1, 2, 3]:
            self.train.update_suggested_speed(speed)
            self.assertEqual(self.train.suggestedSpeed, speed)
        
        # Test negative value gets clamped to 0
        self.train.update_suggested_speed(-1)
        self.assertEqual(self.train.suggestedSpeed, 0)
        
        # Test invalid large speed values get clamped to 3
        self.train.update_suggested_speed(4)
        self.assertEqual(self.train.suggestedSpeed, 3)
        
        self.train.update_suggested_speed(10)
        self.assertEqual(self.train.suggestedSpeed, 3)
        
        
    def test_get_stationary_count(self):
        """Test get_stationary_count method returns correct count"""
        # Initially should be 0
        self.assertEqual(self.train.get_stationary_count(), 0)
        
        # After first movement update
        self.train.update_movement_history(self.mock_block.blockID)
        self.assertEqual(self.train.get_stationary_count(), 1)
        
        # After multiple updates in same block
        self.train.update_movement_history(self.mock_block.blockID)
        self.train.update_movement_history(self.mock_block.blockID)
        self.assertEqual(self.train.get_stationary_count(), 3)
        
        # After moving to new block, should reset to 1
        self.train.update_movement_history(self.mock_next_block.blockID)
        self.assertEqual(self.train.get_stationary_count(), 1)
        
    def test_reset_movement_history(self):
        """Test reset_movement_history method properly resets tracking data"""
        # Initialize some movement history
        self.train.update_movement_history(self.mock_block.blockID)
        self.train.update_movement_history(self.mock_block.blockID)
        
        # Verify history exists
        self.assertEqual(self.train.movement_history['block'], self.mock_block.blockID)
        self.assertEqual(self.train.movement_history['count'], 2)
        self.assertIsNotNone(self.train.movement_history['last_update'])
        
        # Reset history
        self.train.reset_movement_history()
        
        # Verify reset
        self.assertIsNone(self.train.movement_history['block'])
        self.assertEqual(self.train.movement_history['count'], 0)
        self.assertIsNone(self.train.movement_history['last_update'])
        
    def test_to_dict_serialization(self):
        """Test to_dict method serializes train state correctly"""
        # Set up train with various states
        mock_route = Mock(spec=Route)
        mock_route.routeID = "ROUTE_123"
        
        self.train.nextBlock = self.mock_next_block
        self.train.grade = 2.5
        self.train.update_authority(1)  # Use proper method to set valid authority
        self.train.suggestedSpeed = 2
        self.train.line = "Green"
        self.train.is_active = True
        self.train.route = mock_route
        
        # Test serialization
        result = self.train.to_dict()
        
        expected = {
            'trainID': 1001,
            'currentBlock': self.mock_block.blockID,
            'nextBlock': self.mock_next_block.blockID,
            'grade': 2.5,
            'authority': 1,
            'suggestedSpeed': 2,
            'line': "Green",
            'is_active': True,
            'route': "ROUTE_123"
        }
        
        self.assertEqual(result, expected)
        
    def test_to_dict_with_none_values(self):
        """Test to_dict method handles None values correctly"""
        # Train with minimal setup (nextBlock and route are None)
        result = self.train.to_dict()
        
        expected = {
            'trainID': 1001,
            'currentBlock': self.mock_block.blockID,
            'nextBlock': None,
            'grade': 0.0,
            'authority': 0,
            'suggestedSpeed': 0,
            'line': "",
            'is_active': True,
            'route': None
        }
        
        self.assertEqual(result, expected)


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestTrain)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)