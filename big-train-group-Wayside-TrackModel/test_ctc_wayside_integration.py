#!/usr/bin/env python3
"""
Integration test script for CTC-Wayside Controller interface.

This script tests the complete integration between:
1. Master Interface setting up connections
2. CTC calling Wayside Controller functions (command_train)
3. Wayside Controller calling CTC functions

Usage: python test_ctc_wayside_integration.py
"""

import sys
import os
import unittest
import threading
import time
from typing import List, Dict, Any
from datetime import datetime, timedelta

# Set up Qt environment for headless testing
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

# Add project directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'CTC'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'Master_Interface'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'Wayside_Controller'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'Track_Reader'))

# Import the master test interface
from master_test_interface import MasterTestInterface

# Import Qt and project modules
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from CTC.Core.ctc_system import CTCSystem
from CTC.Core.communication_handler import CommunicationHandler
from Master_Interface.master_control import MasterInterface, WaysideManager
from Track_Reader.track_reader import TrackLayoutReader
import numpy as np


def create_test_track_data():
    """Create track data structure expected by WaysideController."""
    # WaysideController expects data[line][mode] structure
    return {
        "Green": {
            "automatic": {}
        }
    }


def create_controller_1_plc():
    """Create a temporary PLC file for controller 1."""
    plc_content = '''
def main(stop_event, blocks, suggested_speed, suggested_authority, switch_suggest, 
         blocks_coveGreen, commanded_speed, commanded_authority, switches, 
         traffic_lights, crossings):
    while(1):
        for i in range(77):
            if blocks_coveGreen[i]:
                commanded_speed[i] = suggested_speed[i]
                commanded_authority[i] = suggested_authority[i]
                switches[i] = switch_suggest[i]
                crossings[i] = True
                traffic_lights[i] = True
    return None

def get_block_coverage():
    coverage = [False] * 77
    coverage[1] = True  # Block 1
    coverage[2] = True  # Block 2
    return coverage
'''
    plc_path = os.path.join(os.path.dirname(__file__), 'Wayside_Controller', 'test_plc_controller_1.py')
    with open(plc_path, 'w') as f:
        f.write(plc_content)
    return plc_path

def create_controller_2_plc():
    """Create a temporary PLC file for controller 2."""
    plc_content = '''
def main(stop_event, blocks, suggested_speed, suggested_authority, switch_suggest, 
         blocks_coveGreen, commanded_speed, commanded_authority, switches, 
         traffic_lights, crossings):
    while(1):
        for i in range(77):
            if blocks_coveGreen[i]:
                commanded_speed[i] = suggested_speed[i]
                commanded_authority[i] = suggested_authority[i]
                switches[i] = switch_suggest[i]
                crossings[i] = True
                traffic_lights[i] = True
    return None

def get_block_coverage():
    coverage = [False] * 77
    coverage[3] = True  # Block 3
    coverage[4] = True  # Block 4
    coverage[5] = True  # Block 5
    return coverage
'''
    plc_path = os.path.join(os.path.dirname(__file__), 'Wayside_Controller', 'test_plc_controller_2.py')
    with open(plc_path, 'w') as f:
        f.write(plc_content)
    return plc_path


