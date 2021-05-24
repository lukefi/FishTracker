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

class PlaybackManager(QObject):

    mapping_done = pyqtSignal()
    # Signals that all polar frames are loaded.
    polars_loaded = pyqtSignal()
    # Called before frame_available
    frame_available_early = pyqtSignal(tuple)
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

        self.mapping_done.connect(lambda: LogObject().print("A"))
        self.polars_loaded.connect(lambda: LogObject().print("B"))
        self.frame_available_early.connect(lambda v: LogObject().print("C"))
        self.frame_available.connect(lambda v: LogObject().print("D"))
        self.file_opened.connect(lambda v: LogObject().print("E"))
        self.playback_ended.connect(lambda: LogObject().print("F"))
        self.file_closed.connect(lambda: LogObject().print("G"))

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

    def openFile(self):
        dir = fh.getLatestDirectory()
        filePathTuple = QFileDialog.getOpenFileName(self.main_window, "Open File", dir, "Sonar Files (*.aris *.ddf)")
        fh.setLatestDirectory(os.path.dirname(filePathTuple[0]))
        self.loadFile(filePathTuple[0])

    def openTestFile(self):
        path = fh.getTestFilePath()
        if path is not None:
            # Override test file length
            self.loadFile(path, 200)
        else:
            self.openFile()

    def loadFile(self, path, overrideLength=-1):
        LogObject().print("LoadFile:", QThread.currentThreadId())
        self.path = path
        self.setTitle(path)
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

    def setLoadedFile(self, sonar):
        self.sonar = sonar
        # Initialize new PlaybackThread
        self.playback_thread = PlaybackThread(self.path, self.sonar, self.thread_pool)

        # Initialize thread process forwarding
        self.playback_thread.signals.start_thread_signal.connect(self.startThread)

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

    def frame_available_f(self, value):
        """
        Forwards signal form PlaybackThread to the two signals below.
        """
        self.frame_available_early.emit(value)
        self.frame_available.emit(value)

    def closeFile(self):
        self.stopAll()

        if self.playback_thread is not None:
            self.playback_thread.clear()
            del self.playback_thread
            self.playback_thread = None

        self.sonar = None
        self.file_closed.emit()
        self.setTitle()

        #self.polar_transform = None

    def setTitle(self, path=""):
        if self.main_window is None:
            return

        if path == "":
            self.main_window.setWindowTitle("FishTracker")
        else:
            self.main_window.setWindowTitle(path)

    def startThread(self, tuple):
        """
        Used to start threads from another thread running in thread_pool.

        Parameter tuple contains:
        thread: Worker object containing the function being executed
        receiver: Function that is attached to signal
        signal: pyqtSignal object triggered (emitted) at some point of the thread and thus calling receiver

        Usually signal is the result signal passing the results to receiver.
        """

        thread, receiver, signal = tuple
        signal.connect(lambda x: receiver(x)) #signal.connect(receiver) <- why this doesn't work?
        self.thread_pool.start(thread)

    def runInThread(self, f):
        """
        Straightforward way to start threads in thread_pool.
        To start threads inside another thread, use startThread instead.
        """

        thread = Worker(f)
        self.thread_pool.start(thread)

    def testSignal(self):
        LogObject().print("TestSignal")
        self.playback_thread.testF()

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
        LogObject().print("Stop")
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

    def getBeamDistance(self, x, y):
        if self.playback_thread and self.playback_thread.polar_transform:
            return self.playback_thread.polar_transform.cart2polMetric(y, x, True)
        else:
            return None

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
        LogObject().print("Closing PlaybackManager . . .")
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

    def pausePolarLoading(self, value):
        if self.playback_thread is not None:
            self.playback_thread.pause_polar_loading = value

            if not self.isPolarsDone():
                if value:
                    LogObject().print("Polar loading paused.")
                else:
                    LogObject().print("Polar loading continued.")

    def isMappingDone(self):
        return self.playback_thread is not None and self.playback_thread.polar_transform is not None

    def isPolarsDone(self):
        return self.playback_thread is not None and self.playback_thread.polars_loaded

class PlaybackSignals(QObject):
    """
    PyQt signals used by PlaybackThread
    """

    # Used to pass processes to a ThreadPool containing the current thread.
    start_thread_signal = pyqtSignal(tuple)

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
        map_worker = Worker(self.createMapping)
        self.signals.start_thread_signal.emit((map_worker, self.mappingDone, map_worker.signals.result))
        polar_worker = Worker(self.loadPolarFrames)
        self.signals.start_thread_signal.emit((polar_worker, self.polarsDone, polar_worker.signals.result))


    def loadPolarFrames(self):
        count = self.sonar.frameCount
        ten_perc = 0.1 * count
        print_limit = 0
        i = 0
        LogObject().print("Polar:", QThread.currentThreadId())
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

    def polarsDone(self, result):
        if self.alive:
            LogObject().print("Loading: 100 %")
            self.polars_loaded = True
            self.signals.polars_loaded_signal.emit()

    def createMapping(self):
        LogObject().print("Mapping:", QThread.currentThreadId())
        radius_limits = (self.sonar.windowStart, self.sonar.windowStart + self.sonar.windowLength)
        height = fh.getSonarHeight()
        beam_angle = 2 * self.sonar.firstBeamAngle/180*np.pi

        return PolarTransform(self.sonar.DATA_SHAPE, height, radius_limits, beam_angle)

    def mappingDone(self, result):
        if self.alive:
            self.polar_transform = result
            self.signals.mapping_done_signal.emit()
            LogObject().print("Polar mapping done")
            self.displayFrame()

    def testF(self):
        LogObject().print("Test")

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
                LogObject().print(e, self.display_ind, "/", len(self.buffer)-1)
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

class Event(list):
    def __call__(self, *args, **kwargs):
        for f in self:
            f(*args, **kwargs)

    def __repr__(self):
        return "Event(%s)" % list.__repr__(self)



if __name__ == "__main__":
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
