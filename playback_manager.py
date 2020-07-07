import sys, os
from file_handler import FOpenSonarFile
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import time

from debug import Debug

FRAME_SIZE = 1.5

class PlaybackManager():
    def __init__(self, app, main_window):
        app.aboutToQuit.connect(self.applicationClosing)

    def openFile(self):
        homeDirectory = str(os.path.expanduser("~"))
        filePathTuple = QFileDialog.getOpenFileName(self.main_window, "Open File", homeDirectory, "Sonar Files (*.aris *.ddf)")
        # if the user has actually chosen a specific file.
        if filePathTuple[0] != "" : 
            self.loadFile(filePathTuple[0])

    def openTestFile(self):
        path = "D:/Projects/VTT/FishTracking/Teno1_2019-07-02_153000.aris"
        if not os.path.exists(path):
            path = "C:/data/LUKE/Teno1_2019-07-02_153000.aris"
        if not os.path.exists(path):
            self.openFile()
            return
        self.loadFile(path)

    def stopAll(self):
        pass

    def applicationClosing(self):
        print("Closing PlaybackManager . . .")
        self.stopAll()
        time.sleep(1)



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