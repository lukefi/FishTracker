from PyQt5 import QtCore
from PyQt5.QtWidgets import *
import sys

class MainWindow(QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        
        self.setWindowTitle("My Awesome App")
        
        label = QLabel("THIS IS AWESOME!!!")
        label.setAlignment(QtCore.Qt.AlignCenter)
        
        self.setCentralWidget(label)
        
        toolbar = QToolBar("My main toolbar")
        self.addToolBar(toolbar)
        
        button_action = QAction("Your button", self)
        button_action.setStatusTip("This is your button")
        button_action.triggered.connect(self.onMyToolBarButtonClick)
        button_action.setCheckable(True)
        toolbar.addAction(button_action)

        toolbar.addWidget(QLabel("Hello"))
        toolbar.addWidget(QCheckBox())
        
        self.setStatusBar(QStatusBar(self))
        
        
    def onMyToolBarButtonClick(self, s):
        print("click", s)

def window():
	app = QApplication(sys.argv)
	win = MainWindow()
	win.show()
	sys.exit(app.exec_())


if __name__ == "__main__":
	window()
