import sys, os, io, cv2
import multiprocessing as mp
import time
from PyQt5 import QtCore, QtGui, QtWidgets
from queue import Queue
from enum import Enum

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

class ProcessState(Enum):
    INITIALIZING = 1
    RUNNING = 2
    TERMINATING = 3
    FINISHED = 4

class BatchTrack(QtCore.QObject):
    """
    Container for multiple TrackProcess objects.
    """

    # Signaled when a process is started or finished.
    active_processes_changed_signal = QtCore.pyqtSignal()

    # Signaled when all processes are finished or terminated.
    exit_signal = QtCore.pyqtSignal(bool)

    def __init__(self, display, files, parallel=1):
        super().__init__()
        LogObject().print("Display: ", display)
        self.files = files
        self.display = display

        self.thread_pool = QtCore.QThreadPool()
        self.thread_pool.setMaxThreadCount(parallel + 1)

        self.processes = []
        self.active_processes = []
        self.state = ProcessState.INITIALIZING
        self.exit_time = time.time()
        self.n_processes = 0
        self.total_processes = len(self.files)

    def beginTrack(self, test=False):
        """
        For each file in files, creates a Worker that runs track and places it in thread_pool.
        Main thread is occupied with a call to communicate method.
        """

        self.state = ProcessState.RUNNING
        id = 0

        worker = Worker(self.communicate)
        self.thread_pool.start(worker)

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
        #self.communicate()

    def track(self, proc_info, child_conn, test):
        """
        Starts a process that runs tp.trackProcess with file as a parameter.
        Waits for the process to finish before exiting. This way thread_pool will
        not start more processes in parallel than is defined.
        """

        self.active_processes.append(proc_info.id)
        self.active_processes_changed_signal.emit()

        proc = mp.Process(target=tp.trackProcess, args=(self.display, proc_info.file, child_conn, test))
        proc_info.process = proc
        proc.start()

        proc.join()

        self.active_processes.remove(proc_info.id)
        self.active_processes_changed_signal.emit()

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

            if self.state is not ProcessState.TERMINATING:
                self.state = ProcessState.FINISHED
                self.exit_time = time.time()
                time.sleep(2)
                self.exit_signal.emit(True)

    def terminate(self):
        """
        Sets system state to TERMINATING, which leads to clean shutdown of the processes.
        """
        self.thread_pool.clear()
        LogObject().print("Terminating")
        self.state = ProcessState.TERMINATING

    def communicate(self):
        """
        Polls through all running processes and forwards all messages to LogObject.
        """
        
        while self.state is ProcessState.RUNNING or self.state is ProcessState.INITIALIZING or time.time() < self.exit_time + 1:
            for proc_info in self.processes:
                if(proc_info.process and proc_info.process.is_alive() and proc_info.connection.poll()):
                    LogObject().print(proc_info.id, proc_info.connection.recv(), end="")
            time.sleep(0.01)

        if self.state is ProcessState.TERMINATING:
            self.finishTerminated()

    def finishTerminated(self):
        """
        Handles the shutdown process initiated by method terminate.
        """
        for proc_info in self.processes:
            try:
                proc_info.connection.send((-1, "Terminate"))
            except BrokenPipeError as e:
                # Process not yet active
                pass

            while True:
                try:
                    id, msg = proc_info.connection.recv()
                    if id == -1:
                        break
                except EOFError:
                    break
                except ValueError:
                    # Received message with no id
                    continue
            LogObject().print("File [{}] terminated.".format(proc_info.id))

        for proc_info in self.processes:
            if proc_info.process is not None:
                proc_info.process.terminate()

        self.exit_signal.emit(False)


if __name__ == "__main__":
    import argparse

    app = QtWidgets.QApplication(sys.argv)

    parser = tp.getDefaultParser()
    parser.add_argument('-p', '--parallel', type=int, default=1, help="number of files processed simultaneously in parallel")
    args = parser.parse_args()
    files = tp.getFiles(args)

    LogObject().print(files)

    batch_track = BatchTrack(args.display, files, args.parallel)
    batch_track.exit_signal.connect(lambda b: app.exit())

    # Delay beginTrack
    timer = QtCore.QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: batch_track.beginTrack(args.test))
    timer.start(100)

    # Start app for signal brokering
    sys.exit(app.exec_())
