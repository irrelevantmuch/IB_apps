from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import Qt

class ProgressBarDialog(QDialog):
    def __init__(self, parent=None):
        super(ProgressBarDialog, self).__init__(parent)

        # Create and set up widgets
        self.overallLabel = QLabel("Overall Progress:", self)
        self.overallProgressBar = QProgressBar(self)
        self.currentProcessLabel = QLabel(self)
        self.currentProgressBar = QProgressBar(self)

        # Create and set layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.overallLabel)
        layout.addWidget(self.overallProgressBar)
        layout.addWidget(self.currentProcessLabel)
        layout.addWidget(self.currentProgressBar)

        self.setLayout(layout)

        # Set initial values
        self.currentProcessLabel.setText("Initializing...")
        self.overallProgressBar.setValue(0)
        self.currentProgressBar.setValue(0)
        self.overallProgressBar.setRange(0, 100)
        self.currentProgressBar.setRange(0, 100)

        # Set window properties
        self.setWindowTitle("Progress")
        self.setWindowModality(Qt.ApplicationModal)

    def setOverallProgress(self, overallProgress, text):
        self.overallProgressBar.setValue(int(overallProgress * 100))
        self.currentProcessLabel.setText(text)
        # Close the dialog if overall progress is complete
        if overallProgress >= 1.0:
            self.accept()


    def setProcessProgress(self, currentProgress):
        self.currentProgressBar.setValue(int(currentProgress * 100))
        

        