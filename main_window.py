"""
This file is part of Fish Tracker.
Copyright 2021, VTT Technical research centre of Finland Ltd.
Developed by: Mikael Uimonen.

Fish Tracker is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Fish Tracker is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Fish Tracker.  If not, see <https://www.gnu.org/licenses/>.
"""

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