"""
This file is part of Fish Tracker.
Copyright 2021, VTT Technical research centre of Finland Ltd.
Developed by: Mikael Uimonen.

Fish Tracker is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Fish Tracker is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Fish Tracker.  If not, see <https://www.gnu.org/licenses/>.
"""

import sys, os, errno
import traceback
import file_handler as fh
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import cv2, time
import numpy as np
from queue import Queue
import gc

from debug import Debug
from polar_transform import PolarTransform
from log_object import LogObject

FRAME_SIZE = 1.5

class Event(list):
    def __call__(self, *args, **kwargs):
        for f in self:
            f(*args, **kwargs)

    def __repr__(self):
        return "Event(%s)" % list.__repr__(self)

class PlaybackManager(QObject):

    # Signals that polar mapping is done and a PolarTransform object is created
    mapping_done = pyqtSignal()
    # Signals that all polar frames are loaded.
    polars_loaded = pyqtSignal()
    # Called before frame_available. This is done in the main thread for every frame, no heavy calculation here.
    frame_available_immediate = Event()
    # Signal that passes the current frame (cartesian) to all connected functions.
    frame_available = pyqtSignal(tuple)
    # Signal that passes the current sonar file to all connected functions.
    file_opened = pyqtSignal(fh.FSONAR_File)
    # Signals that playback has been terminated.
    playback_ended = pyqtSignal()
    # Signals that the current session has been terminated.
    file_closed = pyqtSignal()

    def __init__(self, app, main_window):
        super().__init__()

        self.main_window = main_window
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(16)
        self.playback_thread = None

        self.path = ""
        self.sonar = None
        self.setTitle()

        self.frame_timer = None
        self.fps = 30

        app.aboutToQuit.connect(self.applicationClosing)

    def openFile(self, open_path=None, selected_filter="Sonar Files (*.aris *.ddf)", update_conf=True):
        """
        Select .aris file using QFileDialog
        """
        open_path = open_path if open_path is not None else fh.getLatestDirectory()
        file_path_tuple = QFileDialog.getOpenFileName(self.main_window, "Open File", open_path, selected_filter)
        if update_conf:
            fh.setLatestDirectory(os.path.dirname(file_path_tuple[0]))
        self.loadFile(file_path_tuple[0])

    def selectSaveDirectory(self, open_path=None, selected_filter=QFileDialog.ShowDirsOnly, update_conf=True):
        """
        Select save directory using QFileDialog
        """
        open_path = open_path if open_path is not None else fh.getLatestSaveDirectory()
        print(selected_filter)
        path = QFileDialog.getExistingDirectory(self.main_window, "Select directory", open_path, selected_filter)
        if update_conf:
            fh.setLatestSaveDirectory(path)
        return path

    def selectSaveFile(self, open_path=None, selected_filter="", update_conf=True):
        """
        Select a file for saving detections or tracking results using QFileDialog
        """
        open_path = open_path if open_path is not None else fh.getLatestSaveDirectory()
        file_path_tuple = QFileDialog.getSaveFileName(self.main_window, "Save file", open_path, selected_filter)
        if update_conf:
            fh.setLatestSaveDirectory(os.path.dirname(file_path_tuple[0]))
        return file_path_tuple[0]

    def selectLoadFile(self, open_path=None, selected_filter="", update_conf=True):
        """
        Select a detection or tracking result file to be loaded using QFileDialog
        """
        open_path = open_path if open_path is not None else fh.getLatestSaveDirectory()
        file_path_tuple = QFileDialog.getOpenFileName(self.main_window, "Load File", open_path, selected_filter)
        if update_conf:
            fh.setLatestSaveDirectory(os.path.dirname(file_path_tuple[0]))
        return file_path_tuple[0]

    def openTestFile(self):
        path = fh.getTestFilePath()
        if path is not None:
            # Override test file length
            self.loadFile(path, 1000)
        else:
            self.openFile()

    def loadFile(self, path, overrideLength=-1):
        sonar = fh.FOpenSonarFile(path)
        if overrideLength > 0:
            sonar.frameCount = min(overrideLength, sonar.frameCount)

        if self.playback_thread:
            #LogObject().print("Stopping existing thread.")
            #self.playback_thread.signals.playback_ended_signal.connect(self.setLoadedFile)
            self.closeFile()
            self.setLoadedFile(sonar)
        else:
            self.setLoadedFile(sonar)

        self.path = path
        self.setTitle(path)
        LogObject().print(f"Opened file '{path}'")

    def setLoadedFile(self, sonar):
        self.sonar = sonar
        #self.fps = sonar.frameRate

        # Initialize new PlaybackThread
        self.playback_thread = PlaybackThread(self.path, self.sonar, self.thread_pool)

        # Initialize frame forwarding
        self.playback_thread.signals.frame_available_signal.connect(self.frame_available_f)

        # Initialize other signals
        self.playback_thread.signals.polars_loaded_signal.connect(self.polars_loaded)
        self.playback_thread.signals.playback_ended_signal.connect(self.stop)
        self.playback_thread.signals.mapping_done_signal.connect(self.mapping_done)
        self.thread_pool.start(self.playback_thread)

        # Start 
        self.file_opened.emit(self.sonar)
        self.startFrameTimer()

    def checkLoadedFile(self, path, secondary_path="", override_open=True):
        """
        Checks if file with matching base name is already open. If not,
        tries to open file at path, then at secondary_path and if neither exists,
        opens a file dialog for selecting the correct .aris file.
        Returns True, if file is already open, otherwise False.
        """
        if os.path.basename(self.path) == os.path.basename(path):
            return True
        
        if override_open:
            if os.path.exists(path):
                self.loadFile(path)
                return False
            elif secondary_path != "" and os.path.exists(secondary_path):
                self.loadFile(secondary_path)
                return False
            else:
                self.openFile()
                return False



    def frame_available_f(self, value):
        """
        Forwards signal form PlaybackThread to the two signals below.
        """
        #self.frame_available_early.emit(value)
        self.frame_available_immediate(value)
        self.frame_available.emit(value)

    def closeFile(self):
        self.stopAll()

        if self.playback_thread is not None:
            self.playback_thread.clear()
            del self.playback_thread
            self.playback_thread = None

        self.sonar = None
        LogObject().print(f"Closed file '{self.path}'")
        self.path = ""
        self.setTitle()
        self.file_closed.emit()

        #self.polar_transform = None

    def getFileName(self, extension=True):
        if self.path == "":
            return ""
        basename = os.path.basename(self.path)
        if extension:
            return basename
        else:
            return basename.split('.')[0]

    def setTitle(self, path=""):
        if self.main_window is None:
            return

        if path == "":
            self.main_window.setWindowTitle("FishTracker")
        else:
            self.main_window.setWindowTitle(path)

    def runInThread(self, f):
        """
        Run threads in thread_pool.
        """

        thread = Worker(f)
        self.thread_pool.start(thread)

    def play(self):
        """
        Enables frame playback.
        """
        if self.playback_thread and self.playback_thread.polar_transform:
            LogObject().print("Start")
            #print("F:", sys.getrefcount(self.playback_thread))
            self.playback_thread.is_playing = True
            self.showNextImage()

    def startFrameTimer(self):
        """
        Used to start frame_timer, the main pipeline for displaying frames.
        """
        if self.frame_timer is None:
            self.frame_timer = QTimer(self)
            self.frame_timer.timeout.connect(self.displayFrame)
            self.frame_timer.start(1000.0 / self.fps)


    def displayFrame(self):
        """
        Reroutes the displayFrame function for frame_timer.
        Signal progression might stop abruptly otherwise.
        """
        if self.playback_thread:
            self.playback_thread.displayFrame()

    def refreshFrame(self):
        """
        Used for one time refreshing only.
        """
        if self.playback_thread:
            self.playback_thread.last_displayed_ind = -1
            self.playback_thread.displayFrame()

    def togglePlay(self):
        """
        UI function that toggles playback.
        """
        if self.playback_thread:
            if self.playback_thread.is_playing:
                self.stop()
            else:
                self.play()

    def showNextImage(self):
        """
        Shows next frame without entering play mode.
        """
        if self.playback_thread:
            ind = self.playback_thread.last_displayed_ind + 1
            if ind >= self.sonar.frameCount:
                ind = 0
            self.setFrameInd(ind)

    def showPreviousImage(self):
        """
        Shows previous frame without entering play mode.
        """
        if self.playback_thread:
            ind = self.playback_thread.display_ind - 1
            if ind < 0:
                ind = self.sonar.frameCount - 1
            self.setFrameInd(ind)

    def getFrameInd(self):
        """
        Returns the index of the current frame being displayed.
        """
        if self.playback_thread:
            return self.playback_thread.display_ind
        else:
            return 0

    def setFrameInd(self, ind):
        """
        Sets the index of the frame that is displayed next.
        """
        if self.playback_thread:
            frame_ind = max(0, min(ind, self.sonar.frameCount - 1))
            self.playback_thread.display_ind = frame_ind
            self.playback_thread.next_to_process_ind = frame_ind

    def getPolarBuffer(self):
        if self.playback_thread:
            return self.playback_thread.buffer
        else:
            return None

    def stop(self):
        LogObject().print2("Stop")
        if self.playback_thread:
            self.playback_thread.is_playing = False
            self.playback_thread.display_ind = self.playback_thread.last_displayed_ind
        self.playback_ended.emit()

    def stopAll(self):
        self.stop()
        if self.frame_timer is not None:
            self.frame_timer.timeout.disconnect(self.displayFrame)
            self.frame_timer.stop()
            self.frame_timer = None

    def getFrameNumberText(self):
        if self.playback_thread:
            return "Frame: {}/{}".format(self.playback_thread.display_ind+1, self.sonar.frameCount)
        else:
            return "No File Loaded"

    def getRadiusLimits(self):
        return self.playback_thread.polar_transform.radius_limits

    def getBeamDistance(self, x, y, invert=True):
        """
        Transforms cartesian coordinates to polar coordinates in metric units,
        using the current PolarTransform.
        
        Note: Use isMappingDone to check if this function can be used.

        Returns: (distance, angle)
        """
        return self.playback_thread.polar_transform.cart2polMetric(y, x, invert)

    def isPlaying(self):
        return self.playback_thread is not None and self.playback_thread.is_playing

    def setDistanceCompensation(self, value):
        pass

    def getRelativeIndex(self):
        if self.playback_thread:
            return float(self.playback_thread.display_ind) / self.sonar.frameCount
        else:
            return 0


    def setRelativeIndex(self, value):
        if self.sonar:
            self.setFrameInd(int(value * self.sonar.frameCount))

    def applicationClosing(self):
        LogObject().print2("Closing PlaybackManager . . .")
        self.stopAll()
        time.sleep(1)

    def getFrame(self, i):
        """
        Non-threaded option to get cartesinan frames.
        """
        polar = self.playback_thread.buffer[i]
        if polar is None:
            polar = self.sonar.getPolarFrame(i)
            self.playback_thread.buffer[i] = polar
        return self.playback_thread.polar_transform.remap(polar)

    def getFrameCount(self):
        if self.sonar:
            return self.sonar.frameCount
        else:
            return 0

    def getRecordFrameRate(self):
        """
        Return frame rate of the recording (ARIS file).
        Note that this might differ from the playback frame rate.
        """
        if self.sonar:
            return self.sonar.frameRate
        else:
            return None

    def getImageShape(self):
        """
        Returns (width, height) of the cartesian image in pixels.
        """
        if self.playback_thread and self.playback_thread.polar_transform:
            shape = self.playback_thread.polar_transform.cart_shape
            return shape[1], shape[0]
        else:
            return None

    def getPixelsPerMeter(self):
        """
        Return the conversion rate from world (meters) to image (pixels)
        """
        if self.playback_thread and self.playback_thread.polar_transform:
            return self.playback_thread.polar_transform.pixels_per_meter
        else:
            return None

    def pausePolarLoading(self, value):
        if self.playback_thread is not None:
            self.playback_thread.pause_polar_loading = value

            if not self.isPolarsDone():
                if value:
                    LogObject().print2("Polar loading paused.")
                else:
                    LogObject().print2("Polar loading continued.")

    def isMappingDone(self):
        return self.playback_thread is not None and self.playback_thread.polar_transform is not None

    def isPolarsDone(self):
        return self.playback_thread is not None and self.playback_thread.polars_loaded

