from PyQt5 import QtWidgets, QtGui

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
    def setupStatusBar(self):
        #self._CONFIG = FH.loadJSON("config.json")
        #self.setWindowIcon(pyqtGUI.QIcon(FGetIcon(self._CONFIG["icon"], OS = sys.platform)))
        #self.setWindowTitle(self._CONFIG["windowTitle"])

        self.FStatusBar = QtWidgets.QStatusBar()
        self.FStatusLog = QtWidgets.QLabel()
        self.FStatusBarFrameNumber = QtWidgets.QLabel()
        self.FStatusBarMousePos = QtWidgets.QLabel()
        self.FStatusBarDistance = QtWidgets.QLabel()

        self.FStatusBar.addPermanentWidget(self.FStatusLog)
        self.FStatusBar.addPermanentWidget(self.FStatusBarDistance)
        self.FStatusBar.addPermanentWidget(self.FStatusBarMousePos)
        self.FStatusBar.addPermanentWidget(self.FStatusBarFrameNumber)
        self.setStatusBar(self.FStatusBar)

        #self.showNormal()
        #self.width = 800 #self._CONFIG["initWidth"]
        #self.height = 600 #self._CONFIG["initHeight"]
        #self.left = 560 # self._CONFIG["initLeft"]
        #self.top = 240 #self._CONFIG["initTop"]
        #self.setGeometry(self.left, self.top, self.width, self.height)

    def updateStatusLog(self, str):
        self.FStatusLog.setText(str)