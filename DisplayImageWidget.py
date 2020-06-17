from PyQt5 import QtGui, QtCore, QtWidgets
import cv2
import sys
from playback_manager import PlaybackManager

class DisplayImageWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(DisplayImageWidget, self).__init__(parent)

        self.button = QtWidgets.QPushButton('Open file')
        self.button.clicked.connect(self.show_image)
        self.image_frame = QtWidgets.QLabel()

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.button)
        self.layout.addWidget(self.image_frame)
        self.setLayout(self.layout)

    @QtCore.pyqtSlot()
    def show_image(self):
        #self.image = cv2.imread('placeholder.PNG')
        #self.image = QtGui.QImage(self.image.data, self.image.shape[1], self.image.shape[0], QtGui.QImage.Format_RGB888).rgbSwapped()
        #self.image_frame.setPixmap(QtGui.QPixmap.fromImage(self.image))
        pbManager = PlaybackManager()
        pbManager.open_file()
        gray = sonar.getFrame(0)
        image = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        image = QtGui.QImage(image.data, image.shape[1], image.shape[0], QtGui.QImage.Format_RGB888).rgbSwapped()
        self.image_frame.setPixmap(QtGui.QPixmap.fromImage(image))


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    display_image_widget = DisplayImageWidget()
    display_image_widget.show()
    sys.exit(app.exec_())