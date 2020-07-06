from PyQt5 import QtCore, QtGui, QtWidgets
from image_manipulation import ImageProcessor

class ParameterList(QtWidgets.QDialog):
    def __init__(self, playback_manager, sonar_processor, fish_manager):
        super().__init__()
        self.playback_manager = playback_manager
        self.sonar_processor = sonar_processor
        self.fish_manager = fish_manager

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

        self.contrast_tick = QtWidgets.QCheckBox("Automatic contrast")
        self.contrast_tick.setChecked(False)
        self.contrast_tick.stateChanged.connect(self.sonar_processor.setAutomaticContrast)

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

        self.gamma_layout.addWidget(self.gamma_slider)
        self.gamma_layout.addWidget(self.gamma_value)

        self.colormap_tick = QtWidgets.QCheckBox("Use colormap")
        self.colormap_tick.setChecked(False)
        self.colormap_tick.stateChanged.connect(self.sonar_processor.setColorMap)

        self.verticalLayout.addWidget(self.image_controls_label)
        self.verticalLayout.addWidget(self.distance_tick)
        self.verticalLayout.addWidget(self.contrast_tick)
        self.verticalLayout.addWidget(self.gamma_label)
        self.verticalLayout.addLayout(self.gamma_layout)
        self.verticalLayout.addWidget(self.colormap_tick)
        self.verticalLayout.addStretch()
        self.setLayout(self.verticalLayout)

    def gammaSliderChanged(self, value):
        applied_value = float(value)/20
        self.sonar_processor.setGamma(applied_value)
        self.gamma_value.setText(str(applied_value))

if __name__ == "__main__":
    import sys
    from playback_manager import PlaybackManager
    from fish_manager import FishManager

    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    #playback_manager.openTestFile()
    fish_manager = FishManager()
    fish_manager.testPopulate(100)
    #info_w = InfoWidget(playback_manager, fish_manager)
    sonar_processor = ImageProcessor()
    parameter_list = ParameterList(playback_manager, sonar_processor, fish_manager)
    main_window.setCentralWidget(parameter_list)
    main_window.show()
    sys.exit(app.exec_())