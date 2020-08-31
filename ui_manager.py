import sys, os, cv2
from PyQt5 import QtGui, QtCore, QtWidgets

from main import MainWindow
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

class UIManager():
    def __init__(self, main_window, playback_manager, detector, tracker, fish_manager):
        self.widgets_initialized = False
        self.main_window = main_window

        self.playback = playback_manager
        self.detector = detector
        self.tracker = tracker
        self.fish_manager = fish_manager
        #self.fish_manager.testPopulate(frame_count=100)
        #self.playback.frame_available.append(self.showSonarFrame)

        self.ui = Ui_MainWindow()
        self.ui.setupUi(main_window)
        self.main_window.setupStatusBar()
        self.setUpFunctions()

        self.main_window.show()
        self.setupWidgets()
        self.playback.openTestFile()

    def setupWidgets(self):
        _translate = QtCore.QCoreApplication.translate

        echo = EchogramViewer(self.playback, self.detector, self.fish_manager)
        self.ui.splitter_2.replaceWidget(0, echo)
        self.ui.echogram_widget = echo
        echo.setMaximumHeight(400)

        self.sonar_viewer = SonarViewer(self.main_window, self.playback, self.detector, self.tracker)
        self.ui.splitter.replaceWidget(0, self.sonar_viewer)
        self.ui.sonar_widget = self.sonar_viewer

        self.tool_bar = ParameterList(self.playback, self.sonar_viewer.image_processor, self.sonar_viewer, self.fish_manager, self.detector, self.tracker)
        self.ui.horizontalLayout_2.replaceWidget(self.ui.tool_bar, self.tool_bar)
        self.tool_bar.setMaximumWidth(40)
        self.ui.tool_bar = self.tool_bar

        self.fish_manager
        self.fish_list = FishList(self.fish_manager, self.playback, self.sonar_viewer)
        self.sonar_viewer.measure_event.append(self.fish_list.setMeasurementResult)

        #self.parameter_list = ParameterList(self.playback, self.sonar_viewer.image_processor, self.fish_manager, self.detector, self.tracker)
        self.detector_parameters = DetectorParametersView(self.playback, self.detector, self.sonar_viewer.image_processor)
        detection_model = DetectionDataModel(self.detector)
        self.detection_list = DetectionList(detection_model)

        self.tracker_parameters = TrackerParametersView(self.playback, self.tracker, self.detector)

        self.output = OutputViewer()
        self.output.redirectStdOut()

        self.ui.info_widget.removeTab(0)
        #self.ui.info_widget.addTab(self.parameter_list, "")
        #self.ui.info_widget.setTabText(self.ui.info_widget.indexOf(self.parameter_list), _translate("MainWindow", "Display"))
        self.ui.info_widget.addTab(self.detector_parameters, "")
        self.ui.info_widget.setTabText(self.ui.info_widget.indexOf(self.detector_parameters), _translate("MainWindow", "Detector"))
        self.ui.info_widget.addTab(self.detection_list, "")
        self.ui.info_widget.setTabText(self.ui.info_widget.indexOf(self.detection_list), _translate("MainWindow", "Detections"))
        self.ui.info_widget.addTab(self.tracker_parameters, "")
        self.ui.info_widget.setTabText(self.ui.info_widget.indexOf(self.tracker_parameters), _translate("MainWindow", "Tracker"))
        self.ui.info_widget.addTab(self.fish_list, "")
        self.ui.info_widget.setTabText(self.ui.info_widget.indexOf(self.fish_list), _translate("MainWindow", "Fish List"))
        self.ui.info_widget.addTab(self.output, "")
        self.ui.info_widget.setTabText(self.ui.info_widget.indexOf(self.output), _translate("MainWindow", "Log"))

    def setUpFunctions(self):
        self.ui.action_Open.setShortcut('Ctrl+O')
        self.ui.action_Open.triggered.connect(self.openFile)

        self.ui.action_OpenTest = QtWidgets.QAction(self.main_window)
        self.ui.action_OpenTest.setObjectName("action_OpenTest")
        self.ui.menu_File.addAction(self.ui.action_OpenTest)
        self.ui.action_OpenTest.setShortcut('Ctrl+T')
        self.ui.action_OpenTest.triggered.connect(self.openTestFile)
        self.ui.action_OpenTest.setText(QtCore.QCoreApplication.translate("MainWindow", "&Open test file"))

        self.ui.action_save_detections = QtWidgets.QAction(self.main_window)
        self.ui.action_save_detections.setObjectName("action_save_detections")
        self.ui.menu_File.addAction(self.ui.action_save_detections)
        # self.ui.action_save_detections.setShortcut('Ctrl+Q')
        self.ui.action_save_detections.triggered.connect(self.saveDetections)
        self.ui.action_save_detections.setText(QtCore.QCoreApplication.translate("MainWindow", "&Save detections"))

        self.ui.action_close_file = QtWidgets.QAction(self.main_window)
        self.ui.action_close_file.setObjectName("action_close_file")
        self.ui.menu_File.addAction(self.ui.action_close_file)
        self.ui.action_close_file.setShortcut('Ctrl+Q')
        self.ui.action_close_file.triggered.connect(self.closeFile)
        self.ui.action_close_file.setText(QtCore.QCoreApplication.translate("MainWindow", "&Close file"))

    #def showSonarFrame(self, image):
    #    image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    #    image = QtGui.QImage(image.data, image.shape[1], image.shape[0], QtGui.QImage.Format_RGB888).rgbSwapped()
    #    self.ui.sonar_frame.setPixmap(QtGui.QPixmap.fromImage(image))

        #figurePixmap = QtGui.QPixmap.fromImage(image)
        #self.ui.sonar_frame.setPixmap(figurePixmap.scaled(ffigure.size(), pyqtCore.Qt.KeepAspectRatio))
        #ffigure.setAlignment(pyqtCore.Qt.AlignCenter)

    def getSavePath(self):
        homeDirectory = str(os.path.expanduser("~"))
        filePathTuple = QtWidgets.QFileDialog.getSaveFileName(self.main_window, "Open File", homeDirectory)
        return filePathTuple[0]

    def openFile(self):
        self.playback.openFile()

    def openTestFile(self):
        self.playback.openTestFile()

    def closeFile(self):
        self.playback.closeFile()

    def saveDetections(self):
        path = self.getSavePath()
        if path != "" :
            self.detector.saveDetectionsToFile(path)


if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow() #QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    detector = Detector(playback_manager)
    tracker = Tracker(detector)
    fish_manager = FishManager(tracker)

    detector.all_computed_event.append(playback_manager.refreshFrame)
    tracker.all_computed_signal.connect(playback_manager.refreshFrame)
    playback_manager.mapping_done.append(lambda: playback_manager.runInThread(detector.initMOG))
    playback_manager.frame_available.insert(0, detector.compute_from_event)
    playback_manager.file_opened.append(lambda x: fish_manager.clear())
    playback_manager.file_opened.append(lambda x: detector.clearDetections())

    ui_manager = UIManager(main_window, playback_manager, detector, tracker, fish_manager)
    sys.exit(app.exec_())