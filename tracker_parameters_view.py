from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from tracker import Tracker, TrackingState
from tracker_parameters import TrackerParameters
from filter_parameters import FilterParameters
from detector_parameters_view import LabeledSlider
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
        self.detector.state_changed_signal.connect(self.setButtonsEnabled)
        self.tracker.state_changed_signal.connect(self.setButtonsEnabled)
        self.tracker.state_changed_signal.connect(self.setButtonTexts)
        self.tracker.parameters_changed_signal.connect(self.refreshValues)
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

            min_dets = self.tracker.filter_parameters.getParameter(FilterParameters.ParametersEnum.min_duration)
            mad_limit = self.tracker.filter_parameters.getParameter(FilterParameters.ParametersEnum.mad_limit)

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

        def setParameterSliderP(label, min_value, max_value, parameter_enum):
            value = self.tracker.parameters.getParameter(parameter_enum)
            lambda_param = lambda x: self.tracker.setPrimaryParameter(parameter_enum, x)
            return LabeledSlider(label, self.form_layout_p, [lambda_param], value, min_value, max_value, self)

        self.max_age_slider_p = setParameterSliderP("Max age", 1, 100, TrackerParameters.ParametersEnum.max_age)
        self.min_hits_slider_p = setParameterSliderP("Min hits", 1, 10, TrackerParameters.ParametersEnum.min_hits)
        self.search_radius_slider_p = setParameterSliderP("Search radius", 1, 100, TrackerParameters.ParametersEnum.search_radius)

        self.vertical_spacer1 = QSpacerItem(0, 5, QSizePolicy.Minimum, QSizePolicy.Maximum)
        self.form_layout_p.addItem(self.vertical_spacer1)

        trim_tails_value_p = self.tracker.parameters.getParameter(TrackerParameters.ParametersEnum.trim_tails)
        self.trim_tails_checkbox_p = QCheckBox("", self)
        self.trim_tails_checkbox_p.setChecked(trim_tails_value_p)
        lambda_trim_tails_p = lambda x: self.tracker.setPrimaryParameter(TrackerParameters.ParametersEnum.trim_tails, x)
        self.trim_tails_checkbox_p.stateChanged.connect(lambda_trim_tails_p)
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
        filter_data = self.tracker.filter_parameters.data

        def setParameterSliderF(label, min_value, max_value, parameter_enum):
            value = self.tracker.filter_parameters.getParameter(parameter_enum)
            lambda_param = lambda x: self.tracker.setFilterParameter(parameter_enum, x)
            return LabeledSlider(label, self.form_layout_f, [lambda_param], value, min_value, max_value, self)

        self.min_detections_slider = setParameterSliderF("Min duration", 1, 50, FilterParameters.ParametersEnum.min_duration)
        self.mad_slider = setParameterSliderF("MAD", 0, 50, FilterParameters.ParametersEnum.mad_limit)

        self.collapsible_f.setContentLayout(self.form_layout_f)
        self.vertical_layout.addWidget(self.collapsible_f)

        # Parameters for secondary tracking
        self.form_layout_s = QFormLayout()

        def setParameterSliderS(label, min_value, max_value, parameter_enum):
            value = self.tracker.secondary_parameters.getParameter(parameter_enum)
            lambda_param = lambda x: self.tracker.setSecondaryParameter(parameter_enum, x)
            return LabeledSlider(label, self.form_layout_s, [lambda_param], value, min_value, max_value, self)

        self.max_age_slider_s = setParameterSliderS("Max age", 1, 100, TrackerParameters.ParametersEnum.max_age)
        self.min_hits_slider_s = setParameterSliderS("Min hits", 1, 10, TrackerParameters.ParametersEnum.min_hits)
        self.search_radius_slider_s = setParameterSliderS("Search radius", 1, 100, TrackerParameters.ParametersEnum.search_radius)

        self.vertical_spacer3 = QSpacerItem(0, 5, QSizePolicy.Minimum, QSizePolicy.Maximum)
        self.form_layout_s.addItem(self.vertical_spacer3)

        trim_tails_value_s = self.tracker.secondary_parameters.getParameter(TrackerParameters.ParametersEnum.trim_tails)
        self.trim_tails_checkbox_s = QCheckBox("", self)
        self.trim_tails_checkbox_s.setChecked(trim_tails_value_s)
        lambda_trim_tails_s = lambda x: self.tracker.setSecondaryParameter(TrackerParameters.ParametersEnum.trim_tails, x)
        self.trim_tails_checkbox_s.stateChanged.connect(lambda_trim_tails_s)
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
        dict = self.tracker.getAllParameters().getParameterDict()

        try:
            with open(PARAMETERS_PATH, "w") as f:
                json.dump(dict, f, indent=3)
        except FileNotFoundError as e:
            LogObject().print(e)

    def loadJSON(self):
        try:
            with open(PARAMETERS_PATH, "r") as f:
                dict = json.load(f)
        except FileNotFoundError as e:
            LogObject().print("Error: Tracker parameters file not found:", e)
            return
        except json.JSONDecodeError as e:
            LogObject().print("Error: Invalid tracker parameters file:", e)
            return

        all_params = self.tracker.getAllParameters()
        try:
            all_params.setParameterDict(dict)
            self.tracker.setAllParameters(all_params)
            self.refreshValues()
        except TypeError as e:
            LogObject().print2(e)

    def refreshValues(self):
        primary_data = self.tracker.parameters.data
        filter_data =self.tracker.filter_parameters.data
        secondary_data = self.tracker.secondary_parameters.data

        self.max_age_slider_p.setValue(primary_data.max_age)
        self.min_hits_slider_p.setValue(primary_data.min_hits)
        self.search_radius_slider_p.setValue(primary_data.search_radius)
        self.trim_tails_checkbox_p.setChecked(primary_data.trim_tails)

        self.min_detections_slider.setValue(filter_data.min_duration)
        self.mad_slider.setValue(filter_data.mad_limit)

        self.max_age_slider_s.setValue(secondary_data.max_age)
        self.min_hits_slider_s.setValue(secondary_data.min_hits)
        self.search_radius_slider_s.setValue(secondary_data.search_radius)
        self.trim_tails_checkbox_s.setChecked(secondary_data.trim_tails)

    def printValues(self):
        primary_data = self.tracker.parameters.data
        filter_data =self.tracker.filter_parameters.data
        secondary_data = self.tracker.secondary_parameters.data

        print(f"P Max Age: {primary_data.max_age}")
        print(f"P Min Hits: {primary_data.min_hits}")
        print(f"P Search Radius: {primary_data.search_radius}")
        print(f"P Trim tails: {primary_data.trim_tails}\n")

        print(f"F Min Duration: {filter_data.min_duration}")
        print(f"F MAD Limit: {filter_data.mad_limit}\n")

        print(f"S Max Age: {secondary_data.max_age}")
        print(f"S Min Hits: {secondary_data.min_hits}")
        print(f"S Search Radius: {secondary_data.search_radius}")
        print(f"S Trim tails: {secondary_data.trim_tails}\n")

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
