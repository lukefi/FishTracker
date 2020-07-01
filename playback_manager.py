import sys, os
from file_handler import FOpenSonarFile
import tkinter as tk
from tkinter import filedialog
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import time

from debug import Debug

"""
TODO:
When a file is opened a new playback thread should be created (currently created when the file is played)
This enables smoother interaction with the playback controls even when the file is not being played.
"""

FRAME_SIZE = 1.5

class PlaybackManager():
    def __init__(self, app, main_window):
        self.sonar = None
        self.path = None

        self.frame_available = Event()
        self.frame_available.append(lambda _: print("Frame: " + str(self.frame_index)))
        self.file_opened = Event()
        self.playback_ended = Event()
        self.frame_index = 0
        self.threadpool = QThreadPool()
        self.main_window = main_window
        self.thread = None
        self.rect = None
        self.buffer = None

        self.bufferSizeMb = 1000

        app.aboutToQuit.connect(self.applicationClosing)

    def open_file(self):
        try:
            root = tk.Tk()
            root.withdraw()
            self.path = filedialog.askopenfilename()
            self.sonar = FOpenSonarFile(self.path)

            self.thread = PlaybackThread(self)
            self.thread.signals.frame_signal.connect(self.displayFrame)
            self.threadpool.start(self.thread)

        except FileNotFoundError as err:
            print(err)

    def openFile(self):
        homeDirectory = str(os.path.expanduser("~"))
        filePathTuple = QFileDialog.getOpenFileName(self.main_window,
                                                    "Open File",
                                                    homeDirectory,
                                                    "Sonar Files (*.aris *.ddf)")
        if filePathTuple[0] != "" : 
            # if the user has actually chosen a specific file.
            self.loadFile(filePathTuple[0])

    def openTestFile(self):
        path = "D:/Projects/VTT/FishTracking/Teno1_2019-07-02_153000.aris"
        if not os.path.exists(path):
            path = "C:/data/LUKE/Teno1_2019-07-02_153000.aris"
        if not os.path.exists(path):
            self.openFile()
            return
        self.loadFile(path)

    def loadFile(self, path):
        self.path = path
        if self.thread:
            self.thread.signals.playback_ended_signal.connect(self.setLoadedFile)
            self.stop()
        else:
            print("No thread active.")
            self.setLoadedFile()

    def closeFile(self):
        if self.thread:
            self.thread.signals.playback_ended_signal.connect(self.clearFile)
            self.stop()
        else:
            print("No thread active.")
            self.clearFile()

    def setLoadedFile(self):
        self.frame_index = 0
        self.sonar = FOpenSonarFile(self.path)
        self.buffer = SonarBuffer(self.sonar.frameCount, int(self.bufferSizeMb / FRAME_SIZE))
        self.main_window.setWindowTitle(self.path)
        self.file_opened(self.sonar)
        self.updateSonar()

    def updateSonar(self):
        self.rect, frame = self.sonar.getFrame(self.frame_index)
        self.frame_available(frame)


    def clearFile(self):
        self.path = ""
        self.sonar = None
        self.frame_index = 0
        self.frame_available(None)

    def showNextImage(self):
        """
        Show the next frame image.
        """
        if self.sonar:
            self.frame_index +=1
            if (self.frame_index >= self.sonar.frameCount):
                self.frame_index  = 0
        
            if self.thread is None:
                self.updateSonar()

    def showPreviousImage(self):
        """
        Show the previous frame image
        """
        if self.sonar:
            self.frame_index  -= 1
            if (self.frame_index  < 0 ):
                self.frame_index  = self.sonar.frameCount-1

            if self.thread is None:
                self.updateSonar()

    def play(self):
        if self.isPlaying():
            self.stop()
        elif self.sonar:
            self.thread = PlaybackThread(self)
            self.thread.signals.frame_signal.connect(self.displayFrame)
            self.thread.signals.rect_signal.connect(self.getRect)
            self.thread.signals.eof_signal.connect(self.endOfFile)
            self.thread.signals.playback_ended_signal.connect(self.playBackEnded)
            self.threadpool.start(self.thread)
            

    def stop(self):
        if self.thread is not None:
            self.thread.is_playing = False
            self.thread = None

    def playBackEnded(self):
        print("Stop")
        self.stop()
        self.playback_ended()

    def endOfFile(self):
        print("EOF")
        self.stop()
        self.playback_ended()


    def displayFrame(self, tuple):
        """
        Called from PlaybackThread to update displayed frame in GUI
        """

        ind, frame = tuple
        print(frame.shape)
        self.frame_index = ind
        if frame is not None:
            self.frame_available(frame)

    def getRect(self, rect):
        self.rect = rect

    def setFrameInd(self, ind):
        if self.sonar:
            self.frame_index = max(0, min(ind, self.sonar.frameCount))
        else:
            self.frame_index = 0

        if self.isPlaying():
            self.thread.ind = self.frame_index
        else:
            #self.displayFrame((ind, self.sonar.getFrame(ind)))
            self.updateSonar()
            

    def isPlaying(self):
        return self.thread is not None and self.thread.is_playing

    def applicationClosing(self):
        print("Closing PlaybackManager . . .")
        self.stop()
        time.sleep(1)

    def getFrameNumberText(self):
        if self.sonar:
            return "Frame: {}/{}".format(self.frame_index+1, self.sonar.frameCount)
        else:
            return "No File Loaded"

    def getBeamDistance(self, x, y):
        if self.sonar:
            return self.sonar.getBeamDistance(x, y)
        else:
            return None

    def setDistanceCompensation(self, value):
        if self.sonar:
            self.sonar.setDistanceCompensation(value)

class SonarBuffer():
    def __init__(self, frame_count, max_frames):
        self.buffer = [None] * frame_count
        self.buffer_size = 0
        self.max_size = max_frames

    def addFrame(self, ind, frame):
        try:
            if self.buffer[ind] is None:
                self.buffer_size += 1
            self.buffer[ind] = frame
        except IndexError:
            print("Frame [{}] out of bounds [{}]".format(ind, len(self.buffer)))

    def clearFrame(self, ind):
        try:
            self.buffer[ind] = None
        except IndexError:
            print("Frame [{}] out of bounds [{}]".format(ind, len(self.buffer)))

class PlaybackSignals(QObject):
    frame_signal = pyqtSignal(tuple)
    rect_signal = pyqtSignal(object)
    playback_ended_signal = pyqtSignal()
    eof_signal = pyqtSignal()

class PlaybackThread(QRunnable):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.sonar = manager.sonar
        self.signals = PlaybackSignals()
        self.fps = 24.0
        self.ind = manager.frame_index
        self.is_playing = True
        print("Init thread")

    def run(self):
        prev_update = time.time()
        target_update = 1. / self.fps

        while self.is_playing:
            rect, frame = self.sonar.getFrame(self.ind)
            if frame is None:
                break

            if self.ind >= self.manager.sonar.frameCount:
                self.signals.eof_signal.emit()
                return

            self.signals.frame_signal.emit((self.ind, frame))
            self.signals.rect_signal.emit(rect)
            self.ind += 1   

            time_since = time.time() - prev_update
            prev_update = time.time()

            if(target_update > time_since):
                time.sleep(max(0, target_update - time_since))

        self.signals.playback_ended_signal.emit()
class Event(list):
    def __call__(self, *args, **kwargs):
        for f in self:
            f(*args, **kwargs)

    def __repr__(self):
        return "Event(%s)" % list.__repr__(self)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    playback_manager.openTestFile()
    playback_manager.play()
    main_window.show()
    sys.exit(app.exec_())