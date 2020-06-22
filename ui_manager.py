import sys, os, cv2
from PyQt5 import QtGui, QtCore, QtWidgets
from sonar_widget import SonarViewer
from playback_manager import PlaybackManager
from sonar_view2 import Ui_MainWindow

class UIManager():
    def __init__(self, main_window, playback_manager):
        self.main_window = main_window

        self.playback = playback_manager
        #self.playback.frame_available.append(self.showSonarFrame)

        self.ui = Ui_MainWindow()
        self.ui.setupUi(main_window)
        self.setUpFunctions()


    def openFile(self):
        self.playback.openFile()
        self.setupWidgets()

    def openTestFile(self):
        self.playback.openTestFile()
        self.setupWidgets()

    def setupWidgets(self):
        sonar = SonarViewer(self.playback)
        self.ui.splitter.replaceWidget(0, sonar)
        self.ui.sonar_widget = sonar

    def setUpFunctions(self):
        self.ui.action_Open.setShortcut('Ctrl+O')
        self.ui.action_Open.triggered.connect(self.openFile)

        self.ui.action_OpenTest = QtWidgets.QAction(self.main_window)
        self.ui.action_OpenTest.setObjectName("action_OpenTest")
        self.ui.menu_File.addAction(self.ui.action_OpenTest)
        self.ui.action_OpenTest.setShortcut('Ctrl+T')
        self.ui.action_OpenTest.triggered.connect(self.openTestFile)
        self.ui.action_OpenTest.setText(QtCore.QCoreApplication.translate("MainWindow", "&Open test file"))

    def showSonarFrame(self, image):
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        image = QtGui.QImage(image.data, image.shape[1], image.shape[0], QtGui.QImage.Format_RGB888).rgbSwapped()
        self.ui.sonar_frame.setPixmap(QtGui.QPixmap.fromImage(image))

        #figurePixmap = QtGui.QPixmap.fromImage(image)
        #self.ui.sonar_frame.setPixmap(figurePixmap.scaled(ffigure.size(), pyqtCore.Qt.KeepAspectRatio))
        #ffigure.setAlignment(pyqtCore.Qt.AlignCenter)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    ui_manager = UIManager(main_window, playback_manager)
    main_window.show()
    sys.exit(app.exec_())