from PyQt5 import QtCore, QtGui, QtWidgets
from image_manipulation import ImageProcessor
import iconsLauncher as uiIcons

class ParameterList(QtWidgets.QToolBar):
    def __init__(self, playback_manager, sonar_processor, sonar_viewer, fish_manager, detector, tracker, echogram):
        super().__init__()
        self.playback_manager = playback_manager
        self.sonar_viewer = sonar_viewer
        self.sonar_processor = sonar_processor
        self.fish_manager = fish_manager
        self.detector = detector
        self.tracker = tracker
        self.echogram = echogram

        self.setOrientation(QtCore.Qt.Vertical)
        btn_size = QtCore.QSize(30,30)


        # --- Echogram options ---

        # Echogram detections
        self.show_echogram_detections_btn = QtWidgets.QPushButton(self)
        self.show_echogram_detections_btn.setObjectName("showEchogramDetections")
        self.show_echogram_detections_btn.setFlat(True)
        self.show_echogram_detections_btn.setCheckable(True)
        self.show_echogram_detections_btn.setChecked(False)
        self.show_echogram_detections_btn.clicked.connect(self.showEchogramDetectionsChanged)
        self.show_echogram_detections_btn.setToolTip("Show detections\nOverlay the results from detector to Echogram")
        self.show_echogram_detections_btn.setIcon(QtGui.QIcon(uiIcons.FGetIcon("detections")))
        self.show_echogram_detections_btn.setIconSize(btn_size)

        # Echogram tracks
        self.show_echogram_tracks_btn = QtWidgets.QPushButton(self)
        self.show_echogram_tracks_btn.setObjectName("showEchogramTracks")
        self.show_echogram_tracks_btn.setFlat(True)
        self.show_echogram_tracks_btn.setCheckable(True)
        self.show_echogram_tracks_btn.setChecked(True)
        self.show_echogram_tracks_btn.clicked.connect(self.showEchogramTracksChanged)
        self.show_echogram_tracks_btn.setToolTip("Show tracks\nOverlay the results from tracker to Echogram")
        self.show_echogram_tracks_btn.setIcon(QtGui.QIcon(uiIcons.FGetIcon("tracks")))
        self.show_echogram_tracks_btn.setIconSize(btn_size)

        # Echogram background subtraction
        self.echogram_bgsub_btn = QtWidgets.QPushButton(self)
        self.echogram_bgsub_btn.setObjectName("subtractEchogramBackground")
        self.echogram_bgsub_btn.setFlat(True)
        self.echogram_bgsub_btn.setCheckable(True)
        self.echogram_bgsub_btn.setChecked(False)
        if self.echogram is not None:
            self.echogram_bgsub_btn.clicked.connect(self.echogram.showBGSubtraction)
        self.echogram_bgsub_btn.clicked.connect(self.playback_manager.refreshFrame)
        self.echogram_bgsub_btn.setToolTip("Background subtraction\nShow background subtraction in Echogram")
        self.echogram_bgsub_btn.setIcon(QtGui.QIcon(uiIcons.FGetIcon("background_subtraction")))
        self.echogram_bgsub_btn.setIconSize(btn_size)


        # --- Sonar view options ---

        # SonarView gamma slider + value
        self.gamma_value = QtWidgets.QLabel("1.0", self)
        self.gamma_value.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)
        self.gamma_value.setMinimumWidth(30)
        self.gamma_value.setToolTip("Gamma")

        self.gamma_slider = QtWidgets.QSlider(QtCore.Qt.Vertical)
        self.gamma_slider.setMinimum(10)
        self.gamma_slider.setMaximum(40)
        self.gamma_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.gamma_slider.setTickInterval(1)
        self.gamma_slider.setValue(20)
        self.gamma_slider.valueChanged.connect(self.gammaSliderChanged)
        self.gamma_slider.valueChanged.connect(self.playback_manager.refreshFrame)
        self.gamma_slider.setMinimumHeight(100)
        self.gamma_slider.setToolTip("Gamma\nGamma value for Sonar View")

        # SonarView background subtraction
        self.bgsub_btn = QtWidgets.QPushButton(self)
        self.bgsub_btn.setObjectName("subtractBackground")
        self.bgsub_btn.setFlat(True)
        self.bgsub_btn.setCheckable(True)
        self.bgsub_btn.setIcon(QtGui.QIcon(uiIcons.FGetIcon("background_subtraction")))
        self.bgsub_btn.setIconSize(btn_size)
        self.bgsub_btn.clicked.connect(self.detector.setShowBGSubtraction)
        self.bgsub_btn.clicked.connect(self.playback_manager.refreshFrame)
        self.bgsub_btn.setToolTip("Background subtraction\nShow background subtraction used in detector")
  
        # SonarView distance measurement
        self.measure_btn = QtWidgets.QPushButton(self)
        self.measure_btn.setObjectName("measureDistance")
        self.measure_btn.setFlat(True)
        self.measure_btn.setCheckable(True)
        self.measure_btn.setIcon(QtGui.QIcon(uiIcons.FGetIcon("measure")))
        self.measure_btn.setIconSize(btn_size)
        if self.sonar_viewer is not None:
            self.measure_btn.clicked.connect(self.sonar_viewer.measureDistance)
            self.sonar_viewer.sonar_figure.measure_toggle.append(self.toggleMeasureBtn)
        self.measure_btn.setToolTip("Measure distance\nDraw a line in Sonar View to measure a distance between two points")

        # SonarView colormap
        self.colormap_btn = QtWidgets.QPushButton(self)
        self.colormap_btn.setObjectName("setColormap")
        self.colormap_btn.setFlat(True)
        self.colormap_btn.setCheckable(True)
        self.colormap_btn.setChecked(True)
        self.colormap_btn.setIcon(QtGui.QIcon(uiIcons.FGetIcon("colormap")))
        self.colormap_btn.setIconSize(btn_size)
        self.colormap_btn.clicked.connect(self.sonar_processor.setColorMap)
        self.colormap_btn.clicked.connect(self.playback_manager.refreshFrame)
        self.colormap_btn.setToolTip("Color map\nColor Sonar View with a blue colormap")

        # SonarView detections
        self.show_detections_btn = QtWidgets.QPushButton()
        self.show_detections_btn.setObjectName("showDetections")
        self.show_detections_btn.setFlat(True)
        self.show_detections_btn.setCheckable(True)
        self.show_detections_btn.setChecked(self.sonar_viewer.sonar_figure.show_detections)
        self.show_detections_btn.clicked.connect(self.showDetectionsChanged)
        self.show_detections_btn.setToolTip("Show detections\nOverlay the results from detector to Sonar View")
        self.show_detections_btn.setIcon(QtGui.QIcon(uiIcons.FGetIcon("detections")))
        self.show_detections_btn.setIconSize(btn_size)

        # SonarView detection size
        self.show_detection_size_btn = QtWidgets.QPushButton()
        self.show_detection_size_btn.setObjectName("showDetectionSize")
        self.show_detection_size_btn.setFlat(True)
        self.show_detection_size_btn.setCheckable(True)
        self.show_detection_size_btn.setChecked(self.sonar_viewer.sonar_figure.show_detection_size)
        self.show_detection_size_btn.clicked.connect(self.showDetectionSizeChanged)
        self.show_detection_size_btn.setToolTip("Show detection size\nShow also the length of the detection")
        self.show_detection_size_btn.setIcon(QtGui.QIcon(uiIcons.FGetIcon("det_size")))
        self.show_detection_size_btn.setIconSize(btn_size)

        # SonarView tracks
        self.show_tracks_btn = QtWidgets.QPushButton()
        self.show_tracks_btn.setObjectName("showTracks")
        self.show_tracks_btn.setFlat(True)
        self.show_tracks_btn.setCheckable(True)
        self.show_tracks_btn.setChecked(self.sonar_viewer.sonar_figure.show_tracks)
        self.show_tracks_btn.clicked.connect(self.showTracksChanged)
        self.show_tracks_btn.setToolTip("Show tracks\nOverlay the results from tracker to Sonar View")
        self.show_tracks_btn.setIcon(QtGui.QIcon(uiIcons.FGetIcon("tracks")))
        self.show_tracks_btn.setIconSize(btn_size)

        # SonarView track IDs
        self.show_trackingIDs_btn = QtWidgets.QPushButton()
        self.show_trackingIDs_btn.setObjectName("showTrackID")
        self.show_trackingIDs_btn.setFlat(True)
        self.show_trackingIDs_btn.setCheckable(True)
        self.show_trackingIDs_btn.setChecked(self.sonar_viewer.sonar_figure.show_track_id)
        self.show_trackingIDs_btn.clicked.connect(self.showTrackIDsChanged)
        self.show_trackingIDs_btn.setToolTip("Show track IDs\nShow also the IDs of the tracked fish")
        self.show_trackingIDs_btn.setIcon(QtGui.QIcon(uiIcons.FGetIcon("track_id")))
        self.show_trackingIDs_btn.setIconSize(btn_size)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine);
        line.setFrameShadow(QtWidgets.QFrame.Sunken)

        line2 = QtWidgets.QFrame()
        line2.setFrameShape(QtWidgets.QFrame.HLine);
        line2.setFrameShadow(QtWidgets.QFrame.Sunken)

        # Add widgets from top to bottom
        self.addWidget(self.echogram_bgsub_btn)
        self.addWidget(self.show_echogram_detections_btn)
        self.addWidget(self.show_echogram_tracks_btn)
        self.addWidget(line)
        self.addWidget(self.gamma_value)
        self.addWidget(self.gamma_slider)
        self.addWidget(self.bgsub_btn)
        self.addWidget(self.colormap_btn)
        self.addWidget(self.show_detections_btn)
        self.addWidget(self.show_tracks_btn)
        self.addWidget(self.show_detection_size_btn)
        self.addWidget(self.show_trackingIDs_btn)
        self.addWidget(line2)
        self.addWidget(self.measure_btn)

    def gammaSliderChanged(self, value):
        applied_value = float(value)/20
        self.sonar_processor.setGamma(applied_value)
        self.gamma_value.setText(str(applied_value))

    def showDetectionsChanged(self, value):
        self.sonar_viewer.sonar_figure.show_detections = value
        self.playback_manager.refreshFrame()

    def showDetectionSizeChanged(self, value):
        self.sonar_viewer.sonar_figure.show_detection_size = value
        self.playback_manager.refreshFrame()

    def showTracksChanged(self, value):
        self.sonar_viewer.sonar_figure.show_tracks = value
        self.playback_manager.refreshFrame()

    def showTrackIDsChanged(self, value):
        self.sonar_viewer.sonar_figure.show_track_id = value
        self.playback_manager.refreshFrame()

    def showEchogramDetectionsChanged(self, value):
        if value and self.show_echogram_tracks_btn.isChecked():
            self.show_echogram_tracks_btn.click()

        self.detector.setShowEchogramDetections(value)
        self.playback_manager.refreshFrame()

    def showEchogramTracksChanged(self, value):
        if value and self.show_echogram_detections_btn.isChecked():
            self.show_echogram_detections_btn.click()

        self.fish_manager.setShowEchogramFish(value)
        self.playback_manager.refreshFrame()

    def toggleMeasureBtn(self, value):
        if self.measure_btn.isChecked() == value:
                self.measure_btn.toggle()

if __name__ == "__main__":
    import sys
    from playback_manager import PlaybackManager
    from fish_manager import FishManager
    from detector import Detector
    from tracker import Tracker
    from sonar_widget import SonarViewer

    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    fish_manager = FishManager(None, None)
    sonar_processor = ImageProcessor()
    detector = Detector(playback_manager)
    tracker = Tracker(detector)
    sonar_viewer = SonarViewer(main_window, playback_manager, detector, tracker, fish_manager)

    parameter_list = ParameterList(playback_manager, sonar_processor, sonar_viewer, fish_manager, detector, tracker, None)
    main_window.setCentralWidget(parameter_list)
    main_window.show()
    sys.exit(app.exec_())