from PyQt5 import QtGui, QtCore, QtWidgets
import sys, os, cv2

_MAIN_DIRECTORY = os.getcwd()
sys.path.append(os.path.join(_MAIN_DIRECTORY, "UI"))

import file_handler
import UI_utils
from iconsLauncher import *     # UI/iconsLauncher

from FWelcomeInfo import *      # UI/FWelcomeInfo
from FViewer import *           # UI/FViewer
import fileMainMenu             # UI/fileMainMenu
import editMainMenu             # UI/editMainMenu
import helpMainMenu             # UI/helpMainMenu

class FViewerWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(FViewerWidget, self).__init__(parent)
        self.viewer = FViewer.FViewer(self)
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.viewer)
        self.setLayout(self.layout)

class FTestContainer(QtWidgets.QMainWindow):

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self.initUI()
        return
        
        

    def initUI(self):
        self._MAIN_CONTAINER = self
        self._CONFIG = file_handler.loadJSON("config.json")
        self.setWindowIcon(QtGui.QIcon(FGetIcon(self._CONFIG["icon"], OS = sys.platform)))
        self.setWindowTitle(self._CONFIG["windowTitle"])

        self.FMainMenu_init()
        self.showNormal()
        self.width = self._CONFIG["initWidth"]
        self.height = self._CONFIG["initHeight"]
        self.left = self._CONFIG["initLeft"]
        self.top = self._CONFIG["initTop"]
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.FWelcomeInfo = FWelcomeInfo(self)
        self.FCentralScreen = FViewer(self)
        self.setCentralWidget(self.FCentralScreen)
        #self.setCentralWidget(self.FWelcomeInfo)

        
    def FMainMenu_init(self):
        self.mainMenu = self.menuBar()
        fileMainMenu.FFileMenu_init(self)
        editMainMenu.FEditMenu_init(self)
        helpMainMenu.FHelpMenu_init(self)
        self.FStatusBar = QtWidgets.QStatusBar()
        self.FStatusBarFrameNumber = QtWidgets.QLabel()
        self.FStatusBarFrameNumber.setText("No File Loaded")
        self.FStatusBarMousePos = QtWidgets.QLabel()
        self.FStatusBar.addPermanentWidget(self.FStatusBarMousePos)
        self.FStatusBar.addPermanentWidget(self.FStatusBarFrameNumber)
        self.setStatusBar(self.FStatusBar)
        return

def run():
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = FTestContainer()
    app.exec_()
    return

if __name__ == '__main__':
    run()
    #app = QtWidgets.QApplication(sys.argv)
    #display_image_widget = FViewerWidget()
    #display_image_widget.show()
    #sys.exit(app.exec_())
