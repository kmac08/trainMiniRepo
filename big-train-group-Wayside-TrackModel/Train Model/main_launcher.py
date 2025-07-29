from train_model import TrainModel
from train_test_ui import TrainTestUI
from PyQt5.QtWidgets import QApplication

def main():
    app = QApplication([])

    # Create multiple TrainModel instances
    trains = {
        "T1": TrainModel("T1"),
        "T2": TrainModel("T2"),
        "T3": TrainModel("T3"),
    }

    test_ui = TrainTestUI(trains)
    test_ui.show()

    app.exec_()

if __name__ == "__main__":
    main()