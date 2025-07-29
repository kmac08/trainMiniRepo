"""
CTC Core Package - UML-Compliant Business Logic
===============================================
Contains UML-compliant core business logic for centralized traffic control.
All classes implement the specifications from the UML diagrams.
"""

# Import UML-compliant core classes
from .ctc_system import CTCSystem
from .communication_handler import CommunicationHandler
from .display_manager import DisplayManager
from .failure_manager import FailureManager
from .route_manager import RouteManager
from .block import Block
from .route import Route

__all__ = [
    'CTCSystem',
    'CommunicationHandler', 
    'DisplayManager',
    'FailureManager',
    'RouteManager',
    'Block',
    'Route',
]