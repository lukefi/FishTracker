from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from detector import Detector
import json
import os.path

PARAMETERS_PATH = "detector_parameters.json"
PARAMETER_TYPES = {
            "detection_size": int,
	        "mog_var_thresh": int,
	        "min_fg_pixels": int,
	        "median_size": int,
	        "nof_bg_frames": int,
	        "learning_rate": float,
	        "dbscan_eps": int,
	        "dbscan_min_samples": int
        }

class LabeledSlider:
    def __init__(self, label, form_layout, connected_functions=[], default_value=0, min_value=0, max_value=1, parent=None, mapping=None, reverse_mapping=None, formatting = "{}"):
        self.mapping = mapping
        self.reverse_mapping = reverse_mapping
        self.formatting = formatting

        self.layout = QHBoxLayout()
        self.layout.setObjectName("layout")
        self.layout.setSpacing(5)
        self.layout.setContentsMargins(0,0,0,0)

        self.value = QLabel("1.0", parent)
        self.value.setAlignment(Qt.AlignCenter | Qt.AlignTop)
        self.value.setMinimumWidth(50)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(min_value)
        self.slider.setMaximum(max_value)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(1)
        self.slider.setValue(default_value)

        self.connected_functions = connected_functions
        self.slider.valueChanged.connect(self.valueChanged)
        self.value.setText(self.formatting.format(self.mapping(self.slider.value())))
                     
        self.layout.addWidget(self.slider)
        self.layout.addWidget(self.value)

        form_layout.addRow(label, self.layout)

    def setValue(self, value):
        self.slider.blockSignals(True)

        self.value.setText(self.formatting.format(value))
        if self.reverse_mapping:
            self.slider.setValue(self.reverse_mapping(value))
        else:
            self.slider.setValue(value)

        self.slider.blockSignals(False)

    def valueChanged(self, value):
        if self.mapping:
            applied_value = self.mapping(value)
        else:
            applied_value = value

        self.value.setText(self.formatting.format(applied_value))

        for f in self.connected_functions:
                f(applied_value)

