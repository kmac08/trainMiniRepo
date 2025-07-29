import unittest

# Add the path to your wayside module

try:
    from Wayside_Controller.WaysideController import WaysideController
except ImportError:
    print("Warning: Could not import WaysideController")
    WaysideController = None


class TestWaysideController(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        if WaysideController is None:
            self.skipTest("WaysideController not available")
            
        # Create mock track data
        self.mock_track_data = {
            "Green": {
                "automatic": {
                    "blocks": [{"block": i, "occupied": False, "speed_hazard": False, "authority": 0} 
                              for i in range(151)],
                    "switches": [{"id": i, "suggested_toggle": False, "plc_num": 1, "toggled": False} 
                                for i in range(6)],
                    "crossings": [{"id": i, "toggled": False, "plc_num": 1} 
                                 for i in range(2)],
                    "traffic_lights": [{"id": i, "toggled": False, "plc_num": 1} 
                                      for i in range(10)]
                }
            }
        }
        x= [False] * 151  # Initialize blocksCovered with 75 False values
        for i in range(151):
            x[i]=True
        
        # Create WaysideController instance
        self.controller = WaysideController(
            data=self.mock_track_data,
            line="Green",
            mode="automatic",
            auto=True,
            plc_file="GreenLinePlcV1.py",
            plc_num=1,
            blocks_covered=x
        )

    def test_controller_initialization(self):
        """Test controller initialization with correct parameters"""
        self.assertEqual(self.controller.plcNum, 1)
        self.assertEqual(len(self.controller.blocksCovered), 151)
        self.assertFalse(self.controller.isOperational)


if __name__ == '__main__':
    unittest.main()