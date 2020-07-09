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
    def __init__(self, app, main_window, figure):
        super().__init__()

        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(8)
        self.playback_thread = None

        self.path = ""
        self.sonar = None

        self.figure = figure
        self.frame_timer = None

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
        self.playback_thread = PlaybackThread(self.path, self.sonar, self.thread_pool, self.figure)
        self.playback_thread.signals.start_thread_signal.connect(self.startThread)
        self.playback_thread.signals.first_frame_signal.connect(self.start)
        self.thread_pool.start(self.playback_thread)
        # self.start()

    def startThread(self, tuple):
        thread, receiver, signal = tuple
        signal.connect(lambda x: receiver(x)) #signal.connect(receiver) <- why this doesn't work?
        # signal.connect(self.testSignal)
        self.thread_pool.start(thread)

    def testSignal(self, param):
        print("TestSignal")

    def start(self):
        print("Start")
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self.playback_thread.displayFrame)
        self.frame_timer.start(1000.0/10) #FPS: 10

    def stop(self):
        if self.frame_timer is not None:
            self.frame_timer.stop()

    def stopAll(self):
        pass

    def applicationClosing(self):
        print("Closing PlaybackManager . . .")
        self.stopAll()
        time.sleep(1)

class FrameBuffer():
    def __init__(self, size, max_size):
        #self.new_polars = []
        #self.new_frames = []
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
        #self.new_frames.append((ind, frame))
        self.buffer[ind] = frame
        self.infos[ind].processed = True

    #def insertNewFrames(self):
    #    while len(self.new_polars) > 0:
    #        ind, frame = self.new_frames.pop(0)
    #        try:
    #            self.buffer[ind].frame = frame
    #            self.frame_count += 1
    #        except IndexError as e:
    #            print(e)

    #    while len(self.new_frames) > 0:
    #        ind, frame = self.new_frames.pop(0)
    #        try:
    #            self.buffer[ind].frame = frame
    #            self.frame_count += 1
    #        except IndexError as e:
    #            print(e)

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
    start_thread_signal = pyqtSignal(tuple)
    first_frame_signal = pyqtSignal()

class PlaybackThread(QRunnable):
    def __init__(self, path, sonar, thread_pool, figure):
        super().__init__()
        self.alive = True
        self.path = path
        self.thread_pool = thread_pool
        self.sonar = sonar
        self.buffer = FrameBuffer(sonar.frameCount, 1000)
        self.signals = PlaybackSignals()

        self.frame_readers = None
        self.frame_reader_count = 0
        self.initFrameReaders()

        self.display_ind = 0
        self.next_to_process_ind = 0
        self.prev_shown = 0
        self.polars_to_process = 0

        self.processing_thread_count = 0

        self.figure = figure

    def initFrameReaders(self):
        self.frame_readers = Queue()
        for i in range(self.thread_pool.maxThreadCount() - 1):
            frame_reader = FrameReader(self.path)
            self.frame_readers.put(frame_reader)

    def run(self):
        self.processPolarFrames()

        self.prev_shown = time.time()

        while self.alive:
            #print("Update")
            self.createProcesses()
            # self.buffer.insertNewFrames()
            # self.buffer.removeExcessFrames()

    def processPolarFrames(self):
        limits = np.linspace(0, self.sonar.frameCount, self.thread_pool.maxThreadCount()).astype(np.int32)
        self.polars_to_process = len(limits) - 1
        for i in range(self.polars_to_process):
            frame_reader = self.frame_readers.get()
            thread = frame_reader.getPolarThread(limits[i], limits[i+1] - limits[i])
            self.signals.start_thread_signal.emit((thread, self.polarReady, thread.signals.frame_array_signal))

        while self.polars_to_process > 0:
            time.sleep(0.5)

        print("All processed!")
        self.signals.first_frame_signal.emit()


    def createProcesses(self):
        #while not self.frame_readers.empty():
        while self.processing_thread_count < 2 * self.thread_pool.maxThreadCount():
            try:
                #if self.buffer[self.next_to_process_ind] is None:
                if not self.buffer.infos[self.next_to_process_ind].processed:
                    # frame_reader = self.frame_readers.get()
                    # thread = frame_reader.getThread(self.next_to_process_ind)
                    thread = ProcessFrameThread2(self.buffer, self.sonar, self.next_to_process_ind)
                    self.signals.start_thread_signal.emit((thread, self.frameReady, thread.signals.frame_signal))
                    self.processing_thread_count += 1

                self.next_to_process_ind += 1
            except IndexError as e:
                print(e)

    def polarReady(self, tuple):
        frame_reader, array = tuple
        self.buffer.polarReady(frame_reader.ind, frame_reader.ind + frame_reader.count, array)
        self.frame_readers.put(frame_reader)
        self.polars_to_process -= 1

    def frameReady(self, tuple):
        self.processing_thread_count -= 1
        ind, frame = tuple
        self.buffer.frameReady(ind, frame)

        #frame_reader, frame = tuple
        #self.buffer.frameReady(frame_reader.ind, frame)
        #self.frame_readers.put(frame_reader)

    def frameReady2(self, tuple):
        ind, frame = tuple
        self.buffer.frameReady(ind, frame)

    def displayFrame(self):
        try:
            if not self.buffer.isFrameReady(self.display_ind):
                return
            frame = self.buffer[self.display_ind]
            t = time.time()
            self.figure.delta_time = t - self.prev_shown
            self.figure.frame_ind = self.display_ind
            self.displayImage(frame)
            self.display_ind += 1

            #self.show_next_frame = max(t, self.show_next_frame + self.frame_time)
            self.prev_shown = t

        except IndexError as e:
            print(e, "Ind:", self.display_ind, "Len:", len(self.buffer.buffer))

    def displayImage(self, image):        
        self.figure.setUpdatesEnabled(False)
        self.figure.clear()
        qformat = QImage.Format_Indexed8
        if len(image.shape)==3:
            if image.shape[2]==4:
                qformat = QImage.Format_RGBA8888
            else:
                qformat = QImage.Format_RGB888

        img = cv2.resize(image, (self.figure.size().width(), self.figure.size().height()))
        img = QImage(img, img.shape[1], img.shape[0], img.strides[0], qformat).rgbSwapped()
        figurePixmap = QPixmap.fromImage(img)
        self.figure.setPixmap(figurePixmap.scaled(self.figure.size(), Qt.KeepAspectRatio))
        self.figure.setAlignment(Qt.AlignCenter)
        self.figure.setUpdatesEnabled(True)