class DetectorParameters(QWidget):
    def __init__(self, playback_manager, detector, sonar_processor):
        super().__init__()
        self.playback_manager = playback_manager
        self.detector = detector
        self.sonar_processor = sonar_processor

        self.image_controls_label = QLabel(self)
        self.image_controls_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.image_controls_label.setText("Detector options")

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.setSpacing(5)
        self.verticalLayout.setContentsMargins(7,7,7,7)

        self.verticalLayout.addWidget(self.image_controls_label)

        self.form_layout = QFormLayout()

        def addLine(label, initial_value, validator, connected, layout):
            line = QLineEdit()
            line.setAlignment(Qt.AlignRight)
            line.setValidator(validator)
            line.setText(str(initial_value))
            for f in connected:
                line.textChanged.connect(f)
            layout.addRow(label, line)
            return line

        refresh_lambda = lambda x: playback_manager.refreshFrame()

        self.detection_size_line = addLine("Detection size", 10, QIntValidator(0, 20), [detector.setDetectionSize, refresh_lambda], self.form_layout)
        self.min_fg_pixels_line  = addLine("Min foreground pixels", 25, QIntValidator(0, 50), [detector.setMinFGPixels, refresh_lambda], self.form_layout)
        self.median_size_slider = LabeledSlider("Median size", self.form_layout, [detector.setMedianSize, refresh_lambda], 0, 0, 3, self, lambda x: 2*x + 3, lambda x: (x - 3)/2)
        self.dbscan_eps_line = addLine("Clustering epsilon", 10, QIntValidator(0, 20), [detector.setDBScanEps, refresh_lambda], self.form_layout)
        self.dbscan_min_samples_line = addLine("Clustering min samples", 10, QIntValidator(0, 20), [detector.setDBScanMinSamples, refresh_lambda], self.form_layout)

        self.verticalLayout.addLayout(self.form_layout)

        self.verticalSpacer = QSpacerItem(0, 40, QSizePolicy.Minimum, QSizePolicy.Maximum)
        self.verticalLayout.addItem(self.verticalSpacer)

        self.init_label = QLabel(self)
        self.init_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.init_label.setText("Initialization")
        self.verticalLayout.addWidget(self.init_label)

        self.form_layout2 = QFormLayout()

        self.mog_var_threshold_line = addLine("MOG var threshold", 11, QIntValidator(0, 20), [detector.setMOGVarThresh], self.form_layout2)
        self.nof_bg_frames_line = addLine("Number of bg frames", 10, QIntValidator(10, 10000), [detector.setNofBGFrames], self.form_layout2)
        self.learning_rate_line = addLine("Learning rate", 0.01, QDoubleValidator(0.001, 0.1, 3), [detector.setLearningRate], self.form_layout2)

        self.verticalLayout.addLayout(self.form_layout2)

        #self.detection_size = LabeledSlider(self.verticalLayout, [self.playback_manager.refreshFrame], "Detection size", 10, 0, 20, self)
        #self.mog_var_thresh = LabeledSlider(self.verticalLayout, [self.playback_manager.refreshFrame], "MOG var threshold", 11, 0, 20, self)
        #self.min_fg_pixels = LabeledSlider(self.verticalLayout, [self.playback_manager.refreshFrame], "Min foreground pixels", 25, 0, 50, self)
        #self.nof_bg_frames = LabeledSlider(self.verticalLayout, [self.playback_manager.refreshFrame], "Number of bg frames", 10, 5, 20, self, lambda x: 100*x)
        #self.learning_rate = LabeledSlider(self.verticalLayout, [self.playback_manager.refreshFrame], "Learning rate", -20, -30, -10, self, lambda x: 10**(x/10), "{:.3f}")

        self.verticalLayout.addStretch()

        self.save_btn = QPushButton()
        self.save_btn.setObjectName("saveButton")
        self.save_btn.setText("Save")
        self.save_btn.clicked.connect(self.saveJSON)

        self.load_btn = QPushButton()
        self.load_btn.setObjectName("loadButton")
        self.load_btn.setText("Load")
        self.load_btn.clicked.connect(self.loadJSON)

        self.reset_btn = QPushButton()
        self.reset_btn.setObjectName("resetButton")
        self.reset_btn.setText("Reset")
        self.reset_btn.clicked.connect(self.detector.resetParameters)
        self.reset_btn.clicked.connect(self.refreshValues)

        self.button_layout = QHBoxLayout()
        self.button_layout.setObjectName("buttonLayout")
        self.button_layout.setSpacing(7)
        self.button_layout.setContentsMargins(0,0,0,0)

        self.button_layout.addWidget(self.save_btn)
        self.button_layout.addWidget(self.load_btn)
        self.button_layout.addWidget(self.reset_btn)
        self.button_layout.addStretch()

        self.verticalLayout.addLayout(self.button_layout)

        self.recalculate_mog_btn = QPushButton()
        self.recalculate_mog_btn.setObjectName("recalculateMOGButton")
        self.recalculate_mog_btn.setText("Apply Values")
        self.recalculate_mog_btn.clicked.connect(self.recalculateMOG)

        self.calculate_all_btn = QPushButton()
        self.calculate_all_btn.setObjectName("calculateAllButton")
        self.calculate_all_btn.setText("Calculate All")
        self.calculate_all_btn.clicked.connect(self.calculateAll)

        self.second_button_layout = QHBoxLayout()
        self.second_button_layout.setObjectName("buttonLayout")
        self.second_button_layout.setSpacing(7)
        self.second_button_layout.setContentsMargins(0,0,0,0)

        self.second_button_layout.addWidget(self.recalculate_mog_btn)
        self.second_button_layout.addWidget(self.calculate_all_btn)

        self.verticalLayout.addLayout(self.second_button_layout)

        self.setLayout(self.verticalLayout)

        self.loadJSON()

        self.playback_manager.polars_loaded.append(self.setButtonsEnabled)
        self.detector.state_changed_event.append(self.setButtonsEnabled)
        self.detector.state_changed_event.append(self.setButtonTexts)
        self.setButtonsEnabled()

    def saveJSON(self):
        dict = {
            "detection_size": self.detector.detection_size,
	        "mog_var_thresh": self.detector.mog_var_thresh,
	        "min_fg_pixels": self.detector.min_fg_pixels,
	        "median_size": self.detector.median_size,
	        "nof_bg_frames": self.detector.nof_bg_frames,
	        "learning_rate": self.detector.learning_rate,
	        "dbscan_eps": self.detector.dbscan_eps,
	        "dbscan_min_samples": self.detector.dbscan_min_samples
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
            print("Error: Detector parameters file not found:", e)
        except json.JSONDecodeError as e:
            print("Error: Invalid detector parameters file:", e)

        for key, value in dict.items():
            if hasattr(self.detector, key) and key in PARAMETER_TYPES:
                try:
                    setattr(self.detector, key, PARAMETER_TYPES[key](value))

                except ValueError as e:
                    print("Error: Invalid value in detector parameters file,", e)

            else:
                print("Error: Invalid parameters: {}: {}".format(key, value))

        self.refreshValues()

    def refreshValues(self):
        self.detection_size_line.setText(str(self.detector.detection_size))
        self.mog_var_threshold_line.setText(str(self.detector.mog_var_thresh))
        self.min_fg_pixels_line.setText(str(self.detector.min_fg_pixels))
        self.median_size_slider.setValue(self.detector.median_size)
        self.nof_bg_frames_line.setText(str(self.detector.nof_bg_frames))
        self.learning_rate_line.setText(str(self.detector.learning_rate))
        self.dbscan_eps_line.setText(str(self.detector.dbscan_eps))
        self.dbscan_min_samples_line.setText(str(self.detector.dbscan_min_samples))

    def recalculateMOG(self):
        if not self.detector.initializing:
            self.playback_manager.runInThread(self.detector.initMOG)
        else:
            self.detector.stop_initializing = True

    def calculateAll(self):
        if not self.detector.computing:
            self.playback_manager.runInThread(self.detector.computeAll)
        else:
            self.detector.stop_computing = True

    def setButtonTexts(self):
        if self.detector.computing:
            self.calculate_all_btn.setText("Cancel")
        else:
            self.calculate_all_btn.setText("Calculate All")

        if self.detector.initializing:
            self.recalculate_mog_btn.setText("Cancel")
        else:
            self.recalculate_mog_btn.setText("Apply Values")

    def setButtonsEnabled(self):
        #print("MOG Btn:",self.playback_manager.isMappingDone(), self.detector.initializing)
        mog_value = self.playback_manager.isMappingDone() and self.detector.mog_dirty
        self.recalculate_mog_btn.setEnabled(mog_value)

        all_value = self.playback_manager.isPolarsDone() and not self.detector.initializing and (self.detector.detections_dirty or self.detector.mog_dirty)
        self.calculate_all_btn.setEnabled(all_value)

if __name__ == "__main__":
    import sys
    from playback_manager import PlaybackManager
    from image_manipulation import ImageProcessor

    app = QApplication(sys.argv)
    main_window = QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    #playback_manager.openTestFile()

    sonar_processor = ImageProcessor()

    detector = Detector(playback_manager)
    detector_parameters = DetectorParameters(playback_manager, detector, sonar_processor)

    main_window.setCentralWidget(detector_parameters)
    main_window.show()
    sys.exit(app.exec_())