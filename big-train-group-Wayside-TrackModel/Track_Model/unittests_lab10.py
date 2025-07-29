import unittest
import os
import sys
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

print("Starting unit tests for Track Model functionality")

# Import modules to test
from Track_Model.trackmodel_working import MainWindow, DebugWindow, ClickableBox, InfoPanel
from Inputs import TrackModelInputs
from Track_Reader.track_reader import TrackBlock

class TestTrackModel(unittest.TestCase):
    """
    Test suite for the Track Model functionality in trackmodel_old.py
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up the QApplication once for all tests"""
        cls.app = QApplication.instance() or QApplication([])
    
    def setUp(self):
        """
        Set up test fixtures before each test method.
        Initialize a MainWindow instance for testing.
        """
        self.main_window = MainWindow()
        self.inputs = self.main_window.inputs
        
        # Create a mock block for testing
        self.mock_block = MagicMock(spec=TrackBlock)
        self.mock_block.line = "Green"
        self.mock_block.section = "A"
        self.mock_block.block_number = 5
        self.mock_block.length_m = 100.0
        self.mock_block.grade_percent = 2.5
        self.mock_block.speed_limit_kmh = 40.0
        self.mock_block.elevation_m = 10.0
        self.mock_block.get_direction_description.return_value = "Bidirectional"
        self.mock_block.get_infrastructure_description.return_value = "None"
    
    def tearDown(self):
        """
        Clean up after each test method.
        """
        self.main_window.close()
        self.main_window = None
    
    def test_failure_toggle(self):
        """
        Test that track failures can be toggled correctly
        """
        # Create a clickable box with our mock block
        box = ClickableBox(
            self.mock_block,
            self.main_window.info_panel,
            self.main_window,
            self.inputs
        )
        
        # Set this as the selected block
        self.main_window.set_selected_block(box)
        
        # Initial state should be no failures
        block_id = f"{self.mock_block.line[0].upper()}{self.mock_block.block_number}"
        self.assertFalse(self.inputs.get_power_failure(block_id))
        self.assertFalse(self.inputs.get_broken_rail_failure(block_id))
        self.assertFalse(self.inputs.get_track_circuit_failure(block_id))
        
        # Toggle power failure
        self.main_window.toggle_failure('power')
        self.assertTrue(self.inputs.get_power_failure(block_id))
        
        # Toggle it back off
        self.main_window.toggle_failure('power')
        self.assertFalse(self.inputs.get_power_failure(block_id))
        
        # Test broken rail failure
        self.main_window.toggle_failure('broken_rail')
        self.assertTrue(self.inputs.get_broken_rail_failure(block_id))
        
        # Test track circuit failure
        self.main_window.toggle_failure('track_circuit')
        self.assertTrue(self.inputs.get_track_circuit_failure(block_id))

    def test_temperature_setting(self):
        """
        Test that temperature can be set correctly through the InfoPanel
        """
        # Set inputs for the InfoPanel
        self.main_window.info_panel.inputs = self.inputs
        
        # Initial temp should be default (usually 70°F)
        initial_temp = self.inputs.get_temperature()
        
        # Try to set a valid temperature
        with patch.object(self.main_window.info_panel.temp_edit, 'text') as mock_text:
            mock_text.return_value = "75.5"
            self.main_window.info_panel._try_set_temperature()
            
        # Check if temperature was updated
        self.assertAlmostEqual(self.inputs.get_temperature(), 75.5)
        
        # Try to set an invalid temperature (below -25°F)
        with patch.object(self.main_window.info_panel.temp_edit, 'text') as mock_text:
            mock_text.return_value = "-30.0"
            with patch.object(self.main_window.info_panel, '_show_temp_error') as mock_error:
                self.main_window.info_panel._try_set_temperature()
                mock_error.assert_called_once()
            
        # Temperature should remain unchanged
        self.assertAlmostEqual(self.inputs.get_temperature(), 75.5)

    def test_debug_window_output_bits(self):
        """
        Test that the debug window can generate output bits correctly
        """
        # Get initial bit string
        with patch('Outputs.get_16bit_track_model_output', return_value="1010101010101010"):
            self.main_window.debug_window.display_bits()
            self.assertEqual(
                self.main_window.debug_window.bits_display.text(),
                "Output Bits: 1010101010101010"
            )

    def test_info_panel_clock_update(self):
        """
        Test that the info panel clock updates correctly
        """
        # Record initial clock text
        initial_text = self.main_window.info_panel.clock_label.text()
        
        # Manually set sim_start_time to 5 seconds ago
        self.main_window.info_panel.sim_start_time = self.main_window.info_panel.sim_start_time - 5
        
        # Update the clock
        self.main_window.update_info_panel_clock()
        
        # New text should be different (showing 5 seconds elapsed)
        updated_text = self.main_window.info_panel.clock_label.text()
        self.assertNotEqual(initial_text, updated_text)
        self.assertEqual(updated_text, "Elapsed Time: 00:00:05")


if __name__ == '__main__':
    unittest.main()