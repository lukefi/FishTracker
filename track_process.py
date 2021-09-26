import sys, os, cv2
import argparse, time
import multiprocessing as mp
from queue import Queue
from dataclasses import dataclass
from PyQt5 import QtCore, QtGui, QtWidgets
from pathlib import Path

from playback_manager import PlaybackManager, TestFigure
from detector import Detector, DetectorParameters
from tracker import Tracker, AllTrackerParameters, TrackerParameters, FilterParameters, TrackingState
from fish_manager import FishManager
from save_manager import SaveManager
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

@dataclass
class TrackProcessInfo:
        display: bool
        file: str
        save_directory: str
        connection: mp.connection._ConnectionBase
        params_detector_dict: dict = None
        params_tracker_dict: dict = None
        secondary_tracking: bool = False
        test_file: bool = False

        # Save detections to a text file
        save_detections: bool =False

        # Save tracks to a text file
        save_tracks: bool = False

        # Save complete results with save manager
        save_complete: bool = False

        # Save results as a binary file
        as_binary: bool = True

class TrackProcess(QtCore.QObject):
    """
    TrackProcess launches individual PlaybackManager, Detector and Tracker,
    separate from the ones associated with the UI.
    These are used for the tracking process of the file provided in the track method.
    Each file is intended to be processed with its own TrackProcess instance.
    """

    exit_signal = QtCore.pyqtSignal()

    def __init__(self, app: QtWidgets.QApplication, info: TrackProcessInfo):

        super().__init__()
        self.app = app
        self.info = info
        self.display = info.display
        self.file = info.file
        self.save_directory = os.path.abspath(info.save_directory)
        self.connection = info.connection
        self.test_file = info.test_file
        self.secondary_tracking = info.secondary_tracking
        self.secondary_tracking_started = False
        self.alive = True
        self.figure = None

        self.save_detections = info.save_detections
        self.save_tracks = info.save_tracks
        self.save_complete = info.save_complete
        self.binary = info.as_binary

        if info.display:
            self.main_window = QtWidgets.QMainWindow()
        else:
            self.main_window = None

        self.playback_manager = PlaybackManager(self.app, self.main_window)

        self.detector = Detector(self.playback_manager)
        self.tracker = Tracker(self.detector)
        self.setParametersFromDict(info.params_detector_dict, info.params_tracker_dict)

        self.fish_manager = FishManager(self.playback_manager, self.tracker)
        self.save_manager = SaveManager(self.playback_manager, self.detector, self.tracker, self.fish_manager)

        self.playback_manager.fps = 100
        self.playback_manager.runInThread(self.listenConnection)

        log = LogObject()
        log.disconnectDefault()
        #log.connect(writeToFile)
        log.connect(self.writeToConnection)
        log.print("Process created for file: ", self.file)

    def setParametersFromDict(self, params_detector_dict: dict, params_tracker_dict: dict):
        if params_detector_dict is not None:
            params_detector = DetectorParameters(self.detector.bg_subtractor.mog_parameters)
            params_detector.setParameterDict(params_detector_dict)
            self.detector.parameters = params_detector

        if params_tracker_dict is not None:
            #params_tracker = AllTrackerParameters(TrackerParameters(), FilterParameters(), TrackerParameters())
            #params_tracker.setParameterDict(params_tracker_dict)
            #self.tracker.setAllParameters(params_tracker)
            self.tracker.setAllParametersFromDict(params_tracker_dict)

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
            self.secondary_tracking_started = True
            self.fish_manager.secondaryTrack(self.tracker.filter_parameters)

        if self.display:
            self.playback_manager.play()

    def track(self):
        """
        Handles the tracking process. Opens file and connects detection and tracking
        calls to the appropriate signals, so that they can be started when the file
        has been loaded.
        """
        if self.test_file:
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
        file_path = os.path.join(self.save_directory, "{}{}".format(file_name, end_string))
        return file_path

    def saveResults(self):
        """
        Saves and/or exports results to the directory provided earlier.
        """
        file_name = os.path.splitext(self.file)[0]
        if self.save_detections:
            det_path = self.getSaveFilePath("_dets.txt")
            self.detector.saveDetectionsToFile(det_path)

        if self.save_tracks:
            track_path = self.getSaveFilePath("_tracks.txt")
            self.fish_manager.saveToFile(track_path)

        if self.save_complete:
            save_path = self.getSaveFilePath(".fish")
            self.save_manager.saveFile(save_path, self.binary)

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

def trackProcess(process_info: TrackProcessInfo):
    app = QtWidgets.QApplication(sys.argv)
    process = TrackProcess(app, process_info)
    process.track()
    sys.exit(app.exec_())


#TODO: Fix test code
if __name__ == "__main__":
    save_directory = fh.getLatestSaveDirectory()
    args = getDefaultParser(getArgs=True)
    file = getFiles(args)
    info = TrackProcessInfo(file=file[0], save_directory=save_directory, test_file=args.test)
    trackProcess(args.display, info)
