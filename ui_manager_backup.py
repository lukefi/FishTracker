import sys
import cv2
from sonar_view import Ui_MainWindow
from playback_manager import PlaybackManager
from PyQt5 import QtGui, QtCore, QtWidgets

class UIManager():
    def __init__(self, main_window, playback_manager):
        self.main_window = main_window
        self.ui = Ui_MainWindow()
        self.playback = playback_manager
        self.playback.frame_available.append(self.showSonarFrame)
        self.ui.setupUi(main_window)
        self.setUpFunctions()

    def setUpFunctions(self):
        self.ui.action_Open.setShortcut('Ctrl+O')
        self.ui.action_Open.triggered.connect(self.playback.open_file)

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
    playback_manager = PlaybackManager()
    ui_manager = UIManager(main_window, playback_manager)
    main_window.show()
    sys.exit(app.exec_())