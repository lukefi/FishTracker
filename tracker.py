import numpy as np
import cv2
import seaborn as sns
from enum import Enum
from sort import Sort, KalmanBoxTracker
from PyQt5 import QtCore
from log_object import LogObject

class TrackingState(Enum):
    IDLE = 1
    PRIMARY = 2
    SECONDARY = 3

class Tracker(QtCore.QObject):

    # When new computation is started. Parameter: clear previous results.
    init_signal = QtCore.pyqtSignal(bool)

    # When tracker parameters change.
    state_changed_signal = QtCore.pyqtSignal()

    # When tracker has computed all available frames.
    all_computed_signal = QtCore.pyqtSignal()

    def __init__(self, detector):
        super().__init__()

        self.detector = detector
        self.resetParameters()

        self.clear()
        self.tracking_state = TrackingState.IDLE
        self.stop_tracking = False
        self._show_tracks = True
        self._show_bounding_box = True
        self._show_id = True
        self._show_detection_size = True

    def clear(self):
        self.applied_parameters = None
        self.applied_detector_parameters = None
        self.applied_secondary_parameters = None
        self.tracks_by_frame = {}

    def resetParameters(self):
        self.parameters = TrackerParameters()
        self.parameters.values_changed_signal.connect(self.state_changed_signal)

        self.filter_parameters = FilterParameters()
        self.filter_parameters.values_changed_signal.connect(self.state_changed_signal)

        self.secondary_parameters = TrackerParameters()
        self.secondary_parameters.values_changed_signal.connect(self.state_changed_signal)


    def primaryTrack(self):
        """
        Tracks all detections from detector and stores the results in tracks_by_frame dictionary.
        Signals when the computation has finished.
        """

        self.tracking_state = TrackingState.PRIMARY
        self.state_changed_signal.emit()
        self.init_signal.emit(True)

        if self.detector.allCalculationAvailable():
            self.detector.computeAll()

            # Return if the applied detector parameters are not up to date
            if self.detector.allCalculationAvailable():
                LogObject().print("Stopped before tracking.")
                self.abortComputing(True)
                return

        print(f"First:  {self.detectionCount(self.detector.detections)}")
        self.tracks_by_frame = self.trackDetections(self.detector.detections, self.parameters, reset_count=True)

        self.applied_parameters = self.parameters.copy()
        self.applied_detector_parameters = self.detector.parameters.copy()
        self.applied_secondary_parameters = None

        self.tracking_state = TrackingState.IDLE
        self.state_changed_signal.emit()
        self.all_computed_signal.emit()

    def secondaryTrack(self, used_detections, tracker_parameters):
        """
        Tracks all detections from detector, excluding used_detections using the given
        tracker parameters. Previous results are replaced with the new results.
        Signals when the computation has finished.

        used_detections: Dictionary: frame_index -> list of detections in that frame.
        tracker_parameters: TrackerParameters object containing the parameters for tracking. 
        """

        self.tracking_state = TrackingState.SECONDARY
        self.state_changed_signal.emit()
        self.init_signal.emit(False)

        detections = [[] for i in range(len(self.detector.detections))]
        for frame, dets in enumerate(self.detector.detections):
            if frame in used_detections:
                used_dets = used_detections[frame]
                for det in dets:
                    if det not in used_dets:
                        detections[frame].append(det)
            else:
                detections[frame] = dets


        print(f"Second: {self.detectionCount(detections)}")
        self.tracks_by_frame = self.trackDetections(detections, tracker_parameters, reset_count=False)

        self.applied_secondary_parameters = self.secondary_parameters.copy()

        self.tracking_state = TrackingState.IDLE
        self.state_changed_signal.emit()
        self.all_computed_signal.emit()

    def detectionCount(self, detections):
        count = 0
        for dets in detections:
            for det in dets:
                count += 1
        return count
        

    def trackDetections(self, detection_frames, tracker_parameters, reset_count=False):
        """
        Tracks all detections in the given frames.
        Returns a dictionary containing tracks by frame.
        """

        LogObject().print(tracker_parameters)

        self.stop_tracking = False
        count = len(detection_frames)
        returned_tracks_by_frame = {}
        mot_tracker = Sort(max_age = tracker_parameters.max_age,
                           min_hits = tracker_parameters.min_hits,
                           search_radius = tracker_parameters.search_radius)

        if reset_count:
            KalmanBoxTracker.count = 0

        ten_perc = 0.1 * count
        print_limit = 0

        for i, dets in enumerate(detection_frames):
            if i > print_limit:
                LogObject().print("Tracking:", int(float(i) / count * 100), "%")
                print_limit += ten_perc

            if self.stop_tracking:
                LogObject().print("Stopped tracking at", i)
                self.abortComputing(False)
                return {}

            returned_tracks_by_frame[i] = self.trackBase(mot_tracker, dets, i)
                
        LogObject().print("Tracking: 100 %")    
        return returned_tracks_by_frame

    def trackBase(self, mot_tracker, frame, ind):
        """
        Performs tracking step for a single frame.
        Returns (track, detection) if the track was updated this frame, otherwise (track, None).
        """
        if frame is None:
            LogObject().print("Invalid detector results encountered at frame " + str(ind) +". Consider rerunning the detector.")
            return mot_tracker.update()

        detections = [d for d in frame if d.corners is not None]
        if len(detections) > 0:
            dets = np.array([np.min(d.corners,0).flatten().tolist() + np.max(d.corners,0).flatten().tolist() for d in detections])
            tracks = mot_tracker.update(dets)
        else:
            tracks = mot_tracker.update()

        return [(tr, detections[int(tr[7])]) if tr[7] >= 0 else (tr, None) for tr in tracks]

    def abortComputing(self, detector_aborted):
        self.tracking_state = TrackingState.IDLE
        self.applied_parameters = None
        self.stop_tracking = False
        if detector_aborted:
            self.applied_detector_parameters = None
        self.state_changed_signal.emit()

    def visualize(self, image, ind):
        """
        Visualizes the tracked fish in the frame [ind] of tracks_by_frame.
        Note: This is not used in the main application anymore and similar methods can
        be found in the sonar_widget.py file.
        """

        if ind not in self.tracks_by_frame:
            return image
        
        colors = sns.color_palette('deep', len(self.tracks_by_frame[ind]))
        for tr, det in self.tracks_by_frame[ind]:

            if self._show_id:
                center = [(tr[0] + tr[2]) / 2, (tr[1] + tr[3]) / 2]
                image = cv2.putText(image, "ID: " + str(int(tr[4])), (int(center[1])-20, int(center[0])+25),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1, cv2.LINE_AA)

            if self._show_detection_size and det is not None:
                det.visualize(image, colors, True, False)

            if self._show_bounding_box:
                corners = np.array([[tr[0], tr[1]], [tr[2], tr[1]], [tr[2], tr[3]], [tr[0], tr[3]]])

                for i in range(0,3):
                    cv2.line(image, (int(corners[i,1]),int(corners[i,0])), (int(corners[i+1,1]),int(corners[i+1,0])),  (255,255,255), 1)
                cv2.line(image, (int(corners[3,1]),int(corners[3,0])), (int(corners[0,1]),int(corners[0,0])),  (255,255,255), 1)

        return image

    def parametersDirty(self):
        return self.parameters != self.applied_parameters or self.applied_detector_parameters != self.detector.parameters \
            or self.applied_detector_parameters != self.detector.applied_parameters

    def getParameterDict(self):
        if self.parameters is not None:
            return self.parameters.getParameterDict()
        else:
            return None

    def getAllParameters(self):
        return AllTrackerParameters(self.parameters.copy(), self.filter_parameters.copy(), self.secondary_parameters.copy())


