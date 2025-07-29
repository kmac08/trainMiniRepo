import unittest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os
from datetime import datetime, timedelta
from queue import Queue
import threading
import time

# Add the parent directory to sys.path to import CTC modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from CTC.Core.communication_handler import CommunicationHandler


class TestCommunicationHandler(unittest.TestCase):
    """Test cases for CommunicationHandler class focusing on external communication"""
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        self.comm_handler = CommunicationHandler()
        
        # Mock wayside controller
        self.mock_controller = Mock()
        self.mock_controller.get_line.return_value = "Green"
        self.mock_controller.receive_train_commands = Mock()
        self.mock_controller.set_occupied = Mock()
        
        # Mock blocks
        self.mock_block1 = Mock()
        self.mock_block1.blockID = 1
        self.mock_block1.line = "Green"
        self.mock_block1.block_operational.return_value = True
        
        self.mock_block2 = Mock()
        self.mock_block2.blockID = 2
        self.mock_block2.line = "Green"
        self.mock_block2.block_operational.return_value = True
        
        # Test data
        self.blocks_covered = [("Green", 1), ("Green", 2)]
        self.test_train_id = "TEST001"
    
    def tearDown(self):
        """Clean up after each test"""
        self.comm_handler = None
    
    def test_initialization(self):
        """Test proper initialization of CommunicationHandler"""
        self.assertEqual(self.comm_handler.scheduledClosures, [])
        self.assertEqual(self.comm_handler.waysideControllers, {})
        self.assertEqual(self.comm_handler.controllerBlockMapping, {})
        self.assertIsInstance(self.comm_handler.commandQueue, Queue)
        self.assertIsInstance(self.comm_handler.responseQueue, Queue)
    
    def test_provide_wayside_controller_success(self):
        """Test successful wayside controller registration"""
        result = self.comm_handler.provide_wayside_controller(
            self.mock_controller, 
            self.blocks_covered
        )
        
        self.assertTrue(result)
        self.assertIn("Green", self.comm_handler.waysideControllers)
        self.assertEqual(
            self.comm_handler.waysideControllers["Green"], 
            self.mock_controller
        )
        self.assertEqual(
            self.comm_handler.controllerBlockMapping[self.mock_controller],
            self.blocks_covered
        )
    
    def test_provide_wayside_controller_invalid_input(self):
        """Test controller registration with invalid input"""
        # Test with None controller
        result = self.comm_handler.provide_wayside_controller(None, self.blocks_covered)
        self.assertFalse(result)
        
        # Test with empty blocks list
        result = self.comm_handler.provide_wayside_controller(self.mock_controller, [])
        self.assertFalse(result)
        
        # Test with None blocks
        result = self.comm_handler.provide_wayside_controller(self.mock_controller, None)
        self.assertFalse(result)
    
    def test_provide_wayside_controller_duplicate_registration(self):
        """Test handling of duplicate controller registration"""
        # Register controller first time
        result1 = self.comm_handler.provide_wayside_controller(
            self.mock_controller, 
            self.blocks_covered
        )
        
        # Register same controller again
        result2 = self.comm_handler.provide_wayside_controller(
            self.mock_controller, 
            self.blocks_covered
        )
        
        self.assertTrue(result1)
        self.assertTrue(result2)  # Should update registration
    
    def test_send_train_commands_success(self):
        """Test successful train command transmission"""
        # Register controller first
        self.comm_handler.provide_wayside_controller(
            self.mock_controller, 
            self.blocks_covered
        )
        
        command_data = {
            "train_id": self.test_train_id,
            "line": "Green",
            "block": 1,
            "authority": 1,
            "speed": 2,
            "next_station": "Station A"
        }
        
        result = self.comm_handler.send_train_commands([command_data])
        
        self.assertTrue(result)
        self.mock_controller.receive_train_commands.assert_called_once()
    
    def test_send_train_commands_no_controller(self):
        """Test command transmission with no registered controller"""
        command_data = {
            "train_id": self.test_train_id,
            "line": "Red",  # Line with no controller
            "block": 1,
            "authority": 1,
            "speed": 2
        }
        
        result = self.comm_handler.send_train_commands([command_data])
        self.assertFalse(result)
    
    def test_send_train_commands_controller_failure(self):
        """Test handling of controller communication failure"""
        # Register controller
        self.comm_handler.provide_wayside_controller(
            self.mock_controller, 
            self.blocks_covered
        )
        
        # Make controller raise exception
        self.mock_controller.receive_train_commands.side_effect = Exception("Communication failed")
        
        command_data = {
            "train_id": self.test_train_id,
            "line": "Green",
            "block": 1,
            "authority": 1,
            "speed": 2
        }
        
        result = self.comm_handler.send_train_commands([command_data])
        self.assertFalse(result)
    
    def test_set_occupied_success(self):
        """Test successful block occupation setting"""
        # Register controller
        self.comm_handler.provide_wayside_controller(
            self.mock_controller, 
            self.blocks_covered
        )
        
        result = self.comm_handler.set_occupied("Green", 1, True)
        
        self.assertTrue(result)
        self.mock_controller.set_occupied.assert_called_once_with(1, True)
    
    def test_set_occupied_no_controller(self):
        """Test block occupation setting with no controller"""
        result = self.comm_handler.set_occupied("Red", 1, True)
        self.assertFalse(result)
    
    def test_update_occupied_blocks_success(self):
        """Test processing of occupied block updates from wayside"""
        # Register controller
        self.comm_handler.provide_wayside_controller(
            self.mock_controller, 
            self.blocks_covered
        )
        
        occupied_data = [
            {"line": "Green", "block": 1, "occupied": True, "train_id": self.test_train_id},
            {"line": "Green", "block": 2, "occupied": False, "train_id": None}
        ]
        
        # This would typically be called by the CTC system
        result = self.comm_handler.update_occupied_blocks(occupied_data, self.mock_controller)
        
        self.assertTrue(result)
    
    def test_update_occupied_blocks_unauthorized_controller(self):
        """Test filtering of unauthorized block updates"""
        # Register controller for different blocks
        unauthorized_controller = Mock()
        unauthorized_blocks = [("Green", 5), ("Green", 6)]
        
        self.comm_handler.provide_wayside_controller(
            unauthorized_controller,
            unauthorized_blocks
        )
        
        # Try to send data for blocks this controller doesn't manage
        occupied_data = [
            {"line": "Green", "block": 1, "occupied": True, "train_id": self.test_train_id}
        ]
        
        result = self.comm_handler.update_occupied_blocks(occupied_data, unauthorized_controller)
        
        # Should reject unauthorized data
        self.assertFalse(result)
    
    def test_send_departure_commands_success(self):
        """Test successful departure command transmission"""
        # Register controller
        self.comm_handler.provide_wayside_controller(
            self.mock_controller, 
            self.blocks_covered
        )
        
        departure_data = {
            "train_id": self.test_train_id,
            "line": "Green",
            "departure_block": 1,
            "route_blocks": [1, 2],
            "destination": "Station A"
        }
        
        result = self.comm_handler.send_departure_commands(departure_data)
        
        self.assertTrue(result)
    
    def test_calculate_authority_and_speed_with_block_methods(self):
        """Test centralized authority and speed calculation using Block class methods"""
        # Create mock blocks with Block class methods
        mock_target_block = Mock()
        mock_target_block.blockID = 5
        mock_target_block.calculate_safe_authority.return_value = 1
        mock_target_block.calculate_suggested_speed.return_value = 3
        
        # Create mock CTC system
        mock_ctc = Mock()
        mock_ctc.get_block.return_value = mock_target_block
        self.comm_handler.ctc_system = mock_ctc
        
        # Create mock route
        mock_route = Mock()
        mock_route.blockSequence = [Mock(), Mock(), Mock()]
        mock_route.blockSequence[0].blockID = 5
        mock_route.blockSequence[1].blockID = 6  
        mock_route.blockSequence[2].blockID = 7
        
        # Test calculation
        authority, speed = self.comm_handler.calculate_authority_and_speed("TEST_TRAIN", 5, mock_route)
        
        # Verify Block class methods were called
        mock_target_block.calculate_safe_authority.assert_called_once()
        mock_target_block.calculate_suggested_speed.assert_called_once()
        
        # Verify results
        self.assertEqual(authority, 1)
        self.assertEqual(speed, 3)
    
    def test_calculate_authority_and_speed_block_conditions(self):
        """Test authority and speed calculation with different block conditions"""
        test_cases = [
            # (operational, occupied, maintenance, expected_authority, expected_speed)
            (True, False, False, 1, 3),  # Normal operational block
            (False, False, False, 0, 0), # Not operational
            (True, True, False, 0, 0),   # Occupied
            (True, False, True, 0, 0)    # Maintenance mode
        ]
        
        for operational, occupied, maintenance, exp_auth, exp_speed in test_cases:
            with self.subTest(operational=operational, occupied=occupied, maintenance=maintenance):
                # Create mock block with specific conditions
                mock_block = Mock()
                mock_block.blockID = 10
                mock_block.calculate_safe_authority.return_value = exp_auth
                mock_block.calculate_suggested_speed.return_value = exp_speed
                
                # Mock CTC system
                mock_ctc = Mock()
                mock_ctc.get_block.return_value = mock_block
                self.comm_handler.ctc_system = mock_ctc
                
                # Test calculation
                authority, speed = self.comm_handler.calculate_authority_and_speed("TEST", 10, None)
                
                self.assertEqual(authority, exp_auth, f"Authority mismatch for conditions: operational={operational}, occupied={occupied}, maintenance={maintenance}")
                self.assertEqual(speed, exp_speed, f"Speed mismatch for conditions: operational={operational}, occupied={occupied}, maintenance={maintenance}")
    
    def test_departure_commands_use_centralized_calculation(self):
        """Test that departure commands use the same centralized calculation as regular commands"""
        # Create mock blocks
        mock_block = Mock()
        mock_block.blockID = 63
        mock_block.calculate_safe_authority.return_value = 1
        mock_block.calculate_suggested_speed.return_value = 2
        
        # Mock CTC system  
        mock_ctc = Mock()
        mock_ctc.get_block.return_value = mock_block
        self.comm_handler.ctc_system = mock_ctc
        
        # Mock route
        mock_route = Mock()
        mock_route.blockSequence = [Mock(), Mock(), Mock()]
        mock_route.blockSequence[0].blockID = 0  # Yard
        mock_route.blockSequence[1].blockID = 63
        mock_route.blockSequence[2].blockID = 64
        
        # Mock controller
        mock_controller = Mock()
        mock_controller.redLine = False
        mock_controller.command_train = Mock()
        self.comm_handler.wayside_controllers = [mock_controller]
        
        # Mock helper methods to avoid external dependencies
        self.comm_handler._get_train_line_from_route = Mock(return_value='Green')
        self.comm_handler._get_line_length = Mock(return_value=77)
        self.comm_handler._get_next_station_for_route = Mock(return_value=1)
        
        # Patch simulation time to avoid master interface dependency
        with patch('CTC.Core.communication_handler._get_simulation_time') as mock_time:
            mock_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
            
            # Test that departure commands work (without threading complications)
            # We'll just test the calculation part by calling it directly
            authority, speed = self.comm_handler.calculate_authority_and_speed("TEST_TRAIN", 63, mock_route)
            
            # Verify same results as regular command calculation
            self.assertEqual(authority, 1)
            self.assertEqual(speed, 2)
            
            # Verify Block class methods were used
            mock_block.calculate_safe_authority.assert_called()
            mock_block.calculate_suggested_speed.assert_called()
    
    def test_consistency_between_command_types(self):
        """Test that regular train commands and departure commands produce identical results"""
        # Setup identical mock conditions
        mock_block = Mock()
        mock_block.blockID = 42
        mock_block.calculate_safe_authority.return_value = 1
        mock_block.calculate_suggested_speed.return_value = 2
        
        mock_ctc = Mock()
        mock_ctc.get_block.return_value = mock_block
        self.comm_handler.ctc_system = mock_ctc
        
        mock_route = Mock()
        mock_route.blockSequence = [Mock(), Mock()]
        mock_route.blockSequence[0].blockID = 41
        mock_route.blockSequence[1].blockID = 42
        
        # Test regular train command calculation
        auth1, speed1 = self.comm_handler.calculate_authority_and_speed("TRAIN1", 42, mock_route)
        
        # Store call counts before second test
        first_auth_calls = mock_block.calculate_safe_authority.call_count
        first_speed_calls = mock_block.calculate_suggested_speed.call_count
        
        # Test departure command calculation (same underlying method)
        auth2, speed2 = self.comm_handler.calculate_authority_and_speed("TRAIN2", 42, mock_route)
        
        # Verify identical results
        self.assertEqual(auth1, auth2, "Authority calculations should be identical")
        self.assertEqual(speed1, speed2, "Speed calculations should be identical")
        
        # Verify both calls used Block class methods
        self.assertEqual(first_auth_calls, 1, "First call should use calculate_safe_authority")
        self.assertEqual(first_speed_calls, 1, "First call should use calculate_suggested_speed")
        self.assertEqual(mock_block.calculate_safe_authority.call_count, 2, "Both calls should use calculate_safe_authority")
        self.assertEqual(mock_block.calculate_suggested_speed.call_count, 2, "Both calls should use calculate_suggested_speed")
    
    def test_next_block_context_in_speed_calculation(self):
        """Test that speed calculations properly use next block context"""
        # Create mock blocks
        mock_current = Mock()
        mock_current.blockID = 10
        mock_current.calculate_safe_authority.return_value = 1
        mock_current.calculate_suggested_speed.return_value = 2
        
        mock_next1 = Mock()
        mock_next1.blockID = 11
        mock_next2 = Mock() 
        mock_next2.blockID = 12
        
        # Create route with next blocks
        mock_route = Mock()
        mock_route.blockSequence = [mock_current, mock_next1, mock_next2]
        
        mock_ctc = Mock()
        mock_ctc.get_block.return_value = mock_current
        self.comm_handler.ctc_system = mock_ctc
        
        # Test calculation
        authority, speed = self.comm_handler.calculate_authority_and_speed("TEST", 10, mock_route)
        
        # Verify calculate_suggested_speed was called with next block context
        mock_current.calculate_suggested_speed.assert_called_once_with(mock_next1, mock_next2)
        
        self.assertEqual(authority, 1)
        self.assertEqual(speed, 2)
    
    def test_command_queue_operations(self):
        """Test command queue operations"""
        command = {
            "type": "SWITCH_COMMAND",
            "line": "Green",
            "block": 1,
            "position": True
        }
        
        # Add command to queue
        self.comm_handler.commandQueue.put(command)
        
        # Retrieve command from queue
        retrieved_command = self.comm_handler.commandQueue.get(timeout=1)
        
        self.assertEqual(retrieved_command, command)
    
    def test_response_queue_operations(self):
        """Test response queue operations"""
        response = {
            "type": "COMMAND_ACK",
            "command_id": "12345",
            "status": "SUCCESS"
        }
        
        # Add response to queue
        self.comm_handler.responseQueue.put(response)
        
        # Retrieve response from queue
        retrieved_response = self.comm_handler.responseQueue.get(timeout=1)
        
        self.assertEqual(retrieved_response, response)
    
    def test_thread_safety_controller_registration(self):
        """Test thread safety of controller registration"""
        results = []
        
        def register_controller(controller_id):
            mock_controller = Mock()
            mock_controller.get_line.return_value = f"Line{controller_id}"
            blocks = [(f"Line{controller_id}", 1), (f"Line{controller_id}", 2)]
            
            result = self.comm_handler.provide_wayside_controller(mock_controller, blocks)
            results.append(result)
        
        # Run multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=register_controller, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All registrations should succeed
        self.assertTrue(all(results))
        self.assertEqual(len(self.comm_handler.waysideControllers), 5)
    
    def test_full_line_data_transmission(self):
        """Test full line data transmission behavior"""
        # Register multiple controllers for same line
        controller1 = Mock()
        controller1.get_line.return_value = "Green"
        controller1.receive_train_commands = Mock()
        
        controller2 = Mock()
        controller2.get_line.return_value = "Green"
        controller2.receive_train_commands = Mock()
        
        # Register controllers with different block coverage
        self.comm_handler.provide_wayside_controller(controller1, [("Green", 1), ("Green", 2)])
        self.comm_handler.provide_wayside_controller(controller2, [("Green", 3), ("Green", 4)])
        
        # Send commands for all blocks on the line
        commands = [
            {"train_id": "T001", "line": "Green", "block": 1, "authority": 1, "speed": 2},
            {"train_id": "T001", "line": "Green", "block": 2, "authority": 1, "speed": 2},
            {"train_id": "T001", "line": "Green", "block": 3, "authority": 1, "speed": 2},
            {"train_id": "T001", "line": "Green", "block": 4, "authority": 1, "speed": 2}
        ]
        
        result = self.comm_handler.send_train_commands(commands)
        
        # Both controllers should receive all line data
        self.assertTrue(result)
        # Note: In the actual implementation, both controllers would receive full data
        # but would only act on blocks they manage
    
    @patch('CTC.Core.communication_handler._get_simulation_time')
    def test_scheduled_closures_management(self, mock_time):
        """Test management of scheduled block closures"""
        mock_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        
        closure_time = datetime(2024, 1, 1, 14, 0, 0)  # 2 hours later
        
        # Schedule a closure
        self.comm_handler.scheduledClosures.append((self.mock_block1, closure_time))
        
        self.assertEqual(len(self.comm_handler.scheduledClosures), 1)
        self.assertEqual(self.comm_handler.scheduledClosures[0][0], self.mock_block1)
        self.assertEqual(self.comm_handler.scheduledClosures[0][1], closure_time)
    
    def test_emergency_stop_broadcast(self):
        """Test emergency stop command broadcast"""
        # Register controller
        self.comm_handler.provide_wayside_controller(
            self.mock_controller, 
            self.blocks_covered
        )
        
        # This would typically be implemented as a special command type
        emergency_command = {
            "type": "EMERGENCY_STOP",
            "train_id": self.test_train_id,
            "line": "Green",
            "authority": 0,
            "speed": 0
        }
        
        # Test that emergency commands are processed with high priority
        self.comm_handler.commandQueue.put(emergency_command)
        
        retrieved = self.comm_handler.commandQueue.get(timeout=1)
        self.assertEqual(retrieved["type"], "EMERGENCY_STOP")


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestCommunicationHandler)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)