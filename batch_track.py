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

    exit_signal = QtCore.pyqtSignal()

    def __init__(self, display, files, parallel=1):
        super().__init__()
        LogObject().print("Display: ", display)
        self.files = files
        self.display = display

        # Clear file
        tp.writeToFile("", 'w')

        self.thread_pool = QtCore.QThreadPool()
        self.thread_pool.setMaxThreadCount(parallel)

        self.processes = []
        self.batch_running = False
        self.exit_time = float('inf')
        self.n_processes = 0

    def beginTrack(self, test=False):
        """
        For each file in files, creates a Worker that runs track and places it in thread_pool.
        Main thread is occupied with a call to communicate method.
        """

        self.batch_running = True
        #worker = Worker(self.communicate)
        #self.thread_pool.start(worker)
        id = 0

        for file in self.files:
            parent_conn, child_conn = mp.Pipe()
            proc_info = ProcessInfo(id, file, parent_conn)
            self.processes.append(proc_info)

            worker = Worker(self.track, proc_info, child_conn, test)
            #worker.signals.result.connect(LogObject().print)
            self.thread_pool.start(worker)
            LogObject().print("Created Worker for file " + file)
            id += 1
            self.n_processes += 1

        LogObject().print("Total processes:", self.n_processes)
        self.communicate()

    def track(self, proc_info, child_conn, test):
        """
        Starts a process that runs tp.trackProcess with file as a parameter.
        Waits for the process to finish before exiting. This way thread_pool will
        not start more processes in parallel than is defined.
        """

        proc = mp.Process(target=tp.trackProcess, args=(self.display, proc_info.file, child_conn, test))
        proc_info.process = proc
        proc.start()

        proc.join()
        self.processFinished(proc_info)

    def processFinished(self, proc_info):
        """
        Reduces n_processes by one and if none are remaining, emits the exit_signal
        """

        LogObject().print("File {} finished.".format(proc_info.file))
        self.n_processes -= 1
        if self.n_processes <= 0:
            # Let main thread (running communicate) know the process is about to quit,
            # sleep for 2 seconds and emit signal.
            self.batch_running = False
            self.exit_time = time.time()
            time.sleep(2)
            self.exit_signal.emit()

    def communicate(self):
        """
        Polls through all running processes and forwards all messages to LogObject.
        """

        while(self.batch_running or time.time() < self.exit_time + 1):
            for proc_info in self.processes:
                if(proc_info.process and proc_info.process.is_alive() and proc_info.connection.poll()):
                    LogObject().print(proc_info.id, proc_info.connection.recv(), end="")

            time.sleep(0.01)


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

    batch_track = BatchTrack(args.display, files, args.parallel)
    batch_track.exit_signal.connect(app.exit)

    # Delay beginTrack
    timer = QtCore.QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: batch_track.beginTrack(args.test))
    timer.start(100)

    # Start app for signal brokering
    sys.exit(app.exec_())
