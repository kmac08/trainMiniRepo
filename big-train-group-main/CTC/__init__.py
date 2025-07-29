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
except ImportError:
    # PyQt5 not available - only core functionality will work
    pass

__version__ = "2.0.0"
__author__ = "ECE 1140 Team"