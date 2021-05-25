import sys
from PyQt5 import QtGui, QtCore, QtWidgets
import track_process as tp
import batch_track as bt

class BatchDialog(QtWidgets.QDialog):
    def __init__(self, params_detector=None, params_tracker=None):
        super().__init__()
        self.files = set()

        self.detector_params = params_detector
        self.tracker_params = params_tracker

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.list_btn_layout = QtWidgets.QHBoxLayout()

        self.select_files_btn = QtWidgets.QPushButton(self)
        self.select_files_btn.setText("Add files")
        self.select_files_btn.clicked.connect(self.getFiles)
        self.list_btn_layout.addWidget(self.select_files_btn)

        self.clear_files_btn = QtWidgets.QPushButton(self)
        self.clear_files_btn.setText("Clear files")
        self.clear_files_btn.clicked.connect(self.clearFiles)
        self.list_btn_layout.addWidget(self.clear_files_btn)

        self.main_layout.addLayout(self.list_btn_layout)

        self.file_list = QtWidgets.QListWidget(self)
        self.main_layout.addWidget(self.file_list)

        self.start_btn = QtWidgets.QPushButton(self)
        self.start_btn.setText("Start")
        self.start_btn.clicked.connect(self.startBatch)
        self.main_layout.addWidget(self.start_btn)


        self.setLayout(self.main_layout)


    def getFiles(self):
        for file in tp.getFiles():
            self.files.add(file)

        self.file_list.clear()

        for file in self.files:
            self.file_list.addItem(file)

    def clearFiles(self):
        self.files.clear()
        self.file_list.clear()

    def startBatch(self):
        pass

if __name__ == "__main__":
    def showDialog():
        dialog = BatchDialog()
        dialog.exec_()

    app = QtWidgets.QApplication(sys.argv)
    w = QtWidgets.QMainWindow()
    b = QtWidgets.QPushButton(w)
    b.setText("Show dialog")
    b.move(50,50)
    b.clicked.connect(showDialog)
    w.setWindowTitle("BatcDialog test")
    w.show()
    sys.exit(app.exec_())