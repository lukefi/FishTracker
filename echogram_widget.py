from PyQt5 import QtCore, QtGui, QtWidgets
from zoomable_qlabel import ZoomableQLabel
import cv2
import numpy as np
from debug import Debug

class EchoFigure(ZoomableQLabel):

    def __init__(self, parent):
        super().__init__(False, True, False)
        self.parent = parent
        self.displayed_image = None #cv2.imread('echo_placeholder.png', 0)
        self.resetView()
        self.progress = 0


    def frame2xPos(self, value):
        # return value * width * self.applied_zoom
        try:
            return (value * self.image_width - self.x_min_limit) / (self.x_max_limit - self.x_min_limit) * self.window_width
        except ZeroDivisionError as e:
            print(e)
            return 0

    def xPos2Frame(self, value):
        #return value / width / self.applied_zoom
        try:
            return (value*(self.x_max_limit - self.x_min_limit)/self.window_width + self.x_min_limit) / self.image_width
        except ZeroDivisionError as e:
            print(e)
            return 0

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

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.parent.setFrame(self.xPos2Frame(event.x())) #float(event.x()) / self.size().width())
        super().mousePressEvent(event)

class EchogramViewer(QtWidgets.QWidget):
    def __init__(self, playback_manager):
        super().__init__()

        self.playback_manager = playback_manager
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.figure = EchoFigure(self)
        self.horizontalLayout.addWidget(self.figure)
        self.playback_manager.file_opened.append(self.onFileOpen)
        self.playback_manager.frame_available.append(self.onImageAvailable)
        self.playback_manager.polars_loaded.append(self.imageReady)
        # self.playback_manager.polar_available.append(self.onPolarAvailable)
        # self.playback_manager.polar_ended.append(self.imageReady)

        self.setLayout(self.horizontalLayout)
        self.echogram = None

    def onImageAvailable(self, frame):
        self.figure.progress = self.playback_manager.getRelativeIndex()
        self.figure.update()

    #def onPolarAvailable(self, ind, polar):
    #    self.echogram.insert(polar, ind)

    def setFrame(self, percentage):
        self.playback_manager.setRelativeIndex(percentage)

    def onFileOpen(self, sonar):
        self.echogram = Echogram(sonar.frameCount)

    def imageReady(self):
        self.echogram.processBuffer(self.playback_manager.getPolarBuffer())
        self.figure.setImage(self.echogram.getDisplayedImage())
        self.figure.resetView()

class Echogram():
    """
    Contains raw echogram data which can be edited on the go if needed.
    The final image can be acquired through getDisplayedImage function.
    """
    def __init__(self, length):
        self.data = None
        self.length = length

    def processBuffer(self, buffer):
        buf = [b for b in buffer if b is not None]
        buf = np.asarray(buf, dtype=np.uint8)
        print(buf.shape)
        self.data = np.max(buf, axis=2).T

    #def insert(self, frame, ind):
    #    if self.data is None:
    #        self.data = np.zeros((frame.shape[0], self.length), np.uint8)

    #    col_im = np.max(np.asarray(frame), axis=1)
    #    try:
    #        self.data[:, ind] = col_im
    #    except IndexError as e:
    #        print(e)

    #    if(ind % 100 == 0):
    #        print("EchoFrame:", ind)
    #    #    img = cv2.resize(self.echogram, (1000, 200))
    #    #    cv2.imshow("echogram", img)

    def clear(self):
        if self.data is not None:
            self.data = np.zeros(self.data.shape, np.uint8)

    def getDisplayedImage(self):
        min_v = np.min(self.data)
        max_v = np.max(self.data)
        return (255 / (max_v - min_v) * (self.data - min_v)).astype(np.uint8)





if __name__ == "__main__":
    import sys
    from playback_manager import PlaybackManager

    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    echogram = EchogramViewer(playback_manager)
    playback_manager.openTestFile()
    main_window.setCentralWidget(echogram)
    main_window.show()
    main_window.resize(900,300)
    sys.exit(app.exec_())