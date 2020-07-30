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
        self.frame_ind = 0
        self.margin = 0
        self.frame_count = 0
        self.detection_opacity = 1


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

        try:
            h_pos = self.frame2xPos((self.frame_ind + 0.5) / self.frame_count)
        except ZeroDivisionError:
            h_pos = 0

        painter = QtGui.QPainter(self)
        #painter.drawPixmap(self.rect(), self.figurePixmap)

        self.overlayDetections(painter)

        if h_pos < width:
            painter.setPen(QtCore.Qt.darkRed)
            painter.setOpacity(1.0)
            painter.drawLine(h_pos, 0, h_pos, height)

    def overlayDetections(self, painter):
        try:
            squeezed = self.parent.getDetections()
            painter.setPen(QtCore.Qt.blue)
            painter.setOpacity(self.detection_opacity)
            v_mult = self.parent.getDetectionScale()
            for i in range(len(squeezed)):
                heights = squeezed[i]
                h_pos_0 = self.frame2xPos(i / self.frame_count)
                h_pos_1 = self.frame2xPos((i + 1) / self.frame_count)
                for h in heights:
                    v_pos = h * v_mult
                    painter.drawLine(h_pos_0, v_pos, h_pos_1, v_pos)
        except ZeroDivisionError:
            pass

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            self.parent.setFrame(self.xPos2Frame(event.x())) #float(event.x()) / self.size().width())

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if event.buttons() == QtCore.Qt.LeftButton:
            self.parent.setFrame(self.xPos2Frame(event.x()))

class EchogramViewer(QtWidgets.QWidget):
    def __init__(self, playback_manager, detector):
        super().__init__()

        self.playback_manager = playback_manager
        self.detector = detector
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.horizontalLayout.setContentsMargins(0,0,0,0)

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
        self.figure.frame_ind = self.playback_manager.getFrameInd()
        self.figure.detection_opacity = 0.5 if self.detector.detections_dirty else 1.0
        print("Opacity:", self.figure.detection_opacity)
        print(self.detector.detections_dirty, self.detector.detections_clearable)
        self.figure.update()

    #def onPolarAvailable(self, ind, polar):
    #    self.echogram.insert(polar, ind)

    def setFrame(self, percentage):
        self.playback_manager.setRelativeIndex(percentage)

    def onFileOpen(self, sonar):
        self.echogram = Echogram(sonar.frameCount)
        self.figure.frame_count = sonar.frameCount

    def imageReady(self):
        self.echogram.processBuffer(self.playback_manager.getPolarBuffer())
        self.figure.setImage(self.echogram.getDisplayedImage())
        self.figure.resetView()

    def getDetections(self):
        return self.detector.vertical_detections

    def getDetectionScale(self):
        return self.figure.window_height / self.detector.image_height

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

    class TestDetection():
        def __init__(self, x, y):
            self.center = (y, x)

    class TestDetector():
        def __init__(self, frameCount, height):
            self.frameCount = frameCount
            self.detections = []
            self.image_height = height
            self.detections_dirty = True
            for i in range(frameCount):
                count = np.random.randint(0, 5)
                if count > 0:
                    self.detections.append([TestDetection(0, np.random.randint(0,height)) for j in range(count)])
                else:
                    self.detections.append(None)

            self.vertical_detections = [[d.center[0] for d in dets if d.center is not None] if dets is not None else [] for dets in self.detections]


    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    playback_manager.openTestFile()
    detector = TestDetector(playback_manager.getFrameCount(), playback_manager.sonar.samplesPerBeam)
    echogram = EchogramViewer(playback_manager, detector)
    echogram.onFileOpen(playback_manager.sonar)
    main_window.setCentralWidget(echogram)
    main_window.show()
    main_window.resize(900,300)
    sys.exit(app.exec_())