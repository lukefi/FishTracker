import sys, os
from file_handler import FOpenSonarFile
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import cv2, time
import numpy as np
from queue import Queue

from debug import Debug

FRAME_SIZE = 1.5

class PlaybackManager(QObject):
    def __init__(self, app, main_window):
        super().__init__()

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

        self.frame_timer = QTimer(self)
        self.fps = 10

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
        self.playback_thread.signals.first_frame_signal.connect(self.play)
        self.playback_thread.signals.frame_available_signal.connect(self.frame_available)
        self.thread_pool.start(self.playback_thread)
        self.file_opened(self.sonar)

    def startThread(self, tuple):
        thread, receiver, signal = tuple
        signal.connect(lambda x: receiver(x)) #signal.connect(receiver) <- why this doesn't work?
        # signal.connect(self.testSignal)
        self.thread_pool.start(thread)

    def testSignal(self, param):
        print("TestSignal")

    def play(self):
        if self.playback_thread:
            print("Start")
            self.playback_thread.is_playing = True
            self.frame_timer.timeout.connect(self.playback_thread.displayFrame)
            self.frame_timer.start(1000.0 / self.fps)

    def togglePlay(self):
        if self.playback_thread:
            if self.playback_thread.is_playing:
                self.stop()
            else:
                self.play()

    def showNextImage(self):
        if self.playback_thread:
            ind = self.playback_thread.display_ind + 1
            if ind >= self.sonar.frameCount:
                ind = 0
            self.setFrameInd(ind)

    def showPreviousImage(self):
        if self.playback_thread:
            ind = self.playback_thread.display_ind - 1
            if ind < 0:
                ind = self.sonar.frameCount - 1
            self.setFrameInd(ind)

    def getFrameInd(self):
        if self.playback_thread:
            return self.playback_thread.display_ind
        else:
            return 0

    def setFrameInd(self, ind):
        if self.playback_thread:
            frame_ind = max(0, min(ind, self.sonar.frameCount - 1))
            self.playback_thread.display_ind = frame_ind
            self.playback_thread.next_to_process_ind = frame_ind

    def stop(self):
        if self.playback_thread:
            self.playback_thread.is_playing = False
        self.frame_timer.stop()
        self.playback_ended()

    def stopAll(self):
        pass

    def getFrameNumberText(self):
        if self.playback_thread:
            return "Frame: {}/{}".format(self.frame_index+1, self.sonar.frameCount)
        else:
            return "No File Loaded"

    def isPlaying(self):
        return self.playback_thread is not None and self.playback_thread.is_playing

    def applicationClosing(self):
        print("Closing PlaybackManager . . .")
        self.stopAll()
        time.sleep(1)

class FrameBuffer():
    """
    Stores all the frames for faster access.
    In first iteration the frames are stored as they are read (polar coordinates).
    Later they are converted to cartesian coordinates, which is a process that consumes time the most.
    """
    def __init__(self, size, max_size):
        self.buffer = [None] * size
        self.infos = [None] * size
        self.max_size = max_size
        self.frame_count = 0
        self.first_ind = 0
        self.last_ind = 0

        for i in range(size):
            self.infos[i] = FrameInfo(i)

    def polarReady(self, min_ind, max_ind, array):
        print("Polar ready: [{}-{}]".format(min_ind, max_ind))
        self.buffer[min_ind:max_ind] = array

    def frameReady(self, ind, frame):
        print("Ready:", ind)
        self.buffer[ind] = frame
        self.infos[ind].processed = True

    def isFrameReady(self, ind):
        return self.infos[ind].processed

    def removeExcessFrames(self):
        while self.frame_count > self.max_size:
            self.removeFirst()

    def removeFirst(self):
        new_first = self.buffer[self.first_ind].next
        self.buffer[self.first_ind].frame = None
        self.first_ind = new_first
        self.frame_count -= 1

    def __getitem__(self, key):
        return self.buffer[key]

class FrameInfo:
    """
    Stores information about whether the frame is already converted to cartesian coordinates or not
    and the order of the conversion. The order might change depending on which frames are played first,
    and it is used when removing frames if the maximum frame capacity is exceeded.
    """
    def __init__(self, ind):
        self.ind = ind
        self.next = 0
        self.processed = False

    def __repr__(self):
        if self.processed:
            return "FW " + str(self.ind)
        else:
            return "Empty"

