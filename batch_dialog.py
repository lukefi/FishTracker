import sys
from PyQt5 import QtGui, QtCore, QtWidgets
from playback_manager import PlaybackManager
import track_process as tp
import file_handler as fh
from batch_track import BatchTrack

class BatchDialog(QtWidgets.QDialog):
    def __init__(self, playback_manager, params_detector=None, params_tracker=None):
        super().__init__()
        self.playback_manager = playback_manager

        self.files = set()
        self.n_parallel = fh.getParallelProcesses()

        self.detector_params = params_detector
        self.tracker_params = params_tracker

        self.main_layout = QtWidgets.QVBoxLayout(self)

        # Number of parallel processes
        self.parallel_layout = QtWidgets.QHBoxLayout()

        self.label_p = QtWidgets.QLabel("Parallel:")
        self.parallel_layout.addWidget(self.label_p)

        intValidator = EmptyOrIntValidator(1, 32, self)
        self.line_edit_p = QtWidgets.QLineEdit(self)
        self.line_edit_p.setValidator(intValidator)
        self.line_edit_p.setAlignment(QtCore.Qt.AlignRight)
        self.line_edit_p.editingFinished.connect(self.parallelEditFinished)
        self.line_edit_p.setText(str(self.n_parallel))

        self.parallel_layout.addWidget(self.line_edit_p)
        self.main_layout.addLayout(self.parallel_layout)

        # Modify files buttons
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

        # File list
        self.file_list = QtWidgets.QListWidget(self)
        self.main_layout.addWidget(self.file_list)

        # Start button
        self.start_btn = QtWidgets.QPushButton(self)
        self.start_btn.setText("Start")
        self.start_btn.clicked.connect(self.startBatch)
        self.main_layout.addWidget(self.start_btn)

        self.setLayout(self.main_layout)
        self.setWindowTitle("Run batch")

    def parallelEditFinished(self):
        try:
            int_value = int(self.line_edit_p.text())
            self.n_parallel = int_value
        except ValueError:
            self.line_edit_p.setText(str(self.n_parallel))


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
        fh.setParallelProcesses(self.n_parallel)
        batch_track = BatchTrack(False, self.files, self.n_parallel)
        self.playback_manager.runInThread(batch_track.beginTrack)

class EmptyOrIntValidator(QtGui.QIntValidator):
    def __init__(self, *args, **kwargs):
        super(EmptyOrIntValidator, self).__init__(*args, **kwargs)

    def validate(self, text, pos):
        state, text, pos = super(EmptyOrIntValidator, self).validate(text, pos)
            
        if state != QtGui.QValidator.Acceptable and text == "":
            state = QtGui.QValidator.Acceptable
        return state, text, pos


if __name__ == "__main__":
    def showDialog():
        dialog = BatchDialog(playback_manager)
        dialog.exec_()

    app = QtWidgets.QApplication(sys.argv)
    w = QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, w)

    b = QtWidgets.QPushButton(w)
    b.setText("Show dialog")
    b.move(50,50)
    b.clicked.connect(showDialog)
    w.setWindowTitle("BatcDialog test")
    w.show()
    showDialog()
    sys.exit(app.exec_())