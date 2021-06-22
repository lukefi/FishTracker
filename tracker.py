import numpy as np
import cv2
import seaborn as sns
from sort import Sort, KalmanBoxTracker
from PyQt5 import QtCore
from log_object import LogObject

PARAMETER_TYPES = {
            "max_age": int,
	        "min_hits": int,
            "search_radius": int
        }

class Tracker(QtCore.QObject):
    # When new computation is started
    init_signal = QtCore.pyqtSignal()

    # When tracker parameters change.
    state_changed_signal = QtCore.pyqtSignal()

    # When the results change
    data_changed_signal = QtCore.pyqtSignal(int)

    # When tracker has computed all available frames.
    all_computed_signal = QtCore.pyqtSignal()

    def __init__(self, detector):
        super().__init__()

        self.detector = detector
        self.resetParameters()

        self.clear()
        self.tracking = False
        self.stop_tracking = False
        self._show_tracks = True
        self._show_bounding_box = True
        self._show_id = True
        self._show_detection_size = True

    def clear(self):
        self.applied_parameters = None
        self.applied_detector_parameters = None
        self.mot_tracker = None
        self.tracks_by_frame = {}

    def resetParameters(self):
        self.parameters = TrackerParameters()


    def trackAllDetectorFrames(self):
        self.trackAll(self.detector.detections)

    def trackAll(self, detection_frames):
        """
        Tracks all detections in the given frames. Updates tracks_by_frame and
        signals when the computation has finished.
        """
        self.tracking = True
        self.stop_tracking = False
        self.state_changed_signal.emit()
        self.init_signal.emit()

        if self.detector.allCalculationAvailable():
            self.detector.computeAll()
            if self.detector.allCalculationAvailable():
                LogObject().print("Stopped before tracking.")
                self.abortComputing(True)
                return


        count = len(detection_frames)
        self.tracks_by_frame = {}
        self.mot_tracker = Sort(max_age = self.parameters.max_age,
                                min_hits = self.parameters.min_hits,
                                search_radius = self.parameters.search_radius)
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
                return

            self.tracks_by_frame[i] = self.trackBase(dets, i)
                

        LogObject().print("Tracking: 100 %")
        self.tracking = False
        self.applied_parameters = self.parameters.copy()
        self.applied_detector_parameters = self.detector.parameters.copy()
        
        self.state_changed_signal.emit()
        self.all_computed_signal.emit()

    def trackBase(self, frame, ind):
        """
        Performs tracking step for a single frame.
        Returns (track, detection) if the track was updated this frame, otherwise (track, None).
        """
        if frame is None:
            LogObject().print("Invalid detector results encountered at frame " + str(ind) +". Consider rerunning the detector.")
            return self.mot_tracker.update()

        detections = [d for d in frame if d.corners is not None]
        if len(detections) > 0:
            dets = np.array([np.min(d.corners,0).flatten().tolist() + np.max(d.corners,0).flatten().tolist() for d in detections])
            tracks = self.mot_tracker.update(dets)
        else:
            tracks = self.mot_tracker.update()

        return [(tr, detections[int(tr[7])]) if tr[7] >= 0 else (tr, None) for tr in tracks]

    def abortComputing(self, detector_aborted):
        self.tracking = False
        self.applied_parameters = None
        self.stop_tracking = False
        if detector_aborted:
            self.applied_detector_parameters = None
        self.state_changed_signal.emit()

    def visualize(self, image, ind):
        if ind not in self.tracks_by_frame:
            return image
        
        #colors = sns.color_palette('deep', max([0] + [d.label + 1 for _, d in self.tracks_by_frame[ind]]))
        colors = sns.color_palette('deep', len(self.tracks_by_frame[ind]))
        for tr, det in self.tracks_by_frame[ind]:

            if self._show_id:
                center = [(tr[0] + tr[2]) / 2, (tr[1] + tr[3]) / 2]
                image = cv2.putText(image, "ID: " + str(int(tr[4])), (int(center[1])-20, int(center[0])+25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1, cv2.LINE_AA)

            if self._show_detection_size and det is not None:
                det.visualize(image, colors, True, False)

            if self._show_bounding_box:
                corners = np.array([[tr[0], tr[1]], [tr[2], tr[1]], [tr[2], tr[3]], [tr[0], tr[3]]]) #, [tr[0], tr[1]]

                for i in range(0,3):
                    cv2.line(image, (int(corners[i,1]),int(corners[i,0])), (int(corners[i+1,1]),int(corners[i+1,0])),  (255,255,255), 1)
                cv2.line(image, (int(corners[3,1]),int(corners[3,0])), (int(corners[0,1]),int(corners[0,0])),  (255,255,255), 1)

        return image

    def parametersDirty(self):
        return self.parameters != self.applied_parameters or self.applied_detector_parameters != self.detector.parameters \
            or self.applied_detector_parameters != self.detector.applied_parameters

    def setMaxAge(self, value):
        try:
            self.parameters.max_age = int(value)
            self.state_changed_signal.emit()
        except ValueError as e:
            LogObject().print(e)

    def setMinHits(self, value):
        try:
            self.parameters.min_hits = int(value)
            self.state_changed_signal.emit()
        except ValueError as e:
            LogObject().print(e)

    def setSearchRadius(self, value):
        try:
            self.parameters.search_radius = int(value)
            self.state_changed_signal.emit()
        except ValueError as e:
            LogObject().print(e)

    def getParameterDict(self):
        if self.parameters is not None:
            return self.parameters.getParameterDict()
        else:
            return None


class TrackerParameters:
    def __init__(self, max_age = 10, min_hits = 5, search_radius = 10):
        self.max_age = max_age
        self.min_hits = min_hits
        self.search_radius = search_radius

    def __eq__(self, other):
        if not isinstance(other, TrackerParameters):
            return False
    
        return self.max_age == other.max_age \
            and self.min_hits == other.min_hits \
            and self.search_radius == other.search_radius

    def __repr__(self):
        return "Tracker Parameters: {} {} {}".format(self.max_age, self.min_hits, self.search_radius)

    def copy(self):
        return TrackerParameters(self.max_age, self.min_hits, self.search_radius)

    def getParameterDict(self):
        return {
            "max_age": self.max_age,
	        "min_hits": self.min_hits,
            "search_radius": self.search_radius
        }

    def setParameterDict(self, dict):
        for key, value in dict.items():
            if not hasattr(self, key):
                print("Error: Invalid parameters: {}: {}".format(key, value))
                continue

            if not key in PARAMETER_TYPES:
                print("Error: Key [{}] not in PARAMETER_TYPES".format(key, value))
                continue

            try:
                setattr(self, key, PARAMETER_TYPES[key](value))
            except ValueError as e:
                print("Error: Invalid value in tracker parameters file,", e)


if __name__ == "__main__":
    import sys
    from PyQt5 import QtCore, QtGui, QtWidgets
    from playback_manager import PlaybackManager, TestFigure
    from detector import Detector, DetectorParameters

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
        tracker.trackAll(detection_frames)

    def playbackTest():
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
            tracker.trackAll(detector.detections)
            playback_manager.play()

        app = QtWidgets.QApplication(sys.argv)
        main_window = QtWidgets.QMainWindow()
        playback_manager = PlaybackManager(app, main_window)
        detector = Detector(playback_manager)
        tracker = Tracker(detector)

        playback_manager.fps = 10
        playback_manager.openTestFile()
        playback_manager.frame_available.connect(forwardImage)
        detector.mog_parameters.nof_bg_frames = 500
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
    playbackTest()
