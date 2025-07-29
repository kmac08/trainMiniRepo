#!/usr/bin/env python3
"""
Launcher script for the Big Train Group Master Control Interface
"""
import sys
import os

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

if __name__ == "__main__":
    # Import and run the master interface
    from Master_Interface.master_control import main
    main()