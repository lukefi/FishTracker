import sys
import cv2
from PyQt5 import QtCore, QtGui, QtWidgets

from playback_manager import PlaybackManager, TestFigure
from detector import Detector
from tracker import Tracker

class PatchTrack(QtCore.QObject):
    def __init__(self, display):
        print("Display: ", display)
        super().__init__()

        self.display = display
        self.figure = None

        self.app = QtWidgets.QApplication(sys.argv)
        if display:
            self.main_window = QtWidgets.QMainWindow()
            self.playback_manager = PlaybackManager(self.app, self.main_window)
        else:
            self.playback_manager = PlaybackManager(self.app, None)

        self.detector = Detector(self.playback_manager)
        self.tracker = Tracker(self.detector)
        self.playback_manager.fps = 100

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
        self.detector.initMOG()
        self.detector.computeAll()
        self.tracker.trackAll(self.detector.detections)
        self.playback_manager.play()

    def track(self):
        self.playback_manager.openTestFile()

        if self.display:
            self.playback_manager.frame_available.append(self.forwardImageDisplay)
        else:
            self.playback_manager.frame_available.append(self.forwardImage)

        self.detector.mog_parameters.nof_bg_frames = 500
        self.detector._show_detections = True
        self.playback_manager.mapping_done.append(self.startDetector)

        if self.display:
            self.figure = TestFigure(self.playback_manager.togglePlay)
            self.main_window.setCentralWidget(self.figure)

        print(self.detector.parameters)
        print(self.detector.parameters.mog_parameters)
        print(self.tracker.parameters)

        if self.display:
            self.main_window.show()

        sys.exit(self.app.exec_())


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--display', default=False, action='store_true', help="display frames as the patch is processed")
    args = parser.parse_args()

    display = str2bool(args.display)

    path_track = PatchTrack(display)
    path_track.track()
