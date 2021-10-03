from PyQt5 import QtCore, QtGui, QtWidgets
from zoomable_qlabel import ZoomableQLabel, DebugZQLabel
import cv2
import numpy as np
from debug import Debug
from log_object import LogObject
from fish_manager import FishEntry, pyqt_palette, pyqt_palette_deep
from background_subtractor import BackgroundSubtractor

class EchoFigure(ZoomableQLabel):
    """
    Class that handles drawing the echogram image. Used in EchogramViewer widget.
    """
    def __init__(self, parent):
        super().__init__(False, True, False)
        self.parent = parent
        self.resetView()
        self.frame_ind = 0
        self.margin = 0
        self.frame_count = 0
        self.detection_opacity = 1

        self.max_height = 500
        self.detection_pixmap = None

        self.shown_x_min_limit = 0
        self.shown_x_max_limit = 1
        self.shown_width = 1
        self.shown_height = 1
        self.shown_zoom = 0

        self.draw_selection_box = False
        self.debug_lines = False

    def frame2xPos(self, value):
        """
        Coverts a frame index to a position on the window.
        """
        try:
            return (value * self.image_width - self.x_min_limit) / (self.x_max_limit - self.x_min_limit) * self.window_width
        except ZeroDivisionError as e:
            LogObject().print(e)
            return 0

    def xPos2Frame(self, value):
        """
        Coverts a position on the window to a frame index.
        """
        try:
            return (value * (self.x_max_limit - self.x_min_limit)/self.window_width + self.x_min_limit) / self.image_width
        except ZeroDivisionError as e:
            LogObject().print(e)
            return 0

    def paintEvent(self, event):
        """
        Draws the playhead and overlays detections and tracks.
        The drawing of the echogram image is handled in the ZoomableQLabel class.
        """
        super().paintEvent(event)

        try:
            h_pos_0 = self.frame2xPos((self.frame_ind) / self.frame_count)
            h_pos_1 = self.frame2xPos((self.frame_ind + 1) / self.frame_count)
        except ZeroDivisionError:
            h_pos_0 = 0
            h_pos_1 = self.frame2xPos(0.01)

        painter = QtGui.QPainter(self)

        if self.parent.detector._show_echogram_detections or self.parent.fish_manager.show_echogram_fish:
            if self.detection_pixmap is not None:
                self.overlayPixmap(painter, self.detection_pixmap)

        # Draw current frame indicator / playhead
        if h_pos_0 < self.window_width:
            painter.setPen(QtCore.Qt.white)
            painter.setBrush(QtCore.Qt.white)
            painter.setOpacity(0.3)
            painter.drawRect(h_pos_0, 0, h_pos_1-h_pos_0, self.window_height)

        if self.draw_selection_box:
            self.paintSelection()

    def overlayPixmap(self, painter, pixmap):
        """
        Overlays given pixmap on top of the drawn image.
        The given pixmap is either cropped to fit the current zoom level or
        scaled down so that the overlayed image aligns with the underlying one.

        This enables reusing a previous image until the image has been refreshed.
        """

        current_frames = self.x_max_limit - self.x_min_limit
        shown_frames = self.shown_x_max_limit - self.shown_x_min_limit

        if pixmap is not None and shown_frames > 0 and current_frames > 0:
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

            if self.debug_lines:
                painter.setPen(QtCore.Qt.green)
                painter.drawLine(QtCore.QLineF(target_L, 0, target_L, self.window_height))
                painter.drawLine(QtCore.QLineF(self.window_width - target_R, 0, self.window_width - target_R, self.window_height))

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

                for height, color_ind, selected in height_color_pairs:
                    pen = QtGui.QPen(pyqt_palette[color_ind])
                    pen.setWidth(2 if selected else 1)
                    painter.setPen(pen)

                    v_pos = self.window_height - (height - v_min) * v_mult
                    painter.drawLine(h_pos_0, v_pos, h_pos_1, v_pos)
                h_pos_0 = h_pos_1
        except ZeroDivisionError:
            pass

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.displayed_image is not None and event.button() == QtCore.Qt.LeftButton:
            modifiers = QtWidgets.QApplication.keyboardModifiers()
            self.draw_selection_box = modifiers == QtCore.Qt.ControlModifier
            if not self.draw_selection_box:
                self.parent.setFrame(self.xPos2Frame(event.x()))

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            self.draw_selection_box = False

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.displayed_image is not None and event.buttons() == QtCore.Qt.LeftButton:
            if not self.draw_selection_box:
                self.parent.setFrame(self.xPos2Frame(event.x()))

    def clear(self):
        super().clear()
        self.detection_pixmap = None
        self.frame_ind = 0

