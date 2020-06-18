import sys, os
from file_handler import FOpenSonarFile
import tkinter as tk
from tkinter import filedialog
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import time

class PlaybackManager():
    def __init__(self, main_window):
        self.sonar = None
        self.path = None

        self.frame_available = Event()
        self.frame_index = 0
        self.threadpool = QThreadPool()
        self.main_window = main_window

    def open_file(self):
        try:
            root = tk.Tk()
            root.withdraw()
            self.path = filedialog.askopenfilename()
            self.sonar = FOpenSonarFile(self.path)

            #self.display_frame(0)
            self.thread = PlaybackThread(self.sonar)
            self.thread.signals.frame_available.connect(self.display_frame)
            self.threadpool.start(self.thread)
        except FileNotFoundError as err:
            print(err)

    def openFile(self):
        ## DEBUG : remove filePathTuple and uncomment filePathTuple
        # homeDirectory = str(Path.home())
        homeDirectory = str(os.path.expanduser("~"))
        # filePathTuple = ('/home/mghobria/Documents/work/data/data.aris',) # laptop
        # filePathTuple = ('data.aris',) # Home PC & windows Laptop
        # filePathTuple = ('/home/mghobria/Documents/work/data/data 1/data.aris',) # work PC
        # filePathTuple = ("C:\\Users\\mghobria\\Downloads\\data.aris",) # Home PC windows
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

    def display_frame(self, tuple):
        ind, frame = tuple
        self.frame_index = ind
        self.frame_available(frame)

    def display_frame_by_ind(self, ind):
        self.frame_index = ind
        self.frame_available(self.sonar.getFrame(ind))

class PlaybackSignals(QObject):
    frame_available = pyqtSignal(tuple)

class PlaybackThread(QRunnable):
    def __init__(self, sonar):
        super().__init__()
        self.sonar = sonar
        self.signals = PlaybackSignals()
        self.fps = 24.0

    def run(self):
        prev_update = time.time()
        target_update = 1. / self.fps

        for i in range(100):
            self.signals.frame_available.emit((i, self.sonar.getFrame(i)))
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
    playbackManager = PlaybackManager(main_window)
    playbackManager.openFile()