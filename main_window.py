from PyQt5 import QtWidgets, QtGui

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        self.status_length = 100
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
        if len(str) > self.status_length:
            self.FStatusLog.setText(str[0:self.status_length - 3] + "...")
        else:
            self.FStatusLog.setText(str)