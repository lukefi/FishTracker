from PyQt5 import QtCore, QtGui, QtWidgets
import cv2

class EchoFigure(QtWidgets.QLabel):
    parent = None

    def __init__(self, parent):
        self.parent = parent
        self.figurePixmap = None
        self.test_img = cv2.imread('echo_placeholder.png', 0)
        QtWidgets.QLabel.__init__(self, parent)

    def showTestImage(self):
        self.setAlignment(QtCore.Qt.AlignCenter)
        # self.setScaledContents(True)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)

    def resizeEvent(self, event):
        img = cv2.resize(self.test_img, self.getScale())
        img = QtGui.QImage(img, img.shape[1], img.shape[0], img.strides[0], QtGui.QImage.Format_Indexed8).rgbSwapped()
        self.figurePixmap = QtGui.QPixmap.fromImage(img)
        self.setPixmap(self.figurePixmap) #(self.figurePixmap.scaled(self.size(), QtCore.Qt.KeepAspectRatio))

        if isinstance(self.figurePixmap, QtGui.QPixmap):
            self.setPixmap(self.figurePixmap.scaled(self.size(), QtCore.Qt.KeepAspectRatio))

    def getScale(self):
        sz = self.size()
        return (max(1, sz.width()), max(1, sz.height()))

class EchogramViewer(QtWidgets.QDialog):
    def __init__(self, playback_manager):
        self.playback_manager = playback_manager
        QtWidgets.QDialog.__init__(self)

        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.figure = EchoFigure(self)
        self.horizontalLayout.addWidget(self.figure)
        self.figure.showTestImage()

        self.setLayout(self.horizontalLayout)


if __name__ == "__main__":
    import sys
    from playback_manager import PlaybackManager

    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    playback_manager.openTestFile()
    echogram = EchogramViewer(playback_manager)
    main_window.setCentralWidget(echogram)
    main_window.show()
    sys.exit(app.exec_())