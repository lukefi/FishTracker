import sys, os, cv2
import argparse, time
from queue import Queue
from PyQt5 import QtCore, QtGui, QtWidgets
from pathlib import Path

from playback_manager import PlaybackManager, TestFigure
from detector import Detector, DetectorParameters
from tracker import Tracker, AllTrackerParameters, TrackerParameters, FilterParameters, TrackingState
from fish_manager import FishManager
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
    Each file is intended to be processed with its own TrackProcess instance.
    """

    exit_signal = QtCore.pyqtSignal()

    def __init__(self, app, display, file, save_directory, connection=None, testFile=False, params_detector=None, params_tracker=None, secondary_tracking=False):
        super().__init__()
        self.app = app
        self.display = display
        self.figure = None
        self.file = file
        self.save_directory = os.path.abspath(save_directory)
        self.connection = connection
        self.testFile = testFile
        self.secondary_tracking = secondary_tracking
        self.secondary_tracking_started = False
        self.alive = True

        self.save_detections = True
        self.save_tracks = True

        if display:
            self.main_window = QtWidgets.QMainWindow()
        else:
            self.main_window = None

        self.playback_manager = PlaybackManager(self.app, self.main_window)

        self.detector = Detector(self.playback_manager)
        if params_detector is not None:
            self.detector.parameters = params_detector

        self.tracker = Tracker(self.detector)
        if params_tracker is not None:
            self.tracker.setAllParameters(params_tracker)

        self.fish_manager = FishManager(self.playback_manager, self.tracker)
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
        """
        Default function for forwarding the image, does not visualize the result.
        """
        ind, frame = tuple
        detections = self.detector.getDetection(ind)

    def forwardImageDisplay(self, tuple):
        """
        If the progress is visualized, this is used to forward the image.
        """
        ind, frame = tuple
        detections = self.detector.getDetection(ind)

        image = cv2.applyColorMap(frame, cv2.COLORMAP_OCEAN)
        image = self.tracker.visualize(image, ind)
        self.figure.displayImage((ind, image))

    def startTrackingProcess(self):
        """
        Initiates detecting and tracking. Called from an event (mapping_done)
        when the playback_manager is ready to feed frames.
        """
        self.detector.initMOG()
        self.detector.computeAll()
        self.tracker.primaryTrack()

        if self.secondary_tracking:
            min_dets = self.tracker.filter_parameters.min_duration
            mad_limit = self.tracker.filter_parameters.mad_limit
            used_dets = self.fish_manager.applyFiltersAndGetUsedDetections(min_dets, mad_limit)
            self.secondary_tracking_started = True
            self.tracker.secondaryTrack(used_dets, self.tracker.secondary_parameters)

        if self.display:
            self.playback_manager.play()

    def track(self):
        """
        Handles the tracking process. Opens file and connects detection and tracking
        calls to the appropriate signals, so that they can be started when the file
        has been loaded.
        """
        if self.testFile:
            self.playback_manager.openTestFile()
        else:
            self.playback_manager.loadFile(self.file)
            
        LogObject().print("Frame count:", self.playback_manager.getFrameCount())

        if self.display:
            self.playback_manager.frame_available.connect(self.forwardImageDisplay)
        else:
            self.playback_manager.frame_available.connect(self.forwardImage)

        self.detector.bg_subtractor.mog_parameters.nof_bg_frames = 500
        self.detector._show_detections = True
        self.playback_manager.mapping_done.connect(self.startTrackingProcess)
        self.tracker.all_computed_signal.connect(self.onAllComputed)

        if self.display:
            self.figure = TestFigure(self.playback_manager.togglePlay)
            self.main_window.setCentralWidget(self.figure)

        if self.display:
            self.main_window.show()

    def listenConnection(self):
        """
        Listens the connection for messages. Currently, only terminate message (-1) is supported,
        but others should be easy to add when needed.
        """
        while self.alive:
            if self.connection.poll():
                id, msg = self.connection.recv()
                if id == -1:
                    self.connection.send((-1, "Terminating"))
                    self.quit()
            else:
                time.sleep(0.5)

    def getSaveFilePath(self, end_string):
        """
        Formats the save file path. Detections and tracks are separated based on end_string.
        """
        base_name = os.path.basename(self.file)
        file_name = os.path.splitext(base_name)[0]
        file_path = os.path.join(self.save_directory, "{}_{}".format(file_name, end_string))
        return file_path

    def saveResults(self):
        """
        Saves both detections and tracks to the directory provided earlier.
        """
        file_name = os.path.splitext(self.file)[0]
        if self.save_detections:
            det_path = self.getSaveFilePath("dets.txt")
            self.detector.saveDetectionsToFile(det_path)

        if self.save_tracks:
            track_path = self.getSaveFilePath("tracks.txt")
            self.fish_manager.saveToFile(track_path)

    def onAllComputed(self, tracking_state):
        """
        Saves and quits the process.
        """
        if not self.secondary_tracking or tracking_state == TrackingState.SECONDARY:
            self.saveResults()
            self.quit()

    def quit(self):
        self.alive = False
        self.app.quit()


def trackProcess(display, file, save_directory, connection=None, params_detector_dict=None, params_tracker_dict=None, secondary_tracking=False, testFile=False):
    app = QtWidgets.QApplication(sys.argv)

    params_detector = DetectorParameters()
    params_detector.setParameterDict(params_detector_dict)

    params_tracker = AllTrackerParameters(TrackerParameters(), FilterParameters(), TrackerParameters())
    params_tracker.setParameterDict(params_tracker_dict)

    process = TrackProcess(app, display, file, save_directory, connection, testFile, params_detector, params_tracker, secondary_tracking)
    process.track()
    sys.exit(app.exec_())


#TODO: Fix test code
if __name__ == "__main__":
    save_directory = fh.getLatestSaveDirectory()
    args = getDefaultParser(getArgs=True)
    file = getFiles(args)
    trackProcess(args.display, file[0], save_directory, testFile=args.test)
