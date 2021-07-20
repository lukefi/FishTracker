import sys, os, cv2
import numpy
from datetime import datetime
from PyQt5 import QtGui, QtCore, QtWidgets

import file_handler as fh
from main_window import MainWindow
from sonar_widget import SonarViewer
from echogram_widget import EchogramViewer
from fish_manager import FishManager
from fish_list import FishList
from parameter_list import ParameterList
from detector import Detector
from tracker import Tracker
from detector_parameters import DetectorParametersView
from detection_list import DetectionList, DetectionDataModel
from tracker_parameters import TrackerParametersView
from playback_manager import PlaybackManager
from sonar_view3 import Ui_MainWindow
from output_widget import OutputViewer
from log_object import LogObject
from batch_dialog import BatchDialog
from save_manager import SaveManager

class UIManager():
    def __init__(self, main_window, playback_manager, detector, tracker, fish_manager, save_manager):
        self.widgets_initialized = False
        self.main_window = main_window

        self.playback = playback_manager
        self.detector = detector
        self.tracker = tracker
        self.fish_manager = fish_manager
        self.save_manager = save_manager

        self.ui = Ui_MainWindow()
        self.ui.setupUi(main_window)
        self.main_window.setupStatusBar()
        self.setUpFunctions()

        self.main_window.show()
        self.setupWidgets()
        self.playback.setTitle()

        #self.fish_manager.testPopulate(frame_count=100)
        #self.playback.openTestFile()

    def setupWidgets(self):
        _translate = QtCore.QCoreApplication.translate

        echo = EchogramViewer(self.playback, self.detector, self.fish_manager)
        self.ui.splitter_2.replaceWidget(0, echo)
        self.ui.echogram_widget = echo
        echo.setMaximumHeight(400)

        self.sonar_viewer = SonarViewer(self.main_window, self.playback, self.detector, self.tracker, self.fish_manager)
        self.ui.splitter.replaceWidget(0, self.sonar_viewer)
        self.ui.sonar_widget = self.sonar_viewer

        self.tool_bar = ParameterList(self.playback, self.sonar_viewer.image_processor, self.sonar_viewer, self.fish_manager, self.detector, self.tracker, echo)
        self.ui.horizontalLayout_2.replaceWidget(self.ui.tool_bar, self.tool_bar)
        self.tool_bar.setMaximumWidth(40)
        self.ui.tool_bar = self.tool_bar

        self.fish_list = FishList(self.fish_manager, self.playback, self.sonar_viewer)
        self.sonar_viewer.measure_event.append(self.fish_list.setMeasurementResult)

        self.detector_parameters = DetectorParametersView(self.playback, self.detector, self.sonar_viewer.image_processor)
        self.save_manager.file_loaded_event.connect(self.detector_parameters.refreshValues)

        detection_model = DetectionDataModel(self.detector)
        self.detection_list = DetectionList(detection_model)

        self.tracker_parameters = TrackerParametersView(self.playback, self.tracker, self.detector)
        self.save_manager.file_loaded_event.connect(self.tracker_parameters.refreshValues)

        self.output = OutputViewer()
        #self.output.redirectStdOut()
        #self.output.connectToLogObject()
        self.output.connectToLogObject(self.addTimeStamp)
        self.output.updateLogSignal.connect(self.main_window.updateStatusLog)

        # Tabs for the side panel.
        self.ui.info_widget.removeTab(0)
        self.ui.info_widget.addTab(self.detector_parameters, "")
        self.ui.info_widget.setTabText(self.ui.info_widget.indexOf(self.detector_parameters), _translate("MainWindow", "Detector"))
        self.ui.info_widget.addTab(self.detection_list, "")
        self.ui.info_widget.setTabText(self.ui.info_widget.indexOf(self.detection_list), _translate("MainWindow", "Detections"))
        self.ui.info_widget.addTab(self.tracker_parameters, "")
        self.ui.info_widget.setTabText(self.ui.info_widget.indexOf(self.tracker_parameters), _translate("MainWindow", "Tracker"))
        self.ui.info_widget.addTab(self.fish_list, "")
        self.ui.info_widget.setTabText(self.ui.info_widget.indexOf(self.fish_list), _translate("MainWindow", "Tracks"))
        self.ui.info_widget.addTab(self.output, "")
        self.ui.info_widget.setTabText(self.ui.info_widget.indexOf(self.output), _translate("MainWindow", "Log"))

    def addTimeStamp(self, str):
        """
        Adds a time stamp to the provided string.
        """
        return "{} [{}]\n".format(str, datetime.now().time())

    def setUpFunctions(self):
        self.ui.menu_File.aboutToShow.connect(self.menuFileAboutToShow)

        self.ui.action_Open.setShortcut('Ctrl+O')
        self.ui.action_Open.triggered.connect(self.openFile)

        self.ui.action_Batch.setShortcut('Ctrl+B')
        self.ui.action_Batch.triggered.connect(self.runBatch)

        if fh.getTestFilePath() is not None:
            self.ui.action_OpenTest = QtWidgets.QAction(self.main_window)
            self.ui.action_OpenTest.setObjectName("action_OpenTest")
            self.ui.menu_File.addAction(self.ui.action_OpenTest)
            self.ui.action_OpenTest.setShortcut('Ctrl+T')
            self.ui.action_OpenTest.triggered.connect(self.openTestFile)
            self.ui.action_OpenTest.setText(QtCore.QCoreApplication.translate("MainWindow", "&Open test file"))

        self.ui.action_save_as = QtWidgets.QAction(self.main_window)
        self.ui.action_save_as.setObjectName("action_save_as")
        self.ui.menu_File.addAction(self.ui.action_save_as)
        self.ui.action_save_as.triggered.connect(self.saveAs)
        self.ui.action_save_as.setText(QtCore.QCoreApplication.translate("MainWindow", "&Save as..."))
        self.ui.action_save_as.setShortcut('Ctrl+Shift+S')

        self.ui.action_save = QtWidgets.QAction(self.main_window)
        self.ui.action_save.setObjectName("action_save")
        self.ui.menu_File.addAction(self.ui.action_save)
        self.ui.action_save.triggered.connect(self.save)
        self.ui.action_save.setText(QtCore.QCoreApplication.translate("MainWindow", "&Save..."))
        self.ui.action_save.setShortcut('Ctrl+S')

        self.ui.action_load = QtWidgets.QAction(self.main_window)
        self.ui.action_load.setObjectName("action_load")
        self.ui.menu_File.addAction(self.ui.action_load)
        self.ui.action_load.triggered.connect(self.load)
        self.ui.action_load.setText(QtCore.QCoreApplication.translate("MainWindow", "&Load..."))

        self.ui.action_export_detections = QtWidgets.QAction(self.main_window)
        self.ui.action_export_detections.setObjectName("action_export_detections")
        self.ui.menu_File.addAction(self.ui.action_export_detections)
        self.ui.action_export_detections.triggered.connect(self.exportDetections)
        self.ui.action_export_detections.setText(QtCore.QCoreApplication.translate("MainWindow", "&Export detections..."))

        self.ui.action_export_tracks = QtWidgets.QAction(self.main_window)
        self.ui.action_export_tracks.setObjectName("action_export_tracks")
        self.ui.menu_File.addAction(self.ui.action_export_tracks)
        self.ui.action_export_tracks.triggered.connect(self.exportTracks)
        self.ui.action_export_tracks.setText(QtCore.QCoreApplication.translate("MainWindow", "&Export tracks..."))

        self.ui.action_import_detections = QtWidgets.QAction(self.main_window)
        self.ui.action_import_detections.setObjectName("action_import_detections")
        self.ui.menu_File.addAction(self.ui.action_import_detections)
        self.ui.action_import_detections.triggered.connect(self.importDetections)
        self.ui.action_import_detections.setText(QtCore.QCoreApplication.translate("MainWindow", "&Import detections..."))

        self.ui.action_import_tracks = QtWidgets.QAction(self.main_window)
        self.ui.action_import_tracks.setObjectName("action_import_tracks")
        self.ui.menu_File.addAction(self.ui.action_import_tracks)
        self.ui.action_import_tracks.triggered.connect(self.importTracks)
        self.ui.action_import_tracks.setText(QtCore.QCoreApplication.translate("MainWindow", "&Import tracks..."))

        self.ui.action_close_file = QtWidgets.QAction(self.main_window)
        self.ui.action_close_file.setObjectName("action_close_file")
        self.ui.menu_File.addAction(self.ui.action_close_file)
        self.ui.action_close_file.setShortcut('Ctrl+Q')
        self.ui.action_close_file.triggered.connect(self.closeFile)
        self.ui.action_close_file.setText(QtCore.QCoreApplication.translate("MainWindow", "&Close file"))

    def openFile(self):
        try:
            self.playback.openFile()
        except FileNotFoundError as e:
            if e.filename and e.filename != "":
                LogObject().print(e)


    def openTestFile(self):
        try:
            self.playback.openTestFile()
        except FileNotFoundError as e:
            if e.filename and e.filename != "":
                LogObject().print(e)

    def closeFile(self):
        self.playback.closeFile()

    def saveAs(self):
        path = self.playback.selectSaveFile(None, "FishTracker Files (*.fish)")
        if path != "" :
            self.save_manager.saveFile(path, True)

    def save(self):
        path = None
        if self.save_manager.fast_save_enabled:
            path = self.save_manager.previous_path
            self.save_manager.saveFile(path, True)
        else:
            self.saveAs()

    def load(self):
        path = self.playback.selectLoadFile(None, "FishTracker Files (*.fish)")
        if path != "" :
            self.save_manager.loadFile(path)

    def exportDetections(self):
        path = self.playback.selectSaveFile()
        if path != "" :
            self.detector.saveDetectionsToFile(path)

    def exportTracks(self):
        path = self.playback.selectSaveFile()
        if path != "" :
            self.fish_manager.saveToFile(path)

    def importDetections(self):
        path = self.playback.selectLoadFile()
        if path != "":
            self.detector.loadDetectionsFromFile(path)

    def importTracks(self):
        path = self.playback.selectLoadFile()
        if path != "":
            self.fish_manager.loadFromFile(path)

    def runBatch(self):
        dparams = self.detector.parameters.copy()
        tparams = self.tracker.parameters.copy()
        dialog = BatchDialog(self.playback, dparams, tparams)
        dialog.exec_()

    def menuFileAboutToShow(self):
        file_open = self.playback.sonar is not None
        self.ui.action_save_as.setEnabled(file_open)
        self.ui.action_save.setEnabled(file_open)
        self.ui.action_export_detections.setEnabled(file_open)
        self.ui.action_export_tracks.setEnabled(file_open)
        self.ui.action_import_detections.setEnabled(file_open)
        self.ui.action_import_tracks.setEnabled(file_open)
        self.ui.action_close_file.setEnabled(file_open)


def launch_ui():
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow() #QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    detector = Detector(playback_manager)
    tracker = Tracker(detector)
    fish_manager = FishManager(playback_manager, tracker)
    save_manager = SaveManager(playback_manager, detector, tracker, fish_manager)

    detector.all_computed_event.append(playback_manager.refreshFrame)
    tracker.all_computed_signal.connect(playback_manager.refreshFrame)

    playback_manager.mapping_done.connect(lambda: playback_manager.runInThread(lambda: detector.initMOG(False)))
    playback_manager.mapping_done.connect(lambda: tracker.setImageShape(*playback_manager.getImageShape()))

    playback_manager.frame_available_early.connect(detector.compute_from_event)

    playback_manager.file_opened.connect(detector.clearDetections)
    playback_manager.file_closed.connect(detector.clearDetections)
    playback_manager.file_opened.connect(tracker.clear)
    playback_manager.file_closed.connect(tracker.clear)

    ui_manager = UIManager(main_window, playback_manager, detector, tracker, fish_manager, save_manager)
    sys.exit(app.exec_())


if __name__ == "__main__":
    launch_ui()