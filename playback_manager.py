from file_handler import FOpenSonarFile
import tkinter as tk
from tkinter import filedialog
from PyQt5.QtCore import *
import time

class PlaybackManager():
    def __init__(self):
        self.sonar = None
        self.path = None

        self.frame_available = Event()
        self.frame_index = 0
        self.threadpool = QThreadPool()

    def open_file(self):
        root = tk.Tk()
        root.withdraw()
        self.path = filedialog.askopenfilename()
        self.sonar = FOpenSonarFile(self.path)

        #self.display_frame(0)
        self.thread = PlaybackThread(self.sonar)
        self.thread.signals.frame_available.connect(self.display_frame)
        self.threadpool.start(self.thread)

        try:
            pass
        except FileNotFoundError as err:
            print("File not found.", err)

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
    playbackManager = PlaybackManager()
    playbackManager.open_file()