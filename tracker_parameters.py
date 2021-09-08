from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from tracker import Tracker, TrackingState
from detector_parameters import LabeledSlider
from collapsible_box import CollapsibleBox
from log_object import LogObject

import json
import os.path
import numpy as np

PARAMETERS_PATH = "tracker_parameters.json"

class TrackerParametersView(QScrollArea):
    def __init__(self, playback_manager, tracker, detector, fish_manager=None, debug=False):
        super().__init__()
        self.playback_manager = playback_manager
        self.tracker = tracker
        self.detector = detector
        self.fish_manager = fish_manager

        self.initUI(debug)

        self.playback_manager.polars_loaded.connect(self.setButtonsEnabled)
        self.detector.state_changed_event.append(self.setButtonsEnabled)
        self.tracker.state_changed_signal.connect(self.setButtonsEnabled)
        self.tracker.state_changed_signal.connect(self.setButtonTexts)
        self.setButtonsEnabled()

    def setButtonsEnabled(self):
        detector_active = self.detector.bg_subtractor.initializing or self.detector.computing
        #all_value = self.tracker.parametersDirty() and self.playback_manager.isPolarsDone()
        self.primary_track_btn.setEnabled(self.playback_manager.isPolarsDone() and
                                          (self.tracker.tracking_state != TrackingState.SECONDARY))
        self.secondary_track_btn.setEnabled(self.playback_manager.isPolarsDone() and
                                            (self.tracker.tracking_state != TrackingState.PRIMARY))

    def setButtonTexts(self):
        if self.tracker.tracking_state == TrackingState.PRIMARY:
            self.primary_track_btn.setText("Cancel")
        else:
            self.primary_track_btn.setText("Primary Track")

        if self.tracker.tracking_state == TrackingState.SECONDARY:
            self.secondary_track_btn.setText("Cancel")
        else:
            self.secondary_track_btn.setText("Secondary Track")

    def primaryTrack(self):
        """
        Either starts the first tracking iteration, or cancels the process
        if one is already started.
        """

        if self.tracker.tracking_state == TrackingState.IDLE:
            if self.fish_manager:
                self.fish_manager.clear_old_data = True
            self.playback_manager.runInThread(self.tracker.primaryTrack)
        else:
            if self.detector.bg_subtractor.initializing:
                self.detector.bg_subtractor.stop_initializing = True
            elif self.detector.computing:
                self.detector.stop_computing = True
            else:
                self.tracker.stop_tracking = True

    def secondaryTrack(self):
        """
        Either starts the second (or any subsequent) tracking iteration, or cancels the process
        if one is already started. A FishManager is required for this action.
        """

        if self.fish_manager is None:
            return

        if self.tracker.tracking_state == TrackingState.IDLE:
            self.fish_manager.clear_old_data = False

            min_dets = self.tracker.filter_parameters.min_duration
            mad_limit = self.tracker.filter_parameters.mad_limit

            LogObject().print1(f"Filter Parameters: {min_dets} {mad_limit}")
            used_dets = self.fish_manager.applyFiltersAndGetUsedDetections(min_dets, mad_limit)
            self.playback_manager.runInThread(lambda: self.tracker.secondaryTrack(used_dets, self.tracker.secondary_parameters))

        else:
            if self.detector.bg_subtractor.initializing:
                self.detector.bg_subtractor.stop_initializing = True
            elif self.detector.computing:
                self.detector.stop_computing = True
            else:
                self.tracker.stop_tracking = True

    def initUI(self, debug_btn):
        content = QWidget()
        self.setWidget(content)
        self.setWidgetResizable(True)

        self.vertical_layout = QVBoxLayout()
        self.vertical_layout.setObjectName("verticalLayout")
        self.vertical_layout.setSpacing(5)
        self.vertical_layout.setContentsMargins(7,7,7,7)

        self.main_label = QLabel(self)
        self.main_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.main_label.setText("Tracker options")
        self.vertical_layout.addWidget(self.main_label)

        # Parameters for primary tracking
        self.form_layout_p = QFormLayout()
        self.max_age_slider_p = LabeledSlider("Max age", self.form_layout_p, [self.tracker.parameters.setMaxAge],
                                              self.tracker.parameters.max_age, 1, 100, self)
        self.min_hits_slider_p = LabeledSlider("Min hits", self.form_layout_p, [self.tracker.parameters.setMinHits],
                                               self.tracker.parameters.min_hits, 1, 10, self)
        self.search_radius_slider_p = LabeledSlider("Search radius", self.form_layout_p, [self.tracker.parameters.setSearchRadius],
                                                    self.tracker.parameters.search_radius, 1, 100, self)

        self.vertical_spacer1 = QSpacerItem(0, 5, QSizePolicy.Minimum, QSizePolicy.Maximum)
        self.form_layout_p.addItem(self.vertical_spacer1)

        self.trim_tails_checkbox_p = QCheckBox("", self)
        self.trim_tails_checkbox_p.stateChanged.connect(self.tracker.parameters.setTrimTails)
        self.form_layout_p.addRow("Trim tails", self.trim_tails_checkbox_p)

        self.collapsible_p = CollapsibleBox("Primary tracking", self)
        self.collapsible_p.setContentLayout(self.form_layout_p)
        self.vertical_layout.addWidget(self.collapsible_p)

        self.vertical_spacer2 = QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Maximum)
        self.vertical_layout.addItem(self.vertical_spacer2)

        self.primary_track_btn = QPushButton()
        self.primary_track_btn.setObjectName("primaryTrackButton")
        self.primary_track_btn.setText("Primary Track")
        self.primary_track_btn.setToolTip("Start a process that detects fish and tracks them in all the frames")
        self.primary_track_btn.clicked.connect(self.primaryTrack)
        self.primary_track_btn.setMinimumWidth(150)

        self.track_button_layout_p = QHBoxLayout()
        self.track_button_layout_p.setObjectName("buttonLayout")
        self.track_button_layout_p.setSpacing(7)
        self.track_button_layout_p.setContentsMargins(0,0,0,0)

        self.track_button_layout_p.addStretch()
        self.track_button_layout_p.addWidget(self.primary_track_btn)
        self.vertical_layout.addLayout(self.track_button_layout_p)

        # Parameters for filtering
        self.form_layout_f = QFormLayout()
        self.collapsible_f = CollapsibleBox("Filtering", self)

        self.min_detections_slider = LabeledSlider("Min duration", self.form_layout_f, [self.tracker.filter_parameters.setMinDuration],
                                                   self.tracker.filter_parameters.min_duration, 1, 50, self)
        self.mad_slider = LabeledSlider("MAD", self.form_layout_f, [self.tracker.filter_parameters.setMADLimit],
                                        self.tracker.filter_parameters.mad_limit, 0, 50, self)

        #if self.fish_manager is not None:
        #    self.min_detections_slider = LabeledSlider("Min duration", self.form_layout_f, [self.tracker.filter_parameters.setMinDuration],
        #                                               self.tracker.filter_parameters.min_duration, 1, 50, self)
        #    self.mad_slider = LabeledSlider("MAD", self.form_layout_f, [self.tracker.filter_parameters.setMADLimit],
        #                                    self.tracker.filter_parameters.mad_limit, 0, 50, self)
        #else:
        #    self.min_detections_slider = LabeledSlider("Min duration", self.form_layout_f, [], 1, 1, 50, self)
        #    self.mad_slider = LabeledSlider("MAD", self.form_layout_f, [], 0, 0, 50, self)

        self.collapsible_f.setContentLayout(self.form_layout_f)
        self.vertical_layout.addWidget(self.collapsible_f)

        # Parameters for secondary tracking
        self.form_layout_s = QFormLayout()
        self.max_age_slider_s = LabeledSlider("Max age", self.form_layout_s, [self.tracker.secondary_parameters.setMaxAge],
                                              self.tracker.secondary_parameters.max_age, 1, 100, self)
        self.min_hits_slider_s = LabeledSlider("Min hits", self.form_layout_s, [self.tracker.secondary_parameters.setMinHits],
                                               self.tracker.secondary_parameters.min_hits, 1, 10, self)
        self.search_radius_slider_s = LabeledSlider("Search radius", self.form_layout_s, [self.tracker.secondary_parameters.setSearchRadius],
                                                    self.tracker.secondary_parameters.search_radius, 1, 100, self)

        self.vertical_spacer3 = QSpacerItem(0, 5, QSizePolicy.Minimum, QSizePolicy.Maximum)
        self.form_layout_s.addItem(self.vertical_spacer3)

        self.trim_tails_checkbox_s = QCheckBox("", self)
        self.trim_tails_checkbox_s.stateChanged.connect(self.tracker.secondary_parameters.setTrimTails)
        self.form_layout_s.addRow("Trim tails", self.trim_tails_checkbox_s)

        self.collapsible_s = CollapsibleBox("Secondary tracking", self)
        self.collapsible_s.setContentLayout(self.form_layout_s)
        self.vertical_layout.addWidget(self.collapsible_s)

        self.vertical_spacer4 = QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Maximum)
        self.vertical_layout.addItem(self.vertical_spacer4)

        self.secondary_track_btn = QPushButton()
        self.secondary_track_btn.setObjectName("secondaryTrackButton")
        self.secondary_track_btn.setText("Secondary Track")
        self.secondary_track_btn.setToolTip("Start a process that detects fish and tracks them in all the frames")
        self.secondary_track_btn.clicked.connect(self.secondaryTrack)
        self.secondary_track_btn.setMinimumWidth(150)

        self.track_button_layout_s = QHBoxLayout()
        self.track_button_layout_s.setObjectName("buttonLayout")
        self.track_button_layout_s.setSpacing(7)
        self.track_button_layout_s.setContentsMargins(0,0,0,0)

        self.track_button_layout_s.addStretch()
        self.track_button_layout_s.addWidget(self.secondary_track_btn)
        self.vertical_layout.addLayout(self.track_button_layout_s)

        self.vertical_layout.addStretch()

        # Parameter file management
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

        if debug_btn:
            self.debug_btn = QPushButton()
            self.debug_btn.setObjectName("debugButton")
            self.debug_btn.setText("Print values")
            self.debug_btn.setToolTip("Debug: Print values of parameters")
            self.debug_btn.clicked.connect(self.printValues)

        self.button_layout = QHBoxLayout()
        self.button_layout.setObjectName("buttonLayout")
        self.button_layout.setSpacing(7)
        self.button_layout.setContentsMargins(0,0,0,0)

        self.button_layout.addWidget(self.save_btn)
        self.button_layout.addWidget(self.load_btn)
        self.button_layout.addWidget(self.reset_btn)
        if debug_btn:
            self.button_layout.addWidget(self.debug_btn)
        self.button_layout.addStretch()

        self.vertical_layout.addLayout(self.button_layout)

        content.setLayout(self.vertical_layout)
        self.refreshValues()

    def saveJSON(self):
        p_dict = self.tracker.parameters.getParameterDict()
        f_dict = self.tracker.filter_parameters.getParameterDict()
        s_dict = self.tracker.secondary_parameters.getParameterDict()

        dict = {
            "primary_tracking": p_dict,
            "filtering": f_dict,
            "secondary_tracking": s_dict
            }

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

        if "primary_tracking" in dict:
            self.tracker.parameters.setParameterDict(dict["primary_tracking"])
        if "filtering" in dict:
            self.tracker.filter_parameters.setParameterDict(dict["filtering"])
        if "secondary_tracking" in dict:
            self.tracker.secondary_parameters.setParameterDict(dict["secondary_tracking"])

        self.refreshValues()

    def refreshValues(self):
        params = self.tracker.parameters
        f_params = self.tracker.filter_parameters
        s_params = self.tracker.secondary_parameters

        self.max_age_slider_p.setValue(params.max_age)
        self.min_hits_slider_p.setValue(params.min_hits)
        self.search_radius_slider_p.setValue(params.search_radius)
        self.trim_tails_checkbox_p.setChecked(params.trim_tails)

        self.min_detections_slider.setValue(f_params.min_duration)
        self.mad_slider.setValue(f_params.mad_limit)

        self.max_age_slider_s.setValue(s_params.max_age)
        self.min_hits_slider_s.setValue(s_params.min_hits)
        self.search_radius_slider_s.setValue(s_params.search_radius)
        self.trim_tails_checkbox_s.setChecked(s_params.trim_tails)

    def printValues(self):
        params = self.tracker.parameters
        f_params = self.tracker.filter_parameters
        s_params = self.tracker.secondary_parameters

        print(f"P Max Age: {params.max_age}")
        print(f"P Min Hits: {params.min_hits}")
        print(f"P Search Radius: {params.search_radius}")
        print(f"P Trim tails: {params.trim_tails}\n")

        print(f"F Min Duration: {f_params.min_duration}")
        print(f"F MAD Limit: {f_params.mad_limit}\n")

        print(f"S Max Age: {s_params.max_age}")
        print(f"S Min Hits: {s_params.min_hits}")
        print(f"S Search Radius: {s_params.search_radius}")
        print(f"S Trim tails: {s_params.trim_tails}\n")

if __name__ == "__main__":
    import sys
    from playback_manager import PlaybackManager
    from detector import Detector
    
    app = QApplication(sys.argv)
    main_window = QMainWindow()
    playback_manager = PlaybackManager(app, main_window)

    detector = Detector(playback_manager)

    tracker = Tracker(detector)
    tracker_params = TrackerParametersView(playback_manager, tracker, detector, fish_manager=None, debug=True)

    main_window.setCentralWidget(tracker_params)
    main_window.show()
    sys.exit(app.exec_())
