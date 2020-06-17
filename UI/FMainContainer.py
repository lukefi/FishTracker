import PyQt5.QtCore as pyqtCore
import PyQt5.QtGui as pyqtGUI
import PyQt5.QtWidgets as pyqtWidgets

## Other windows connected to this one
# All the following modules are inside directory: UI/
from FWelcomeInfo import *      # UI/FWelcomeInfo
from FViewer import *           # UI/FViewer
from iconsLauncher import *     # UI/iconsLauncher
import fileMainMenu             # UI/fileMainMenu
import editMainMenu             # UI/editMainMenu
import helpMainMenu             # UI/helpMainMenu


## Other entities dealing with the UI
import os
import sys
import cv2


class FMainContainer(pyqtWidgets.QMainWindow):
    """This class holds the welcome window which will be used to 
    open ARIS and DIDSON files and show statistics and information
    about the project and the developers.
    
    Arguments:
        pyqtWidgets.QMainWindow {Class} -- inheriting from 
                PyQt5.QtWidgets.QMainWindow class.
    """
    def __init__(self):
        """Initializes the window and displays the main container
        which contains:
            - status bar
            - main menu (File-Edit-Help)
        """

        ##  UI elements description
        pyqtWidgets.QMainWindow.__init__(self)
        self.initUI()
        return
        
        

    def initUI(self):
        self._MAIN_CONTAINER = self
        self._CONFIG = FH.loadJSON("config.json")
        self.setWindowIcon(pyqtGUI.QIcon(FGetIcon(self._CONFIG["icon"], OS = sys.platform)))
        self.setWindowTitle(self._CONFIG["windowTitle"])

        self.FMainMenu_init()
        self.showNormal()
        self.width = self._CONFIG["initWidth"]
        self.height = self._CONFIG["initHeight"]
        self.left = self._CONFIG["initLeft"]
        self.top = self._CONFIG["initTop"]
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.FWelcomeInfo = FWelcomeInfo(self)
        self.setCentralWidget(self.FWelcomeInfo)

        
    def FMainMenu_init(self):
        """initializes the main menu for the application.
        """
        self.mainMenu = self.menuBar()
        fileMainMenu.FFileMenu_init(self)
        editMainMenu.FEditMenu_init(self)
        helpMainMenu.FHelpMenu_init(self)
        self.FStatusBar = pyqtWidgets.QStatusBar()
        self.FStatusBarFrameNumber = pyqtWidgets.QLabel()
        self.FStatusBarFrameNumber.setText("No File Loaded")
        self.FStatusBarMousePos = pyqtWidgets.QLabel()
        self.FStatusBar.addPermanentWidget(self.FStatusBarMousePos)
        self.FStatusBar.addPermanentWidget(self.FStatusBarFrameNumber)
        self.setStatusBar(self.FStatusBar)
        return

    
