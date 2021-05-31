import sys, os, cv2
import argparse, time
from queue import Queue
from PyQt5 import QtCore, QtGui, QtWidgets

from playback_manager import PlaybackManager, TestFigure
from detector import Detector
from tracker import Tracker
from output_widget import WriteStream, StreamReceiver
import file_handler as fh
from log_object import LogObject

def getDefaultParser(getArgs=False):
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--display', default=False, action='store_true', help="display frames as the patch is processed")
    parser.add_argument('-f', '--file', type=argparse.FileType('r'), nargs='*', help=".aris file(s) to be processed")
    parser.add_argument('-t', '--test', default=False, action='store_true', help="use test file (if exists)")
    if getArgs:
        return parser.parse_args()
    else:
        return parser

def getFiles(args = None):
    files = []
    if args is not None and args.file:
         files = [f.name for f in args.file]
    elif args is not None and args.test:
        files = [fh.getTestFilePath()]
    else:
        dir = fh.getLatestDirectory()
        filePathTuple = QtWidgets.QFileDialog.getOpenFileNames(None, "Open File", dir, "Sonar Files (*.aris *.ddf)")
        files = [f for f in filePathTuple[0]]
        try:
            fh.setLatestDirectory(os.path.dirname(files[0]))
        except IndexError:
            pass

    return files

def writeToFile(value, mode='a'):
    with open("track_process_io.txt", mode) as f:
        f.write(str(value) + "\n")

class TrackProcess(QtCore.QObject):
    """
    TrackProcess launches individual PlaybackManager, Detector and Tracker,
    separate from the ones associated with the UI.
    These are used for the tracking process of the file provided in the track method.
    Each file are intended to be processed with their own TrackProcess instances.
    """

    exit_signal = QtCore.pyqtSignal()

    def __init__(self, app, display, file, connection=None, testFile=False):
        super().__init__()
        self.app = app
        self.display = display
        self.figure = None
        self.file = file
        self.connection = connection
        self.testFile = testFile
        self.alive = True

        if display:
            self.main_window = QtWidgets.QMainWindow()
        else:
            self.main_window = None

        self.playback_manager = PlaybackManager(self.app, self.main_window)

        self.detector = Detector(self.playback_manager)
        self.tracker = Tracker(self.detector)
        self.playback_manager.fps = 100

        self.playback_manager.runInThread(self.listenConnection)

        log = LogObject()
        log.disconnectDefault()
        #log.connect(writeToFile)
        log.connect(self.writeToConnection)
        log.print("Process created for file: ", self.file)

    def writeToConnection(self, value):
        if self.connection:
            self.connection.send(value)

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
        if self.testFile:
            self.playback_manager.openTestFile()
        else:
            self.playback_manager.loadFile(self.file)
            
        LogObject().print("Frame count:", self.playback_manager.getFrameCount())

        if self.display:
            self.playback_manager.frame_available.connect(self.forwardImageDisplay)
        else:
            self.playback_manager.frame_available.connect(self.forwardImage)

        self.detector.mog_parameters.nof_bg_frames = 500
        self.detector._show_detections = True
        self.playback_manager.mapping_done.connect(self.startDetector)
        self.tracker.all_computed_signal.connect(self.onAllComputed)

        if self.display:
            self.figure = TestFigure(self.playback_manager.togglePlay)
            self.main_window.setCentralWidget(self.figure)

        LogObject().print(self.detector.parameters)
        LogObject().print(self.detector.parameters.mog_parameters)
        LogObject().print(self.tracker.parameters)

        if self.display:
            self.main_window.show()

    def listenConnection(self):
        while self.alive:
            if self.connection.poll():
                id, msg = self.connection.recv()
                if id == -1:
                    self.connection.send((-1, "Terminating"))
                    self.quit()
            else:
                time.sleep(0.5)

    def onAllComputed(self):
        # Save to file here
        self.quit()

    def quit(self):
        self.alive = False
        self.app.quit()


def trackProcess(display, file, connection=None, testFile=False):
    app = QtWidgets.QApplication(sys.argv)
    process = TrackProcess(app, display, file, connection, testFile)
    process.track()
    sys.exit(app.exec_())


#TODO: Fix test code
if __name__ == "__main__":
    args = getDefaultParser(getArgs=True)
    file = getFiles(args)
    trackProcess(args.display, file[0], testFile=args.test)
