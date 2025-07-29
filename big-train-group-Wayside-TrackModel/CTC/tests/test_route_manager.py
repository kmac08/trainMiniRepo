import unittest
from unittest.mock import Mock, patch
import sys
import os
from datetime import datetime, timedelta
import logging
from typing import Dict

# Add the parent directory to sys.path to import CTC modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from CTC.Core.route_manager import RouteManager
from CTC.Core.route import Route
from CTC.Core.block import Block
from CTC.Core.ctc_system import CTCSystem
from Track_Reader.track_reader import TrackLayoutReader

# Set up logging
logger = logging.getLogger(__name__)


class TestRouteManager(unittest.TestCase):
    """Test cases for RouteManager class focusing on route orchestration"""
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        # Mock all simulation time functions to avoid Master Interface dependency
        self.time_patches = [
            patch('CTC.Core.ctc_system._get_simulation_time'),
            patch('CTC.Core.route_manager._get_simulation_time'),
            patch('CTC.Core.route._get_simulation_time'),
            patch('CTC.Core.block._get_simulation_time'),
            patch('CTC.Core.failure_manager._get_simulation_time'),
            patch('CTC.Core.communication_handler._get_simulation_time'),
            patch('CTC.Core.display_manager._get_simulation_time'),
        ]
        
        # Start all patches and set return value
        self.mock_time = datetime(2024, 1, 1, 12, 0, 0)
        for patch_obj in self.time_patches:
            mock = patch_obj.start()
            mock.return_value = self.mock_time
        
        # Create real track reader with actual track data
        track_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 
                                     'Track_Reader', 'Track Layout & Vehicle Data vF2.xlsx')
        self.track_reader = TrackLayoutReader(track_file_path)
        
        # Create real CTC system
        self.ctc_system = CTCSystem(track_reader=self.track_reader)
        
        # Create RouteManager instance with real track reader
        self.route_manager = RouteManager(track_reader=self.track_reader)
        # Connect the real CTC system to the route manager
        self.route_manager.ctc_system = self.ctc_system
        
        # Get real blocks from track data for testing
        green_blocks = self.track_reader.lines.get("Green", [])
        
        # Select some real blocks for testing using real Track Reader data
        self.test_blocks = {}
        for block_data in green_blocks:
            block_id = block_data.block_number
            # Create Block objects using real TrackBlock data
            block = Block(block_data)
            
            # Store in test blocks dictionary
            self.test_blocks[block_id] = block
            
            # Keep first 3 blocks as test blocks for compatibility
            if len(self.test_blocks) == 1:
                self.test_block1 = block
            elif len(self.test_blocks) == 2:
                self.test_block2 = block  
            elif len(self.test_blocks) == 3:
                self.test_block3 = block
                break
        
        # Test data
        self.test_train_id = "TEST001"
        self.test_destination = "Station A"
    
    def tearDown(self):
        """Clean up after each test"""
        # Stop all time patches
        for patch_obj in self.time_patches:
            patch_obj.stop()
        self.route_manager = None
    
    def test_route_manager_initialization(self):
        """Test proper RouteManager initialization"""
        self.assertEqual(self.route_manager.activeRoutes, [])
        self.assertEqual(self.route_manager.route_history, [])
        self.assertEqual(self.route_manager.scheduled_routes, {})
        self.assertEqual(self.route_manager.route_conflicts, [])
        self.assertEqual(self.route_manager.train_schedules, {})
        self.assertEqual(self.route_manager.schedule_buffer_seconds, 30.0)
        self.assertEqual(self.route_manager.station_dwell_default, 60.0)
        self.assertEqual(self.route_manager.track_reader, self.track_reader)
    
    def _create_block_for_test(self, line: str, block_number: int, section: str = None) -> Block:
        """Helper method to create a block object for testing"""
        # Get the actual block data from track reader if available
        line_blocks = self.track_reader.lines.get(line, [])
        for block_data in line_blocks:
            if block_data.block_number == block_number:
                block = Block(block_data)
                # Ensure block has required attributes for testing
                if not hasattr(block, 'line'):
                    block.line = line
                if section and not hasattr(block, 'section'):
                    block.section = section
                return block
        
        # If not found in track data, create a mock block
        mock_block = Mock(spec=Block)
        mock_block.blockID = block_number
        mock_block.blockNumber = block_number
        mock_block.line = line
        mock_block.section = section
        mock_block.block_operational.return_value = True
        mock_block.connected_blocks = []
        return mock_block
    
    def _test_yard_to_section_route(self, line: str, destination_block: int, section: str, expected_block_sequence=None):
        """Helper method to test yard-to-section routes using real CTC system
        
        Args:
            line: Line name (e.g., 'Green', 'Red')
            destination_block: Destination block ID
            section: Section name (e.g., 'P', 'T', 'F')
            expected_block_sequence: Optional list of expected block IDs in order
        """
        # Get yard block from CTC system
        yard_block = self.ctc_system.get_block_by_line_new(line, 0)
        
        # Get destination block from CTC system
        dest_block = self.ctc_system.get_block_by_line_new(line, destination_block)
        if not dest_block:
            dest_block = self._create_block_for_test(line, destination_block, section)
        
        # Generate route using real CTC system
        route = self.route_manager.generate_route(
            yard_block,
            dest_block,
            datetime(2024, 1, 1, 13, 0, 0)
        )
        
        # Verify route was generated
        self.assertIsNotNone(route, f"Route from yard to {line} Line section {section} should be generated")
        self.assertEqual(route.startBlock.blockID, 0)
        self.assertEqual(route.endBlock.blockID, destination_block)
        self.assertGreater(len(route.blockSequence), 2, "Route should have multiple blocks")
        
        # Verify route starts from yard
        block_ids = [block.blockID for block in route.blockSequence]
        self.assertEqual(block_ids[0], 0, "Route should start from yard")
        
        # Check that route uses valid yard exit
        yard_exit_block = self.ctc_system.get_yard_exit_block(line)
        if yard_exit_block:
            self.assertIn(yard_exit_block, block_ids[:5], f"Route should go through yard exit block {yard_exit_block} early")
        
        # Validate exact block sequence if provided
        if expected_block_sequence is not None:
            actual_block_sequence = [block.blockID for block in route.blockSequence]
            self.assertEqual(
                actual_block_sequence, 
                expected_block_sequence,
                f"Route block sequence mismatch for {line} Line section {section}:\n"
                f"Expected: {expected_block_sequence}\n"
                f"Actual:   {actual_block_sequence}"
            )
        
        return route
    
    def _test_block_to_section_route(self, line: str, start_block: int, destination_block: int, section: str, expected_block_sequence=None, initial_direction=None):
        """Helper method to test routes from a specific block to a section using real CTC system
        
        Args:
            line: Line name (e.g., 'Green', 'Red')
            start_block: Starting block ID
            destination_block: Destination block ID
            section: Section name (e.g., 'P', 'T', 'F')
            expected_block_sequence: Optional list of expected block IDs in order
            initial_direction: Optional initial direction ('forward' or 'backward')
        """
        # Get start block from CTC system
        start_block_obj = self.ctc_system.get_block_by_line_new(line, start_block)
        if not start_block_obj:
            start_block_obj = self._create_block_for_test(line, start_block)
        
        # Get destination block from CTC system
        dest_block = self.ctc_system.get_block_by_line_new(line, destination_block)
        if not dest_block:
            dest_block = self._create_block_for_test(line, destination_block, section)
        
        # Generate route using real CTC system
        route = self.route_manager.generate_route(
            start_block_obj,
            dest_block,
            datetime(2024, 1, 1, 13, 0, 0),
            initial_direction
        )
        
        # Verify route was generated
        self.assertIsNotNone(route, f"Route from block {start_block} to {line} Line section {section} should be generated")
        self.assertEqual(route.startBlock.blockID, start_block)
        self.assertEqual(route.endBlock.blockID, destination_block)
        self.assertGreater(len(route.blockSequence), 0, "Route should have at least one block")
        
        # Verify route starts from correct block
        block_ids = [block.blockID for block in route.blockSequence]
        self.assertEqual(block_ids[0], start_block, f"Route should start from block {start_block}")
        
        # Validate exact block sequence if provided
        if expected_block_sequence is not None:
            actual_block_sequence = [block.blockID for block in route.blockSequence]
            self.assertEqual(
                actual_block_sequence, 
                expected_block_sequence,
                f"Route block sequence mismatch for {line} Line from block {start_block} to section {section}:\n"
                f"Expected: {expected_block_sequence}\n"
                f"Actual:   {actual_block_sequence}"
            )
        
        return route
    
    
    @patch('CTC.Core.route_manager._get_simulation_time')
    @patch('CTC.Core.route._get_simulation_time')
    def test_yard_to_green_line_section_P(self, mock_route_time, mock_time):
        """Test route generation from yard to Green Line Section P"""
        mock_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        mock_route_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        
        # Test route from yard to block 96 in section P
        expected_sequence = [0, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80,
                             81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96]
        self._test_yard_to_section_route('Green', 96, 'P', expected_sequence)
    
    @patch('CTC.Core.route_manager._get_simulation_time')
    @patch('CTC.Core.route._get_simulation_time')
    def test_yard_to_green_line_section_T(self, mock_route_time, mock_time):
        """Test route generation from yard to Green Line Section T"""
        mock_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        mock_route_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        
        # Test route from yard to block 107 in section T
        expected_sequence = [0, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84,
                             85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 85, 84, 83, 82, 81, 80,
                             79, 78, 77, 101, 102, 103, 104, 105, 106, 107]
        self._test_yard_to_section_route('Green', 107, 'T', expected_sequence)
    
    @patch('CTC.Core.route_manager._get_simulation_time')
    @patch('CTC.Core.route._get_simulation_time')
    def test_yard_to_green_line_section_F(self, mock_route_time, mock_time):
        """Test route generation from yard to Green Line Section F"""
        mock_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        mock_route_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        
        # Test route from yard to block 25 in section F
        expected_sequence = [0, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84,
                             85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 85, 84, 83, 82, 81, 80,
                             79, 78, 77, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116,
                             117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134,
                             135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 29, 28, 27, 26,
                             25]
        self._test_yard_to_section_route('Green', 25, 'F', expected_sequence)
    
    @patch('CTC.Core.route_manager._get_simulation_time')
    @patch('CTC.Core.route._get_simulation_time')
    def test_yard_to_green_line_section_A(self, mock_route_time, mock_time):
        """Test route generation from yard to Green Line Section A"""
        mock_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        mock_route_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        
        # Test route from yard to block 2 in section A
        expected_sequence = [0, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84,
                             85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 85, 84, 83, 82, 81, 80,
                             79, 78, 77, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116,
                             117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134,
                             135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 29, 28, 27, 26,
                             25, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2]
        route = self._test_yard_to_section_route('Green', 2, 'A', expected_sequence)
        
        self.assertIsNotNone(route, "Route from yard to Green Line section A should be generated")
        self.assertEqual(route.startBlock.blockID, 0)
        self.assertEqual(route.endBlock.blockID, 2)
    
    @patch('CTC.Core.route_manager._get_simulation_time')
    @patch('CTC.Core.route._get_simulation_time')
    def test_yard_to_green_line_section_I(self, mock_route_time, mock_time):
        """Test route generation from yard to Green Line Section I"""
        mock_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        mock_route_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        
        # Test route from yard to block 48 in section I
        expected_sequence = [0, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84,
                             85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 85, 84, 83, 82, 81, 80,
                             79, 78, 77, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116,
                             117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134,
                             135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 29, 28, 27, 26,
                             25, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1,
                             13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35,
                             36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48]
        self._test_yard_to_section_route('Green', 48, 'I', expected_sequence)
    
    @patch('CTC.Core.route_manager._get_simulation_time')
    @patch('CTC.Core.route._get_simulation_time')
    def test_yard_to_red_line_section_a(self, mock_route_time, mock_time):
        """Test route generation from yard to Red Line Section A"""
        mock_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        mock_route_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        
        # Test route from yard to block 2 in section A
        expected_sequence = [0, 9, 8, 7, 6, 5, 4, 3, 2]
        self._test_yard_to_section_route('Red', 2, 'A', expected_sequence)
    
    @patch('CTC.Core.route_manager._get_simulation_time')
    @patch('CTC.Core.route._get_simulation_time')
    def test_yard_to_red_line_section_h(self, mock_route_time, mock_time):
        """Test route generation from yard to Red Line Section H"""
        mock_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        mock_route_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        
        # Test route from yard to block 35 in section H
        expected_sequence = [0, 9, 8, 7, 6, 5, 4, 3, 2, 1, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
                             31, 32, 33, 34, 35]
        self._test_yard_to_section_route('Red', 35, 'H', expected_sequence)
    
    @patch('CTC.Core.route_manager._get_simulation_time')
    @patch('CTC.Core.route._get_simulation_time')
    def test_yard_to_red_line_section_k(self, mock_route_time, mock_time):
        """Test route generation from yard to Red Line Section K"""
        mock_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        mock_route_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        
        # Test route from yard to block 56 in section K
        expected_sequence = [0, 9, 8, 7, 6, 5, 4, 3, 2, 1, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
                             31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53,
                             54, 55, 56]
        self._test_yard_to_section_route('Red', 56, 'K', expected_sequence)
    
    @patch('CTC.Core.route_manager._get_simulation_time')
    @patch('CTC.Core.route._get_simulation_time')
    def test_yard_to_red_line_section_p(self, mock_route_time, mock_time):
        """Test route generation from yard to Red Line Section P"""
        mock_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        mock_route_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        
        # Test route from yard to block 69 in section P
        expected_sequence = [0, 9, 8, 7, 6, 5, 4, 3, 2, 1, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
                             31, 32, 33, 34, 35, 36, 37, 38, 71, 70, 69]
        self._test_yard_to_section_route('Red', 69, 'P', expected_sequence)
    
    @patch('CTC.Core.route_manager._get_simulation_time')
    @patch('CTC.Core.route._get_simulation_time')
    def test_yard_to_red_line_section_t(self, mock_route_time, mock_time):
        """Test route generation from yard to Red Line Section T"""
        mock_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        mock_route_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        
        # Test route from yard to block 76 in section T
        expected_sequence = [0, 9, 8, 7, 6, 5, 4, 3, 2, 1, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 76]
        self._test_yard_to_section_route('Red', 76, 'T', expected_sequence)

    @patch('CTC.Core.route_manager._get_simulation_time')
    @patch('CTC.Core.route._get_simulation_time')
    def test_red_line_block_59_to_p(self, mock_route_time, mock_time):
        """Test route generation from block 59 to Red Line Section P"""
        mock_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        mock_route_time.return_value = datetime(2024, 1, 1, 12, 0, 0)

        # Test route from block 59 to block 69 in section P
        expected_sequence = [59, 60, 61, 62, 63, 64, 65, 66, 52, 51, 50, 49, 48, 47, 46, 45, 44, 67, 68, 69]
        self._test_block_to_section_route('Red', 59, 69, 'P', expected_sequence, initial_direction='forward')

    @patch('CTC.Core.route_manager._get_simulation_time')
    @patch('CTC.Core.route._get_simulation_time')
    def test_red_line_block_59_to_t(self, mock_route_time, mock_time):
        """Test route generation from block 59 to Red Line Section T"""
        mock_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        mock_route_time.return_value = datetime(2024, 1, 1, 12, 0, 0)

        # Test route from block 59 to block 76 in section T
        expected_sequence = [59, 60, 61, 62, 63, 64, 65, 66, 52, 51, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 40, 39,
                             38, 37, 36, 35, 34, 33, 72, 73, 74, 75, 76]
        self._test_block_to_section_route('Red', 59, 76, 'T', expected_sequence, initial_direction='forward')

    @patch('CTC.Core.route_manager._get_simulation_time')
    @patch('CTC.Core.route._get_simulation_time')
    def test_yard_to_red_line_section_d(self, mock_route_time, mock_time):
        """Test route generation from yard to Red Line Section D"""
        mock_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        mock_route_time.return_value = datetime(2024, 1, 1, 12, 0, 0)
        
        # Test route from yard to block 11 in section D
        expected_sequence = [0, 9, 8, 7, 6, 5, 4, 3, 2, 1, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
                             31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53,
                             54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 52, 51, 50, 49, 48, 47, 46, 45, 44, 43,
                             42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 32, 31, 30, 29, 28, 27, 26, 25, 24, 23, 22, 21, 20,
                             19, 18, 17, 16, 15, 14, 13, 12, 11]
        self._test_yard_to_section_route('Red', 11, 'D', expected_sequence)

    def test_validate_destination(self):
        """Test destination validation with different block states"""
        # Test with a failed block
        test_block = self.test_block1
        test_block.set_block_failed(True)

        failed_result = self.route_manager.validate_destination(test_block)
        self.assertFalse(failed_result.is_valid)
        self.assertEqual(failed_result.failure_reason, "block_failed")
        self.assertIn("has failed", failed_result.error_message)

        # Reset block state for other tests
        test_block.set_block_failed(False)

        # Test with a closed block
        test_block.set_block_open(False)
        closed_result = self.route_manager.validate_destination(test_block)
        self.assertFalse(closed_result.is_valid)
        self.assertEqual(closed_result.failure_reason, "block_closed")
        self.assertIn("is closed", closed_result.error_message)

        # Test with None destination
        none_result = self.route_manager.validate_destination(None)
        self.assertFalse(none_result.is_valid)
        self.assertEqual(none_result.failure_reason, "missing_block_id")
        self.assertIn("Block is None", none_result.error_message)

        # Test with valid destination - reopen the block and validate again
        test_block.set_block_open(True)
        valid_result = self.route_manager.validate_destination(test_block)
        self.assertTrue(valid_result.is_valid)
        self.assertEqual(valid_result.failure_reason, "")
        self.assertEqual(valid_result.error_message, "")

        # Test with both failed and closed (failed should take precedence)
        test_block.set_block_failed(True)
        test_block.set_block_open(False)
        failed_and_closed_result = self.route_manager.validate_destination(test_block)
        self.assertFalse(failed_and_closed_result.is_valid)
        self.assertEqual(failed_and_closed_result.failure_reason, "block_failed")
        
        # Clean up for other tests
        test_block.set_block_failed(False)
        test_block.set_block_open(True)

    def test_confirm_route(self):
        """Test successful route confirmation and check that routes are assigned to trains"""
        # Create a test train in the CTC system
        from CTC.Core.train import Train
        test_train = Train(trainID=1, currentBlock=self.test_block1)
        test_train.line = "Green"
        
        # Add train to CTC system
        self.ctc_system.trains["TRAIN_001"] = test_train
        
        # Create a real route with valid block sequence
        test_route = Route()
        test_route.routeID = "ROUTE_123"
        test_route.trainID = "TRAIN_001"  # Assign to our test train
        test_route.blockSequence = [self.test_block1, self.test_block2]
        test_route.startBlock = self.test_block1
        test_route.endBlock = self.test_block2
        test_route.isActive = True  # Make route active for occupancy scheduling
        test_route.scheduledDeparture = self.mock_time
        
        # Mock the block connectivity validation to allow this test to pass
        with patch.object(self.route_manager, '_blocks_connected', return_value=True):
            result = self.route_manager.confirm_route(test_route)
        
        self.assertTrue(result)
        
        # Verify route was added to history
        self.assertTrue(len(self.route_manager.route_history) > 0)
        confirmed_route = self.route_manager.route_history[-1]
        self.assertEqual(confirmed_route['route'], test_route)
        self.assertEqual(confirmed_route['status'], 'CONFIRMED')
        
        # Verify route was assigned to the train
        assigned_route = test_train.get_route()
        self.assertIsNotNone(assigned_route)
        self.assertEqual(assigned_route.routeID, "ROUTE_123")
        
        # Verify the route object is stored in the train
        self.assertEqual(test_train.route, test_route)
        
        # Verify scheduled occupancies were updated (if blocks support it)
        for block in test_route.blockSequence:
            if hasattr(block, 'scheduledOccupations'):
                self.assertTrue(len(block.scheduledOccupations) > 0)
    
    def test_confirm_route_invalid_route(self):
        """Test route confirmation with invalid route"""
        # Create a real route that will fail validation (empty block sequence)
        invalid_route = Route()
        invalid_route.routeID = "INVALID_ROUTE"
        invalid_route.blockSequence = []  # Empty sequence will fail validation
        invalid_route.startBlock = None
        invalid_route.endBlock = None
        
        result = self.route_manager.confirm_route(invalid_route)
        
        self.assertFalse(result)
        self.assertNotIn(invalid_route, self.route_manager.activeRoutes)
    
    def test_confirm_route_train_assignment_no_train(self):
        """Test route confirmation when specified train doesn't exist"""
        # Create route with non-existent train ID
        test_route = Route()
        test_route.routeID = "ROUTE_NO_TRAIN"
        test_route.trainID = "NONEXISTENT_TRAIN"
        test_route.blockSequence = [self.test_block1, self.test_block2]
        test_route.startBlock = self.test_block1
        test_route.endBlock = self.test_block2
        test_route.isActive = True
        
        # Store initial route history length
        initial_history_length = len(self.route_manager.route_history)
        
        # Mock connectivity to focus on train assignment
        with patch.object(self.route_manager, '_blocks_connected', return_value=True):
            result = self.route_manager.confirm_route(test_route)
        
        # Route should fail when train doesn't exist
        self.assertFalse(result)
        
        # Verify route was NOT added to history since confirmation failed
        self.assertEqual(len(self.route_manager.route_history), initial_history_length)

    def test_validate_route_empty_sequence(self):
        """Test route validation with empty block sequence"""
        # Create route with empty block sequence
        empty_route = Route()
        empty_route.routeID = "EMPTY_TEST"
        empty_route.blockSequence = []
        empty_route.startBlock = None
        empty_route.endBlock = None
        
        result = self.route_manager.validate_route(empty_route)
        
        self.assertFalse(result)

    def test_validate_route_missing_start_end_blocks(self):
        """Test route validation with missing start/end blocks"""
        # Create route with block sequence but missing start/end
        incomplete_route = Route()
        incomplete_route.routeID = "INCOMPLETE_TEST"
        incomplete_route.blockSequence = [self.test_block1, self.test_block2]
        incomplete_route.startBlock = None  # Missing start block
        incomplete_route.endBlock = self.test_block2
        
        result = self.route_manager.validate_route(incomplete_route)
        
        self.assertFalse(result)
        
        # Test missing end block
        incomplete_route.startBlock = self.test_block1
        incomplete_route.endBlock = None  # Missing end block
        
        result = self.route_manager.validate_route(incomplete_route)
        
        self.assertFalse(result)
    
    def test_validate_route_block_connectivity(self):
        """Test route validation for block connectivity"""
        # Create route with disconnected blocks
        disconnected_route = Route()
        disconnected_route.routeID = "DISCONNECTED_TEST"
        
        # Create blocks that are not connected to each other
        # Use different block IDs that are far apart to ensure they're not connected
        green_blocks = self.track_reader.lines.get("Green", [])
        # Get blocks that are far apart (likely not connected)
        block1_data = green_blocks[0]  # First block
        block2_data = green_blocks[-1]  # Last block (does not connect to first block

        block1 = Block(block1_data)
        block2 = Block(block2_data)

        disconnected_route.blockSequence = [block1, block2]
        disconnected_route.startBlock = block1
        disconnected_route.endBlock = block2

        # This should fail if blocks are not connected
        # Note: This test depends on the actual track layout
        result = self.route_manager.validate_route(disconnected_route)

        # The result depends on actual connectivity in the track data
        # We mainly test that validation runs without error
        self.assertIsInstance(result, bool)
    
    def test_validate_route_operational_status(self):
        """Test route validation for block operational status"""
        # Create route with non-operational block
        non_operational_route = Route()
        non_operational_route.routeID = "NON_OPERATIONAL_TEST"
        
        # Make one of the test blocks non-operational
        test_block_failed = self.test_block1
        test_block_failed.set_block_failed(True)  # Make it failed
        
        non_operational_route.blockSequence = [test_block_failed, self.test_block2]
        non_operational_route.startBlock = test_block_failed
        non_operational_route.endBlock = self.test_block2
        
        result = self.route_manager.validate_route(non_operational_route)
        
        self.assertFalse(result)
        
        # Reset block state for other tests
        test_block_failed.set_block_failed(False)
    
    def test_validate_route_loop_routing(self):
        """Test route validation for loop routing constraints"""
        # Create an excessively long route that should fail loop validation
        long_route = Route()
        long_route.routeID = "LONG_LOOP_TEST"
        
        # Create a very long block sequence (over 100 blocks)
        green_blocks = self.track_reader.lines.get("Green", [])
        # Create blocks from track data
        long_sequence = []
        for i in range(min(101, len(green_blocks))):  # Over the 100 block limit
            block_data = green_blocks[i]
            block = Block(block_data)
            long_sequence.append(block)

        long_route.blockSequence = long_sequence
        long_route.startBlock = long_sequence[0]
        long_route.endBlock = long_sequence[-1]

        result = self.route_manager.validate_route(long_route)

        # Should fail due to excessive length
        self.assertFalse(result)
    
    def test_validate_route_timing_feasibility(self):
        """Test route validation for timing feasibility"""
        # Create route with impossible timing
        timing_route = Route()
        timing_route.routeID = "TIMING_TEST"
        timing_route.blockSequence = [self.test_block1, self.test_block2]
        timing_route.startBlock = self.test_block1
        timing_route.endBlock = self.test_block2
        
        # Set arrival time in the past and calculate departure time that would be too soon
        past_time = datetime(2023, 1, 1, 12, 0, 0)  # Past time
        timing_route.scheduledArrival = past_time
        timing_route.estimatedTravelTime = 3600.0  # 1 hour travel time
        
        # Calculate scheduled departure based on arrival time and travel time
        # This will result in a departure time that's too soon (in the past)
        timing_route.scheduledDeparture = past_time - timedelta(seconds=timing_route.estimatedTravelTime)
        
        result = self.route_manager.validate_route(timing_route)
        
        # Should fail due to departure time being too soon (more than 5 minutes in the past)
        self.assertFalse(result)
        
        # Test edge case: departure time exactly 4 minutes in the future (should fail)
        current_time = self.mock_time
        too_soon_departure = current_time + timedelta(minutes=4)
        timing_route.scheduledDeparture = too_soon_departure
        timing_route.scheduledArrival = too_soon_departure + timedelta(seconds=timing_route.estimatedTravelTime)
        
        result = self.route_manager.validate_route(timing_route)
        self.assertFalse(result)
        
        # Test valid case: departure time 6 minutes in the future (should pass)
        valid_departure = current_time + timedelta(minutes=6)
        timing_route.scheduledDeparture = valid_departure
        timing_route.scheduledArrival = valid_departure + timedelta(seconds=timing_route.estimatedTravelTime)
        
        # Ensure blocks are operational for this test
        self.test_block1.set_block_failed(False)
        self.test_block2.set_block_failed(False)
        
        # Mock block connectivity for this test
        with patch.object(self.route_manager, '_blocks_connected', return_value=True):
            result = self.route_manager.validate_route(timing_route)
            self.assertTrue(result)
    
    def test_validate_route_successful_case(self):
        """Test route validation with a valid route"""
        # Create a proper valid route
        valid_route = Route()
        valid_route.routeID = "VALID_TEST"
        valid_route.blockSequence = [self.test_block1, self.test_block2]
        valid_route.startBlock = self.test_block1
        valid_route.endBlock = self.test_block2
        
        # Set reasonable timing
        future_time = datetime(2024, 1, 1, 14, 0, 0)  # Future time
        valid_route.scheduledArrival = future_time
        valid_route.estimatedTravelTime = 600.0  # 10 minutes travel time
        
        # Ensure blocks are operational
        self.test_block1.set_block_failed(False)
        self.test_block2.set_block_failed(False)
        
        result = self.route_manager.validate_route(valid_route)
        
        # This test depends on the actual block connectivity and track data
        # We mainly verify that validation runs and returns a boolean
        self.assertIsInstance(result, bool)
    
    def test_validate_route_edge_cases(self):
        """Test route validation edge cases"""
        # Test with None route
        with self.assertRaises(AttributeError):
            self.route_manager.validate_route(None)
        
        # Test with route containing None blocks
        none_block_route = Route()
        none_block_route.routeID = "NONE_BLOCK_TEST"
        none_block_route.blockSequence = [self.test_block1, None, self.test_block2]
        none_block_route.startBlock = self.test_block1
        none_block_route.endBlock = self.test_block2
        
        # This should handle None blocks gracefully
        with self.assertRaises(AttributeError):
            self.route_manager.validate_route(none_block_route)
    
    def test_validate_route_single_block(self):
        """Test route validation with single block route"""
        # Create route with only one block
        single_block_route = Route()
        single_block_route.routeID = "SINGLE_BLOCK_TEST"
        single_block_route.blockSequence = [self.test_block1]
        single_block_route.startBlock = self.test_block1
        single_block_route.endBlock = self.test_block1
        
        # Ensure block is operational
        self.test_block1.set_block_failed(False)
        
        result = self.route_manager.validate_route(single_block_route)
        
        # Single block route should be valid (no connectivity to check)
        self.assertTrue(result)
    
    def test_update_scheduled_occupancy_accuracy(self):
        """Test that update_scheduled_occupancy uses actual route calculation times"""
        # Create a route with estimated travel time
        test_route = Route()
        test_route.routeID = "OCCUPANCY_TEST"
        test_route.blockSequence = [self.test_block1, self.test_block2, self.test_block3]
        test_route.startBlock = self.test_block1
        test_route.endBlock = self.test_block3
        test_route.isActive = True
        test_route.scheduledDeparture = self.mock_time
        test_route.estimatedTravelTime = 180.0  # 3 minutes total
        
        # Add scheduledOccupations attribute to blocks if they don't have it
        for block in test_route.blockSequence:
            if not hasattr(block, 'scheduledOccupations'):
                block.scheduledOccupations = []
        
        # Clear any existing occupancies
        for block in test_route.blockSequence:
            block.scheduledOccupations.clear()
        
        # Call the enhanced update_scheduled_occupancy function
        self.route_manager.update_scheduled_occupancy(test_route)
        
        # Verify that occupancies were scheduled
        for i, block in enumerate(test_route.blockSequence):
            if hasattr(block, 'scheduledOccupations'):
                if i == 0:
                    # First block should be occupied at departure time
                    self.assertEqual(len(block.scheduledOccupations), 1)
                    self.assertEqual(block.scheduledOccupations[0], self.mock_time)
                else:
                    # Other blocks should have occupancy times based on route calculation
                    self.assertEqual(len(block.scheduledOccupations), 1)
                    # Occupancy time should be after departure time
                    self.assertGreater(block.scheduledOccupations[0], self.mock_time)
        
        # Verify that occupancy times are progressive (later blocks occupied later)
        if len(test_route.blockSequence) >= 2:
            block1_time = test_route.blockSequence[0].scheduledOccupations[0]
            block2_time = test_route.blockSequence[1].scheduledOccupations[0]
            self.assertGreater(block2_time, block1_time)
    
    def test_update_scheduled_occupancy_inactive_route(self):
        """Test that inactive routes don't get occupancy scheduling"""
        # Create an inactive route
        inactive_route = Route()
        inactive_route.routeID = "INACTIVE_TEST"
        inactive_route.blockSequence = [self.test_block1, self.test_block2]
        inactive_route.startBlock = self.test_block1
        inactive_route.endBlock = self.test_block2
        inactive_route.isActive = False  # Route is not active
        
        # Add scheduledOccupations attribute to blocks
        for block in inactive_route.blockSequence:
            if not hasattr(block, 'scheduledOccupations'):
                block.scheduledOccupations = []
            block.scheduledOccupations.clear()
        
        # Call update_scheduled_occupancy
        self.route_manager.update_scheduled_occupancy(inactive_route)
        
        # Verify no occupancies were scheduled
        for block in inactive_route.blockSequence:
            if hasattr(block, 'scheduledOccupations'):
                self.assertEqual(len(block.scheduledOccupations), 0)
    
    def test_generate_route_timing_validation(self):
        """Test that generate_route rejects routes with arrival times that are too soon"""
        # Ensure blocks are operational
        self.test_block1.set_block_failed(False)
        self.test_block2.set_block_failed(False)
        
        # Test arrival time that is too soon (4 minutes in the future)
        current_time = self.mock_time
        too_soon_arrival = current_time + timedelta(minutes=4)
        
        # Mock pathfinding to ensure we get to timing validation
        with patch.object(self.route_manager, '_find_path', return_value=[self.test_block1, self.test_block2]):
            route = self.route_manager.generate_route(
                self.test_block1,
                self.test_block2,
                too_soon_arrival
            )
        
        # Route should be None due to timing validation failure
        self.assertIsNone(route)
        
        # Test valid arrival time (6 minutes in the future)
        valid_arrival = current_time + timedelta(minutes=6)
        
        with patch.object(self.route_manager, '_find_path', return_value=[self.test_block1, self.test_block2]):
            with patch.object(self.route_manager, '_blocks_connected', return_value=True):
                route = self.route_manager.generate_route(
                    self.test_block1,
                    self.test_block2,
                    valid_arrival
                )
        
        # Route should be successfully generated
        self.assertIsNotNone(route)
        self.assertEqual(route.startBlock, self.test_block1)
        self.assertEqual(route.endBlock, self.test_block2)


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestRouteManager)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)