class PlaybackSignals(QObject):
    """
    PyQt signals used by PlaybackThread
    """
    # Used to pass processes to a ThreadPool outside.
    start_thread_signal = pyqtSignal(tuple)

    # Signals that playback can be started.
    first_frame_signal = pyqtSignal()

    # Used to pass the current frame.
    frame_available_signal = pyqtSignal(tuple)

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
        self.buffer = FrameBuffer(sonar.frameCount, 1000)

        self.last_displayed_ind = 0
        self.display_ind = 0
        self.next_to_process_ind = 0
        self.polars_to_process = 0

        self.processing_thread_count = 0

    def run(self):
        self.processPolarFrames()
        while self.alive:
            self.manageFrameProcesses()
            # self.buffer.removeExcessFrames()

            if not self.is_playing and self.last_displayed_ind != self.display_ind:
                self.displayFrame()


    def processPolarFrames(self):
        limits = np.linspace(0, self.sonar.frameCount, self.thread_pool.maxThreadCount()).astype(np.int32)
        self.polars_to_process = len(limits) - 1
        for i in range(self.polars_to_process):
            thread = ProcessPolarThread(self.path, limits[i], limits[i+1] - limits[i])
            self.signals.start_thread_signal.emit((thread, self.polarReady, thread.signals.frame_array_signal))

        while self.polars_to_process > 0:
            time.sleep(0.5)

        print("All processed!")
        self.signals.first_frame_signal.emit()


    def manageFrameProcesses(self):
        while self.processing_thread_count < self.thread_pool.maxThreadCount():
            try:
                if not self.buffer.infos[self.next_to_process_ind].processed:
                    thread = ProcessFrameThread(self.buffer, self.sonar, self.next_to_process_ind)
                    self.signals.start_thread_signal.emit((thread, self.frameReady, thread.signals.frame_signal))
                    self.processing_thread_count += 1

                self.next_to_process_ind += 1
            except IndexError as e:
                print(e)

    def polarReady(self, tuple):
        self.buffer.polarReady(*tuple)
        self.polars_to_process -= 1

    def frameReady(self, tuple):
        self.processing_thread_count -= 1
        ind, frame = tuple
        self.buffer.frameReady(ind, frame)

    def displayFrame(self):
        try:
            if not self.buffer.isFrameReady(self.display_ind):
                return
            frame = self.buffer[self.display_ind]
            self.signals.frame_available_signal.emit((self.display_ind, frame))
            self.last_displayed_ind = self.display_ind

            if self.is_playing:
                self.display_ind += 1

        except IndexError as e:
            print(e, "Ind:", self.display_ind, "Len:", len(self.buffer.buffer))

class ProcessSignals(QObject):
    """
    PyQt signals used by processing threads.
    """
    frame_signal = pyqtSignal(tuple)
    frame_array_signal = pyqtSignal(tuple)

class ProcessPolarThread(QRunnable):
    """
    A QRunnable class that reads a range of frames in polar coordinates.
    """
    def __init__(self, path, ind, count):
        super().__init__()
        self.signals = ProcessSignals()
        self.ind = ind
        self.count = count
        self.sonar = FOpenSonarFile(path)

    def run(self):
        print("Start: [{}-{}]".format(self.ind, self.ind + self.count))
        array = [None] * self.count
        for i in range(self.count):
            frame_ind = self.ind + i
            if frame_ind % 100 == 0:
                print(frame_ind)
            array[i] = self.sonar.getPolarFrame(frame_ind)

        self.signals.frame_array_signal.emit((self.ind, self.ind + self.count, array))

class ProcessFrameThread(QRunnable):
    """
    A QRunnable class that converts a single frame from polar to cartesian coordinates.
    """
    def __init__(self, buffer, sonar, ind):
        super().__init__()
        self.signals = ProcessSignals()
        self.ind = ind
        self.buffer = buffer
        self.sonar = sonar

    def run(self):
        frame = self.sonar.constructImages(self.buffer[self.ind])
        self.signals.frame_signal.emit((self.ind, frame))

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
        painter.drawText(point, str(self.fps))




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
    #playback_manager.play()
    main_window.show()
    sys.exit(app.exec_())