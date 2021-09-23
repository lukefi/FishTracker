import sys, os
import track_process as tp
import file_handler as fh
import iconsLauncher as uiIcons

from PyQt5 import QtGui, QtCore, QtWidgets
from playback_manager import PlaybackManager
from batch_track import BatchTrack
from log_object import LogObject
from collapsible_box import CollapsibleBox

class BatchDialog(QtWidgets.QDialog):
    """
    UI window/dialog for configuring and launching BatchTrack processes.
    """
    def __init__(self, playback_manager, params_detector=None, params_tracker=None):
        super().__init__()
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)
        self.playback_manager = playback_manager

        self.files = set()
        self.n_parallel = fh.getParallelProcesses()
        self.save_path = fh.getConfValue(fh.ConfKeys.latest_batch_directory)
        self.batch_track = None

        self.detector_params = params_detector
        self.tracker_params = params_tracker

        self.initUI()

        self.setRemoveBtnActive(None, None)
        self.setListDependentButtons()

    def initUI(self):
        self.main_layout = QtWidgets.QVBoxLayout(self)

        # Number of parallel processes
        self.parallel_layout = QtWidgets.QHBoxLayout()

        parallel_tooltip = "Defines the number of files that are processed simultaneosly / in parallel."
        self.label_p = QtWidgets.QLabel("Parallel:")
        self.label_p.setToolTip(parallel_tooltip)
        self.parallel_layout.addWidget(self.label_p)

        intValidator = EmptyOrIntValidator(1, 32, self)
        self.line_edit_p = QtWidgets.QLineEdit(self)
        self.line_edit_p.setValidator(intValidator)
        self.line_edit_p.setAlignment(QtCore.Qt.AlignRight)
        self.line_edit_p.editingFinished.connect(self.parallelEditFinished)
        self.line_edit_p.setText(str(self.n_parallel))
        self.line_edit_p.setToolTip(parallel_tooltip)

        self.parallel_layout.addWidget(self.line_edit_p)
        self.main_layout.addLayout(self.parallel_layout)

        # Save path
        self.path_layout = QtWidgets.QHBoxLayout()

        path_tooltip = "Set the folder where the results are saved."
        self.label_path = QtWidgets.QLabel("Save path:")
        self.label_path.setToolTip(path_tooltip)
        self.path_layout.addWidget(self.label_path)

        self.line_edit_path = QtWidgets.QLineEdit(self)
        #self.line_edit_path.setAlignment(QtCore.Qt.AlignRight)
        self.line_edit_path.editingFinished.connect(self.savePathEditFinished)
        self.line_edit_path.setText(self.save_path)
        self.line_edit_path.setToolTip(path_tooltip)
        self.path_layout.addWidget(self.line_edit_path)

        self.btn_path = QtWidgets.QToolButton()
        self.btn_path.setIcon(QtGui.QIcon(uiIcons.FGetIcon("three_dots")))
        self.btn_path.clicked.connect(self.selectSavePath)
        self.path_layout.addWidget(self.btn_path)

        self.main_layout.addLayout(self.path_layout)

        self.double_layout = QtWidgets.QHBoxLayout()
        double_tooltip = "Perform double tracking."
        self.label_double = QtWidgets.QLabel("Double tracking:")
        self.label_double.setToolTip(double_tooltip)
        self.double_layout.addWidget(self.label_double)

        self.check_double = QtWidgets.QCheckBox("")
        self.check_double.setChecked(fh.getConfValue(fh.ConfKeys.batch_double_track))
        self.double_layout.addWidget(self.check_double)

        self.main_layout.addLayout(self.double_layout)

        # Test file
        if fh.getTestFilePath() is not None:
            self.test_layout = QtWidgets.QHBoxLayout()

            test_tooltip = "Use a test file instead of selected files."
            self.label_test = QtWidgets.QLabel("Test file:")
            self.label_test.setToolTip(test_tooltip)
            self.test_layout.addWidget(self.label_test)

            self.check_test = QtWidgets.QCheckBox("")
            self.check_test.stateChanged.connect(self.setListDependentButtons)
            self.test_layout.addWidget(self.check_test)

            self.main_layout.addLayout(self.test_layout)
        else:
            self.check_test = None

        # Save options
        self.form_layout_save = QtWidgets.QFormLayout()

        def setupCheckbox(label, tooltip, layout, key):
            qlabel = QtWidgets.QLabel(label)
            qlabel.setToolTip(tooltip)
            checkbox = QtWidgets.QCheckBox("")
            checkbox.setToolTip(tooltip)
            self.form_layout_save
            layout.addRow(qlabel, checkbox)
            checkbox.setChecked(fh.getConfValue(key))
            checkbox.stateChanged.connect(lambda x: fh.setConfValue(key, x))
            return checkbox

        self.check_save_dets = setupCheckbox("Export detections\t\t", "Export detections to a text file.",
                                             self.form_layout_save, fh.ConfKeys.batch_save_detections)
        self.check_save_tracks = setupCheckbox("Export tracks", "Export tracks to a text file.",
                                               self.form_layout_save, fh.ConfKeys.batch_save_tracks)
        self.check_save_complete = setupCheckbox("Save results", "Save results to a .fish file.",
                                                 self.form_layout_save, fh.ConfKeys.batch_save_complete)
        self.check_binary = setupCheckbox("Binary format", "Save results to a binary format. JSON format is used otherwise.",
                                          self.form_layout_save, fh.ConfKeys.save_as_binary)

        self.collapsible_save = CollapsibleBox("Save options", self)
        self.collapsible_save.setContentLayout(self.form_layout_save)
        self.main_layout.addWidget(self.collapsible_save)

        # Modify files buttons
        self.list_btn_layout = QtWidgets.QHBoxLayout()

        self.select_files_btn = QtWidgets.QPushButton(self)
        self.select_files_btn.setText("Add files")
        self.select_files_btn.clicked.connect(self.getFiles)
        self.list_btn_layout.addWidget(self.select_files_btn)

        self.remove_file_btn = QtWidgets.QPushButton(self)
        self.remove_file_btn.setText("Remove file")
        self.remove_file_btn.clicked.connect(self.removeFile)
        self.list_btn_layout.addWidget(self.remove_file_btn)

        self.clear_files_btn = QtWidgets.QPushButton(self)
        self.clear_files_btn.setText("Clear files")
        self.clear_files_btn.clicked.connect(self.clearFiles)
        self.list_btn_layout.addWidget(self.clear_files_btn)

        self.main_layout.addLayout(self.list_btn_layout)

        # File list
        self.file_list = QtWidgets.QListWidget(self)
        self.main_layout.addWidget(self.file_list)
        self.file_list.currentItemChanged.connect(self.setRemoveBtnActive)

        # Status label
        self.status_label = QtWidgets.QLabel()
        self.setStatusLabel()
        self.main_layout.addWidget(self.status_label)

        # Start button
        self.start_btn = QtWidgets.QPushButton(self)
        self.start_btn.setText("Start")
        self.start_btn.clicked.connect(self.toggleBatch)
        self.main_layout.addWidget(self.start_btn)

        self.setLayout(self.main_layout)
        self.setWindowTitle("Run batch")

    def parallelEditFinished(self):
        try:
            int_value = int(self.line_edit_p.text())
            self.n_parallel = int_value
        except ValueError:
            self.line_edit_p.setText(str(self.n_parallel))

    def savePathEditFinished(self):
        if os.path.exists(self.line_edit_path.text()):
            self.save_path = self.line_edit_path.text()
        else:
            self.line_edit_path.setText(self.save_path)

    def selectSavePath(self):
        open_path = self.line_edit_path.text()
        open_path = open_path if os.path.exists(open_path) else None
        path = self.playback_manager.selectSaveDirectory(open_path, update_conf=False)
        if path != "" :
            self.save_path = path
            self.line_edit_path.setText(path)



    def getFiles(self):
        for file in tp.getFiles():
            self.files.add(file)

        self.updateList()

    def removeFile(self):
        for file in self.file_list.selectedItems():
            if file.text() in self.files:
                self.files.remove(file.text())
        
        self.updateList()

    def setRemoveBtnActive(self, current, previous):
        is_selected = current is not None
        self.remove_file_btn.setEnabled(is_selected)

    def setListDependentButtons(self):
        """
        Updates the state of buttons that require at least one file to be selected.
        """
        list_not_empty = len(self.files) > 0
        test_btn = False if self.check_test is None else self.check_test.isChecked()

        self.clear_files_btn.setEnabled(list_not_empty)
        self.start_btn.setEnabled(list_not_empty or test_btn)

    def clearFiles(self):
        self.files.clear()
        self.updateList()

    def updateList(self):
        self.file_list.clear()
        for file in self.files:
            self.file_list.addItem(file)
        self.setListDependentButtons()

    def toggleBatch(self):
        """
        Starts a new batch process or cancels the existing one.
        """
        if self.batch_track is None:
            self.startBatch()
        else:
            self.terminateBatch()

    def startBatch(self):
        """
        Starts a new batch process.
        """
        fh.setParallelProcesses(self.n_parallel)
        fh.setConfValue(fh.ConfKeys.batch_double_track, self.check_double.isChecked())
        fh.setConfValue(fh.ConfKeys.latest_batch_directory, self.save_path)

        self.batch_track = BatchTrack(False, self.files, self.save_path, self.n_parallel,
                                      True, self.detector_params, self.tracker_params,
                                      self.check_double.isChecked())
        self.batch_track.active_processes_changed_signal.connect(self.setStatusLabel)
        self.batch_track.exit_signal.connect(self.onBatchExit)

        use_test_file = self.check_test is not None and self.check_test.isChecked()

        f = lambda: self.batch_track.beginTrack(use_test_file)
        self.playback_manager.runInThread(f)

        self.start_btn.setText("Cancel")
        self.setStatusLabel()

    def terminateBatch(self):
        """
        Terminates existing batch process.
        """
        self.batch_track.terminate()
        self.batch_track = None
        self.start_btn.setText("Start")
        self.start_btn.setEnabled(False)
        self.setStatusLabel()

    def onBatchExit(self, finished):
        """
        Called when the system is ready to start a new batch.
        """

        LogObject().print("Batch done.")

        self.start_btn.setText("Start")
        self.start_btn.setEnabled(True)
        self.batch_track = None
        self.setStatusLabel()

    def setStatusLabel(self):
        """
        Sets the status label based on the current state of the system.
        """
        if self.batch_track is None:
            self.status_label.setText("Status: Inactive")
        else:
            process_ids = [id + 1 for id in self.batch_track.active_processes]
            if len(process_ids) > 1:
                text = "Status: Processing files {} / {}".format(process_ids, self.batch_track.total_processes)
            elif len(process_ids) == 1:
                text = "Status: Processing file {} / {}".format(process_ids[0], self.batch_track.total_processes)
            else:
                text = "Status: No active files to process"

            self.status_label.setText(text)

    def closeEvent(self, e):
        """
        Terminates batch track (if active) when the dialog window is closed.
        """
        if self.batch_track is not None:
            self.terminateBatch()


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