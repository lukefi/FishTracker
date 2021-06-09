from PyQt5 import QtCore, QtGui, QtWidgets
from zoomable_qlabel import ZoomableQLabel
import cv2
import numpy as np
from debug import Debug
from log_object import LogObject

class EchoFigure(ZoomableQLabel):
    """
    Class that handles drawing the echogram image. Used in EchogramViewer widget.
    """
    def __init__(self, parent):
        super().__init__(False, True, False)
        self.parent = parent
        self.displayed_image = None
        self.resetView()
        self.frame_ind = 0
        self.margin = 0
        self.frame_count = 0
        self.detection_opacity = 1

        self.update_lines = False
        self.max_height = 1000
        self.detection_lines = []
        self.track_lines = {}


    def frame2xPos(self, value):
        try:
            #print((value * self.image_width - self.x_min_limit), self.image_width)
            return (value * self.image_width - self.x_min_limit) / (self.x_max_limit - self.x_min_limit) * self.window_width
        except ZeroDivisionError as e:
            LogObject().print(e)
            return 0

    def xPos2Frame(self, value):
        try:
            return (value * (self.x_max_limit - self.x_min_limit)/self.window_width + self.x_min_limit) / self.image_width
        except ZeroDivisionError as e:
            LogObject().print(e)
            return 0

    def paintEvent(self, event):
        print("Paint")
        super().paintEvent(event)

        try:
            h_pos_0 = self.frame2xPos((self.frame_ind) / self.frame_count)
            h_pos_1 = self.frame2xPos((self.frame_ind + 1) / self.frame_count)
        except ZeroDivisionError:
            h_pos_0 = 0
            h_pos_1 = self.frame2xPos(0.01)

        painter = QtGui.QPainter(self)

        if self.parent.detector._show_echogram_detections:
            if self.update_lines:
                self.updateDetectionLines(self.parent.getDetections())
            #self.overlayDetections(painter, self.parent.getDetections(), QtCore.Qt.red)
            self.overlayLines(painter, self.detection_lines, QtCore.Qt.red)

        if self.parent.fish_manager.show_echogram_fish:
            if self.update_lines:
                self.updateFishLines(self.parent.squeezed_fish)
            self.overlayDetections(painter, self.parent.squeezed_fish, QtCore.Qt.green)

        if h_pos_0 < self.window_width:
            painter.setPen(QtCore.Qt.white)
            painter.setBrush(QtCore.Qt.white)
            painter.setOpacity(0.3)
            painter.drawRect(h_pos_0, 0, h_pos_1-h_pos_0, self.window_height)

        self.update_lines = False

    def getQLine(self, v_pos, h_pos_0, h_pos_1):
        return QtCore.QLineF(h_pos_0, v_pos, h_pos_1, v_pos)

    def overlayDetections(self, painter, squeezed, color):
        try:
            painter.setPen(color)
            painter.setOpacity(self.detection_opacity)
            v_mult, v_min = self.parent.getScaleLinearModel(self.window_height)

            for i in range(len(squeezed)):
                heights = squeezed[i]
                h_pos_0 = self.frame2xPos(i / self.frame_count)
                h_pos_1 = self.frame2xPos((i + 1) / self.frame_count)
                lines = [self.getQLine(self.window_height - (height - v_min) * v_mult, h_pos_0, h_pos_1) for height in heights]
                painter.drawLines(lines)
                #for h in heights:
                #    v_pos = self.window_height - (h - v_min) * v_mult
                #    painter.drawLine(h_pos_0, v_pos, h_pos_1, v_pos)
        except ZeroDivisionError:
            pass

    def overlayLines(self, painter, line_list, color):
        painter.setPen(color)
        painter.setOpacity(self.detection_opacity)
        for lines in line_list:
            painter.drawLines(lines)

    def updateDetectionLines(self, vertical_detections):
        self.detection_lines = []
        try:
            v_mult, v_min = self.parent.getScaleLinearModel(self.max_height)
            h_pos_0 = self.frame2xPos(0)

            for i, heights in enumerate(vertical_detections):
                h_pos_1 = self.frame2xPos((i + 1) / self.frame_count)
                #print(i, (i + 1) / self.frame_count, h_pos_0, h_pos_1)
                lines = [self.getQLine(self.max_height - (height - v_min) * v_mult, h_pos_0, h_pos_1) for height in heights]
                self.detection_lines.append(lines)
                h_pos_0 = h_pos_1
            print([[(l.p1(), l.p2()) for l in list] for list in self.detection_lines[0:10]])
        except ZeroDivisionError:
            pass

    def updateFishLines(self, vertical_fish):
        pass

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.displayed_image is not None and event.button() == QtCore.Qt.LeftButton:
            self.parent.setFrame(self.xPos2Frame(event.x()))

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.displayed_image is not None and event.buttons() == QtCore.Qt.LeftButton:
            self.parent.setFrame(self.xPos2Frame(event.x()))

    def clear(self):
        super().clear()
        self.displayed_image = None