class AllTrackerParameters(QtCore.QObject):
    def __init__(self, primary, filter, secondary):
        self.primary = primary
        self.filter = filter
        self.secondary = secondary

    def __eq__(self, other):
        if not isinstance(other, AllTrackerParameters):
            return False
        return self.primary == other.primary \
            and self.filter == other.filter \
            and self.secondary == other.secondary

    def copy(self):
        return AllTrackerParameters(self.primary.copy(), self.filter.copy(), self.secondary.copy())

TRACKER_PARAMETER_TYPES = {
    "max_age": int,
    "min_hits": int,
    "search_radius": int,
    "trim_tails": bool
    }

class TrackerParameters(QtCore.QObject):

    values_changed_signal = QtCore.pyqtSignal()

    def __init__(self, max_age = 10, min_hits = 5, search_radius = 10, trim_tails = True):
        super().__init__()

        self.max_age = max_age
        self.min_hits = min_hits
        self.search_radius = search_radius
        self.trim_tails = trim_tails

    def __eq__(self, other):
        if not isinstance(other, TrackerParameters):
            return False
    
        return self.max_age == other.max_age \
            and self.min_hits == other.min_hits \
            and self.search_radius == other.search_radius \
            and self.trim_tails == other.trim_tails

    def __repr__(self):
        return "Tracker Parameters: {} {} {}".format(self.max_age, self.min_hits, self.search_radius, self.trim_tails)

    def copy(self):
        return TrackerParameters(self.max_age, self.min_hits, self.search_radius, self.trim_tails)

    def getParameterDict(self):
        return {
            "max_age": self.max_age,
	        "min_hits": self.min_hits,
            "search_radius": self.search_radius,
            "trim_tails": self.trim_tails
        }

    def setParameterDict(self, dict):
        for key, value in dict.items():
            if not hasattr(self, key):
                print("Error: Invalid parameters: {}: {}".format(key, value))
                continue

            if not key in TRACKER_PARAMETER_TYPES:
                print("Error: Key [{}] not in TRACKER_PARAMETER_TYPES".format(key, value))
                continue

            try:
                setattr(self, key, TRACKER_PARAMETER_TYPES[key](value))
            except ValueError as e:
                print("Error: Invalid value in tracker parameters file,", e)

    def setMaxAge(self, value):
        try:
            self.max_age = int(value)
            self.values_changed_signal.emit()
            return True
        except ValueError as e:
            LogObject().print(e)
            return False

    def setMinHits(self, value):
        try:
            self.min_hits = int(value)
            self.values_changed_signal.emit()
            return True
        except ValueError as e:
            LogObject().print(e)
            return False

    def setSearchRadius(self, value):
        try:
            self.search_radius = int(value)
            self.values_changed_signal.emit()
            return True
        except ValueError as e:
            LogObject().print(e)
            return False

    def setTrimTails(self, value):
        try:
            self.trim_tails = bool(value)
            self.values_changed_signal.emit()
            return True
        except ValueError as e:
            LogObject().print(e)
            return False


