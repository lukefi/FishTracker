import sys, os, cv2
import argparse, time
from queue import Queue
from PyQt5 import QtCore, QtGui, QtWidgets

from playback_manager import PlaybackManager, TestFigure
from detector import Detector
from tracker import Tracker

def getDefaultParser(getArgs=False):
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--display', default=False, action='store_true', help="display frames as the patch is processed")
    parser.add_argument('-f', '--file', type=argparse.FileType('r'), nargs='*', help=".aris file(s) to be processed")
    parser.add_argument('-t', '--test', default=False, action='store_true', help="use test file (if exists)")
    if getArgs:
        return parser.parse_args()
    else:
        return parser

def getFiles(args):
    files = []
    if args.file:
         files = [f.name for f in args.file]
    elif args.test:
        files = [PlaybackManager.getTestFilePath()]
    else:
        homeDirectory = str(os.path.expanduser("~"))
        filePathTuple = QtWidgets.QFileDialog.getOpenFileNames(None, "Open File", homeDirectory, "Sonar Files (*.aris *.ddf)")
        files = [f for f in filePathTuple[0]]

    return files

class TrackProcess(QtCore.QObject):
    """
    TrackProcess launches individual PlaybackManager, Detector and Tracker.
    These are used for the tracking process of the file provided in the method track.
    Each file should be processed with their own TrackProcess instances.
    """
    def __init__(self, app, display, file):
        super().__init__()
        self.app = app
        self.display = display
        self.figure = None
        self.file = file

        if display:
            self.main_window = QtWidgets.QMainWindow()
        else:
            self.main_window = None

        self.playback_manager = PlaybackManager(self.app, self.main_window)

        self.detector = Detector(self.playback_manager)
        self.tracker = Tracker(self.detector)
        self.playback_manager.fps = 100

        print("Process created for file: ", self.file)

    def forwardImage(self, tuple):
        ind, frame = tuple
        detections = self.detector.getDetection(ind)

    def forwardImageDisplay(self, tuple):
        ind, frame = tuple
        detections = self.detector.getDetection(ind)

        image = cv2.applyColorMap(frame, cv2.COLORMAP_OCEAN)
        image = self.tracker.visualize(image, ind)
        self.figure.displayImage((ind, image))

    def startDetector(self):
        """
        Initiates detecting and tracking. Called from an event (mapping_done)
        when the playback_manager is ready to feed frames.
        """
        self.detector.initMOG()
        self.detector.computeAll()
        self.tracker.trackAll(self.detector.detections)
        if self.display:
            self.playback_manager.play()

    def track(self):
        self.playback_manager.loadFile(self.file)


        #if test:
        #    self.playback_manager.openTestFile()
        #elif file is None:
        #    self.playback_manager.openFile()
            

        if self.display:
            self.playback_manager.frame_available.append(self.forwardImageDisplay)
        else:
            self.playback_manager.frame_available.append(self.forwardImage)

        self.detector.mog_parameters.nof_bg_frames = 500
        self.detector._show_detections = True
        self.playback_manager.mapping_done.append(self.startDetector)
        self.tracker.all_computed_signal.connect(self.quit)

        if self.display:
            self.figure = TestFigure(self.playback_manager.togglePlay)
            self.main_window.setCentralWidget(self.figure)

        print(self.detector.parameters)
        print(self.detector.parameters.mog_parameters)
        print(self.tracker.parameters)

        if self.display:
            self.main_window.show()

    def quit(self):
        self.app.quit()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    args = getDefaultParser(getArgs=True)
    file = getFiles(args)
    process = TrackProcess(app, args.display, file[0])
    process.track()
    sys.exit(app.exec_())
