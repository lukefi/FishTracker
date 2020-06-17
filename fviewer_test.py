from PyQt5 import QtGui, QtCore, QtWidgets
import sys, os, cv2

_MAIN_DIRECTORY = os.getcwd()
sys.path.append(os.path.join(_MAIN_DIRECTORY, "UI"))

import UI_handler as ui
import file_handler as fh
import UI_utils
import FViewer



class FViewerWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(FViewerWidget, self).__init__(parent)
        self.viewer = FViewer.FViewer(self)
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.viewer)
        self.setLayout(self.layout)

def run():
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = ui.FMainContainer()
    app.exec_()
    return

if __name__ == '__main__':
    run()
    #app = QtWidgets.QApplication(sys.argv)
    #display_image_widget = FViewerWidget()
    #display_image_widget.show()
    #sys.exit(app.exec_())
