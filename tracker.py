import numpy as np
import cv2
from sort import Sort, KalmanBoxTracker
from playback_manager import Event

class Tracker:
    def __init__(self, detector):
        self.detector = detector
        self.parameters = TrackerParameters()
        self.applied_parameters = None
        self.applied_detector_parameters = None
        self.mot_tracker = None
        self.tracks_by_frame = {}
        self.tracking = False
        self.stop_tracking = False
        self._show_tracks = False
        self._show_id = True

		# When tracker parameters change.
        self.state_changed_event = Event()

		### When the results change
        self.data_changed_event = Event()

		# When tracker has computed all available frames.
        self.all_computed_event = Event()

    def trackAllDetectorFrames(self):
        self.trackAll(self.detector.detections)

    def trackAll(self, detection_frames):
        self.tracking = True
        self.stop_tracking = False
        self.state_changed_event()

        if self.detector.allCalculationAvailable():
            self.detector.computeAll()
            if self.detector.allCalculationAvailable():
                print("Stopped before tracking.")
                self.abortComputing(True)
                return


        count = len(detection_frames)
        self.tracks_by_frame = {}
        self.mot_tracker = Sort(max_age=self.parameters.max_age,
                                min_hits=self.parameters.min_hits,
                                iou_threshold=self.parameters.iou_threshold)
        KalmanBoxTracker.count = 0

        ten_perc = 0.1 * count
        print_limit = 0
        for i, frame in enumerate(detection_frames):
            if i > print_limit:
                print("Tracking:", int(float(i) / count * 100), "%")
                print_limit += ten_perc
            if self.stop_tracking:
                print("Stopped tracking at", i)
                self.abortComputing(False)
                return

            tracks = self.trackBase(frame, i)
            if len(tracks) > 0:
                self.tracks_by_frame[i] = tracks

        print("Tracking: 100 %")
        self.tracking = False
        self.applied_parameters = self.parameters.copy()
        self.applied_detector_parameters = self.detector.parameters.copy()
        
        self.state_changed_event()
        self.all_computed_event()

    def trackBase(self, frame, ind):
        if frame is None:
            print("Invalid detector results encountered at frame " + str(ind) +". Consider rerunning the detector.")
            return self.mot_tracker.update()

        detections = np.array([np.min(d.corners,0).flatten().tolist() + np.max(d.corners,0).flatten().tolist() for d in frame if d.corners is not None]) #[d.corners for d in f]
        #print(detections)
        if len(detections) > 0:
            return self.mot_tracker.update(detections)
        else:
            return self.mot_tracker.update()

    def abortComputing(self, detector_aborted):
        self.tracking = False
        self.applied_parameters = None
        self.stop_tracking = False
        if detector_aborted:
            self.applied_detector_parameters = None
        self.state_changed_event()

    def visualize(self, image, ind):
        if ind not in self.tracks_by_frame:
            return image
        
        for tr in self.tracks_by_frame[ind]:
            if self._show_id:
                center = [(tr[0] + tr[2]) / 2, (tr[1] + tr[3]) / 2]
                image = cv2.putText(image, "ID: " + str(int(tr[4])), (int(center[1])-20, int(center[0])+25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1, cv2.LINE_AA)


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
            self.state_changed_event()
        except ValueError as e:
            print(e)

    def setMinHits(self, value):
        try:
            self.parameters.min_hits = int(value)
            self.state_changed_event()
        except ValueError as e:
            print(e)

    def setIoUThreshold(self, value):
        try:
            self.parameters.iou_threshold = float(value)
            self.state_changed_event()
        except ValueError as e:
            print(e)

    def setShowTracks(self, value):
        self._show_tracks = value
        if not self._show_tracks:
            self.data_changed_event(0)

    def setShowTrackingIDs(self, value):
        self._show_id = value


class TrackerParameters:
    def __init__(self, max_age = 20, min_hits = 3, iou_threshold = 0.1):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold

    def __eq__(self, other):
        if not isinstance(other, TrackerParameters):
            return False
    
        return self.max_age == other.max_age \
            and self.min_hits == other.min_hits \
            and self.iou_threshold == other.iou_threshold

    def copy(self):
        return TrackerParameters(self.max_age, self.min_hits, self.iou_threshold)


if __name__ == "__main__":
    import sys
    from PyQt5 import QtCore, QtGui, QtWidgets
    from playback_manager import PlaybackManager, Event, TestFigure
    from detector import Detector

    def test1():
        class DetectionTest:
            def __init__(self):
                self.center = center = np.random.uniform(5, 95, (1,2))
                self.diff = diff = np.random.uniform(1,5,2)
                self.corners = np.array([center+[-diff[0],-diff[1]], \
                    center+[diff[0],-diff[1]], \
				    center+[diff[0],diff[1]], \
				    center+[-diff[0],diff[1]], \
				    center+[-diff[0],-diff[1]]])

                #print(np.min(self.corners,0), np.max(self.corners,0))

            def __repr__(self):
                return "DT"

        tracker = Tracker()
        detection_frames = [[DetectionTest() for j in range(int(np.random.uniform(0,5)))] for i in range(50)]
        tracker.run(detection_frames)

    def playbackTest():
        def forwardImage(tuple):
            ind, frame = tuple
		    # detections = detector.compute(ind, frame)
            detections = detector.getDetection(ind)

            image = cv2.applyColorMap(frame, cv2.COLORMAP_OCEAN)
            #image = detector.overlayDetections(image, detections)
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
        playback_manager.frame_available.append(forwardImage)
        detector.mog_parameters.nof_bg_frames = 500
        detector._show_detections = True
        playback_manager.mapping_done.append(startDetector)
        #playback_manager.frame_available.insert(0, detector.compute_from_event)

        figure = TestFigure(playback_manager.togglePlay)
        main_window.setCentralWidget(figure)

        main_window.show()
        sys.exit(app.exec_())

    #test1()
    playbackTest()
