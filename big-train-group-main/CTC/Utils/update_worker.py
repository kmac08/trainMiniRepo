"""
CTC Utils - Update Worker
=========================
Threading utility for handling system updates at different frequencies.
Updated to work with migrated CTC System architecture.
"""

from PyQt5.QtCore import QThread, pyqtSignal
from datetime import datetime


class UpdateWorker(QThread):
    """Worker thread for system updates with separate signals for different update frequencies"""
    updateData = pyqtSignal()  # High frequency - data only
    updateVisuals = pyqtSignal()  # Low frequency - charts/plots
    updateTables = pyqtSignal()  # Medium frequency - table content

    def __init__(self, ctc_office):
        super().__init__()
        self.ctcOffice = ctc_office
        self.running = True
        self.updateCounter = 0

    def run(self):
        """Main update loop with different frequencies for different components"""
        while self.running and getattr(self.ctcOffice, 'running', True):
            try:
                # Get the CTC system instance
                ctc_system = getattr(self.ctcOffice, 'ctc_system', None)
                if not ctc_system:
                    self.msleep(100)
                    continue

                # System tick for CTC system (replaces individual manager updates)
                try:
                    from Master_Interface.master_control import get_time
                    current_time = get_time()
                except RuntimeError:
                    # Fall back to real time if master interface isn't running
                    current_time = datetime.now()
                ctc_system.system_tick(current_time)

                # High frequency data updates (every 100ms)
                self.updateData.emit()

                # Medium frequency table updates (every 500ms)
                if self.updateCounter % 5 == 0:
                    self.updateTables.emit()

                # Low frequency visual updates (every 2 seconds)
                if self.updateCounter % 20 == 0:
                    self.updateVisuals.emit()

                self.updateCounter += 1
                self.msleep(100)  # 10Hz base rate

            except Exception as e:
                print(f"Update loop error: {e}")
                import traceback
                traceback.print_exc()
                self.msleep(1000)

    def stop(self):
        """Stop the update worker thread"""
        self.running = False
        self.wait()