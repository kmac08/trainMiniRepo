import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime

# Add the parent directory to sys.path to import CTC modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from CTC.Core.ctc_system import CTCSystem
from CTC.Core.train import Train
from CTC.Core.block import Block
from CTC.Core.route import Route
from Track_Reader.track_reader import TrackLayoutReader


@patch('CTC.Core.ctc_system._get_simulation_time')
class TestCTCSystem(unittest.TestCase):
    """Test cases for CTCSystem class focusing on train scheduling and management"""
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        # Set up real TrackReader with actual Excel data
        excel_path = os.path.join(os.path.dirname(__file__), '..', '..', 'Track_Reader', 'Track Layout & Vehicle Data vF2.xlsx')
        self.track_reader = TrackLayoutReader(excel_path, ["Green"])
        
        # Create CTCSystem instance with time mocking to avoid master interface dependency
        with patch('CTC.Core.ctc_system._get_simulation_time') as mock_time:
            mock_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
            self.ctc_system = CTCSystem(track_reader=self.track_reader)
        
        # Sample test data
        self.test_train_id = "G001"
        self.base_time = datetime(2024, 1, 1, 12, 0, 0)
    
    def tearDown(self):
        """Clean up after each test"""
        self.ctc_system = None

    def _create_test_train(self, train_id, block_number=1):
        """
        Helper method to create a real Train object using real Block data from track reader
        
        Args:
            train_id: ID for the train (can be string or int)
            block_number: Block number to place the train on (default: 1)
        
        Returns:
            Train: Real Train object with real Block
        """
        # Get real block data from track reader
        block_data = self.track_reader.get_block_by_number(block_number, "Green")
        # Create real Block object
        real_block = Block(block_data)
        # Create real Train object
        real_train = Train(trainID=train_id, currentBlock=real_block)
        return real_train

    def test_validate_ID(self, mock_time):
        """Test validate_ID with valid train ID format"""
        valid_ids = ["G001", "R001", "G002", "R002"]
        
        for train_id in valid_ids:
            with self.subTest(train_id=train_id):
                result = self.ctc_system.validate_ID(train_id)
                self.assertTrue(result, f"Expected {train_id} to be valid")

        """Test validate_ID with invalid train ID format"""
        invalid_ids = ["", "123", "T", "R1", "L001", "G00", None]
        
        for train_id in invalid_ids:
            with self.subTest(train_id=train_id):
                result = self.ctc_system.validate_ID(train_id)
                self.assertFalse(result, f"Expected {train_id} to be invalid")

        """Test validate_ID rejects duplicate train IDs"""
        # Add a real train first
        real_train = self._create_test_train(self.test_train_id)
        self.ctc_system.trains[self.test_train_id] = real_train

        # Try to validate the same ID
        result = self.ctc_system.validate_ID(self.test_train_id)
        self.assertFalse(result, "Should reject duplicate train ID")
    
    def test_add_train_success(self, mock_time):
        """Test successful train addition to the system"""
        result = self.ctc_system.add_train(self.test_train_id)

        self.assertTrue(result)
        self.assertIn(self.test_train_id, self.ctc_system.trains)
        self.assertIsInstance(self.ctc_system.trains[self.test_train_id], Train)

    def test_add_train_invalid_id(self, mock_time):
        """Test train addition with invalid ID"""
        with patch.object(self.ctc_system, 'validate_ID', return_value=False):
            result = self.ctc_system.add_train("Green")
            
            self.assertFalse(result)
            self.assertNotIn(self.test_train_id, self.ctc_system.trains)
    
    def test_remove_train_existing(self, mock_time):
        """Test removal of existing train"""
        # Add a real train first
        real_train = self._create_test_train(self.test_train_id, 1)
        self.ctc_system.trains[self.test_train_id] = real_train
        self.ctc_system.activeTrains.append(real_train)
        
        result = self.ctc_system.remove_train(self.test_train_id)
        
        self.assertTrue(result)
        self.assertNotIn(self.test_train_id, self.ctc_system.trains)
        self.assertNotIn(real_train, self.ctc_system.activeTrains)
    
    def test_remove_train_nonexistent(self, mock_time):
        """Test removal of non-existent train"""
        result = self.ctc_system.remove_train("NONEXISTENT")
        self.assertFalse(result)
    
    def test_dispatch_train_from_yard_success(self, mock_time):
        """Test successful train dispatch from yard"""
        mock_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        
        # Setup mocks
        with patch.object(self.ctc_system, 'validate_ID', return_value=True), \
             patch.object(self.ctc_system, 'add_train', return_value=True), \
             patch.object(self.ctc_system, 'generate_route', return_value="route_123"):
            
            result = self.ctc_system.dispatch_train_from_yard(
                self.test_train_id, "Green", "Station A"
            )
            
            self.assertTrue(result)
    
    def test_dispatch_train_from_yard_invalid_id(self, mock_time):
        """Test train dispatch with invalid train ID"""
        with patch.object(self.ctc_system, 'validate_ID', return_value=False):
            result = self.ctc_system.dispatch_train_from_yard(
                "INVALID", "Green", "Station A"
            )
            
            self.assertFalse(result)
    
    def test_generate_route_success(self, mock_time):
        """Test successful route generation"""
        # Mock route manager
        mock_route_manager = Mock()
        mock_route_manager.generate_route.return_value = "route_123"
        self.ctc_system.routeManager = mock_route_manager
        
        result = self.ctc_system.generate_route("Green", 1, "Station A")
        
        self.assertEqual(result, "route_123")
        mock_route_manager.generate_route.assert_called_once()
    
    def test_generate_route_no_route_manager(self, mock_time):
        """Test route generation without route manager"""
        self.ctc_system.routeManager = None
        
        result = self.ctc_system.generate_route("Green", 1, "Station A")
        
        self.assertIsNone(result)
    
    def test_activate_route_success(self, mock_time):
        """Test successful route activation"""
        # Setup test data
        mock_route = Mock()
        real_train = self._create_test_train(self.test_train_id, 1)
        
        self.ctc_system.routes["route_123"] = mock_route
        self.ctc_system.trains[self.test_train_id] = real_train
        
        result = self.ctc_system.activate_route("route_123", self.test_train_id)
        
        self.assertTrue(result)
        # Verify that the real train's route was actually updated
        self.assertEqual(real_train.route, mock_route)
    
    def test_activate_route_invalid_route(self, mock_time):
        """Test route activation with invalid route ID"""
        result = self.ctc_system.activate_route("INVALID", self.test_train_id)
        self.assertFalse(result)
    
    def test_activate_route_invalid_train(self, mock_time):
        """Test route activation with invalid train ID"""
        mock_route = Mock()
        self.ctc_system.routes["route_123"] = mock_route
        
        result = self.ctc_system.activate_route("route_123", "INVALID")
        self.assertFalse(result)
    
    def test_process_occupied_blocks(self, mock_time):
        """Test processing of occupied block updates"""
        occupied_blocks = [
            {"line": "Green", "block": 1, "occupied": True},
            {"line": "Green", "block": 2, "occupied": False}
        ]
        
        # Mock blocks
        mock_block1 = Mock()
        mock_block2 = Mock()
        self.ctc_system.blocks[("Green", 1)] = mock_block1
        self.ctc_system.blocks[("Green", 2)] = mock_block2
        
        self.ctc_system.process_occupied_blocks(occupied_blocks)
        
        mock_block1.update_occupation.assert_called_once_with(True)
        mock_block2.update_occupation.assert_called_once_with(False)
    
    def test_provide_wayside_controller(self, mock_time):
        """Test wayside controller registration"""
        mock_controller = Mock()
        blocks_covered = [("Green", 1), ("Green", 2)]
        
        result = self.ctc_system.provide_wayside_controller(mock_controller, blocks_covered)
        
        self.assertTrue(result)
    
    def test_thread_safety_train_operations(self, mock_time):
        """Test thread safety of train operations"""
        import threading
        import time
        
        results = []
        
        def add_trains():
            for i in range(10):
                train_id = f"THREAD_TEST_{i}"
                with patch.object(self.ctc_system, 'validate_ID', return_value=True):
                    result = self.ctc_system.add_train(train_id)
                    results.append(result)
                time.sleep(0.001)  # Small delay to increase chance of race conditions
        
        # Run multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=add_trains)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All operations should succeed
        self.assertTrue(all(results))
    
    def test_emergency_handling(self, mock_time):
        """Test emergency stop functionality"""
        # Create real train and simulate emergency condition
        real_train = self._create_test_train(self.test_train_id, 1)
        
        # Simulate the train being stationary too long by setting up movement history
        # Call update_movement_history multiple times with same block to simulate stationary train
        block_id = real_train.currentBlock.blockID
        for _ in range(5):  # More than the default threshold of 3
            real_train.update_movement_history(block_id)
        
        # Use a very short time threshold to ensure emergency detection
        # Patch the is_stationary_too_long method to use minimal time threshold
        with patch.object(real_train, 'is_stationary_too_long', return_value=True):
            self.ctc_system.trains[self.test_train_id] = real_train
            self.ctc_system.activeTrains.append(real_train)
            
            # Mock communication handler
            mock_comm_handler = Mock()
            self.ctc_system.communicationHandler = mock_comm_handler
            
            # This would typically be called in a monitoring loop
            emergencies = self.ctc_system._check_for_emergencies()
            
            # Should detect the emergency
            self.assertTrue(len(emergencies) > 0)
    
    def test_schedule_block_closure(self, mock_time):
        """Test scheduling a block closure"""
        mock_time.return_value = self.base_time
        
        # Schedule a closure 5 minutes in the future
        from datetime import timedelta
        closure_time = self.base_time + timedelta(minutes=5)
        
        result = self.ctc_system.schedule_block_closure('Green', 5, closure_time)
        
        # Should succeed
        self.assertTrue(result['success'])
        
        # Check that scheduled closure was added
        self.assertEqual(len(self.ctc_system.scheduledClosures), 1)
        scheduled = self.ctc_system.scheduledClosures[0]
        self.assertEqual(scheduled['line'], 'Green')
        self.assertEqual(scheduled['block_number'], 5)
        self.assertEqual(scheduled['scheduled_time'], closure_time)
        self.assertEqual(scheduled['status'], 'scheduled')
    
    def test_schedule_block_closure_with_duration(self, mock_time):
        """Test scheduling a block closure with automatic reopening"""
        mock_time.return_value = self.base_time
        
        from datetime import timedelta
        closure_time = self.base_time + timedelta(minutes=5)
        duration = timedelta(minutes=30)
        
        result = self.ctc_system.schedule_block_closure('Green', 5, closure_time, duration)
        
        # Should succeed
        self.assertTrue(result['success'])
        
        # Check that scheduled opening was also added
        self.assertEqual(len(self.ctc_system.scheduledOpenings), 1)
        opening = self.ctc_system.scheduledOpenings[0]
        self.assertEqual(opening['line'], 'Green')
        self.assertEqual(opening['block_number'], 5)
        self.assertEqual(opening['scheduled_time'], closure_time + duration)
    
    def test_process_scheduled_closures(self, mock_time):
        """Test processing of scheduled closures"""
        from datetime import timedelta
        
        # Schedule a closure in the past (should execute)
        past_time = self.base_time - timedelta(minutes=5)
        self.ctc_system.scheduledClosures.append({
            'id': 'test-1',
            'line': 'Green',
            'block_number': 5,
            'scheduled_time': past_time,
            'status': 'scheduled'
        })
        
        # Set current time to after the scheduled closure
        mock_time.return_value = self.base_time
        
        # Process closures
        actions = self.ctc_system.process_scheduled_closures()
        
        # Should have executed the closure
        self.assertEqual(len(actions), 1)
        self.assertIn('Executed scheduled closure', actions[0])
        
        # Check status was updated
        self.assertEqual(self.ctc_system.scheduledClosures[0]['status'], 'active')
        
        # Check maintenance closure was added
        self.assertIn(5, self.ctc_system.maintenance_closures.get('Green', []))
    
    def test_process_scheduled_openings(self, mock_time):
        """Test processing of scheduled openings"""
        from datetime import timedelta
        
        # Add a maintenance closure first
        self.ctc_system.add_maintenance_closure('Green', 5)
        
        # Schedule an opening in the past (should execute)
        past_time = self.base_time - timedelta(minutes=5)
        self.ctc_system.scheduledOpenings.append({
            'line': 'Green',
            'block_number': 5,
            'scheduled_time': past_time,
            'related_closure': 'test-1'
        })
        
        # Set current time to after the scheduled opening
        mock_time.return_value = self.base_time
        
        # Process openings
        actions = self.ctc_system.process_scheduled_openings()
        
        # Should have executed the opening
        self.assertEqual(len(actions), 1)
        self.assertIn('Executed scheduled opening', actions[0])
        
        # Check maintenance closure was removed
        self.assertNotIn(5, self.ctc_system.maintenance_closures.get('Green', []))
        
        # Check scheduled opening was removed
        self.assertEqual(len(self.ctc_system.scheduledOpenings), 0)
    
    def test_cancel_scheduled_closure(self, mock_time):
        """Test canceling a scheduled closure"""
        from datetime import timedelta
        
        # Schedule a closure
        closure_time = self.base_time + timedelta(minutes=5)
        self.ctc_system.schedule_block_closure('Green', 5, closure_time)
        
        # Cancel it
        result = self.ctc_system.cancel_scheduled_closure('Green', 5)
        
        # Should succeed
        self.assertTrue(result['success'])
        self.assertIn('Cancelled 1 scheduled closures', result['message'])
        
        # Check that closure was removed
        self.assertEqual(len(self.ctc_system.scheduledClosures), 0)
    
    def test_close_block_immediately(self, mock_time):
        """Test immediate block closure"""
        mock_time.return_value = self.base_time
        
        # Get the block and mock can_close_safely
        block = self.ctc_system.get_block_by_line_new('Green', 5)
        with patch.object(block, 'can_close_safely', return_value={'success': True}):
            result = self.ctc_system.close_block_immediately('Green', 5)
        
        # Should succeed
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], 'Block 5 closed')
        
        # Check maintenance closure was added
        self.assertIn(5, self.ctc_system.maintenance_closures.get('Green', []))
    
    def test_open_block_immediately(self, mock_time):
        """Test immediate block opening"""
        mock_time.return_value = self.base_time
        
        # Close a block first
        block = self.ctc_system.get_block_by_line_new('Green', 5)
        with patch.object(block, 'can_close_safely', return_value={'success': True}):
            self.ctc_system.close_block_immediately('Green', 5)
        
        # Now open it
        result = self.ctc_system.open_block_immediately('Green', 5)
        
        # Should succeed
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], 'Block 5 opened')
        
        # Check maintenance closure was removed
        self.assertNotIn(5, self.ctc_system.maintenance_closures.get('Green', []))
    
    def test_scheduled_closure_block_not_found(self, mock_time):
        """Test scheduled closure when block doesn't exist"""
        from datetime import timedelta
        
        # Use a block number that doesn't exist on the Green line
        result = self.ctc_system.schedule_block_closure('Green', 999, self.base_time + timedelta(minutes=5))
        
        # Should fail
        self.assertFalse(result['success'])
        self.assertIn('not found', result['message'])


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestCTCSystem)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)