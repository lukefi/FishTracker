from PyQt5 import QtWidgets, QtGui

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
    def setupStatusBar(self):
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

    def updateStatusLog(self, str):
        self.FStatusLog.setText(str)