"""
CTC Package - Central Traffic Control System
===========================================
Modular CTC system for PAAC Light Rail System

Structure:
- Core/: Business logic and data management
- UI/: User interface components  
- Utils/: Helper utilities and workers
"""

try:
    from .ctc_main import create_ctc_office, send_to_ctc, get_from_ctc
    from .Core import communication_handler
except ImportError:
    # PyQt5 not available - only core functionality will work
    create_ctc_office = None
    send_to_ctc = None
    get_from_ctc = None
    communication_handler = None

__version__ = "2.0.0"
__author__ = "ECE 1140 Team"