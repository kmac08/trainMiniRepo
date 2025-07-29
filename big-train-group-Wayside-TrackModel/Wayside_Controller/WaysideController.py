from PyQt5.QtCore import QObject, QTimer
from typing import List
import importlib.util
import os
import sys
from threading import Event
from CTC import communication_handler
from Master_Interface import CommunicationObject   


class WaysideController(QObject):
    
    def __init__(self, data, line: str, mode: str, auto: bool, plc_num: int, plc_file: str, blocks_covered: List[bool], total_blocks: int):
        super().__init__()
        
        # Basic configuration (maintain compatibility with Master Interface)
        self.trackData = data[line][mode]
        self.auto = auto
        self.plcNum = plc_num
        self.line = line
        self.plc_file = plc_file
        self.total_blocks = total_blocks
        self.blocksCovered = blocks_covered.copy() if blocks_covered else [False] * total_blocks
        
        # Dual PLC support - determine PLC files based on line
        self.plc_files = self._determine_plc_files(line)
        self.plc_modules = []
        
        # Communication objects
        self.ctc_commObj = None  # Set by Master Interface via set_communication_object()
        self.track_CommObj = None  # For future track model integration
        self.isOperational = False
        
        # Timer management
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_cycle)
        self.check_timer = QTimer()  # Referenced in get_status method
        self.time_manager = None  # Referenced in get_status method
        
        
        
        # Core wayside data arrays - sized to match total blocks for track model interface
        self.speed = [0] * total_blocks
        self.authorities = [False] * total_blocks
        self.block_occupancy = [False] * total_blocks
        self.switch_positions = [False] * total_blocks  # Full size - PLC maps internal switches to specific indices
        self.traffic_lights = [False] * total_blocks    # Full size - PLC maps internal lights to specific indices  
        self.railroad_crossings = [False] * total_blocks  # Full size - PLC maps internal crossings to specific indices
        
        # CTC input arrays (received from CTC)
        self.ctc_suggested_speeds = [0] * total_blocks
        self.ctc_authorities = [False] * total_blocks
        self.ctc_UpdateBlockInQueue = [0] * total_blocks
        self.ctc_station_numbers = [0] * total_blocks
        self.ctc_block_numbers = [0] * total_blocks
        self.ctc_occupied = [0]* total_blocks  # Occupancy state from CTC
        
        # Pass-through data to track model
        self.station_numbers = [0] * total_blocks
        self.UpdateBlockInQueue = [0] * total_blocks
        self.block_numbers = [0] * total_blocks
        
        # PLC module management
        self.plcModule = None
        self.stopEvent = Event()
        
        # Load PLC files (dual PLC support)
        print(f"[WAYSIDE] Controller {self.plcNum}: About to load PLC files during initialization")
        load_result = self.load_plc_modules()
        print(f"[WAYSIDE] Controller {self.plcNum}: PLC loading result: {load_result}")
        print(f"[WAYSIDE] Controller {self.plcNum}: PLC modules loaded: {len(self.plc_modules)}")
        
        print(f"Wayside Controller {self.plcNum} initialized for {line} line")
        print(f"PLC Files: {self.plc_files}")
        print(f"Managing {sum(self.blocksCovered)} blocks out of {total_blocks}")
        print(f"PLC Modules Status: {len(self.plc_modules)} modules loaded")

    # ========== Master Interface Compatibility ==========
    
    def set_communication_object(self, ctc_comm_obj):
        """Set CTC communication object (called by Master Interface)"""
        try:
            self.ctc_commObj = ctc_comm_obj
            print(f"Communication object set for Wayside Controller {self.plcNum}")
        except Exception as e:
            print(f"Error setting communication object: {e}")
            self.isOperational = False
    
    def set_track_model_communication_object(self, track_comm_obj):
        """Set track model communication object (for future use)"""
        self.track_CommObj = track_comm_obj
        print(f"Track model communication object set for Controller {self.plcNum}")

    # ========== Timer Management ==========
    
    def start_update_cycle(self):
        """Start the update cycle timer at 0.05s intervals"""
        try:
            self.update_timer.start(50)  # 50ms = 0.05s intervals
            self.isOperational = True
            print(f"[WAYSIDE] Controller {self.plcNum}: Update cycle started (50ms intervals)")
        except Exception as e:
            print(f"[WAYSIDE] Error starting update cycle: {e}")
            self.isOperational = False
    
    def stop_update_cycle(self):
        """Stop the update cycle timer"""
        try:
            self.update_timer.stop()
            self.isOperational = False
            print(f"[WAYSIDE] Controller {self.plcNum}: Update cycle stopped")
        except Exception as e:
            print(f"[WAYSIDE] Error stopping update cycle: {e}")

    # ========== PLC Management ==========
    
    def _determine_plc_files(self, line: str):
        """Determine which PLC files to load based on the line."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        if line.lower() == 'green':
            return [
                os.path.join(base_dir, 'GreenLinePlcV1_Part1.py'),
                os.path.join(base_dir, 'GreenLinePlcV1_Part2.py')
            ]
        elif line.lower() == 'red':
            return [
                os.path.join(base_dir, 'RedLinePlcV1_Part1.py'),
                os.path.join(base_dir, 'RedLinePlcV1_Part2.py')
            ]
        else:
            # Fallback to original single PLC file
            return [self.plc_file] if self.plc_file else []
    
    def load_plc_modules(self):
        """Dynamically load multiple PLC Python files as modules."""
        self.plc_modules = []
        
        for plc_file in self.plc_files:
            try:
                if not os.path.exists(plc_file):
                    print(f"[WAYSIDE] Warning: PLC file not found: {plc_file}")
                    continue
                    
                module_name = os.path.basename(plc_file)
                print(f"[WAYSIDE] Loading PLC Module: {module_name}")
                spec = importlib.util.spec_from_file_location(module_name, plc_file)
                plc_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(plc_module)
                self.plc_modules.append(plc_module)
                print(f"[WAYSIDE] Successfully loaded: {module_name}")
                
            except Exception as e:
                print(f"[WAYSIDE] Error loading PLC file {plc_file}: {e}")
                import traceback
                traceback.print_exc()
        
        # Maintain backward compatibility
        if len(self.plc_modules) > 0:
            self.plcModule = self.plc_modules[0]  # First module for compatibility
        
        return len(self.plc_modules) > 0
    
    def load_plc_module(self):
        """Legacy method - maintained for backward compatibility."""
        return self.load_plc_modules()
    # ========== CTC Communication Functions ==========
    
    def command_train(self, suggestedSpeed: List[int], authority: List[int], 
                     blockNum: List[int], updateBlockInQueue: List[bool], 
                     nextStation: List[int], blocksAway: List[int]):
        print("hey_wayside_im_here_now")
        """Receive commands from CTC (called by CTC)"""
        try:
            print(f"[WAYSIDE] Controller {self.plcNum}: Received CTC commands")
            print(f"  Active commands: {len([i for i, s in enumerate(suggestedSpeed) if s > 0])}")

            # Store CTC commands for processing
            self.ctc_block_numbers = blockNum.copy()

            # Store CTC suggested speeds and authorities for PLC input
            for i, block in enumerate(blockNum):
                if block < self.total_blocks and i < len(suggestedSpeed):
                    self.ctc_suggested_speeds[block] = suggestedSpeed[i]
                if block < self.total_blocks and i < len(authority):
                    self.ctc_authorities[block] = bool(authority[i])
            
            # Store pass-through data from CTC
            for i, block in enumerate(blockNum):
                if block < self.total_blocks and i < len(nextStation):
                    self.ctc_station_numbers[block] = nextStation[i]
                if block < self.total_blocks and i < len(updateBlockInQueue):
                    self.ctc_UpdateBlockInQueue[block] = int(updateBlockInQueue[i])
            
        except Exception as e:
            print(f"[WAYSIDE] Error processing CTC commands: {e}")
    
    def set_occupied(self, block: int, block_state: bool):
        """Receive occupancy from CTC (called by CTC)"""
        try:
            for i in range(self.total_blocks):
                if i == block:
                    self.ctc_occupied[i] = block_state

        except Exception as e:
            print(f"[WAYSIDE] Error processing occupancy data: {e}")
    
    def send_updates_to_ctc(self):
        """Send current actual states to CTC"""
        if self.ctc_commObj is None or not self.isOperational:
            return
            
        try:
            # Send updates to CTC via communication object
            self.ctc_commObj.update_occupied_blocks(self.block_occupancy, sending_controller=self)
            self.ctc_commObj.update_switch_positions(self.switch_positions, sending_controller=self)
            self.ctc_commObj.update_railway_crossings(self.railroad_crossings, sending_controller=self)
            
            
            
        except Exception as e:
            print(f"[WAYSIDE] Error sending updates to CTC: {e}")

    # ========== Track Model Interface (Future) ==========
    
    def send_commands_to_track_model(self):
        """Send all commands to track model via communication object"""
        if self.track_CommObj is None:
            return  # Track model not connected yet

        # Future implementation for track model communication
        try:
            self.track_CommObj.setSwitchStates(self.switch_positions.copy())
            self.track_CommObj.setTrafficLightStates(self.traffic_lights.copy())
            self.track_CommObj.setCrossingStates(self.railroad_crossings.copy())
            self.track_CommObj.setAuthorities(self.authorities.copy())
            self.track_CommObj.setCommandedSpeeds(self.speed.copy())
            self.track_CommObj.setNextStationNumbers(self.station_numbers.copy())
            self.track_CommObj.setUpdateBlockInQueue(self.UpdateBlockInQueue.copy())
            #need a set occupancy function here
            self.receive_from_track_model()
        except Exception as e:
            print(f"[WAYSIDE] Error communicating with track model: {e}")

    def receive_from_track_model(self):
        """Receive everything from track model"""
        if self.track_CommObj is None:
            return
            
        try:
            self.switch_positions = self.track_CommObj.getSwitchStates()
            self.traffic_lights = self.track_CommObj.getTrafficLightStates()
            self.railroad_crossings = self.track_CommObj.getCrossingStates()
            self.block_occupancy = self.track_CommObj.getBlockOccupancy()
        except Exception as e:
            print(f"[WAYSIDE] Error receiving from track model: {e}")

    # ========== Main Operations ==========
    
    
    
    def update_cycle(self):
        """Main update cycle - called when simulation time advances by 0.05 seconds"""
       
        

        # 3. Run PLC logic if loaded
        if len(self.plc_modules) > 0:
            try:
                # 1. Process CTC commands (copy CTC inputs to working arrays)
                self.process_ctc_commands()
                
                # 2. Get data from track model (if available)
                self.receive_from_track_model()
                
                # Run all PLC modules (dual PLC support)
                for i, plc_module in enumerate(self.plc_modules):
                    try:
                        print(f"[WAYSIDE] Running PLC module {i+1}/{len(self.plc_modules)}")
                        # Call PLC with standardized signature
                        # main(block_occupancy, speed, authority, switches_actual, 
                        #      traffic_lights_actual, crossings_actual, block_numbers)
                        plc_module.main(
                            self.block_occupancy, 
                            self.speed, 
                            self.authorities, 
                            self.switch_positions, 
                            self.traffic_lights, 
                            self.railroad_crossings,
                            self.block_numbers
                        )
                        print(f"[WAYSIDE] PLC module {i+1} executed successfully")
                        
                    except Exception as e:
                        print(f"[WAYSIDE] ERROR running PLC module {i+1}: {e}")
                        import traceback
                        traceback.print_exc()
                        # Continue with other modules even if one fails
                
                # 4. Send commands to track model (if available)
                self.send_commands_to_track_model()
                
                # 5. Send updates back to CTC
                self.send_updates_to_ctc()

                
            except Exception as e:
                print(f"[WAYSIDE] ERROR in PLC execution cycle for Controller {self.plcNum}: {e}")
                print(f"[WAYSIDE] PLC modules will remain loaded despite execution error")
                import traceback
                traceback.print_exc()
                # Don't clear self.plc_modules here - keep them loaded even if execution fails
        else:
            print(f"[WAYSIDE] Controller {self.plcNum}: No PLC modules loaded")

        

    def process_ctc_commands(self):
        """Process commands received from CTC"""
        # Copy CTC inputs to working arrays for PLC to use
        self.speed = self.ctc_suggested_speeds.copy()
        self.authorities = self.ctc_authorities.copy()
        self.UpdateBlockInQueue = self.ctc_UpdateBlockInQueue.copy()
        self.station_numbers = self.ctc_station_numbers.copy()
        self.block_numbers = self.ctc_block_numbers.copy()
        #set block occupancy based on CTC input
        #self.track_CommObj.setBlockOccupancy(self.ctc_occupied.copy())


    # ========== Testing/Debug Methods ==========
    
    
    
    def get_status(self):
        """Get current controller status for debugging"""
        return {
            'controller_id': getattr(self, 'controller_id', f'Controller_{self.plcNum}'),
            'line': self.line,
            'operational': self.isOperational,
            'time_manager_connected': self.time_manager is not None,
            'plc_loaded': len(self.plc_modules) > 0,
            'plc_modules_count': len(self.plc_modules),
            'plc_files': self.plc_files,
            'timer_running': self.check_timer.isActive(),
            'blocks_managed': sum(self.blocksCovered),
            'occupied_blocks': sum(self.block_occupancy),
            'ctc_connected': self.ctc_commObj is not None,
            'track_model_connected': self.track_CommObj is not None,
            'current_time': self.time_manager.get_current_time_string() if self.time_manager else "N/A"
        }