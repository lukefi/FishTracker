from PyQt5 import QtCore, QtGui, QtWidgets
from image_manipulation import ImageProcessor

class ParameterList(QtWidgets.QDialog):
    def __init__(self, sonar_processor, fish_manager):
        super().__init__()
        self.fish_manager = fish_manager
        self.sonar_processor = sonar_processor

        self.image_controls_label = QtWidgets.QLabel(self)
        self.image_controls_label.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.image_controls_label.setText("Image options")

        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.setSpacing(5)
        self.verticalLayout.setContentsMargins(7,7,7,7)

        #self.verticalLayout.addWidget(self.contrast_label)

        #self.contrast_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        #self.contrast_slider.setMinimum(0)
        #self.contrast_slider.setMaximum(100)
        #self.contrast_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        #self.contrast_slider.setTickInterval(5)
        #self.contrast_slider.setValue(50)
        ##self.contrast_slider.valueChanged.connect(self.F_BGS_SliderValueChanged)

        #self.contrast_value = QtWidgets.QLabel(self)
        #self.contrast_value.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        #self.contrast_value.setText("50")

        self.contrast_tick = QtWidgets.QCheckBox("Automatic contrast")
        self.contrast_tick.setChecked(False)
        self.contrast_tick.stateChanged.connect(self.sonar_processor.setAutomaticContrast)

        self.verticalLayout.addWidget(self.image_controls_label)
        self.verticalLayout.addWidget(self.contrast_tick)
        self.verticalLayout.addStretch()
        self.setLayout(self.verticalLayout)

if __name__ == "__main__":
    import sys
    from playback_manager import PlaybackManager
    from fish_manager import FishManager

    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    #playback_manager = PlaybackManager(app, main_window)
    #playback_manager.openTestFile()
    fish_manager = FishManager()
    fish_manager.testPopulate()
    #info_w = InfoWidget(playback_manager, fish_manager)
    sonar_processor = ImageProcessor()
    parameter_list = ParameterList(sonar_processor, fish_manager)
    main_window.setCentralWidget(parameter_list)
    main_window.show()
    sys.exit(app.exec_())