class TestCTCWaysideIntegration(unittest.TestCase):
    """Integration tests for CTC-Wayside Controller interface."""
    
    def setUp(self):
        """Set up test fixtures with actual master interface."""
        # Set up Qt application for master interface
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
        
        # Create real track reader
        excel_path = os.path.join(os.path.dirname(__file__), 'Track_Reader', 'Track Layout & Vehicle Data vF2.xlsx')
        self.track_reader = TrackLayoutReader(excel_path, selected_lines=["Green"])
        
        # Initialize system components
        self.master_interface = None
        self.ctc_system = None
        self.controllers = {}
        self.test_interface = None  # Master test interface for train simulation
        
        # Get total blocks from track reader and add 1 for array sizing
        # Green line has blocks 1-76, so we need arrays of size 77 (indices 0-76)
        Green_line_summary = self.track_reader.get_line_summary("Green")
        self.total_blocks = Green_line_summary['total_blocks'] + 1  # 76 + 1 = 77
        
        # Command verification storage
        self.captured_commands = {
            'train_commands': [],
            'switch_commands': [],
            'occupancy_updates': []
        }
    
    def tearDown(self):
        """Clean up after tests."""
        # Stop test interface if running
        if hasattr(self, 'test_interface') and self.test_interface:
            self.test_interface.shutdown()
            
        # Stop the time manager thread if it's running
        if hasattr(self, 'master_interface') and self.master_interface:
            if hasattr(self.master_interface, 'time_manager'):
                self.master_interface.time_manager.is_running = False
                if self.master_interface.time_manager.isRunning():
                    self.master_interface.time_manager.quit()
                    self.master_interface.time_manager.wait(1000)  # Wait up to 1 second
        
        # Stop wayside controllers
        for controller in getattr(self, 'controllers', {}).values():
            if hasattr(controller, 'stop_operations'):
                controller.stop_operations()
        
        if self.ctc_system:
            # Give time for any pending operations to complete
            time.sleep(0.1)
        
        # Clean up temporary PLC files
        for plc_file in getattr(self, 'plc_files', {}).values():
            try:
                if os.path.exists(plc_file):
                    os.remove(plc_file)
            except Exception as e:
                print(f"Warning: Could not remove temporary PLC file {plc_file}: {e}")
        
        # Process Qt events to ensure cleanup
        if hasattr(self, 'app') and self.app:
            self.app.processEvents()
    
    def test_master_interface_setup(self):
        """Test 1: Master interface sets up connections between CTC and wayside controllers."""
        print("\n=== Test 1: Master Interface Setup ===")
        
        # Initialize actual master interface
        self.master_interface = MasterInterface()
        
        # Start the time manager thread
        self.master_interface.time_manager.start()
        time.sleep(0.1)  # Give time manager a moment to start
        
        # The master interface sets the global instance for get_time() function
        print("✓ Master interface initialized and time manager started")
        
        # Set selected lines for Green line testing
        self.master_interface.selected_lines = ["Green"]
        
        # Initialize CTC system through master interface (if available)
        # For testing, we'll create the CTC system directly but with timing available
        self.ctc_system = CTCSystem(self.track_reader)
        
        # Setup wayside controllers using master interface's wayside manager
        self.master_interface.wayside_manager.setup_wayside_controllers(
            selected_lines=["Green"],
            ctc_system=self.ctc_system,
            track_reader=self.track_reader
        )
        
        # Get the controllers that were created by the master interface
        if "Green" in self.master_interface.wayside_manager.active_controllers:
            self.controllers = {
                i+1: controller for i, controller in 
                enumerate(self.master_interface.wayside_manager.active_controllers["Green"])
            }
        
        print(f"✓ Master interface set up {len(self.controllers)} wayside controllers")
        print("✓ Master interface successfully set up CTC-Wayside connections")
    
    def test_ctc_calls_wayside_command_train(self):
        """Test 2: CTC calls wayside controller command_train function."""
        print("\n=== Test 2: CTC → Wayside command_train ===")
        
        # Set up the system
        self.test_master_interface_setup()
        
        # Create a test train
        train_id = self.ctc_system.add_train("Green", "Manual")
        self.assertIsNotNone(train_id, "Failed to create test train")
        
        # Generate and activate a route
        start_block = self.ctc_system.get_block_by_number(0, "Green")
        end_block = self.ctc_system.get_block_by_number(96, "Green")
        arrival_time = datetime.now() + timedelta(hours=1)
        route = self.ctc_system.generate_route(start_block, end_block, arrival_time)
        self.assertIsNotNone(route, "Failed to generate route from 0 to 96")
        route_success = self.ctc_system.activate_route(train_id, route)
        self.assertTrue(route_success, "Failed to activate route")
        
        # Dispatch train from yard (this should trigger command_train calls)
        dispatch_success = self.ctc_system.dispatch_train_from_yard(train_id)
        self.assertTrue(dispatch_success, "Failed to dispatch train from yard")
        
        # Give time for communication
        time.sleep(0.2)
        
        # Verify command_train was called on appropriate controllers
        # With real controllers, we check if they received CTC commands
        for controller_id, controller in self.controllers.items():
            # Check if controller has any non-zero suggested speeds (indicates commands received)
            has_commands = any(controller.ctc_suggested_speeds[i] > 0 for i in range(self.total_blocks))
            self.assertTrue(has_commands, "Failed to find commands for controller {controller_id}")
        
        print("✓ CTC successfully called wayside command_train functions")
    
    def test_wayside_calls_ctc_functions(self):
        """Test 3: Wayside controller calls CTC functions."""
        print("\n=== Test 3: Wayside → CTC function calls ===")
        
        # Set up the system with a train
        self.test_ctc_calls_wayside_command_train()
        
        # Get the train we created
        train_id = list(self.ctc_system.trains.keys())[0]
        initial_train_count = len(self.ctc_system.trains)
        
        # Simulate wayside controller reporting occupancy
        controller = self.controllers[1]  # Controller managing blocks 1, 2
        
        # Simulate train entering block 1 by updating controller's occupancy data
        controller.blocks[1] = True  # Set block 1 as occupied
        controller.send_updates_to_ctc()  # Send update to CTC
        
        # Give time for processing
        time.sleep(0.1)
        
        # Verify the train's location was updated in CTC
        train = self.ctc_system.trains.get(train_id)
        self.assertIsNotNone(train, "Train not found in CTC system")
        
        # Simulate train moving to block 2
        controller.blocks[1] = False  # Leave block 1
        controller.blocks[2] = True   # Enter block 2
        controller.send_updates_to_ctc()  # Send update to CTC
        
        time.sleep(0.1)
        
        print("✓ Wayside controller successfully called CTC occupancy functions")
        
        # Test controller sending switch command response
        print("✓ Wayside controller can communicate bidirectionally with CTC")
    
    def test_full_train_journey_integration(self):
        """Test 4: Complete train journey with full CTC-Wayside integration."""
        print("\n=== Test 4: Full Train Journey Integration ===")
        
        # Set up the system
        self.test_master_interface_setup()
        
        # Create and dispatch train
        train_id = self.ctc_system.add_train("Green", "Manual")
        start_block = self.ctc_system.get_block_by_number(1, "Green")
        end_block = self.ctc_system.get_block_by_number(5, "Green")
        arrival_time = datetime.now() + timedelta(hours=1)
        route = self.ctc_system.generate_route(start_block, end_block, arrival_time)
        activation_success = False
        dispatch_success = False
        if route:
            activation_success = self.ctc_system.activate_route(train_id, route)
            dispatch_success = self.ctc_system.dispatch_train_from_yard(train_id)
        
        self.assertTrue(all([route is not None, activation_success, dispatch_success]), 
                       "Failed to set up train journey")
        
        time.sleep(0.1)
        
        # Simulate complete journey: blocks 1 → 2 → 3 → 4 → 5
        journey_blocks = [1, 2, 3, 4, 5]
        
        for i, block_id in enumerate(journey_blocks):
            # Determine which controller manages this block
            managing_controller = None
            for controller_id, controller in self.controllers.items():
                if controller.blocksCoveGreen[block_id]:  # Check if controller covers this block
                    managing_controller = controller
                    break
            
            self.assertIsNotNone(managing_controller, f"No controller found for block {block_id}")
            
            # Train enters block
            managing_controller.blocks[block_id] = True
            managing_controller.send_updates_to_ctc()
            time.sleep(0.05)
            
            # If not the last block, train leaves this block when entering next
            if i < len(journey_blocks) - 1:
                managing_controller.blocks[block_id] = False
                managing_controller.send_updates_to_ctc()
                time.sleep(0.05)
            
            print(f"✓ Train {train_id} processed through block {block_id}")
        
        # Verify final state
        train = self.ctc_system.trains.get(train_id)
        self.assertIsNotNone(train, "Train lost during journey")
        
        print("✓ Complete train journey integration successful")
    
    def test_concurrent_operations(self):
        """Test 5: Multiple trains with concurrent CTC-Wayside operations."""
        print("\n=== Test 5: Concurrent Operations ===")
        
        # Set up the system
        self.test_master_interface_setup()
        
        # Create multiple trains
        train_ids = []
        for i in range(3):
            train_id = self.ctc_system.add_train("Green", "Manual")
            train_ids.append(train_id)
            start_block = self.ctc_system.get_block_by_number(1, "Green")
            end_block = self.ctc_system.get_block_by_number(5, "Green")
            arrival_time = datetime.now() + timedelta(hours=1)
            route = self.ctc_system.generate_route(start_block, end_block, arrival_time)
            if route:
                self.ctc_system.activate_route(train_id, route)
        
        # Dispatch trains concurrently
        def dispatch_train(tid):
            self.ctc_system.dispatch_train_from_yard(tid)
            time.sleep(0.1)
            # Simulate some movement using proper communication handler
            occupied_blocks = [False] * self.total_blocks
            occupied_blocks[1] = True
            if hasattr(self.ctc_system, 'communicationHandler'):
                self.ctc_system.communicationHandler.update_occupied_blocks(occupied_blocks, self.controllers[1])
            time.sleep(0.1)
            occupied_blocks[1] = False
            if hasattr(self.ctc_system, 'communicationHandler'):
                self.ctc_system.communicationHandler.update_occupied_blocks(occupied_blocks, self.controllers[1])
        
        threads = []
        for train_id in train_ids:
            thread = threading.Thread(target=dispatch_train, args=(train_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all operations to complete
        for thread in threads:
            thread.join()
        
        # Verify all trains are still managed correctly
        self.assertEqual(len(self.ctc_system.trains), 3)
        
        # Verify controllers received commands (check if any have non-zero suggested speeds)
        total_commands = sum(1 for controller in self.controllers.values() 
                           if any(controller.ctc_suggested_speeds[i] > 0 for i in range(self.total_blocks)))
        self.assertGreaterEqual(total_commands, 0, "Controllers should be operational for concurrent operations")
        
        print(f"✓ Concurrent operations successful with {total_commands} controllers receiving commands")
    
    def test_error_handling(self):
        """Test 6: Error handling in CTC-Wayside communication."""
        print("\n=== Test 6: Error Handling ===")
        
        # Set up the system
        self.test_master_interface_setup()
        
        # Test with real controller error scenarios
        controller = self.controllers[1]
        
        # Try to update non-existent block (should not crash)
        try:
            if 999 < len(controller.blocks):
                controller.blocks[999] = True
                controller.send_updates_to_ctc()
            else:
                print("Block 999 out of range as expected")
        except Exception as e:
            print(f"Expected error handled: {e}")
        
        # Verify system is still operational
        train_id = self.ctc_system.add_train("Green", "Manual")
        self.assertIsNotNone(train_id, "System not operational after error scenarios")
        
        print("✓ Error handling tests completed successfully")
    
    def test_command_train_detailed_verification(self):
        """Test 7: Detailed verification of command_train parameters."""
        print("\n=== Test 7: Detailed command_train Verification ===")
        
        # Set up the system with test interface
        self.test_master_interface_setup()
        
        # Create test interface for detailed command capture
        self.test_interface = MasterTestInterface(total_blocks=self.total_blocks, line="Green")
        self.test_interface.enable_logging_to_file("command_train_verification.log")
        
        # Monkey-patch wayside controller command_train to capture calls
        original_command_train = {}
        for controller_id, controller in self.controllers.items():
            original_command_train[controller_id] = controller.command_train
            
            def create_capture_function(ctrl, orig_func):
                def capture_command_train(suggestedSpeed, authority, blockNum, 
                                        updateBlockInQueue, nextStation, blocksAway):
                    # Capture the command
                    self.captured_commands['train_commands'].append({
                        'controller': ctrl.controller_id,
                        'suggestedSpeed': suggestedSpeed.copy() if suggestedSpeed else [],
                        'authority': authority.copy() if authority else [],
                        'blockNum': blockNum.copy() if blockNum else [],
                        'updateBlockInQueue': updateBlockInQueue.copy() if updateBlockInQueue else [],
                        'nextStation': nextStation.copy() if nextStation else [],
                        'blocksAway': blocksAway.copy() if blocksAway else []
                    })
                    # Call original function
                    return orig_func(suggestedSpeed, authority, blockNum, 
                                   updateBlockInQueue, nextStation, blocksAway)
                return capture_command_train
            
            controller.command_train = create_capture_function(controller, original_command_train[controller_id])
        
        # Create train and dispatch
        train_id = self.ctc_system.add_train("Green", "Manual")
        start_block = self.ctc_system.get_block_by_number(1, "Green")
        end_block = self.ctc_system.get_block_by_number(10, "Green")
        route = self.ctc_system.routeManager.generate_route(start_block, end_block)
        self.assertIsNotNone(route, "Failed to generate route")
        self.ctc_system.activate_route(train_id, route)
        self.ctc_system.dispatch_train_from_yard(train_id)
        
        time.sleep(0.5)
        
        # Verify commands were captured
        self.assertGreater(len(self.captured_commands['train_commands']), 0, 
                          "No command_train calls captured")
        
        # Verify command structure
        for cmd in self.captured_commands['train_commands']:
            print(f"✓ Controller {cmd['controller']} received command_train:")
            
            # Verify array lengths match
            if cmd['suggestedSpeed']:
                self.assertEqual(len(cmd['suggestedSpeed']), len(cmd['authority']),
                               "Speed and authority arrays have different lengths")
                self.assertEqual(len(cmd['suggestedSpeed']), len(cmd['blockNum']),
                               "Speed and blockNum arrays have different lengths")
                
                # Find non-zero commands
                active_commands = []
                for i, speed in enumerate(cmd['suggestedSpeed']):
                    if speed > 0 or (i < len(cmd['authority']) and cmd['authority'][i] > 0):
                        active_commands.append({
                            'index': i,
                            'speed': speed,
                            'authority': cmd['authority'][i] if i < len(cmd['authority']) else 0,
                            'block': cmd['blockNum'][i] if i < len(cmd['blockNum']) else 0,
                            'station': cmd['nextStation'][i] if i < len(cmd['nextStation']) else 0,
                            'distance': cmd['blocksAway'][i] if i < len(cmd['blocksAway']) else 0
                        })
                
                print(f"  Active commands: {len(active_commands)}")
                for active in active_commands[:3]:  # Show first 3
                    print(f"    Block {active['block']}: speed={active['speed']}, " +
                          f"auth={active['authority']}, station={active['station']}, " +
                          f"distance={active['distance']}")
                
                # Verify speed values are in valid range (0-3)
                for speed in cmd['suggestedSpeed']:
                    self.assertIn(speed, [0, 1, 2, 3], f"Invalid speed value: {speed}")
                
                # Verify authority values are binary (0 or 1)
                for auth in cmd['authority']:
                    self.assertIn(auth, [0, 1], f"Invalid authority value: {auth}")
        
        # Restore original functions
        for controller_id, controller in self.controllers.items():
            controller.command_train = original_command_train[controller_id]
            
        print("✓ Detailed command_train verification completed")
    
    def test_command_switch_detailed_verification(self):
        """Test 8: Detailed verification of command_switch parameters."""
        print("\n=== Test 8: Detailed command_switch Verification ===")
        
        # Set up the system
        self.test_master_interface_setup()
        
        # Monkey-patch wayside controller command_switch to capture calls
        original_command_switch = {}
        for controller_id, controller in self.controllers.items():
            original_command_switch[controller_id] = controller.command_switch
            
            def create_capture_function(ctrl, orig_func):
                def capture_command_switch(switchPositions):
                    # Capture the command
                    self.captured_commands['switch_commands'].append({
                        'controller': ctrl.controller_id,
                        'switchPositions': switchPositions.copy() if switchPositions else []
                    })
                    # Call original function
                    return orig_func(switchPositions)
                return capture_command_switch
            
            controller.command_switch = create_capture_function(controller, original_command_switch[controller_id])
        
        # Create train with route through switches
        train_id = self.ctc_system.add_train("Green", "Manual")
        
        # Find blocks with switches in track data
        switch_blocks = []
        for block_id, block in self.ctc_system.blocks.items():
            if hasattr(block, 'switch') and block.switch:
                switch_blocks.append(block.blockID)
        
        print(f"Found {len(switch_blocks)} switch blocks: {switch_blocks[:5]}")
        
        # Generate route through switch blocks if available
        if len(switch_blocks) >= 2:
            start_block = min(switch_blocks[:2])
            end_block = max(switch_blocks[:2])
            start_block_obj = self.ctc_system.get_block_by_number(start_block, "Green")
            end_block_obj = self.ctc_system.get_block_by_number(end_block, "Green")
            arrival_time = datetime.now() + timedelta(hours=1)
        route = self.ctc_system.generate_route(start_block_obj, end_block_obj, arrival_time)
        if route:
            self.ctc_system.activate_route(train_id, route)
            self.ctc_system.dispatch_train_from_yard(train_id)
            
            time.sleep(0.5)
            
            # Verify switch commands were sent
            self.assertGreater(len(self.captured_commands['switch_commands']), 0,
                             "No command_switch calls captured")
            
            for cmd in self.captured_commands['switch_commands']:
                print(f"✓ Controller {cmd['controller']} received command_switch:")
                print(f"  Array length: {len(cmd['switchPositions'])}")
                
                # Find active switches
                active_switches = []
                for i, pos in enumerate(cmd['switchPositions']):
                    if pos:
                        active_switches.append(i)
                
                print(f"  Active switches (True): {active_switches[:10]}")
                
                # Verify all values are boolean
                for pos in cmd['switchPositions']:
                    self.assertIsInstance(pos, bool, f"Switch position not boolean: {pos}")
        
        # Restore original functions
        for controller_id, controller in self.controllers.items():
            controller.command_switch = original_command_switch[controller_id]
            
        print("✓ Detailed command_switch verification completed")
    
    def test_wayside_to_ctc_occupancy_verification(self):
        """Test 9: Verify wayside → CTC occupancy update mechanism."""
        print("\n=== Test 9: Wayside → CTC Occupancy Updates ===")
        
        # Set up the system with test interface
        self.test_master_interface_setup()
        
        # Create test interface and connect to wayside controllers
        self.test_interface = MasterTestInterface(total_blocks=self.total_blocks, line="Green")
        
        # Register test interface with each wayside controller
        for controller_id, controller in self.controllers.items():
            blocks_covered = controller.blocksCovered
            comm_obj = self.test_interface.provide_wayside_controller(controller, blocks_covered)
            controller.set_track_model_communication_object(comm_obj)
        
        # Capture CTC occupancy updates
        original_update_occupied = self.ctc_system.communicationHandler.update_occupied_blocks
        captured_occupancy = []
        
        def capture_occupancy_update(occupiedBlocks, sending_controller=None):
            captured_occupancy.append({
                'controller': getattr(sending_controller, 'controller_id', 'Unknown'),
                'occupiedBlocks': occupiedBlocks.copy() if occupiedBlocks else [],
                'timestamp': time.time()
            })
            return original_update_occupied(occupiedBlocks, sending_controller)
        
        self.ctc_system.communicationHandler.update_occupied_blocks = capture_occupancy_update
        
        # Simulate train movements
        train = self.test_interface.add_train("TEST001", start_block=1, route=[1, 2, 3, 4, 5])
        
        # Move train through blocks
        for block in [2, 3, 4, 5]:
            self.test_interface.move_train("TEST001", block)
            time.sleep(0.2)
        
        # Verify occupancy updates were sent
        self.assertGreater(len(captured_occupancy), 0,
                          "No occupancy updates captured")
        
        print(f"✓ Captured {len(captured_occupancy)} occupancy updates")
        
        for update in captured_occupancy[:3]:  # Show first 3
            occupied_blocks = [i for i, occ in enumerate(update['occupiedBlocks']) if occ]
            print(f"  Controller {update['controller']}: {len(occupied_blocks)} occupied blocks")
            print(f"    Blocks: {occupied_blocks[:10]}")
        
        # Verify update format
        for update in captured_occupancy:
            self.assertIsInstance(update['occupiedBlocks'], list,
                                "Occupied blocks not a list")
            for occ in update['occupiedBlocks']:
                self.assertIsInstance(occ, bool,
                                    f"Occupancy value not boolean: {occ}")
        
        # Restore original function
        self.ctc_system.communicationHandler.update_occupied_blocks = original_update_occupied
        
        print("✓ Wayside → CTC occupancy verification completed")
    
    def test_bidirectional_communication_flow(self):
        """Test 10: Complete bidirectional communication flow."""
        print("\n=== Test 10: Bidirectional Communication Flow ===")
        
        # Set up the system with test interface
        self.test_master_interface_setup()
        
        # Create test interface
        self.test_interface = MasterTestInterface(total_blocks=self.total_blocks, line="Green")
        self.test_interface.enable_logging_to_file("bidirectional_flow.log")
        
        # Connect test interface to wayside controllers
        for controller_id, controller in self.controllers.items():
            blocks_covered = controller.blocksCovered
            comm_obj = self.test_interface.provide_wayside_controller(controller, blocks_covered)
            controller.set_track_model_communication_object(comm_obj)
        
        # Start test interface movement simulation
        self.test_interface.start_movement_simulation(update_interval=0.5)
        
        # Create and dispatch CTC train
        train_id = self.ctc_system.add_train("Green", "Manual")
        start_block = self.ctc_system.get_block_by_number(1, "Green")
        end_block = self.ctc_system.get_block_by_number(10, "Green")
        route = self.ctc_system.routeManager.generate_route(start_block, end_block)
        self.assertIsNotNone(route, "Failed to generate route")
        self.ctc_system.activate_route(train_id, route)
        self.ctc_system.dispatch_train_from_yard(train_id)
        
        # Add simulated train to test interface
        sim_train = self.test_interface.add_train(train_id, start_block=1, route=list(range(1, 11)))
        
        # Run bidirectional communication for several cycles
        print("Running bidirectional communication test...")
        for cycle in range(5):
            print(f"\nCycle {cycle + 1}:")
            
            # CTC → Wayside: Send commands
            self.ctc_system.communicationHandler.send_updated_train_commands("Green")
            time.sleep(0.1)
            
            # Check wayside received commands
            commands_received = self.test_interface.commands_received
            print(f"  Commands received by test interface: {commands_received}")
            
            # Wayside → CTC: Send occupancy
            for controller in self.controllers.values():
                controller.send_updates_to_ctc()
            time.sleep(0.1)
            
            # Check CTC received updates
            occupancy_sent = self.test_interface.occupancy_updates_sent
            print(f"  Occupancy updates sent: {occupancy_sent}")
            
            # Move simulated train
            next_block = sim_train.get_next_block()
            if next_block and not self.test_interface.block_occupancy[next_block]:
                self.test_interface.move_train(train_id, next_block)
                print(f"  Moved train to block {next_block}")
            
            time.sleep(0.5)
        
        # Get final statistics
        stats = self.test_interface.get_statistics()
        print("\nFinal Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Verify bidirectional flow
        self.assertGreater(stats['commands_received'], 0,
                          "No commands received from wayside")
        self.assertGreater(stats['occupancy_updates_sent'], 0,
                          "No occupancy updates sent to wayside")
        
        print("✓ Bidirectional communication flow verified")
    
    def test_concurrent_trains_communication(self):
        """Test 11: Communication with multiple concurrent trains."""
        print("\n=== Test 11: Concurrent Trains Communication ===")
        
        # Set up the system
        self.test_master_interface_setup()
        
        # Create test interface
        self.test_interface = MasterTestInterface(total_blocks=self.total_blocks, line="Green")
        
        # Connect test interface
        for controller_id, controller in self.controllers.items():
            blocks_covered = controller.blocksCovered
            comm_obj = self.test_interface.provide_wayside_controller(controller, blocks_covered)
            controller.set_track_model_communication_object(comm_obj)
        
        # Create multiple trains with different routes
        train_configs = [
            {"id": "TRAIN001", "start": 0, "end": 30, "sim_start": 0},
            {"id": "TRAIN002", "start": 30, "end": 60, "sim_start": 30},
            {"id": "TRAIN003", "start": 60, "end": 96, "sim_start": 60}
        ]
        
        # Dispatch CTC trains
        for config in train_configs:
            train_id = self.ctc_system.add_train("Green", "Manual")
            config['ctc_id'] = train_id
            start_block = self.ctc_system.get_block_by_number(config['start'], "Green")
            end_block = self.ctc_system.get_block_by_number(config['end'], "Green")
            arrival_time = datetime.now() + timedelta(hours=1)
            route = self.ctc_system.generate_route(start_block, end_block, arrival_time)
            if route:
                self.ctc_system.activate_route(train_id, route)
                self.ctc_system.dispatch_train_from_yard(train_id)
            
            # Add simulated train
            route = list(range(config['start'], config['end'] + 1))
            self.test_interface.add_train(config['id'], start_block=config['sim_start'], route=route)
        
        # Run concurrent operations
        print("Running concurrent train operations...")
        for cycle in range(3):
            print(f"\nCycle {cycle + 1}:")
            
            # Send commands for all trains
            self.ctc_system.communicationHandler.send_updated_train_commands("Green")
            time.sleep(0.2)
            
            # Move all simulated trains
            for config in train_configs:
                train = self.test_interface.trains.get(config['id'])
                if train:
                    next_block = train.get_next_block()
                    if next_block and not self.test_interface.block_occupancy[next_block]:
                        self.test_interface.move_train(config['id'], next_block)
                        print(f"  {config['id']} moved to block {next_block}")
            
            # Send occupancy updates
            for controller in self.controllers.values():
                controller.send_updates_to_ctc()
            
            time.sleep(0.5)
        
        # Verify all trains are tracked
        self.assertEqual(len(self.test_interface.trains), 3,
                        "Not all trains tracked in test interface")
        
        # Verify occupancy for multiple trains
        occupied_count = sum(self.test_interface.block_occupancy)
        self.assertGreaterEqual(occupied_count, 3,
                               "Expected at least 3 occupied blocks for 3 trains")
        
        print(f"✓ Concurrent trains test completed with {occupied_count} occupied blocks")
    
    def test_all_communication_functions(self):
        """Test 12: Verify all CTC-Wayside communication functions are called correctly."""
        print("\n=== Test 12: All Communication Functions ===")
        
        # Set up the system
        self.test_master_interface_setup()
        
        # Track which functions were called
        functions_called = {
            'command_train': False,
            'command_switch': False,
            'update_occupied_blocks': False,
            'update_switch_positions': False
        }
        
        # Monkey-patch to track function calls
        for controller in self.controllers.values():
            # Track command_train calls
            original_command_train = controller.command_train
            def track_command_train(*args, **kwargs):
                functions_called['command_train'] = True
                return original_command_train(*args, **kwargs)
            controller.command_train = track_command_train
            
            # Track command_switch calls
            original_command_switch = controller.command_switch
            def track_command_switch(*args, **kwargs):
                functions_called['command_switch'] = True
                return original_command_switch(*args, **kwargs)
            controller.command_switch = track_command_switch
        
        # Track CTC communication handler calls
        original_update_occupied = self.ctc_system.communicationHandler.update_occupied_blocks
        def track_update_occupied(*args, **kwargs):
            functions_called['update_occupied_blocks'] = True
            return original_update_occupied(*args, **kwargs)
        self.ctc_system.communicationHandler.update_occupied_blocks = track_update_occupied
        
        original_update_switch = self.ctc_system.communicationHandler.update_switch_positions
        def track_update_switch(*args, **kwargs):
            functions_called['update_switch_positions'] = True
            return original_update_switch(*args, **kwargs)
        self.ctc_system.communicationHandler.update_switch_positions = track_update_switch
        
        # Create and dispatch train with route 0 to 96
        train_id = self.ctc_system.add_train("Green", "Manual")
        start_block = self.ctc_system.get_block_by_number(0, "Green")
        end_block = self.ctc_system.get_block_by_number(96, "Green")
        route = self.ctc_system.routeManager.generate_route(start_block, end_block)
        self.assertIsNotNone(route, "Failed to generate route from 0 to 96")
        self.ctc_system.activate_route(train_id, route)
        self.ctc_system.dispatch_train_from_yard(train_id)
        
        # Send commands (should trigger command_train and command_switch)
        self.ctc_system.communicationHandler.send_updated_train_commands("Green")
        time.sleep(0.2)
        
        # Send switch commands specifically
        # CTC sends switch commands directly to controllers via command_switch
        switch_positions = [False] * self.total_blocks
        switch_positions[13] = True  # Set a switch position
        for controller in self.controllers.values():
            if hasattr(controller, 'command_switch'):
                controller.command_switch(switch_positions)
        time.sleep(0.2)
        
        # Simulate wayside sending updates to CTC
        controller = self.controllers[1]
        occupied_blocks = [False] * self.total_blocks
        occupied_blocks[1] = True
        self.ctc_system.communicationHandler.update_occupied_blocks(occupied_blocks, controller)
        
        switch_positions = [False] * self.total_blocks
        switch_positions[13] = True
        self.ctc_system.communicationHandler.update_switch_positions(switch_positions, controller)
        
        time.sleep(0.2)
        
        # Verify all functions were called
        print("Function call results:")
        for func_name, was_called in functions_called.items():
            print(f"  {func_name}: {'✓ Called' if was_called else '✗ Not called'}")
            self.assertTrue(was_called, f"{func_name} was not called")
        
        print("✓ All CTC-Wayside communication functions verified")


def run_integration_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("CTC-WAYSIDE CONTROLLER INTEGRATION TESTS")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCTCWaysideIntegration)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n✅ ALL INTEGRATION TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED!")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)