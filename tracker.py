import numpy as np
import cv2
import seaborn as sns
from enum import Enum
from sort import Sort, KalmanBoxTracker
from PyQt5 import QtCore
from tracker_parameters import TrackerParameters
from filter_parameters import FilterParameters
from log_object import LogObject

class TrackingState(Enum):
    IDLE = 1
    PRIMARY = 2
    SECONDARY = 3

class AllTrackerParameters:
    pass

class Tracker(QtCore.QObject):

    # When new computation is started. Parameter: clear previous results.
    init_signal = QtCore.pyqtSignal(bool)

    # When parameters are changed
    parameters_changed_signal = QtCore.pyqtSignal()

    # When tracker state changes.
    state_changed_signal = QtCore.pyqtSignal()

    # When tracker has computed all available frames.
    all_computed_signal = QtCore.pyqtSignal(TrackingState)

    def __init__(self, detector):
        super().__init__()

        self.detector = detector

        self.clear()
        self.tracking_state = TrackingState.IDLE
        self.stop_tracking = False
        self._show_tracks = True
        self._show_bounding_box = True
        self._show_id = True
        self._show_detection_size = True

        self.paramters = None
        self.filter_parameters = None
        self.secondary_parameters = None
        self.resetParameters()

    def clear(self):
        self.applied_parameters = None
        self.applied_detector_parameters = None
        self.applied_secondary_parameters = None
        self.tracks_by_frame = {}

    # TODO: Use AllTrackerParameters instead of separate objects.
    def resetParameters(self):
        self.setParameters(TrackerParameters(), FilterParameters(), TrackerParameters())

    def setParameters(self, primary_parameters, filter_parameters, secondary_parameters):
        if self.paramters is not None:
            self.parameters.values_changed_signal.disconnect(self.parameters_changed_signal)
        self.parameters = primary_parameters
        self.parameters.values_changed_signal.connect(self.parameters_changed_signal)

        if self.filter_parameters is not None:
            self.filter_parameters.values_changed_signal.disconnect(self.parameters_changed_signal)
        self.filter_parameters = filter_parameters
        self.filter_parameters.values_changed_signal.connect(self.parameters_changed_signal)

        if self.secondary_parameters is not None:
            self.secondary_parameters.values_changed_signal.disconnect(self.parameters_changed_signal)
        self.secondary_parameters = secondary_parameters
        self.secondary_parameters.values_changed_signal.connect(self.parameters_changed_signal)

        self.parameters_changed_signal.emit()


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

        LogObject().print1(f"Primary tracking. Available detections: {self.detectionCount(self.detector.detections)}")
        self.tracks_by_frame = self.trackDetections(self.detector.detections, self.parameters, reset_count=True)

        self.applied_parameters = self.parameters.copy()
        self.applied_detector_parameters = self.detector.parameters.copy()
        self.applied_secondary_parameters = None

        self.tracking_state = TrackingState.IDLE
        self.state_changed_signal.emit()
        self.all_computed_signal.emit(TrackingState.PRIMARY)

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


        LogObject().print1(f"Secondary tracking. Available detections: {self.detectionCount(detections)}")
        self.tracks_by_frame = self.trackDetections(detections, tracker_parameters, reset_count=False)

        self.applied_secondary_parameters = self.secondary_parameters.copy()

        self.tracking_state = TrackingState.IDLE
        self.state_changed_signal.emit()
        self.all_computed_signal.emit(TrackingState.SECONDARY)

    def detectionCount(self, detections):
        count = 0
        for dets in detections:
            for det in dets:
                count += 1
        return count
        

    def trackDetections(self, detection_frames, tracker_parameters: TrackerParameters, reset_count=False):
        """
        Tracks all detections in the given frames.
        Returns a dictionary containing tracks by frame.
        """

        LogObject().print1(tracker_parameters)

        self.stop_tracking = False
        count = len(detection_frames)
        returned_tracks_by_frame = {}
        mot_tracker = Sort(max_age = tracker_parameters.getParameter(TrackerParameters.ParametersEnum.max_age),
                           min_hits = tracker_parameters.getParameter(TrackerParameters.ParametersEnum.min_hits),
                           search_radius = tracker_parameters.getParameter(TrackerParameters.ParametersEnum.search_radius))

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

    def getAllParameters(self) -> AllTrackerParameters:
        return AllTrackerParameters(self.parameters.copy(), self.filter_parameters.copy(), self.secondary_parameters.copy())

    def setPrimaryParameter(self, key, value):
        self.parameters.setKeyValuePair(key, value)

    def setFilterParameter(self, key, value):
        self.filter_parameters.setKeyValuePair(key, value)

    def setSecondaryParameter(self, key, value):
        self.secondary_parameters.setKeyValuePair(key, value)

    def setAllParameters(self, all_params: AllTrackerParameters):
        self.setParameters(
            all_params.primary.copy(),
            all_params.filter.copy(),
            all_params.secondary.copy()
            )

    def setAllParametersFromDict(self, all_params_dict: dict):
        all_params = self.getAllParameters()
        try:
            all_params.setParameterDict(all_params_dict)
            self.setAllParameters(all_params)
        except TypeError as e:
            LogObject().print2(e)


class AllTrackerParameters(QtCore.QObject):
    def __init__(self, primary, filter, secondary):
        super().__init__()

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

    def getParameterDict(self):
        return {
            "primary_tracking": self.primary.getParameterDict(),
            "filtering": self.filter.getParameterDict(),
            "secondary_tracking": self.secondary.getParameterDict()
            }

    def setParameterDict(self, dictionary):
        if type(dictionary) != dict:
            raise TypeError(f"Cannot set values of '{type(self).__name__}' from a '{type(dictionary).__name__}' object.")

        if "primary_tracking" in dictionary:
            self.primary.setParameterDict(dictionary["primary_tracking"])
        if "filtering" in dictionary:
            self.filter.setParameterDict(dictionary["filtering"])
        if "secondary_tracking" in dictionary:
            self.secondary.setParameterDict(dictionary["secondary_tracking"])


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
        LogObject().print(detector.bg_subtractor.mog_parameters)
        LogObject().print(tracker.parameters)

        main_window.show()
        sys.exit(app.exec_())

    #test1()
    playbackTest(True)