class ProcessSignals(QObject):
    frame_signal = pyqtSignal(tuple)
    frame_array_signal = pyqtSignal(tuple)

class FrameReader():
    def __init__(self, path):
        self.sonar = FOpenSonarFile(path)
        self.ind = 0
        self.count = 0

    def getPolarThread(self, ind, count):
        self.ind = ind
        self.count = count
        thread = ProcessPolarThread(self, ind, count)
        return thread

    def getThread(self, ind):
        self.ind = ind
        self.count = 1
        thread = ProcessFrameThread(self, ind)
        return thread

class ProcessPolarThread(QRunnable):
    def __init__(self, frame_reader, ind, count):
        super().__init__()
        self.signals = ProcessSignals()
        self.ind = ind
        self.count = count
        self.frame_reader = frame_reader

    def run(self):
        print("Start: [{}-{}]".format(self.ind, self.ind + self.count))
        array = [None] * self.count
        for i in range(self.count):
            frame_ind = self.ind + i
            if frame_ind % 100 == 0:
                print(frame_ind)
            array[i] = self.frame_reader.sonar.getPolarFrame(frame_ind)

        self.signals.frame_array_signal.emit((self.frame_reader, array))

class ProcessFrameThread2(QRunnable):
    def __init__(self, buffer, sonar, ind):
        super().__init__()
        self.signals = ProcessSignals()
        self.ind = ind
        self.buffer = buffer
        self.sonar = sonar

    def run(self):
        frame = self.sonar.constructImages(self.buffer[self.ind])
        self.signals.frame_signal.emit((self.ind, frame))

class ProcessFrameThread(QRunnable):
    def __init__(self, frame_reader, ind):
        super().__init__()
        self.signals = ProcessSignals()
        self.ind = ind
        self.frame_reader = frame_reader

    def run(self):
        _, frame = self.frame_reader.sonar.getFrame(self.ind)

        self.signals.frame_signal.emit((self.frame_reader, frame))

class TestFigure(QLabel):
    def __init__(self):
        super().__init__()
        self.figurePixmap = None
        self.frame_ind = 0
        self.delta_time = 1
        self.fps = 1
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

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

    playback_manager = PlaybackManager(app, main_window, figure)
    playback_manager.openTestFile()
    #playback_manager.play()
    main_window.show()
    sys.exit(app.exec_())