class EchogramViewer(QtWidgets.QWidget):
    """
    Widget containing EchoFigure. Handles communication to PlaybackManager and other
    core classes.
    """
    def __init__(self, playback_manager, detector, fish_manager):
        super().__init__()

        # Contains vertical position of each fish in each frame, as well as the associated
        # color index and a bool indicating  whether the fish is selected or not.
        self.vertical_tracks = []

        self.playback_manager = playback_manager
        self.detector = detector
        self.detector.all_computed_signal.connect(self.updateOverlayedImage)
        self.fish_manager = fish_manager
        self.echogram = None
        self.show_bg_subtracted = False

        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.horizontalLayout.setContentsMargins(0,0,0,0)

        self.fish_manager.updateContentsSignal.connect(self.updateVerticalTracks)
        self.fish_manager.updateContentsSignal.connect(self.setInputUpdateTimer)

        self.figure = EchoFigure(self)
        self.figure.userInputSignal.connect(self.setInputUpdateTimer)
        self.figure.boxSelectSignal.connect(self.onBoxSelect)
        self.horizontalLayout.addWidget(self.figure)

        self.playback_manager.file_opened.connect(self.onFileOpen)
        self.playback_manager.frame_available.connect(self.onImageAvailable)
        self.playback_manager.polars_loaded.connect(lambda: self.playback_manager.runInThread(self.processEchogram))
        self.playback_manager.file_closed.connect(self.onFileClose)

        self.update_timer = None

        # Delay for echohram to update overlayed detections/tracks after user input
        self.update_timer_delay = 100

        self.setLayout(self.horizontalLayout)

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
        If an old timer exists, it is stopped first to avoid updating repeatedly.

        This is used to update overlayed image, which is too heavy to update
        every frame.
        """
        if self.update_timer:
            self.update_timer.stop()
            self.update_timer.deleteLater()
        
        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.updateOverlayedImage)
        self.update_timer.setSingleShot(True)
        self.update_timer.start(self.update_timer_delay)

    def setFrame(self, percentage):
        self.playback_manager.setRelativeIndex(percentage)

    def onFileOpen(self, sonar):
        self.echogram = Echogram(self.playback_manager, sonar.frameCount)
        self.figure.frame_count = sonar.frameCount

    def onFileClose(self):
        if self.figure is not None:
            self.figure.clear()
        if self.echogram is not None:
            self.echogram.clear()
            self.echogram = None
        self.vertical_tracks = []
        self.setInputUpdateTimer()

    def processEchogram(self):
        self.echogram.processBuffer(self.playback_manager.getPolarBuffer())
        self.showBGSubtraction(self.show_bg_subtracted)
        self.figure.resetView()
        self.playback_manager.refreshFrame()

    def showBGSubtraction(self, value):
        self.show_bg_subtracted = value
        if self.echogram is None:
            return
        if self.show_bg_subtracted:
            self.figure.setImage(self.echogram.getBGSubtractedImage())
        else:
            self.figure.setImage(self.echogram.getDisplayedImage())

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
    def updateVerticalTracks(self):
        """
        Iterates through FishManagers fish_list array to update the list of vertical tracks
        (i.e. "squeezed" fish) that are displayed on the echogram.
        """
        if not self.playback_manager.isMappingDone():
            return

        self.vertical_tracks = [[] for fr in range(self.playback_manager.getFrameCount())]

        for ind, fish in enumerate(self.fish_manager.fish_list):
            selected = ind in self.fish_manager.selected_rows
            for key, (tr, _) in fish.tracks.items():
                avg_y, avg_x = FishEntry.trackCenter(tr)
                distance, _ = self.playback_manager.getBeamDistance(avg_x, avg_y, True)
                self.vertical_tracks[key].append((distance, fish.color_ind, selected))

        self.figure.update()

    def updateOverlayedImage(self):
        self.figure.updateOverlayedImage(self.detector.vertical_detections, self.vertical_tracks)
        self.figure.update()

    def onBoxSelect(self, box_positions):
        """
        Converts image coordinates to frame and height measurements
        and selects fish corresponding to those values.
        """
        if not self.figure.draw_selection_box:
            return

        m_pos1, m_pos2 = box_positions
        min_x = min(m_pos1[0], m_pos2[0])
        max_x = max(m_pos1[0], m_pos2[0])
        min_y = min(m_pos1[1], m_pos2[1])
        max_y = max(m_pos1[1], m_pos2[1])

        frame_min = min_x / self.figure.image_width * self.figure.frame_count
        frame_min = max(0, int(frame_min))
        frame_max = max_x / self.figure.image_width * self.figure.frame_count
        frame_max = min(int(frame_max), self.figure.frame_count)

        min_d, max_d = self.playback_manager.getRadiusLimits()
        height_max = min_d + max(0, (1 - min_y / self.figure.image_height)) * (max_d - min_d)
        height_min = min_d + min((1 - max_y / self.figure.image_height), 1) * (max_d - min_d)

        self.fish_manager.selectFromEchogram(frame_min, frame_max, height_min, height_max)


class Echogram():
    """
    Transforms polar frames into an echogram image.
    """
    def __init__(self, image_provider, length):
        self.bg_subtractor = BackgroundSubtractor(self)
        self.bg_subtractor.mog_parameters.nof_bg_frames = 100
        self.bg_subtractor.mog_parameters.mixture_count = 3
        self.data = None
        self.bgs_data = None
        self.length = length

    def processBuffer(self, buffer):
        """
        Calculates the normal echogram image and the background subtracted one.
        The data is transposed only when returning the displayed image
        to allow easier iteration.
        """
        try:
            # Calculate echogram
            buf = [b for b in buffer]
            #buf = [b for b in buffer if b is not None]

            buf = np.asarray(buf, dtype=np.uint8)
            self.data = np.max(buf, axis=2)
            min_v = np.min(self.data)
            max_v = np.max(self.data)
            self.data = (255 / (max_v - min_v) * (self.data - min_v)).astype(np.uint8)

            # Subtract background
            self.bg_subtractor.initMOG()
            self.bgs_data = np.squeeze([self.bg_subtractor.subtractBG(column) for column in self.data])
            self.bgs_data = self.bgs_data.astype(np.uint8)

        except np.AxisError as e:
            LogObject().print("Echogram processing error:", e)
            self.data = None


    def clear(self):
        self.data = None

    def getDisplayedImage(self):
        return self.data.T

    def getBGSubtractedImage(self):
        return self.bgs_data.T

    def getFrameCount(self):
        return self.length

    def getFrame(self, ind):
        """
        Returns the column of echogram corresponding to the given frame index.
        """
        return self.data[ind, :]

class DebugEchoFigure(DebugZQLabel):
    def __init__(self, echo_figure):
        super().__init__(echo_figure)
        self.echo_figure = echo_figure

    def paintEvent(self, event):
        super().paintEvent(event)

        width = self.size().width()
        height = self.size().height()

        w_mult = width / self.echo_figure.frame_count
        source_L = w_mult * self.echo_figure.shown_x_min_limit;
        source_R = w_mult * self.echo_figure.shown_x_max_limit;

        painter = QtGui.QPainter(self)
        painter.setPen(QtCore.Qt.green)
        painter.drawLine(QtCore.QLineF(source_L, 0, source_L, height))
        painter.drawLine(QtCore.QLineF(source_R, 0, source_R, height))




if __name__ == "__main__":
    import sys
    from playback_manager import PlaybackManager, Event

    class TestDetection():
        def __init__(self, x, y):
            self.center = (y, x)

    class TestDetector(QtCore.QObject):
        all_computed_signal = QtCore.pyqtSignal()

        def __init__(self, playback_manager):
            super().__init__()

            self.playback_manager = playback_manager
            self.frameCount = 0
            self.image_height = 0
            self.detections_clearable = True
            self._show_echogram_detections = True
            self.detections = []
            self.vertical_detections = []

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
            self.all_computed_signal.emit()

    class TestFishManager(QtCore.QAbstractTableModel):

        updateContentsSignal = QtCore.pyqtSignal()

        def __init__(self):
            super().__init__()
            self.show_fish = True
            self.show_echogram_fish = True

        def selectFromEchogram(self, frame_min, frame_max, height_min, height_max):
            pass


    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    detector = TestDetector(playback_manager)
    fish_manager = TestFishManager()
    echogram = EchogramViewer(playback_manager, detector, fish_manager)
    echogram.show_bg_subtracted = True
    echogram.figure.debug_lines = True

    playback_manager.openTestFile()

    main_window.setCentralWidget(echogram)
    main_window.show()
    main_window.resize(900,300)

    debug_window = QtWidgets.QMainWindow()
    debug_label = DebugEchoFigure(echogram.figure)
    debug_window.setCentralWidget(debug_label)
    debug_window.show()
    debug_window.setWindowTitle("Debug window")

    sys.exit(app.exec_())