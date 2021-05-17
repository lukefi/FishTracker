import sys, os, io, cv2
import multiprocessing as mp
import time
from PyQt5 import QtCore, QtGui, QtWidgets
from queue import Queue

from playback_manager import PlaybackManager, TestFigure, Worker
from detector import Detector
from tracker import Tracker
import track_process as tp
from output_widget import WriteStream
from log_object import LogObject

class ProcessInfo(object):
    def __init__(self, id, file, connection):
        self.id = id
        self.file = file
        self.connection = connection
        self.process = None

class BatchTrack(QtCore.QObject):
    """
    Container for multiple TrackProcess objects.
    """
    def __init__(self, app, display, files, parallel=1):
        super().__init__()
        LogObject().print("Display: ", display)
        self.app = app
        self.files = files
        self.display = display

        # Clear file
        tp.writeToFile("", 'w')

        self.thread_pool = QtCore.QThreadPool()
        self.thread_pool.setMaxThreadCount(parallel + 1)

        self.processes = []
        self.batch_running = False

    def beginTrack(self, test=False):
        """
        For each file in files, creates a Worker that runs track and places it in thread_pool.
        """

        self.batch_running = True
        worker = Worker(self.communicate)
        self.thread_pool.start(worker)
        id = 0

        for file in self.files:
            parent_conn, child_conn = mp.Pipe()
            proc_info = ProcessInfo(id, file, parent_conn)
            self.processes.append(proc_info)

            worker = Worker(self.track, proc_info, child_conn)
            self.thread_pool.start(worker)
            LogObject().print("Created Worker for file " + file)
            id += 1

    def track(self, proc_info, child_conn):
        """
        Starts a process running trackProcess with file as a parameter.
        Waits for the process to finish before exiting. This way thread_pool will
        not start more processes in parallel than is defined.
        """

        proc = mp.Process(target=tp.trackProcess, args=(self.display, proc_info.file, child_conn))
        proc_info.process = proc
        proc.start()
        proc.join()

        LogObject().print("File", proc_info.file, "finished.")

    def communicate(self):
        while(self.batch_running):
            for proc_info in self.processes:
                if(proc_info.process and proc_info.process.is_alive() and proc_info.connection.poll()):
                    LogObject().print(proc_info.id, proc_info.connection.recv(), end="")

            time.sleep(0.2)


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

    parser = tp.getDefaultParser()
    parser.add_argument('-p', '--parallel', type=int, default=1, help="number of files processed simultaneously in parallel")
    args = parser.parse_args()
    files = tp.getFiles(args)

    LogObject().print(files)

    bath_track = BatchTrack(app, args.display, files, args.parallel)
    bath_track.beginTrack(args.test)

    sys.exit(app.exec_())