FILTER_PARAMETER_TYPES = {
    "min_duration": int,
    "mad_limit": int
    }


class FilterParameters(QtCore.QObject):

    values_changed_signal = QtCore.pyqtSignal()

    def __init__(self, min_duration=2, mad_limit=0):
        super().__init__()

        self.min_duration = min_duration
        self.mad_limit = mad_limit

    def __eq__(self, other):
        if not isinstance(other, FilterParameters):
            return False
    
        return self.min_duration == min_duration \
            and self.mad_limit == mad_limit

    def __repr__(self):
        return "Filter Parameters: {} {}".format(self.min_duration, self.mad_limit)

    def copy(self):
        return FilterParameters(self.min_duration, self.mad_limit)

    def getParameterDict(self):
        return {
            "min_duration": self.min_duration,
            "mad_limit": self.mad_limit
        }

    def setParameterDict(self, dict):
        for key, value in dict.items():
            if not hasattr(self, key):
                print("Error: Invalid parameters: {}: {}".format(key, value))
                continue

            if not key in FILTER_PARAMETER_TYPES:
                print("Error: Key [{}] not in FILTER_PARAMETER_TYPES".format(key, value))
                continue

            try:
                setattr(self, key, FILTER_PARAMETER_TYPES[key](value))
            except ValueError as e:
                print("Error: Invalid value in filter parameters file,", e)

    def setMinDuration(self, value):
        try:
            self.min_duration = int(value)
            self.values_changed_signal.emit()
            return True
        except ValueError as e:
            LogObject().print(e)
            return False

    def setMADLimit(self, value):
        try:
            self.mad_limit = int(value)
            self.values_changed_signal.emit()
            return True
        except ValueError as e:
            LogObject().print(e)
            return False


if __name__ == "__main__":
    import sys
    from PyQt5 import QtCore, QtGui, QtWidgets
    from playback_manager import PlaybackManager, TestFigure
    from detector import Detector, DetectorParameters
    from fish_manager import FishManager

    def test1():
        """
        Simple test code to assure tracker is working.
        """

        class DetectorTest:
            def __init__(self):
                self.allCalculationAvailable = lambda: False
                self.parameters = DetectorParameters()

        class DetectionTest:
            def __init__(self):
                self.center = center = np.random.uniform(5, 95, (1,2))
                self.diff = diff = np.random.uniform(1,5,2)
                self.corners = np.array([center+[-diff[0],-diff[1]], \
                    center+[diff[0],-diff[1]], \
				    center+[diff[0],diff[1]], \
				    center+[-diff[0],diff[1]], \
				    center+[-diff[0],-diff[1]]])

            def __repr__(self):
                return "DT"

        detector = DetectorTest()
        tracker = Tracker(detector)
        detection_frames = [[DetectionTest() for j in range(int(np.random.uniform(0,5)))] for i in range(50)]
        tracker.trackDetections(detection_frames)

    def playbackTest(secondary):
        """
        Test code to assure tracker works with detector.
        """
        def forwardImage(tuple):
            ind, frame = tuple
            detections = detector.getDetection(ind)

            image = cv2.applyColorMap(frame, cv2.COLORMAP_OCEAN)
            image = tracker.visualize(image, ind)

            figure.displayImage((ind, image))

        def startDetector():
            detector.initMOG()
            detector.computeAll()
            tracker.primaryTrack()

            if secondary:
                LogObject().print("Secondary track...")
                used_dets = fish_manager.applyFiltersAndGetUsedDetections()
                tracker.secondaryTrack(used_dets, tracker.parameters)

            playback_manager.play()

        app = QtWidgets.QApplication(sys.argv)
        main_window = QtWidgets.QMainWindow()
        playback_manager = PlaybackManager(app, main_window)
        detector = Detector(playback_manager)
        tracker = Tracker(detector)
        fish_manager = FishManager(playback_manager, tracker)

        playback_manager.fps = 10
        playback_manager.openTestFile()
        playback_manager.frame_available.connect(forwardImage)
        detector.bg_subtractor.mog_parameters.nof_bg_frames = 500
        detector._show_detections = True
        playback_manager.mapping_done.connect(startDetector)

        figure = TestFigure(playback_manager.togglePlay)
        main_window.setCentralWidget(figure)

        LogObject().print(detector.parameters)
        LogObject().print(detector.parameters.mog_parameters)
        LogObject().print(tracker.parameters)

        main_window.show()
        sys.exit(app.exec_())

    #test1()
    playbackTest(True)
