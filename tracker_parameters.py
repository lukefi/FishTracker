from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from tracker import Tracker
from detector_parameters import LabeledSlider
from fish_manager import FishManager

import json
import os.path
import numpy as np

PARAMETERS_PATH = "tracker_parameters.json"
PARAMETER_TYPES = {
            "max_age": int,
	        "min_hits": int,
            "search_radius": int
        }

class TrackerParametersView(QWidget):
    def __init__(self, playback_manager, tracker, detector):
        super().__init__()
        self.playback_manager = playback_manager
        self.tracker = tracker
        self.detector = detector

        self.initUI()

        self.playback_manager.polars_loaded.append(self.setButtonsEnabled)
        self.detector.state_changed_event.append(self.setButtonsEnabled)
        self.tracker.state_changed_signal.connect(self.setButtonsEnabled)
        self.tracker.state_changed_signal.connect(self.setButtonTexts)
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
        self.max_age_slider = LabeledSlider("Max age", self.form_layout, [self.tracker.setMaxAge], self.tracker.parameters.max_age, 1, 100, self)
        self.min_hits_slider = LabeledSlider("Min hits", self.form_layout, [self.tracker.setMinHits], self.tracker.parameters.min_hits, 1, 10, self)
        self.search_radius_slider = LabeledSlider("Search radius", self.form_layout, [self.tracker.setSearchRadius], self.tracker.parameters.search_radius, 1, 100, self)
        self.vertical_layout.addLayout(self.form_layout)

        self.vertical_layout.addStretch()

        self.save_btn = QPushButton()
        self.save_btn.setObjectName("saveButton")
        self.save_btn.setText("Save")
        self.save_btn.setToolTip("Save tracker parameters")
        self.save_btn.clicked.connect(self.saveJSON)

        self.load_btn = QPushButton()
        self.load_btn.setObjectName("loadButton")
        self.load_btn.setText("Load")
        self.load_btn.setToolTip("Load tracker parameters")
        self.load_btn.clicked.connect(self.loadJSON)

        self.reset_btn = QPushButton()
        self.reset_btn.setObjectName("resetButton")
        self.reset_btn.setText("Reset")
        self.reset_btn.setToolTip("Reset tracker parameters")
        self.reset_btn.clicked.connect(self.tracker.resetParameters)
        self.reset_btn.clicked.connect(self.refreshValues)

        self.button_layout = QHBoxLayout()
        self.button_layout.setObjectName("buttonLayout")
        self.button_layout.setSpacing(7)
        self.button_layout.setContentsMargins(0,0,0,0)

        self.track_all_btn = QPushButton()
        self.track_all_btn.setObjectName("trackAllButton")
        self.track_all_btn.setText("Track all")
        self.track_all_btn.setToolTip("Start a process that detects fish and tracks them in all the frames")
        self.track_all_btn.clicked.connect(self.trackAll)

        self.button_layout.addWidget(self.track_all_btn)
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.save_btn)
        self.button_layout.addWidget(self.load_btn)
        self.button_layout.addWidget(self.reset_btn)

        self.vertical_layout.addLayout(self.button_layout)

        self.setLayout(self.vertical_layout)

    def saveJSON(self):
        dict = self.tracker.getParameterDict()
        if dict is None:
            return

        try:
            with open(PARAMETERS_PATH, "w") as f:
                json.dump(dict, f, indent=3)
        except FileNotFoundError as e:
            print(e)

    def loadJSON(self):
        try:
            with open(PARAMETERS_PATH, "r") as f:
                dict = json.load(f)
        except FileNotFoundError as e:
            print("Error: Tracker parameters file not found:", e)
            return
        except json.JSONDecodeError as e:
            print("Error: Invalid tracker parameters file:", e)
            return


        params = self.tracker.parameters
        for key, value in dict.items():
            if not hasattr(params, key):
                print("Error: Invalid parameters: {}: {}".format(key, value))
                continue

            if not key in PARAMETER_TYPES:
                print("Error: Key [{}] not in PARAMETER_TYPES".format(key, value))
                continue

            try:
                setattr(params, key, PARAMETER_TYPES[key](value))
            except ValueError as e:
                print("Error: Invalid value in tracker parameters file,", e)

        self.refreshValues()

    def refreshValues(self):
        params = self.tracker.parameters

        self.max_age_slider.setValue(params.max_age)
        self.min_hits_slider.setValue(params.min_hits)
        self.search_radius_slider.setValue(params.search_radius)

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