class PlaybackSignals(QObject):
    """
    PyQt signals used by PlaybackThread
    """

    # Signals that playback can be started (cartesian mapping created).
    mapping_done_signal = pyqtSignal()

    # Signals that all polar frames have been read to memory.
    polars_loaded_signal = pyqtSignal()

    # Used to pass the current frame.
    frame_available_signal = pyqtSignal(tuple)

    # Signals that playback has ended.
    playback_ended_signal = pyqtSignal()

class PlaybackThread(QRunnable):
    """
    A QRunnable class, that is created when a new .aris-file is loaded.
    It keeps track of the currently displayed frame and makes sure that new frames
    are processed before / when they are needed.

    Pausing does not stop this thread, since it is necessary for smoother interaction with UI.
    """
    def __init__(self, path, sonar, thread_pool):
        super().__init__()
        self.signals = PlaybackSignals()
        self.is_playing = False
        self.path = path
        self.thread_pool = thread_pool
        self.sonar = sonar
        self.buffer = [None] * sonar.frameCount
        self.polar_transform = None

        self.last_displayed_ind = -1
        self.display_ind = 0
        self.polars_loaded = False

        self.pause_polar_loading = False

        self.alive = True

    def __del__(self):
        #print("Playback thread destroyed")
        pass

    def run(self):
        pt = self.createMapping()
        self.mappingDone(pt)

        self.loadPolarFrames()
        self.polarsDone()


    def loadPolarFrames(self):
        count = self.sonar.frameCount
        ten_perc = 0.1 * count
        print_limit = 0
        i = 0
        while i < count and self.alive:
            if self.pause_polar_loading:
                time.sleep(0.1)
                continue

            if i > print_limit:
                LogObject().print("Loading:", int(float(print_limit) / count * 100), "%")
                print_limit += ten_perc
            if self.buffer[i] is None:
                value = self.sonar.getPolarFrame(i)
                if self.alive:
                    self.buffer[i] = value
            i += 1

    def polarsDone(self):
        if self.alive:
            LogObject().print("Loading: 100 %")
            self.polars_loaded = True
            self.signals.polars_loaded_signal.emit()

    def createMapping(self):
        radius_limits = (self.sonar.windowStart, self.sonar.windowStart + self.sonar.windowLength)
        height = fh.getSonarHeight()
        beam_angle = 2 * self.sonar.firstBeamAngle/180*np.pi

        return PolarTransform(self.sonar.DATA_SHAPE, height, radius_limits, beam_angle)

    def mappingDone(self, result):
        if self.alive:
            self.polar_transform = result
            self.signals.mapping_done_signal.emit()
            self.displayFrame()

    def displayFrame(self):
        if self.last_displayed_ind != self.display_ind:
            try:
                polar = self.buffer[self.display_ind]
                if polar is not None and self.polar_transform is not None:
                    frame = self.polar_transform.remap(polar)
                    self.signals.frame_available_signal.emit((self.display_ind, frame))
                    self.last_displayed_ind = self.display_ind

                    if self.is_playing:
                        self.display_ind += 1

            except IndexError as e:
                LogObject().print2(e, self.display_ind, "/", len(self.buffer)-1)
                self.signals.playback_ended_signal.emit()

    def clear(self):
        self.alive = False
        self.buffer = None
        self.polar_transform = None


