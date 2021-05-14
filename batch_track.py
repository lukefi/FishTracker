import sys, os, io, cv2
import subprocess
import time
from PyQt5 import QtCore, QtGui, QtWidgets
from queue import Queue

from playback_manager import PlaybackManager, TestFigure, Worker
from detector import Detector
from tracker import Tracker
from track_process import TrackProcess, getDefaultParser, getFiles
from output_widget import WriteStream

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
        """
        For each file in files, creates a Worker that runs track and places it in thread_pool.
        """

        for file in self.files:
            worker = Worker(self.track, file)
            self.thread_pool.start(worker)
            print("Created Worker for file ", file)

    def track(self, file):
        """
        Starts a subprocess running track_process.py with file as a parameter.
        Waits for the process to finish before exiting. This way thread_pool will
        not start more processes in parallel than is defined.
        """
        args = ['python', '-u', 'track_process.py', '-f', file]
        proc = subprocess.Popen(args, creationflags=self.creationflags, universal_newlines=True)
        #proc = subprocess.Popen(args, creationflags=self.creationflags, universal_newlines=True)
        print(proc)

        while proc.returncode is None:
            try:
                outs, errs = proc.communicate(timeout=1)
                print("Output:", outs)
                        
                if errs:
                    print(errs)
            except subprocess.TimeoutExpired:
                print("Timeout")
                pass
        
        print("Process returned: ", proc.returncode)

#class TrackIO(object):
#    def __init__(self):
#        self.io = None

#    def __enter__(self):
#        self.io = io.StringIO()

#    def __exit__(self):
#        self.io.close()

#    def write()


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
