from PyQt5 import QtCore, QtGui, QtWidgets
from zoomable_qlabel import ZoomableQLabel
import cv2

class EchoFigure(ZoomableQLabel):

    def __init__(self, parent):
        super().__init__(False, True, False)
        self.parent = parent
        self.displayed_image = cv2.imread('echo_placeholder.png', 0)
        self.resetView()
        self.progress = 0


    def frame2xPos(self, value):
        # return value * width * self.applied_zoom
        return (value * self.image_width - self.x_min_limit) / (self.x_max_limit - self.x_min_limit) * self.window_width

    def xPos2Frame(self, value):
        #return value / width / self.applied_zoom
        return (value*(self.x_max_limit - self.x_min_limit)/self.window_width + self.x_min_limit) / self.image_width

    def paintEvent(self, event):
        super().paintEvent(event)
        size = self.size()
        width = size.width()
        height = size.height()

        h_pos = self.frame2xPos(self.progress) #self.applied_zoom * self.progress * width

        painter = QtGui.QPainter(self)
        #painter.drawPixmap(self.rect(), self.figurePixmap)

        if h_pos < width:
            painter.setPen(QtCore.Qt.red)
            painter.drawLine(h_pos, 0, h_pos, height)

    #def mouseMoveEvent(self, event):
    #    #if event.buttons() == QtCore.Qt.NoButton:
    #    #    print("Simple mouse motion")
    #    if event.buttons() == QtCore.Qt.LeftButton:
    #        pass
    #    elif event.buttons() == QtCore.Qt.RightButton:
    #        pass
    #    super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.parent.setFrame(self.xPos2Frame(event.x())) #float(event.x()) / self.size().width())
        super().mousePressEvent(event)

    #def wheelEvent(self, event):
    #    self.zoom_01 = max(0, min(self.zoom_01 + event.angleDelta().y() / 2000, 1))
    #    self.applyPixmap()

class EchogramViewer(QtWidgets.QWidget):
    def __init__(self, playback_manager):
        super().__init__()

        self.playback_manager = playback_manager
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.figure = EchoFigure(self)
        self.horizontalLayout.addWidget(self.figure)
        self.playback_manager.frame_available.append(self.updateLocation)

        self.setLayout(self.horizontalLayout)

    def updateLocation(self, frame):
        self.figure.progress = self.playback_manager.getRelativeIndex()
        self.figure.update()

    def setFrame(self, percentage):
        self.playback_manager.setRelativeIndex(percentage)



if __name__ == "__main__":
    import sys
    from playback_manager import PlaybackManager

    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    playback_manager.openTestFile()
    playback_manager.play()
    echogram = EchogramViewer(playback_manager)
    main_window.setCentralWidget(echogram)
    main_window.show()
    sys.exit(app.exec_())