import sys, os, cv2
from PyQt5 import QtGui, QtCore, QtWidgets

from main import MainWindow
from sonar_widget import SonarViewer
from echogram_widget import EchogramViewer
from fish_manager import FishManager
from fish_list import FishList
from parameter_list import ParameterList
from playback_manager import PlaybackManager
from sonar_view2 import Ui_MainWindow

class UIManager():
    def __init__(self, main_window, playback_manager, fish_manager):
        self.widgets_initialized = False
        self.main_window = main_window

        self.playback = playback_manager
        self.fish_manager = fish_manager
        self.fish_manager.testPopulate(7000)
        #self.playback.frame_available.append(self.showSonarFrame)

        self.ui = Ui_MainWindow()
        self.ui.setupUi(main_window)
        self.main_window.setupStatusBar()
        self.setUpFunctions()

        self.main_window.show()
        self.setupWidgets()


    def openFile(self):
        self.playback.openFile()

    def openTestFile(self):
        self.playback.openTestFile()

    def closeFile(self):
        self.main_window.FStatusBarMousePos.setText("")
        self.playback.closeFile()

    def setupWidgets(self):
        _translate = QtCore.QCoreApplication.translate

        echo = EchogramViewer(self.playback)
        self.ui.splitter_2.replaceWidget(0, echo)
        self.ui.echogram_widget = echo
        echo.setMaximumHeight(200)

        sonar = SonarViewer(self.main_window, self.playback)
        self.ui.splitter.replaceWidget(0, sonar)
        self.ui.sonar_widget = sonar

        self.fish_manager
        self.fish_list = FishList(self.fish_manager, self.playback)
        self.parameter_list = ParameterList(self.playback, sonar.image_processor, self.fish_manager)

        self.ui.info_widget.removeTab(0)
        self.ui.info_widget.addTab(self.fish_list, "")
        self.ui.info_widget.setTabText(self.ui.info_widget.indexOf(self.fish_list), _translate("MainWindow", "Fish List"))
        self.ui.info_widget.addTab(self.parameter_list, "")
        self.ui.info_widget.setTabText(self.ui.info_widget.indexOf(self.parameter_list), _translate("MainWindow", "Parameter List"))

    def setUpFunctions(self):
        self.ui.action_Open.setShortcut('Ctrl+O')
        self.ui.action_Open.triggered.connect(self.openFile)

        self.ui.action_OpenTest = QtWidgets.QAction(self.main_window)
        self.ui.action_OpenTest.setObjectName("action_OpenTest")
        self.ui.menu_File.addAction(self.ui.action_OpenTest)
        self.ui.action_OpenTest.setShortcut('Ctrl+T')
        self.ui.action_OpenTest.triggered.connect(self.openTestFile)
        self.ui.action_OpenTest.setText(QtCore.QCoreApplication.translate("MainWindow", "&Open test file"))

        self.ui.action_close_file = QtWidgets.QAction(self.main_window)
        self.ui.action_close_file.setObjectName("action_close_file")
        self.ui.menu_File.addAction(self.ui.action_close_file)
        self.ui.action_close_file.setShortcut('Ctrl+Q')
        self.ui.action_close_file.triggered.connect(self.closeFile)
        self.ui.action_close_file.setText(QtCore.QCoreApplication.translate("MainWindow", "&Close file"))

    def showSonarFrame(self, image):
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        image = QtGui.QImage(image.data, image.shape[1], image.shape[0], QtGui.QImage.Format_RGB888).rgbSwapped()
        self.ui.sonar_frame.setPixmap(QtGui.QPixmap.fromImage(image))

        #figurePixmap = QtGui.QPixmap.fromImage(image)
        #self.ui.sonar_frame.setPixmap(figurePixmap.scaled(ffigure.size(), pyqtCore.Qt.KeepAspectRatio))
        #ffigure.setAlignment(pyqtCore.Qt.AlignCenter)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow() #QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    fish_manager = FishManager()
    ui_manager = UIManager(main_window, playback_manager, fish_manager)
    sys.exit(app.exec_())