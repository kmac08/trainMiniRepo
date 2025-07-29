# gui/engineer_gui.py
"""
Engineer UI module that exports the EngineerUI class for use in the main application.
This is a simple wrapper that imports from the main engineer module.
"""

from ui.train_controller_engineer import EngineerUI, EngineerWindow

__all__ = ['EngineerUI', 'EngineerWindow']
