from PyQt5 import QtCore, QtGui, QtWidgets
from image_manipulation import ImageProcessor

class ParameterList(QtWidgets.QDialog):
    def __init__(self, playback_manager, sonar_processor, fish_manager, detector, tracker):
        super().__init__()
        self.playback_manager = playback_manager
        self.sonar_processor = sonar_processor
        self.fish_manager = fish_manager
        self.detector = detector
        self.tracker = tracker

        self.image_controls_label = QtWidgets.QLabel(self)
        self.image_controls_label.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.image_controls_label.setText("Image options")

        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.setSpacing(5)
        self.verticalLayout.setContentsMargins(7,7,7,7)

        self.distance_tick = QtWidgets.QCheckBox("Distance compensation")
        self.distance_tick.setChecked(False)
        self.distance_tick.stateChanged.connect(self.playback_manager.setDistanceCompensation)
        self.distance_tick.stateChanged.connect(self.playback_manager.refreshFrame)

        self.contrast_tick = QtWidgets.QCheckBox("Automatic contrast")
        self.contrast_tick.setChecked(False)
        self.contrast_tick.stateChanged.connect(self.sonar_processor.setAutomaticContrast)
        self.contrast_tick.stateChanged.connect(self.playback_manager.refreshFrame)

        self.gamma_layout = QtWidgets.QHBoxLayout()
        self.gamma_layout.setObjectName("gammaLayout")
        self.gamma_layout.setSpacing(5)
        self.gamma_layout.setContentsMargins(0,0,0,0)

        self.gamma_label = QtWidgets.QLabel("Gamma", self)
        self.gamma_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.gamma_label.setMinimumWidth(50)

        self.gamma_value = QtWidgets.QLabel("1.0", self)
        self.gamma_value.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)
        self.gamma_value.setMinimumWidth(50)

        self.gamma_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.gamma_slider.setMinimum(10)
        self.gamma_slider.setMaximum(40)
        self.gamma_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.gamma_slider.setTickInterval(1)
        self.gamma_slider.setValue(20)
        self.gamma_slider.valueChanged.connect(self.gammaSliderChanged)
        self.gamma_slider.valueChanged.connect(self.playback_manager.refreshFrame)

        self.gamma_layout.addWidget(self.gamma_slider)
        self.gamma_layout.addWidget(self.gamma_value)

        self.bgsub_tick = QtWidgets.QCheckBox("BG Subtraction")
        self.bgsub_tick.setChecked(False)
        self.bgsub_tick.stateChanged.connect(self.detector.setShowBGSubtraction)
        self.bgsub_tick.stateChanged.connect(self.playback_manager.refreshFrame)

        self.colormap_tick = QtWidgets.QCheckBox("Use colormap")
        self.colormap_tick.setChecked(False)
        self.colormap_tick.stateChanged.connect(self.sonar_processor.setColorMap)
        self.colormap_tick.stateChanged.connect(self.playback_manager.refreshFrame)

        self.show_detections_checkbox = QtWidgets.QCheckBox("Show detections")
        self.show_detections_checkbox.setChecked(False)
        self.show_detections_checkbox.stateChanged.connect(self.showDetectionsChanged)
        #self.show_detections_checkbox.setEnabled(False)
        #self.detector.state_changed_event.append(lambda: self.show_detections_checkbox.setEnabled(self.detector.mog_ready))

        self.show_detection_size_checkbox = QtWidgets.QCheckBox("Show detection size")
        self.show_detection_size_checkbox.setChecked(True)
        self.show_detection_size_checkbox.stateChanged.connect(self.detector.setShowSize)
        self.show_detection_size_checkbox.stateChanged.connect(self.playback_manager.refreshFrame)
        self.show_detection_size_checkbox.setEnabled(False)

        self.show_tracks_checkbox = QtWidgets.QCheckBox("Show tracks")
        self.show_tracks_checkbox.setChecked(False)
        self.show_tracks_checkbox.stateChanged.connect(self.showTracksChanged)
        #self.show_tracks_checkbox.setToolTip('This is a tooltip for the QPushButton widget') 

        #self.show_tracks_checkbox.setEnabled(False)
        #self.tracker.state_changed_event.append(lambda: self.show_tracks_checkbox.setEnabled(self.detector.mog_ready))

        self.show_trackingIDs_checkbox = QtWidgets.QCheckBox("Show tracking IDs")
        self.show_trackingIDs_checkbox.setChecked(True)
        self.show_trackingIDs_checkbox.stateChanged.connect(self.tracker.setShowTrackingIDs)
        self.show_trackingIDs_checkbox.stateChanged.connect(self.playback_manager.refreshFrame)
        self.show_trackingIDs_checkbox.setEnabled(False)

        self.verticalLayout.addWidget(self.image_controls_label)
        self.verticalLayout.addWidget(self.distance_tick)
        self.verticalLayout.addWidget(self.contrast_tick)
        self.verticalLayout.addWidget(self.gamma_label)
        self.verticalLayout.addLayout(self.gamma_layout)
        self.verticalLayout.addWidget(self.bgsub_tick)
        self.verticalLayout.addWidget(self.colormap_tick)
        self.verticalLayout.addWidget(self.show_detections_checkbox)
        self.verticalLayout.addWidget(self.show_detection_size_checkbox)
        self.verticalLayout.addWidget(self.show_tracks_checkbox)
        self.verticalLayout.addWidget(self.show_trackingIDs_checkbox)
        self.verticalLayout.addStretch()
        self.setLayout(self.verticalLayout)

    def gammaSliderChanged(self, value):
        applied_value = float(value)/20
        self.sonar_processor.setGamma(applied_value)
        self.gamma_value.setText(str(applied_value))

    def showDetectionsChanged(self, value):
        self.detector.setShowDetections(value)
        self.show_detection_size_checkbox.setEnabled(value)
        self.playback_manager.refreshFrame()

    def showTracksChanged(self, value):
        self.tracker.setShowTracks(value)
        self.show_trackingIDs_checkbox.setEnabled(value)
        self.playback_manager.refreshFrame()

if __name__ == "__main__":
    import sys
    from playback_manager import PlaybackManager
    from fish_manager import FishManager
    from detector import Detector
    from tracker import Tracker

    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    #playback_manager.openTestFile()
    fish_manager = FishManager()
    fish_manager.testPopulate(100)
    #info_w = InfoWidget(playback_manager, fish_manager)
    sonar_processor = ImageProcessor()
    detector = Detector(playback_manager)
    tracker = Tracker(detector)

    parameter_list = ParameterList(playback_manager, sonar_processor, fish_manager, detector, tracker)
    main_window.setCentralWidget(parameter_list)
    main_window.show()
    sys.exit(app.exec_())