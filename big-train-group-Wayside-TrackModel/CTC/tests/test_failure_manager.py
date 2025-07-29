"""
Test Failure Manager Module
===========================
Tests for the refactored FailureManager that delegates to Block class methods
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from CTC.Core.failure_manager import FailureManager


class TestFailureManager(unittest.TestCase):
    """Test cases for FailureManager system coordination"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock the simulation time function
        self.time_patcher = patch('CTC.Core.failure_manager._get_simulation_time')
        self.mock_time = self.time_patcher.start()
        self.mock_time.return_value = datetime.now()
        
        self.failure_manager = FailureManager()
        
        # Mock CTC system
        self.mock_ctc = Mock()
        self.failure_manager.ctc_system = self.mock_ctc
        
        # Mock other components
        self.failure_manager.communication_handler = Mock()
        self.failure_manager.display_manager = Mock()
    
    def tearDown(self):
        """Clean up after tests"""
        self.time_patcher.stop()
    
    # NOTE: Scheduled closure tests removed - these methods are now in CTC System
    
    def test_add_failed_block_delegates_to_block(self):
        """Test that add_failed_block delegates to block's set_block_failed"""
        # Create mock block
        mock_block = Mock()
        mock_block.set_block_failed = Mock()
        mock_block.blockID = 5
        
        # Mock get_train_list to return empty list
        self.mock_ctc.get_train_list.return_value = []
        
        # Add failed block
        self.failure_manager.add_failed_block(mock_block)
        
        # Verify delegation
        mock_block.set_block_failed.assert_called_once_with(True, reason="System failure detected")
        self.assertIn(mock_block, self.failure_manager.failedBlocks)
    
    def test_remove_failed_block_delegates_to_block(self):
        """Test that remove_failed_block delegates to block's set_block_failed"""
        # Create mock block
        mock_block = Mock()
        mock_block.set_block_failed = Mock()
        mock_block.blockID = 5
        
        # Add block to failed list first
        self.failure_manager.failedBlocks.append(mock_block)
        
        # Remove failed block
        result = self.failure_manager.remove_failed_block(mock_block)
        
        # Verify delegation
        mock_block.set_block_failed.assert_called_once_with(False, reason="Failure resolved")
        self.assertNotIn(mock_block, self.failure_manager.failedBlocks)
        self.assertTrue(result)
    
    def test_maintenance_closures_basic_tracking(self):
        """Test that basic maintenance closures tracking still works"""
        # Test that the maintenanceClosures dict is properly initialized
        self.assertIn('Green', self.failure_manager.maintenanceClosures)
        self.assertIn('Red', self.failure_manager.maintenanceClosures)
        self.assertIn('Blue', self.failure_manager.maintenanceClosures)
        
        # Test adding to maintenance closures (this would be done by external systems now)
        self.failure_manager.maintenanceClosures['Green'].append(5)
        self.assertIn(5, self.failure_manager.maintenanceClosures['Green'])


if __name__ == '__main__':
    unittest.main()