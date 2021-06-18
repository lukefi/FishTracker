from PyQt5 import QtCore, QtGui, QtWidgets
from zoomable_qlabel import ZoomableQLabel, DebugZQLabel
import cv2
import numpy as np
from debug import Debug
from log_object import LogObject
from fish_manager import pyqt_palette

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
        self.max_height = 500
        self.detection_lines = []
        self.track_lines = {}
        self.detection_pixmap = None

        self.shown_x_min_limit = 0
        self.shown_x_max_limit = 1
        self.shown_width = 1
        self.shown_height = 1
        self.shown_zoom = 0

    def frame2xPos(self, value):
        try:
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
        super().paintEvent(event)

        try:
            h_pos_0 = self.frame2xPos((self.frame_ind) / self.frame_count)
            h_pos_1 = self.frame2xPos((self.frame_ind + 1) / self.frame_count)
        except ZeroDivisionError:
            h_pos_0 = 0
            h_pos_1 = self.frame2xPos(0.01)

        painter = QtGui.QPainter(self)

        if self.parent.detector._show_echogram_detections or self.parent.fish_manager.show_echogram_fish:
            self.overlayPixmap(painter, self.detection_pixmap)

        #if self.parent.fish_manager.show_echogram_fish:
        #    if self.update_lines:
        #        self.updateFishLines(self.parent.squeezed_fish)
        #    self.overlayDetections(painter, self.parent.squeezed_fish, QtCore.Qt.green)

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

    def overlayPixmap(self, painter, pixmap):
        """
        Overlays given pixmap on top of the drawn image.
        The given pixmap is cropped to fit the current zoom level or
        scaled down so that the overlayed image aligns with the underlying one.

        This enables reusing precalculating images until the image is refreshed.
        """

        if pixmap is not None:
            current_frames = self.x_max_limit - self.x_min_limit
            shown_frames = self.shown_x_max_limit - self.shown_x_min_limit

            source_L = max(0, self.x_min_limit - self.shown_x_min_limit)
            source_L = int(source_L / shown_frames * self.shown_width)

            source_R = max(0, self.shown_x_max_limit - self.x_max_limit)
            source_R = int(source_R / shown_frames * self.shown_width)

            target_L = max(0, self.shown_x_min_limit - self.x_min_limit)
            target_L = int(target_L / current_frames * self.window_width)

            target_R = max(0, self.x_max_limit - self.shown_x_max_limit)
            target_R = int(target_R / current_frames * self.window_width)


            source = QtCore.QRectF(source_L, 0, self.shown_width - source_R - source_L, self.shown_height)
            target = QtCore.QRectF(target_L, 0, self.window_width - target_R - target_L, self.window_height)

            painter.drawPixmap(target, pixmap, source)

            painter.setPen(QtCore.Qt.green)
            painter.drawLine(QtCore.QLineF(target_L, 0, target_L, self.window_height))
            painter.drawLine(QtCore.QLineF(self.window_width - target_R, 0, self.window_width - target_R, self.window_height))

    def updateDetectionLines(self, vertical_detections):
        self.detection_lines = []
        try:
            v_mult, v_min = self.parent.getScaleLinearModel(self.max_height)
            h_pos_0 = self.frame2xPos(0)

            for i, heights in enumerate(vertical_detections):
                h_pos_1 = self.frame2xPos((i + 1) / self.frame_count)
                lines = [self.getQLine(self.max_height - (height - v_min) * v_mult, h_pos_0, h_pos_1) for height in heights]
                self.detection_lines.append(lines)
                h_pos_0 = h_pos_1
        except ZeroDivisionError:
            pass

    def updateOverlayedImage(self, vertical_detections, vertical_tracks):
        """
        Precalculates an image (QPixmap) containing the detection lines of each detection.
        The calculated image can then be used repeatedly to overlay the detections to
        the echogram view.

        The image is calculated based on the current position and zoom level of the echogram view,
        meaning any detections outside the current view will not be included.
        """
        self.detection_pixmap = QtGui.QPixmap(self.window_width, self.window_height)
        self.detection_pixmap.fill(QtGui.QColor(0,0,0,0))

        painter = QtGui.QPainter(self.detection_pixmap)
        painter.setOpacity(self.detection_opacity)

        self.shown_x_min_limit = self.x_min_limit
        self.shown_x_max_limit = self.x_max_limit
        self.shown_width = self.window_width
        self.shown_height = self.window_height
        self.shown_zoom = self.zoom_01

        if self.parent.detector._show_echogram_detections:
            self.updateDetectionImage(painter, vertical_detections)

        if self.parent.fish_manager.show_echogram_fish:
            self.updateTrackImage(painter, vertical_tracks)


    def updateDetectionImage(self, painter, vertical_detections):

        painter.setPen(QtCore.Qt.red)
        v_mult, v_min = self.parent.getScaleLinearModel(self.window_height)
        h_pos_0 = 0
        show_frame_count = self.x_max_limit - self.x_min_limit

        try:
            for i, heights in enumerate(vertical_detections[self.x_min_limit:self.x_max_limit]):
                h_pos_1 = (i + 1) / show_frame_count * self.window_width
                for height in heights:
                    v_pos = self.window_height - (height - v_min) * v_mult
                    painter.drawLine(h_pos_0, v_pos, h_pos_1, v_pos)
                h_pos_0 = h_pos_1
        except ZeroDivisionError:
            pass

    def updateTrackImage(self, painter, vertical_tracks):
        """

        """
        v_mult, v_min = self.parent.getScaleLinearModel(self.window_height)
        h_pos_0 = 0
        show_frame_count = self.x_max_limit - self.x_min_limit

        try:
            for i, height_color_pairs in enumerate(vertical_tracks[self.x_min_limit:self.x_max_limit]):
                h_pos_1 = (i + 1) / show_frame_count * self.window_width

                for height, color_ind in height_color_pairs:
                    painter.setPen(pyqt_palette[color_ind])
                    v_pos = self.window_height - (height - v_min) * v_mult
                    painter.drawLine(h_pos_0, v_pos, h_pos_1, v_pos)
                h_pos_0 = h_pos_1
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
        #self.setMaximumHeight(500)

        self.playback_manager = playback_manager
        self.detector = detector
        self.detector.all_computed_event.append(self.updateDetectionImage)
        self.fish_manager = fish_manager
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.horizontalLayout.setContentsMargins(0,0,0,0)

        self.squeezed_fish = []
        self.fish_manager.updateContentsSignal.connect(self.squeezeFish)

        self.figure = EchoFigure(self)
        self.figure.userInputSignal.connect(self.setInputUpdateTimer)
        self.horizontalLayout.addWidget(self.figure)
        self.playback_manager.file_opened.connect(self.onFileOpen)
        self.playback_manager.frame_available.connect(self.onImageAvailable)
        self.playback_manager.polars_loaded.connect(self.processEchogram)
        self.playback_manager.file_closed.connect(self.onFileClose)

        self.update_timer = None
        self.update_timer_delay = 100

        self.setLayout(self.horizontalLayout)
        self.echogram = None

    def onImageAvailable(self, tuple):
        """
        Update view as new frames are displayed.
        """
        if tuple is None:
            self.figure.clear()
            return

        self.setInputUpdateTimer()

        self.figure.frame_ind = self.playback_manager.getFrameInd()
        self.figure.detection_opacity = 0.5 if self.detector.parametersDirty() else 1.0
        self.figure.update()

    def setInputUpdateTimer(self):
        """
        Starts a new timer that updates the image when set amount of time has passed.
        If an old timer exists, it is stopped first to avoid updating too often.

        This is used to update overlayed image, which is too heavy to update
        every frame.
        """
        if self.update_timer:
            self.update_timer.stop()
            self.update_timer.deleteLater()
        
        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.updateDetectionImage)
        self.update_timer.setSingleShot(True)
        self.update_timer.start(self.update_timer_delay)

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

    def processEchogram(self):
        self.echogram.processBuffer(self.playback_manager.getPolarBuffer())
        self.figure.setImage(self.echogram.getDisplayedImage())
        self.figure.resetView()

    def getDetections(self):
        return self.detector.vertical_detections

    def getScaleLinearModel(self, height):
        """
        Returns parameters to a linear model, which can be used to convert metric distances
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
                self.squeezed_fish[key].append((distance, fish.color_ind))
        self.figure.update()

    def updateDetectionImage(self):
        self.figure.updateOverlayedImage(self.detector.vertical_detections, self.squeezed_fish)
        self.figure.update()

        #self.figure.update_lines = True
        #self.figure.max_height = self.maximumHeight()
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
            LogObject().print("Echogram processing error:", e)
            self.data = None

    def clear(self):
        self.data = None

    def getDisplayedImage(self):
        return self.data

class DebugEchoFigure(DebugZQLabel):
    def __init__(self, echo_figure):
        super().__init__(echo_figure)
        self.echo_figure = echo_figure
        #self.echo_figure.afterUserInputSignal.connect(self.update)

    def paintEvent(self, event):
        super().paintEvent(event)

        width = self.size().width()
        height = self.size().height()

        current_frames = self.echo_figure.x_max_limit - self.echo_figure.x_min_limit
        shown_frames = self.echo_figure.shown_x_max_limit - self.echo_figure.shown_x_min_limit

        source_L = max(0, self.echo_figure.x_min_limit - self.echo_figure.shown_x_min_limit)
        source_L = int(source_L / shown_frames * width)

        source_R = max(0, self.echo_figure.shown_x_max_limit - self.echo_figure.x_max_limit)
        source_R = int(source_R / shown_frames * width)

        #target_L = max(0, self.echo_figure.shown_x_min_limit - self.echo_figure.x_min_limit)
        #target_L = int(target_L / current_frames * self.echo_figure.window_width)

        #target_R = max(0, self.echo_figure.x_max_limit - self.echo_figure.shown_x_max_limit)
        #target_R = int(target_R / current_frames * self.echo_figure.window_width)


        #source = QtCore.QRectF(source_L, 0, self.echo_figure.shown_width - source_R, self.echo_figure.shown_height)
        #target = QtCore.QRectF(target_L, 0, self.echo_figure.window_width - target_R, self.echo_figure.window_height)

        painter = QtGui.QPainter(self)
        painter.setPen(QtCore.Qt.green)
        painter.drawLine(QtCore.QLineF(source_L, 0, source_L, height))
        painter.drawLine(QtCore.QLineF(width - source_R, 0, width - source_R, height))




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

    debug_window = QtWidgets.QMainWindow()
    debug_label = DebugEchoFigure(echogram.figure)
    debug_window.setCentralWidget(debug_label)
    debug_window.show()
    debug_window.setWindowTitle("Debug window")
    #debug_window.resize(echogram.figure.image_width, echogram.figure.image_height)
    #debug_window.move(500, 100)

    sys.exit(app.exec_())