class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)


class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()

        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done


class TestFigure(QLabel):
    def __init__(self, play_f, reload_f=None):
        super().__init__()
        self.figurePixmap = None
        self.frame_ind = 0
        self.delta_time = 1
        self.fps = 1
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.prev_shown = 0
        self.toggle_play = play_f
        self.reload_file = reload_f
        self.setFocusPolicy(Qt.StrongFocus)

    def displayImage(self, tuple):
        if tuple is None:
            self.clear()
            return

        self.frame_ind, image = tuple
        LogObject().print("TF Frame:", self.frame_ind)

        t = time.time()
        self.delta_time = t - self.prev_shown
        self.prev_shown = t

        self.setUpdatesEnabled(False)
        self.clear()
        qformat = QImage.Format_Indexed8
        if len(image.shape)==3:
            if image.shape[2]==4:
                qformat = QImage.Format_RGBA8888
            else:
                qformat = QImage.Format_RGB888

        img = cv2.resize(image, (self.size().width(), self.size().height()))
        img = QImage(img, img.shape[1], img.shape[0], img.strides[0], qformat).rgbSwapped()
        figurePixmap = QPixmap.fromImage(img)
        self.setPixmap(figurePixmap.scaled(self.size(), Qt.KeepAspectRatio))
        self.setAlignment(Qt.AlignCenter)
        self.setUpdatesEnabled(True)

    def resizeEvent(self, event):
        if isinstance(self.figurePixmap, QPixmap):
            self.setPixmap(self.figurePixmap.scaled(self.size(), Qt.KeepAspectRatio))

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setPen(Qt.red)
        point = QPoint(10,20)
        painter.drawText(point, str(self.frame_ind))

        if self.delta_time != 0:
            self.fps = 0.3 * (1.0 / self.delta_time) + 0.7 * self.fps
        point = QPoint(10,50)
        painter.drawText(point, "{:.1f}".format(self.fps))

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if event.key() == Qt.Key_Space:
            self.toggle_play()
        elif event.key() == Qt.Key_T and self.reload_file is not None:
            self.reload_file()
        event.accept()


if __name__ == "__main__":
    def playback_test():
        def loadFile():
            playback_manager.openTestFile()
            playback_manager.playback_thread.signals.mapping_done_signal.connect(lambda: playback_manager.play())

        app = QApplication(sys.argv)
        main_window = QMainWindow()

        playback_manager = PlaybackManager(app, main_window)
        figure = TestFigure(playback_manager.togglePlay, loadFile)
        playback_manager.frame_available.connect(figure.displayImage)
        main_window.setCentralWidget(figure)

        loadFile()

        main_window.show()
        sys.exit(app.exec_())

    def benchmark_loading():
        app = QApplication(sys.argv)
        main_window = QMainWindow()

        playback_manager = PlaybackManager(app, main_window)
        path = fh.getTestFilePath()
        sonar = fh.FOpenSonarFile(path)
        sonar.frameCount = min(1000, sonar.frameCount)
        playback_thread = PlaybackThread(path, sonar, playback_manager.thread_pool)
        playback_thread.loadPolarFrames()

    playback_test()
    #benchmark_loading()
