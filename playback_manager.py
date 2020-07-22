import sys, os
from file_handler import FOpenSonarFile
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import cv2, time
import numpy as np
from queue import Queue

from debug import Debug
from polar_transform import PolarTransform

FRAME_SIZE = 1.5

class PlaybackManager(QObject):
    def __init__(self, app, main_window):
        super().__init__()

        self.mapping_done = Event()
        # Event that signals that all polar frames are loaded.
        self.polars_loaded = Event()
        # Event that passes the current frame (cartesian) to all connected functions.
        self.frame_available = Event()
        # Event that passes the current sonar file to all connected functions.
        self.file_opened = Event()
        # Event that signals that playback has been terminated.
        self.playback_ended = Event()

        self.main_window = main_window
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(16)
        self.playback_thread = None

        self.path = ""
        self.sonar = None

        self.frame_timer = None
        self.fps = 30

        app.aboutToQuit.connect(self.applicationClosing)

    def openFile(self):
        homeDirectory = str(os.path.expanduser("~"))
        filePathTuple = QFileDialog.getOpenFileName(self.main_window, "Open File", homeDirectory, "Sonar Files (*.aris *.ddf)")
        if filePathTuple[0] != "" : 
            self.loadFile(filePathTuple[0])

    def openTestFile(self):
        path = "D:/Projects/VTT/FishTracking/Teno1_2019-07-02_153000.aris"
        if not os.path.exists(path):
            path = "C:/data/LUKE/Teno1_2019-07-02_153000.aris"
        if os.path.exists(path):
            self.loadFile(path)
        else:
            self.openFile()

    def loadFile(self, path):
        self.path = path
        if self.playback_thread:
            raise NotImplementedError()

            #print("Stopping existing thread.")
            #self.playback_thread.signals.playback_ended_signal.connect(self.setLoadedFile)
            #self.stopAll()
        else:
            self.setLoadedFile()

    def setLoadedFile(self):
        self.sonar = FOpenSonarFile(self.path)
        self.playback_thread = PlaybackThread(self.path, self.sonar, self.thread_pool)
        self.playback_thread.signals.start_thread_signal.connect(self.startThread)
        # self.playback_thread.signals.first_frame_signal.connect(self.play)
        self.playback_thread.signals.frame_available_signal.connect(self.frame_available)
        self.playback_thread.signals.polars_loaded_signal.connect(self.polars_loaded)
        self.playback_thread.signals.playback_ended_signal.connect(self.stop)
        self.playback_thread.signals.mapping_done_signal.connect(self.mapping_done)
        self.thread_pool.start(self.playback_thread)
        self.file_opened(self.sonar)

    def unloadFile(self):
        self.sonar = None
        #self.polar_transform = None

    def startThread(self, tuple):
        """
        Used to start threads from another thread running in thread_pool.
        """
        thread, receiver, signal = tuple
        signal.connect(lambda x: receiver(x)) #signal.connect(receiver) <- why this doesn't work?
        self.thread_pool.start(thread)

    def testSignal(self):
        print("TestSignal")
        self.playback_thread.testF()

    def play(self):
        """
        Enables frame playback.
        """
        if self.playback_thread and self.playback_thread.polar_transform:
            print("Start")
            self.playback_thread.is_playing = True
            self.showNextImage()
            self.startFrameTimer()

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
        print("Stop")
        if self.playback_thread:
            self.playback_thread.is_playing = False
            self.playback_thread.display_ind = self.playback_thread.last_displayed_ind
        self.playback_ended()

    def stopAll(self):
        pass

    def getFrameNumberText(self):
        if self.playback_thread:
            return "Frame: {}/{}".format(self.playback_thread.display_ind+1, self.sonar.frameCount)
        else:
            return "No File Loaded"

    def getBeamDistance(self, x, y):
        if self.sonar:
            return (0, 0)
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
        print("Closing PlaybackManager . . .")
        self.stopAll()
        time.sleep(1)

    def getFrame(self, i):
        """
        Non threaded option to get cartesinan frames.
        """
        polar = self.playback_thread.buffer[i]
        return self.playback_thread.polar_transform.remap(polar)

    def getFrameCount(self):
        return self.sonar.frameCount

class PlaybackSignals(QObject):
    """
    PyQt signals used by PlaybackThread
    """

    # Used to pass processes to a ThreadPool outside.
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
        self.alive = True
        self.is_playing = False
        self.path = path
        self.thread_pool = thread_pool
        self.sonar = sonar
        self.buffer = [None] * sonar.frameCount
        self.polar_transform = None

        self.last_displayed_ind = -1
        self.display_ind = 0
        self.polars_loaded = False

    def __del__(self):
        print("Playback thread destroyed")

    def run(self):
        map_worker = Worker(self.createMapping)
        self.signals.start_thread_signal.emit((map_worker, self.mappingDone, map_worker.signals.result))
        polar_worker = Worker(self.loadPolarFrames)
        self.signals.start_thread_signal.emit((polar_worker, self.polarsDone, polar_worker.signals.result))

        #while self.alive:
        #    if not self.is_playing and self.last_displayed_ind != self.display_ind and self.polar_transform:
        #        self.displayFrame()
        #        time.sleep(0.05)

    def loadPolarFrames(self):
        print("Start: [{}-{}]".format(0, self.sonar.frameCount))
        for i in range(self.sonar.frameCount):
            if i % 100 == 0:
                print(i)
            self.buffer[i] = self.sonar.getPolarFrame(i)

    def polarsDone(self, result):
        print("Polar frames loaded")
        self.signals.polars_loaded_signal.emit()
        self.polars_loaded = True

        #frame = self.polar_transform.remap(self.buffer[0])
        #self.signals.frame_available_signal.emit((0, frame))

    def createMapping(self):
        radius_limits = (self.sonar.windowStart, self.sonar.windowStart + self.sonar.windowLength)
        return PolarTransform(self.sonar.DATA_SHAPE, 1200, radius_limits, 2 * self.sonar.firstBeamAngle/180*np.pi)

    def mappingDone(self, result):
        self.polar_transform = result
        self.signals.mapping_done_signal.emit()
        print("Polar mapping done")
        self.displayFrame()

    def testF(self):
        print("Test")

    def displayFrame(self):
        if self.last_displayed_ind != self.display_ind:
            try:
                polar = self.buffer[self.display_ind]
                if polar is not None:
                    frame = self.polar_transform.remap(polar)
                    self.signals.frame_available_signal.emit((self.display_ind, frame))
                    self.last_displayed_ind = self.display_ind

                    if self.is_playing:
                        self.display_ind += 1

            except IndexError as e:
                print(e, self.display_ind, "/", len(self.buffer)-1)
                self.signals.playback_ended_signal.emit()


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
    def __init__(self):
        super().__init__()
        self.figurePixmap = None
        self.frame_ind = 0
        self.delta_time = 1
        self.fps = 1
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.prev_shown = 0

    def displayImage(self, tuple):
        self.frame_ind, image = tuple
        print(self.frame_ind)

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




class Event(list):
    def __call__(self, *args, **kwargs):
        for f in self:
            f(*args, **kwargs)

    def __repr__(self):
        return "Event(%s)" % list.__repr__(self)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = QMainWindow()
    figure = TestFigure()
    main_window.setCentralWidget(figure)

    playback_manager = PlaybackManager(app, main_window)
    playback_manager.openTestFile()
    playback_manager.frame_available.append(figure.displayImage)
    playback_manager.playback_thread.signals.mapping_done_signal.connect(lambda: playback_manager.play())
    main_window.show()
    sys.exit(app.exec_())