class EchogramViewer(QtWidgets.QWidget):
    """
    Widget containing EchoFigure. Handles communication to PlaybackManager and other
    core classes.
    """
    def __init__(self, playback_manager, detector, fish_manager):
        super().__init__()
        self.setMaximumHeight(500)

        self.playback_manager = playback_manager
        self.detector = detector
        self.detector.all_computed_event.append(self.updateDetectionLines)
        self.fish_manager = fish_manager
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.horizontalLayout.setContentsMargins(0,0,0,0)

        self.squeezed_fish = []
        self.fish_manager.updateContentsSignal.connect(self.squeezeFish)

        self.figure = EchoFigure(self)
        self.horizontalLayout.addWidget(self.figure)
        self.playback_manager.file_opened.connect(self.onFileOpen)
        self.playback_manager.frame_available.connect(self.onImageAvailable)
        self.playback_manager.polars_loaded.connect(self.imageReady)
        self.playback_manager.file_closed.connect(self.onFileClose)

        self.setLayout(self.horizontalLayout)
        self.echogram = None

    def onImageAvailable(self, tuple):
        if tuple is None:
            self.figure.clear
            return

        self.figure.frame_ind = self.playback_manager.getFrameInd()
        self.figure.detection_opacity = 0.5 if self.detector.parametersDirty() else 1.0
        self.figure.update()

    def setFrame(self, percentage):
        self.playback_manager.setRelativeIndex(percentage)

    def onFileOpen(self, sonar):
        self.echogram = Echogram(sonar.frameCount)
        self.figure.frame_count = sonar.frameCount

    def onFileClose(self):
        if self.figure is not None:
            self.figure.clear()
        if self.echogram is not None:
            self.echogram.clear()
            self.echogram = None

    def imageReady(self):
        self.echogram.processBuffer(self.playback_manager.getPolarBuffer())
        self.figure.setImage(self.echogram.getDisplayedImage())
        self.figure.resetView()

    def getDetections(self):
        return self.detector.vertical_detections

    def getScaleLinearModel(self, height):
        """
        Returns parameters to a linear model, with which metric distances can be converted
        into vertical position on the displayed image.
        """
        if self.playback_manager.isMappingDone():
            min_d, max_d = self.playback_manager.getRadiusLimits()
            mult = height / (max_d - min_d)
            return mult, min_d
        else:
            return 1, 0

    @QtCore.pyqtSlot()
    def squeezeFish(self):
        self.squeezed_fish = [[] for fr in range(self.playback_manager.getFrameCount())]
        if not self.playback_manager.isMappingDone():
            return

        for fish in self.fish_manager.fish_list:
            for key, (tr, _) in fish.tracks.items():
                avg_y = (tr[0] + tr[2]) / 2
                avg_x = (tr[1] + tr[3]) / 2

                distance, _ = self.playback_manager.getBeamDistance(avg_x, avg_y, True)
                self.squeezed_fish[key].append(distance)
        self.figure.update()

    def updateDetectionLines(self):
        print("Update detection lines")
        self.figure.update_lines = True
        self.figure.max_height = self.maximumHeight()
        #self.figure.updateDetectionLines(self.detector.vertical_detections)

class Echogram():
    """
    Transforms polar frames into an echogram image.
    """
    def __init__(self, length):
        self.data = None
        self.length = length

    def processBuffer(self, buffer):
        try:
            buf = [b for b in buffer if b is not None]
            buf = np.asarray(buf, dtype=np.uint8)
            self.data = np.max(buf, axis=2).T
            min_v = np.min(self.data)
            max_v = np.max(self.data)
            self.data = (255 / (max_v - min_v) * (self.data - min_v)).astype(np.uint8)
        except np.AxisError as e:
            LogObject().print("Echogram process buffer error:", e)
            self.data = None

    def clear(self):
        self.data = None

    def getDisplayedImage(self):
        return self.data





if __name__ == "__main__":
    import sys
    from playback_manager import PlaybackManager, Event

    class TestDetection():
        def __init__(self, x, y):
            self.center = (y, x)

    class TestDetector():
        def __init__(self, playback_manager):
            self.playback_manager = playback_manager
            self.frameCount = 0
            self.image_height = 0
            self.detections_clearable = True
            self._show_echogram_detections = True
            self.detections = []
            self.vertical_detections = []
            self.all_computed_event = Event()

            self.playback_manager.file_opened.connect(self.onFileOpen)
            self.playback_manager.polars_loaded.connect(self.onPolarsLoaded)

        def onFileOpen(self, sonar):
            self.frameCount = self.playback_manager.getFrameCount()
            self.image_height = sonar.samplesPerBeam

        def parametersDirty(self):
            return False

        def onPolarsLoaded(self):
            min_r, max_r = self.playback_manager.getRadiusLimits()
            min_r += 0.01

            for i in range(self.frameCount):
                count = np.random.randint(0, 5)
                if count > 0:
                    self.detections.append([TestDetection(0, np.random.uniform(min_r,max_r)) for j in range(count)] + [TestDetection(0, min_r), TestDetection(0, max_r)])
                else:
                    #self.detections.append(None)
                    self.detections.append([TestDetection(0, min_r), TestDetection(0, max_r)])

            self.vertical_detections = [[d.center[0] for d in dets if d.center is not None] if dets is not None else [] for dets in self.detections]
            print("All computed")
            self.all_computed_event()

    class TestFishManager(QtCore.QAbstractTableModel):

        updateContentsSignal = QtCore.pyqtSignal()

        def __init__(self):
            super().__init__()
            self.show_fish = True
            self.show_echogram_fish = True


    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    detector = TestDetector(playback_manager)
    fish_manager = TestFishManager()
    echogram = EchogramViewer(playback_manager, detector, fish_manager)

    playback_manager.openTestFile()

    main_window.setCentralWidget(echogram)
    main_window.show()
    main_window.resize(900,300)
    sys.exit(app.exec_())