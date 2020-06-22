import sys, os
from file_handler import FOpenSonarFile
import tkinter as tk
from tkinter import filedialog
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import time

from debug import Debug

class PlaybackManager():
    def __init__(self, app, main_window):
        self.sonar = None
        self.path = None

        self.frame_available = Event()
        self.frame_available.append(self.printDisplay)
        self.frame_index = 0
        self.threadpool = QThreadPool()
        self.main_window = main_window
        self.thread = None

        self.playing = False

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
            self.path = filePathTuple[0]
            self.sonar = FOpenSonarFile(self.path)
            self.main_window.setWindowTitle(self.path)

    def openTestFile(self):
        self.path = "D:/Projects/VTT/FishTracking/Teno1_2019-07-02_153000.aris"
        if not os.path.exists(self.path):
            self.path = "C:/data/LUKE/Teno1_2019-07-02_153000.aris"
        if not os.path.exists(self.path):
            self.openFile()
            return

        self.sonar = FOpenSonarFile(self.path)
        self.main_window.setWindowTitle(self.path)

    def showNextImage(self):
        """Show the next frame image.
        """
        self.frame_index +=1
        if (self.frame_index >= self.sonar.frameCount):
            self.frame_index  = 0
        
        if self.thread is None:
            self.frame_available(self.sonar.getFrame(self.frame_index))

    def showPreviousImage(self):
        """Show the previous frame image
        """

        self.frame_index  -= 1
        if (self.frame_index  < 0 ):
            self.frame_index  = self.sonar.frameCount-1

        if self.thread is None:
            self.frame_available(self.sonar.getFrame(self.frame_index))

    def play(self):
        self.playing = not self.playing
        if self.playing:
            if self.thread is not None:
                self.thread.exit()
            self.thread = PlaybackThread(self)
            self.thread.signals.frame_signal.connect(self.displayFrame)
            self.thread.signals.eof.connect(self.endOfFile)
            self.threadpool.start(self.thread)

    def displayFrame(self, tuple):
        """Called from PlaybackThread
        """

        ind, frame = tuple
        self.frame_index = ind
        if frame is not None:
            self.frame_available(frame)

    def setFrameInd(self, ind):
        if self.thread is not None:
            self.thread.ind = self.frame_index

        self.frame_index = ind

    def printDisplay(self, _):
        Debug.Log("Frame: " + str(self.frame_index))

    def endOfFile(self):
        self.playing = False

    def applicationClosing(self):
        print("Closing PlaybackManager . . .")
        self.playing = False
        time.sleep(1)

class PlaybackSignals(QObject):
    frame_signal = pyqtSignal(tuple)
    eof = pyqtSignal()

class PlaybackThread(QRunnable):
    def __init__(self, manager):
        super().__init__()
        self.sonar = manager.sonar
        self.manager = manager
        self.signals = PlaybackSignals()
        self.fps = 24.0
        self.ind = manager.frame_index

    def run(self):
        prev_update = time.time()
        target_update = 1. / self.fps

        while self.ind < self.manager.sonar.frameCount and self.manager.playing:
            if (self.ind >= self.sonar.frameCount):
                self.signals.eof.emit()
                break

            frame = self.sonar.getFrame(self.ind)
            if frame is None:
                break

            self.signals.frame_signal.emit((self.ind, frame))
            self.ind += 1

            time_since = time.time() - prev_update
            prev_update = time.time()
            if(target_update > time_since):
                time.sleep(max(0, target_update - time_since))

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