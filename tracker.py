import numpy as np
from sort import Sort

class Tracker:
    def __init__(self):
        self.parameters = TrackerParameters()
        self.tracks = []
        self.mot_tracker = None

    def trackAll(self, detection_frames):
        count = len(detection_frames)
        self.tracks = [[] for i in range(count)]
        self.mot_tracker = Sort(max_age=self.parameters.max_age,
                                min_hits=self.parameters.min_hits,
                                iou_threshold=self.parameters.iou_threshold)

        ten_perc = 0.1 * count
        print_limit = 0
        for i, frame in enumerate(detection_frames):
            if i > print_limit:
                print("Tracking:", int(float(i) / count * 100), "%")
                print_limit += ten_perc

            tracks = self.trackBase(frame)

            self.tracks[i] = tracks

            if len(tracks) > 0:
                print("Frame", i)
                print(tracks)

        print("Tracking: 100 %")

    def trackBase(self, frame):
        detections = np.array([np.min(d.corners,0).flatten().tolist() + np.max(d.corners,0).flatten().tolist() for d in frame if d.corners is not None]) #[d.corners for d in f]
        #print(detections)
        if len(detections) > 0:
            return self.mot_tracker.update(detections)
        else:
            return self.mot_tracker.update()

    def visualize(self, image, ind):
        if len(self.tracks) == 0 or len(self.tracks[ind]) == 0:
            return image

		## Visualize results	
  #      if self.length > 0:
  #          size_txt = 'Size (cm): ' + str(int(100*self.length))
  #      else:
  #          size_txt = 'Size (pix): ' + str(int(self.diff[1]*2))
  #      image = cv2.putText(image, size_txt, (int(self.center[1])-50, int(self.center[0])-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1, cv2.LINE_AA)

        #for i in range(self.data.shape[0]):
        #    cv2.line(image, (self.data[i,1], self.data[i,0]), (self.data[i,1], self.data[i,0]), \
        #        (int(255*colors[self.label][0]), int(255*colors[self.label][1]), int(255*colors[self.label][2])), 2)
        
        for tr in self.tracks[ind]:
            corners = np.array([[tr[0], tr[1]], [tr[2], tr[1]], [tr[2], tr[3]], [tr[0], tr[3]], [tr[0], tr[1]]])

            for i in range(0,3):
                cv2.line(image, (int(corners[i,1]),int(corners[i,0])), (int(corners[i+1,1]),int(corners[i+1,0])),  (255,255,255), 1)
            cv2.line(image, (int(corners[3,1]),int(corners[3,0])), (int(corners[0,1]),int(corners[0,0])),  (255,255,255), 1)

        return image


class TrackerParameters:
    def __init__(self):
        self.max_age = 20
        self.min_hits = 3
        self.iou_threshold = 0.1

    def __eq__(self, other):
        if not isinstance(other, TrackerParameters):
            return False
    
        return self.max_age == other.max_age \
            and self.min_hits == other.min_hits \
            and self.iou_threshold == other.iou_threshold


if __name__ == "__main__":
    import sys
    import cv2
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
        tracker = Tracker()

        playback_manager.fps = 5
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
