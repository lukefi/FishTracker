import sys, os, cv2
import subprocess
import time
from PyQt5 import QtCore, QtGui, QtWidgets

from playback_manager import PlaybackManager, TestFigure, Worker
from detector import Detector
from tracker import Tracker
from track_process import TrackProcess, getDefaultParser, getFiles

class BatchTrack(QtCore.QObject):
    """
    Container for multiple TrackProcess objects.
    """
    def __init__(self, app, display, files, parallel=1):
        super().__init__()
        print("Display: ", display)
        self.app = app
        self.files = files
        self.creationflags = subprocess.CREATE_NEW_CONSOLE

        self.thread_pool = QtCore.QThreadPool()
        self.thread_pool.setMaxThreadCount(parallel)


    def beginTrack(self, test=False):
        for file in self.files:
            thread = Worker(self.track, file)
            self.thread_pool.start(thread)
            print("Created Worker for file ", file)

    def track(self, file):
        args = ['python', 'track_process.py', '-f', file]
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, creationflags=self.creationflags)
        print(proc)

        while proc.returncode is None:
            try:
                outs, errs = proc.communicate(timeout=1)
                if outs is not None:
                    print(outs)
            except subprocess.TimeoutExpired:
                pass
        
        print("Process returned: ", proc.returncode)


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

    app = QtWidgets.QApplication(sys.argv)

    parser = getDefaultParser()
    parser.add_argument('-p', '--parallel', type=int, default=1, help="number of files processed simultaneously in parallel")
    args = parser.parse_args()
    files = getFiles(args)

    print(files)

    bath_track = BatchTrack(app, args.display, files, args.parallel)
    bath_track.beginTrack(args.test)

    sys.exit(app.exec_())
