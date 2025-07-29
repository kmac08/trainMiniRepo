"""
Failure Manager Module
=====================
Manages failure detection, tracking, and recovery for the CTC system
according to UML specifications.

This module handles:
- Block and train failure detection
- Affected train identification
- Emergency response procedures
- Failure history and tracking
"""

from typing import List, Dict, Optional, Set
from datetime import datetime
import logging
import uuid

# Set up logging
logger = logging.getLogger(__name__)


class FailureManager:
    """
    Failure Manager implementing UML interface
    Handles all aspects of failure detection and management
    """
    
    def __init__(self):
        """Initialize Failure Manager with UML-specified attributes"""
        # Attributes from UML
        self.failedBlocks = []     # List[Block]
        
        # Additional attributes needed for implementation
        self.failedTrains = []     # List[Train]
        self.failure_history = []  # Historical failures
        self.active_emergencies = {}  # emergency_id -> emergency_details
        
        # Recovery tracking
        self.recovery_actions = {}  # failure_id -> recovery_status
        self.stopped_trains = set()  # Set of train IDs that were stopped due to failures
        
        # Migrated from maintenance_manager.py
        self.maintenanceClosures = {
            "Blue": [],   # List of block numbers closed on Blue Line
            "Red": [],    # List of block numbers closed on Red Line  
            "Green": []   # List of block numbers closed on Green Line
        }  # {line: [block_numbers]}
        
        # Scheduled maintenance closures
        self.scheduledClosures = []  # List of scheduled closure objects
        self.scheduledOpenings = []  # List of scheduled opening objects
        
        # References to other system components
        self.ctc_system = None
        self.communication_handler = None
        self.display_manager = None
        
        logger.info("Failure Manager initialized")
    
    # Methods from UML
    
    def find_affected_trains(self) -> List:
        """
        Find trains affected by current failures
        
        Returns:
            List of Train objects affected by active failures
        """
        affected_trains = []
        
        if not self.ctc_system:
            logger.warning("No CTC System connected - cannot find affected trains")
            return affected_trains
        
        # Get all active trains
        all_trains = self.ctc_system.get_train_list() if hasattr(self.ctc_system, 'get_train_list') else []
        
        # Check trains against failed blocks
        for train in all_trains:
            if self._is_train_affected_by_blocks(train):
                affected_trains.append(train)
        
        # Add trains that are directly failed
        affected_trains.extend(self.failedTrains)
        
        # Remove duplicates
        unique_trains = []
        train_ids = set()
        for train in affected_trains:
            train_id = self._get_train_id(train)
            if train_id not in train_ids:
                unique_trains.append(train)
                train_ids.add(train_id)
        
        logger.info(f"Found {len(unique_trains)} trains affected by failures")
        return unique_trains
    
    def check_for_failures(self) -> None:
        """
        Scan system for new failures
        Proactively detect failures in blocks and trains
        """
        # Check for block failures
        self._check_block_failures()
        
        # Check for train failures
        self._check_train_failures()
        
        # Check for communication failures
        self._check_communication_failures()
        
        # Update emergency table
        self._update_emergency_displays()
        
        logger.debug("Failure check completed")
    
    def add_failed_block(self, block) -> None:
        """
        Register block failure
        
        Args:
            block: Block object that has failed
        """
        if block not in self.failedBlocks:
            self.failedBlocks.append(block)
            
            # Create emergency record
            emergency_id = str(uuid.uuid4())
            block_id = self._get_block_id(block)
            
            emergency_data = {
                'id': emergency_id,
                'type': 'BLOCK_FAILURE',
                'train_id': None,
                'block_id': block_id,
                'description': f"Block {block_id} failure detected",
                'timestamp': datetime.now(),
                'addressed': False,
                'resolution': None,
                'failure_object': block
            }
            
            self.active_emergencies[emergency_id] = emergency_data
            self.failure_history.append(emergency_data.copy())
            
            # Notify display manager
            if self.display_manager:
                self.display_manager.update_block_failure(block_id, emergency_data['description'])
            
            # Automatically stop affected trains
            self._stop_affected_trains_for_block(block)
            
            logger.error(f"Block {block_id} added to failed blocks list")
    
    def add_failed_train(self, train) -> None:
        """
        Register train failure
        
        Args:
            train: Train object that has failed
        """
        if train not in self.failedTrains:
            self.failedTrains.append(train)
            
            # Create emergency record
            emergency_id = str(uuid.uuid4())
            train_id = self._get_train_id(train)
            current_block = getattr(train, 'currentBlock', None)
            
            emergency_data = {
                'id': emergency_id,
                'type': 'TRAIN_FAILURE',
                'train_id': train_id,
                'block_id': current_block,
                'description': f"Train {train_id} malfunction detected",
                'timestamp': datetime.now(),
                'addressed': False,
                'resolution': None,
                'failure_object': train
            }
            
            self.active_emergencies[emergency_id] = emergency_data
            self.failure_history.append(emergency_data.copy())
            
            # Notify display manager
            if self.display_manager:
                self.display_manager.update_train_error(train)
            
            # Automatically stop the failed train
            self._emergency_stop_train(train)
            
            logger.error(f"Train {train_id} added to failed trains list")
    
    def reroute_trains(self) -> None:
        """
        Attempt to reroute around failures
        NOTE: This should only be called by dispatcher via emergency page
        """
        if not self.ctc_system:
            logger.warning("No CTC System connected - cannot reroute trains")
            return
        
        affected_trains = self.find_affected_trains()
        reroute_results = {}
        
        for train in affected_trains:
            train_id = self._get_train_id(train)
            
            # Only reroute if train was stopped due to failures (not if train itself failed)
            if train not in self.failedTrains and train_id in self.stopped_trains:
                try:
                    new_route = self._generate_alternative_route(train)
                    if new_route:
                        # Apply new route to train
                        if hasattr(train, 'route'):
                            train.route = new_route
                        
                        # Remove from stopped trains
                        self.stopped_trains.discard(train_id)
                        
                        reroute_results[train_id] = 'SUCCESS'
                        logger.info(f"Train {train_id} successfully rerouted")
                    else:
                        reroute_results[train_id] = 'NO_ROUTE_FOUND'
                        logger.warning(f"No alternative route found for train {train_id}")
                
                except Exception as e:
                    reroute_results[train_id] = f'ERROR: {str(e)}'
                    logger.error(f"Error rerouting train {train_id}: {e}")
            else:
                reroute_results[train_id] = 'TRAIN_FAILED_NO_REROUTE'
        
        logger.info(f"Rerouting completed. Results: {reroute_results}")
        return reroute_results
    
    def stop_trains(self) -> None:
        """
        Emergency stop affected trains
        Called automatically when failures are detected
        """
        affected_trains = self.find_affected_trains()
        
        for train in affected_trains:
            self._emergency_stop_train(train)
        
        logger.warning(f"Emergency stop issued to {len(affected_trains)} trains")
    
    # Additional methods for enhanced functionality
    
    def generate_emergency_routes(self, affected_trains: List) -> Dict[str, any]:
        """
        Generate alternative routes for affected trains
        
        Args:
            affected_trains: List of trains needing rerouting
            
        Returns:
            Dict mapping train_id to new route or error message
        """
        emergency_routes = {}
        
        for train in affected_trains:
            train_id = self._get_train_id(train)
            
            try:
                # Only generate routes for trains that aren't themselves failed
                if train not in self.failedTrains:
                    alternative_route = self._generate_alternative_route(train)
                    if alternative_route:
                        emergency_routes[train_id] = alternative_route
                    else:
                        emergency_routes[train_id] = "No safe route available"
                else:
                    emergency_routes[train_id] = "Train failed - no rerouting possible"
            
            except Exception as e:
                emergency_routes[train_id] = f"Route generation error: {str(e)}"
        
        logger.info(f"Generated emergency routes for {len(emergency_routes)} trains")
        return emergency_routes
    
    def clear_failure(self, failure_id: str) -> None:
        """
        Mark failure as resolved
        
        Args:
            failure_id: ID of failure to clear
        """
        if failure_id in self.active_emergencies:
            emergency = self.active_emergencies[failure_id]
            emergency['addressed'] = True
            emergency['resolution'] = "Failure resolved by dispatcher"
            
            # Remove from active failures
            failure_object = emergency.get('failure_object')
            if failure_object:
                if emergency['type'] == 'BLOCK_FAILURE' and failure_object in self.failedBlocks:
                    self.failedBlocks.remove(failure_object)
                elif emergency['type'] == 'TRAIN_FAILURE' and failure_object in self.failedTrains:
                    self.failedTrains.remove(failure_object)
            
            # Update display
            if self.display_manager:
                self.display_manager.address_emergency(failure_id, emergency['resolution'])
            
            logger.info(f"Failure {failure_id} cleared")
    
    def get_failure_impact(self, failure_id: str) -> dict:
        """
        Analyze impact of specific failure
        
        Args:
            failure_id: ID of failure to analyze
            
        Returns:
            Dict containing impact analysis
        """
        if failure_id not in self.active_emergencies:
            return {'error': 'Failure not found'}
        
        emergency = self.active_emergencies[failure_id]
        impact = {
            'failure_type': emergency['type'],
            'affected_trains': [],
            'blocked_routes': [],
            'capacity_impact': 0
        }
        
        if emergency['type'] == 'BLOCK_FAILURE':
            # Find trains that use this block
            block_id = emergency['block_id']
            affected_trains = self.find_affected_trains()
            
            for train in affected_trains:
                train_id = self._get_train_id(train)
                if hasattr(train, 'route') and train.route:
                    route_blocks = train.route.get_block_sequence() if hasattr(train.route, 'get_block_sequence') else []
                    if any(block.blockID == block_id for block in route_blocks if hasattr(block, 'blockID')):
                        impact['affected_trains'].append(train_id)
        
        elif emergency['type'] == 'TRAIN_FAILURE':
            # Single train impact
            impact['affected_trains'] = [emergency['train_id']]
        
        impact['capacity_impact'] = len(impact['affected_trains']) * 10  # Simplified calculation
        
        return impact
    
    # Private helper methods
    
    def _is_train_affected_by_blocks(self, train) -> bool:
        """Check if train is affected by any failed blocks"""
        if not hasattr(train, 'route') or not train.route:
            return False
        
        # Get train's route blocks
        route_blocks = train.route.get_block_sequence() if hasattr(train.route, 'get_block_sequence') else []
        
        # Check if any route blocks are in failed blocks
        for route_block in route_blocks:
            for failed_block in self.failedBlocks:
                if hasattr(route_block, 'blockID') and hasattr(failed_block, 'blockID'):
                    if route_block.blockID == failed_block.blockID:
                        return True
        
        return False
    
    def _emergency_stop_train(self, train):
        """Send emergency stop command to train"""
        train_id = self._get_train_id(train)
        
        # Add to stopped trains set
        self.stopped_trains.add(train_id)
        
        # Send stop command via communication handler
        if self.communication_handler:
            self.communication_handler.stop_train(train)
        
        logger.warning(f"Emergency stop sent to train {train_id}")
    
    def _stop_affected_trains_for_block(self, failed_block):
        """Stop all trains affected by a specific block failure"""
        affected_trains = []
        
        if self.ctc_system:
            all_trains = self.ctc_system.get_train_list() if hasattr(self.ctc_system, 'get_train_list') else []
            
            for train in all_trains:
                # Check if train's current route uses the failed block
                if hasattr(train, 'route') and train.route:
                    route_blocks = train.route.get_block_sequence() if hasattr(train.route, 'get_block_sequence') else []
                    failed_block_id = self._get_block_id(failed_block)
                    
                    for block in route_blocks:
                        if hasattr(block, 'blockID') and block.blockID == failed_block_id:
                            affected_trains.append(train)
                            break
        
        # Stop all affected trains
        for train in affected_trains:
            self._emergency_stop_train(train)
    
    def _generate_alternative_route(self, train):
        """Generate alternative route avoiding failed blocks"""
        if not hasattr(train, 'route') or not train.route:
            return None
        
        current_route = train.route
        
        # Get route manager to generate alternative
        if self.ctc_system and hasattr(self.ctc_system, 'routeManager'):
            route_manager = self.ctc_system.routeManager
            
            # Get start and end blocks
            start_block = current_route.startBlock if hasattr(current_route, 'startBlock') else None
            end_block = current_route.endBlock if hasattr(current_route, 'endBlock') else None
            
            if start_block and end_block and hasattr(route_manager, 'find_alternative_routes'):
                # Find routes avoiding failed blocks
                alternative_routes = route_manager.find_alternative_routes(
                    start_block, end_block, self.failedBlocks
                )
                
                if alternative_routes:
                    return alternative_routes[0]  # Return first alternative
        
        return None
    
    def _check_block_failures(self):
        """Check for new block failures"""
        # This would integrate with track monitoring systems
        # For now, failures are reported manually via add_failed_block
        pass
    
    def _check_train_failures(self):
        """Check for new train failures"""
        # This would integrate with train monitoring systems
        # For now, failures are reported manually via add_failed_train
        pass
    
    def _check_communication_failures(self):
        """Check for communication system failures"""
        # This would check wayside communication health
        # Could monitor last message times, response delays, etc.
        pass
    
    def _update_emergency_displays(self):
        """Update emergency displays with current status"""
        if self.display_manager:
            # Update emergency table with current active emergencies
            for emergency in self.active_emergencies.values():
                if not emergency['addressed']:
                    # Ensure display manager has current emergency info
                    pass
    
    def _get_train_id(self, train) -> str:
        """Extract train ID from train object"""
        if hasattr(train, 'trainID'):
            return str(train.trainID)
        elif hasattr(train, 'id'):
            return str(train.id)
        else:
            return f"train_{id(train)}"
    
    def _get_block_id(self, block) -> int:
        """Extract block ID from block object"""
        if hasattr(block, 'blockID'):
            return block.blockID
        elif hasattr(block, 'block_number'):
            return block.block_number
        elif isinstance(block, int):
            return block
        else:
            return 0
    
    # Compatibility methods for UI integration
    
    def close_block(self, line: str, block_number: int) -> Dict:
        """
        Close a track block for maintenance work (migrated from maintenance_manager)
        
        This is a critical safety function that prevents trains from entering
        blocks where maintenance work is being performed.
        
        Args:
            line: Line name ("Blue", "Red", or "Green")
            block_number: Block number to close for maintenance
            
        Returns:
            Dict: Result with success status, message, and block info
        """
        # Check if block is already closed
        if block_number in self.maintenanceClosures[line]:
            return {
                "success": False,
                "message": f"Block {block_number} is already closed for maintenance"
            }
        
        # Get block object
        block = None
        block_info = None
        if self.ctc_system and hasattr(self.ctc_system, 'get_block_by_line'):
            block = self.ctc_system.get_block_by_line(line, block_number)
            if hasattr(self.ctc_system, 'trackLayout') and self.ctc_system.trackLayout:
                block_info = self.ctc_system.trackLayout.get_block_info(line, block_number)
        
        # Add block to closure list using ctc_system state manager
        if self.ctc_system:
            self.ctc_system.add_maintenance_closure(line, block_number)
            # Sync backward compatibility dict
            if block_number not in self.maintenanceClosures[line]:
                self.maintenanceClosures[line].append(block_number)
        else:
            # Fallback for legacy mode
            self.maintenanceClosures[line].append(block_number)
        
        logger.info(f"Block {block_number} on {line} line added to maintenance closures")
        
        # Send immediate closure notification to wayside controller
        if self.communication_handler:
            self.communication_handler.send_maintenance_closure(line, block_number, "close")
        
        # Also add to failed blocks if block object exists
        if block:
            self.add_failed_block(block)
        
        # Create informative message for dispatcher
        if block_info and hasattr(block_info, 'has_station') and block_info.has_station and hasattr(block_info, 'station'):
            message = f"Block {block_number} closed for maintenance.\nStation {block_info.station.name} may experience delays."
        else:
            message = f"Block {block_number} closed for maintenance."
            
        return {
            "success": True,
            "message": message,
            "block_info": block_info
        }
    
    def generate_warnings(self, track_status=None, railway_crossings=None):
        """Generate system warnings"""
        warnings = []
        
        # Check for failed blocks
        for block in self.failedBlocks:
            warnings.append({
                'type': 'block_failure',
                'message': f"Block {getattr(block, 'blockID', 'Unknown')} is failed",
                'severity': 'high'
            })
        
        # Check for active emergencies
        for emergency_id, emergency in self.active_emergencies.items():
            if not emergency.get('addressed', False):
                warnings.append({
                    'type': 'emergency',
                    'message': emergency.get('description', 'Unknown emergency'),
                    'severity': 'critical'
                })
        
        return warnings
    
    def get_scheduled_closures(self):
        """Get scheduled block closures (from maintenance_manager)"""
        return self.scheduledClosures.copy()
    
    def cancel_scheduled_closure(self, closure_id):
        """Cancel a scheduled closure (from maintenance_manager)"""
        # Find and remove the closure from the scheduled list
        for scheduled in self.scheduledClosures[:]:
            if scheduled['id'] == closure_id:
                self.scheduledClosures.remove(scheduled)
                
                # Also remove related opening
                for opening in self.scheduledOpenings[:]:
                    if opening.get('related_closure') == closure_id:
                        self.scheduledOpenings.remove(opening)
                
                logger.info(f"Cancelled scheduled closure: {closure_id}")
                return {"success": True, "message": f"Closure for block {scheduled['block_number']} cancelled"}
        
        logger.warning(f"Could not find scheduled closure: {closure_id}")
        return {"success": False, "message": f"Closure {closure_id} not found"}
    
    def process_scheduled_closures(self):
        """Process any scheduled closures that are due (from maintenance_manager)"""
        from Master_Interface.master_control import get_time
        current_time = get_time()
        actions = []
        
        logger.debug(f"Processing scheduled closures. Current time: {current_time}, Scheduled closures: {len(self.scheduledClosures)}")
        
        for scheduled in self.scheduledClosures[:]:
            if scheduled['status'] == 'scheduled' and scheduled['scheduled_time'] <= current_time:
                logger.info(f"Executing scheduled closure: Block {scheduled['block_number']} on {scheduled['line']} line (scheduled: {scheduled['scheduled_time']}, current: {current_time})")
                # Execute the closure
                result = self.close_block(scheduled['line'], scheduled['block_number'])
                if result['success']:
                    scheduled['status'] = 'active'
                    logger.info(f"Successfully executed scheduled closure of block {scheduled['block_number']} on {scheduled['line']} line")
                    actions.append(f"Executed scheduled closure of block {scheduled['block_number']} on {scheduled['line']} line")
                else:
                    # Mark as failed
                    scheduled['status'] = 'failed'
                    logger.error(f"Failed to execute closure of block {scheduled['block_number']}: {result['message']}")
                    actions.append(f"Failed to execute closure of block {scheduled['block_number']}: {result['message']}")
        
        return actions
    
    def process_scheduled_openings(self):
        """Process any scheduled openings that are due (from maintenance_manager)"""
        from Master_Interface.master_control import get_time
        current_time = get_time()
        actions = []
        
        logger.debug(f"Processing scheduled openings. Current time: {current_time}, Scheduled openings: {len(self.scheduledOpenings)}")
        
        for scheduled in self.scheduledOpenings[:]:
            if scheduled['scheduled_time'] <= current_time:
                logger.info(f"Executing scheduled opening: Block {scheduled['block_number']} on {scheduled['line']} line (scheduled: {scheduled['scheduled_time']}, current: {current_time})")
                # Execute the opening
                result = self.open_block(scheduled['line'], scheduled['block_number'])
                if result['success']:
                    self.scheduledOpenings.remove(scheduled)
                    
                    # Mark related closure as completed
                    for closure in self.scheduledClosures:
                        if closure['id'] == scheduled.get('related_closure'):
                            closure['status'] = 'completed'
                    
                    logger.info(f"Successfully executed scheduled opening of block {scheduled['block_number']} on {scheduled['line']} line")
                    actions.append(f"Executed scheduled opening of block {scheduled['block_number']} on {scheduled['line']} line")
                else:
                    logger.error(f"Failed to execute opening of block {scheduled['block_number']}: {result['message']}")
                    actions.append(f"Failed to execute opening of block {scheduled['block_number']}: {result['message']}")
        
        return actions
    
    def open_block(self, line: str, block_number: int) -> Dict:
        """Reopen a block after maintenance (migrated from maintenance_manager)"""
        # Check if block is closed
        is_closed = False
        if self.ctc_system:
            is_closed = self.ctc_system.is_block_closed(line, block_number)
        else:
            # Fallback for legacy mode
            is_closed = block_number in self.maintenanceClosures[line]
        
        if is_closed:
            # Remove from state manager
            if self.ctc_system:
                self.ctc_system.remove_maintenance_closure(line, block_number)
                # Sync backward compatibility dict
                if block_number in self.maintenanceClosures[line]:
                    self.maintenanceClosures[line].remove(block_number)
            else:
                # Fallback for legacy mode
                self.maintenanceClosures[line].remove(block_number)
            
            # Send immediate opening notification to wayside controller
            if self.communication_handler:
                self.communication_handler.send_maintenance_closure(line, block_number, "open")
            
            # Also remove from failed blocks if exists
            if self.ctc_system and hasattr(self.ctc_system, 'get_block_by_line'):
                block = self.ctc_system.get_block_by_line(line, block_number)
                if block:
                    self.remove_failed_block(block)
            
            logger.info(f"Block {block_number} on {line} line opened")
            
            return {
                "success": True,
                "message": f"Block {block_number} on {line} Line is now open"
            }
        else:
            return {
                "success": False,
                "message": "This block is not currently closed"
            }
    
    def get_closed_blocks(self, line: str = None) -> Dict[str, List[int]]:
        """Get list of closed blocks, optionally filtered by line (from maintenance_manager)"""
        # Get from ctc_system state manager
        if self.ctc_system:
            closures = self.ctc_system.get_maintenance_closures()
        else:
            # Fallback for legacy mode
            closures = self.maintenanceClosures.copy()
        
        if line:
            return {line: closures.get(line, [])}
        return closures
    
    def schedule_block_closure(self, line: str, block_number: int, scheduled_time: datetime, duration_hours: float = 2.0) -> Dict:
        """
        Schedule a block closure for future maintenance (from maintenance_manager)
        
        Args:
            line: Line name ("Blue", "Red", or "Green")
            block_number: Block number to schedule for closure
            scheduled_time: When to close the block
            duration_hours: How long the closure should last (default 2 hours)
            
        Returns:
            Dict: Result with success status and scheduling info
        """
        # Check if block is already closed
        if block_number in self.maintenanceClosures[line]:
            return {
                "success": False,
                "message": f"Block {block_number} is already closed for maintenance"
            }
        
        # Check if block is already scheduled
        for scheduled in self.scheduledClosures:
            if (scheduled['line'] == line and 
                scheduled['block_number'] == block_number and 
                scheduled['status'] == 'scheduled'):
                return {
                    "success": False,
                    "message": f"Block {block_number} is already scheduled for closure"
                }
        
        # Create scheduled closure object
        import time
        from datetime import timedelta
        closure_id = f"{line}_{block_number}_{int(time.time())}"
        scheduled_closure = {
            'id': closure_id,
            'line': line,
            'block_number': block_number,
            'scheduled_time': scheduled_time,
            'end_time': scheduled_time + timedelta(hours=duration_hours),
            'duration_hours': duration_hours,
            'status': 'scheduled',  # scheduled, active, completed, cancelled
            'created_at': datetime.now()
        }
        
        self.scheduledClosures.append(scheduled_closure)
        
        # Also schedule the opening
        scheduled_opening = {
            'id': f"opening_{closure_id}",
            'line': line,
            'block_number': block_number,
            'scheduled_time': scheduled_time + timedelta(hours=duration_hours),
            'related_closure': closure_id
        }
        self.scheduledOpenings.append(scheduled_opening)
        
        logger.info(f"Scheduled closure for block {block_number} on {line} line at {scheduled_time}")
        
        return {
            "success": True,
            "message": f"Block {block_number} scheduled for closure at {scheduled_time.strftime('%H:%M')}",
            "closure_id": closure_id,
            "duration": duration_hours
        }
    
    def remove_failed_block(self, block):
        """Remove block from failed list (recovery)"""
        if block in self.failedBlocks:
            self.failedBlocks.remove(block)
            block_id = self._get_block_id(block)
            logger.info(f"Block {block_id} removed from failed blocks")
            return True
        else:
            block_id = self._get_block_id(block)
            logger.warning(f"Block {block_id} was not in failed blocks list")
            return False