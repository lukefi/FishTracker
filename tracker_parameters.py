from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from tracker import Tracker
from detector_parameters import LabeledSlider
from fish_manager import FishManager

class TrackerParametersView(QWidget):
    def __init__(self, playback_manager, tracker, detector):
        super().__init__()
        self.playback_manager = playback_manager
        self.tracker = tracker
        self.detector = detector

        self.initUI()

        self.playback_manager.polars_loaded.append(self.setButtonsEnabled)
        self.detector.state_changed_event.append(self.setButtonsEnabled)
        self.tracker.state_changed_event.append(self.setButtonsEnabled)
        self.tracker.state_changed_event.append(self.setButtonTexts)
        #self.tracker.state_changed_event.append(self.setButtonTexts)
        self.setButtonsEnabled()

    def setButtonsEnabled(self):
        all_value = self.tracker.parametersDirty() and self.playback_manager.isPolarsDone() and ((not self.detector.initializing and not self.detector.computing) or self.tracker.tracking)
        self.track_all_btn.setEnabled(all_value)

    def setButtonTexts(self):
        if self.tracker.tracking:
            self.track_all_btn.setText("Cancel")
        else:
            self.track_all_btn.setText("Track All")

    def trackAll(self):
        if not self.tracker.tracking:
            self.playback_manager.runInThread(self.tracker.trackAllDetectorFrames)
        else:
            if self.detector.initializing:
                self.detector.stop_initializing = True
            elif self.detector.computing:
                self.detector.stop_computing = True
            else:
                self.tracker.stop_tracking = True

    def initUI(self):
        self.vertical_layout = QVBoxLayout()
        self.vertical_layout.setObjectName("verticalLayout")
        self.vertical_layout.setSpacing(5)
        self.vertical_layout.setContentsMargins(7,7,7,7)

        self.main_label = QLabel(self)
        self.main_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.main_label.setText("Tracker options")
        self.vertical_layout.addWidget(self.main_label)

        self.form_layout = QFormLayout()
        self.max_age_slider = LabeledSlider("Max age", self.form_layout, [self.tracker.setMaxAge], 20, 1, 100, self)
        self.min_hits_slider = LabeledSlider("Min hits", self.form_layout, [self.tracker.setMinHits], 3, 1, 10, self)
        self.iou_threshold_slider = LabeledSlider("IoU threshold", self.form_layout, [self.tracker.setIoUThreshold], 10, 1, 100, self, lambda x: x/100, lambda x: 100*x)
        self.min_detections_slider = LabeledSlider("IoU threshold", self.form_layout, [self.tracker.setIoUThreshold], 10, 1, 100, self, lambda x: x/100, lambda x: 100*x)
        self.vertical_layout.addLayout(self.form_layout)

        self.vertical_layout.addStretch()

        self.button_layout = QHBoxLayout()
        self.button_layout.setObjectName("buttonLayout")
        self.button_layout.setSpacing(7)
        self.button_layout.setContentsMargins(0,0,0,0)

        self.track_all_btn = QPushButton()
        self.track_all_btn.setObjectName("trackAllButton")
        self.track_all_btn.setText("Track all")
        self.track_all_btn.clicked.connect(self.trackAll)

        self.button_layout.addWidget(self.track_all_btn)
        self.button_layout.addStretch()

        self.vertical_layout.addLayout(self.button_layout)

        self.setLayout(self.vertical_layout)


if __name__ == "__main__":
    import sys
    from playback_manager import PlaybackManager
    from detector import Detector
    
    app = QApplication(sys.argv)
    main_window = QMainWindow()
    playback_manager = PlaybackManager(app, main_window)

    detector = Detector(playback_manager)

    tracker = Tracker(detector)
    tracker_params = TrackerParametersView(playback_manager, tracker, detector)

    main_window.setCentralWidget(tracker_params)
    main_window.show()
    sys.exit(app.exec_())
