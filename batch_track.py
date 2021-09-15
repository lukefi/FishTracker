import sys, os, io, cv2
import multiprocessing as mp
import time
from PyQt5 import QtCore, QtGui, QtWidgets
from queue import Queue
from enum import Enum
from datetime import datetime

from playback_manager import PlaybackManager, TestFigure, Worker
from detector import Detector, DetectorParameters
from tracker import Tracker, AllTrackerParameters, TrackerParameters, FilterParameters
import file_handler as fh
import track_process as tp
from output_widget import WriteStream
from log_object import LogObject

class BatchTrackInfo(object):
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

    def __init__(self, display, files, save_directory, parallel=1, create_directory=True, params_detector=None, params_tracker=None, secondary_track=False):
        super().__init__()
        LogObject().print("Display: ", display)
        self.files = files
        self.display = display
        self.secondary_track = secondary_track

        self.save_detections = fh.getConfValue(fh.ConfKeys.batch_save_detections)
        self.save_tracks = fh.getConfValue(fh.ConfKeys.batch_save_tracks)
        self.save_complete = fh.getConfValue(fh.ConfKeys.batch_save_complete)
        self.as_binary = fh.getConfValue(fh.ConfKeys.save_as_binary)

        if params_detector is None:
            LogObject().print2("BatchTrack: Using default parameters for Detector.")
            self.detector_params = DetectorParameters()
        else:
            self.detector_params = params_detector

        if params_tracker is None:
            LogObject().print2("BatchTrack: Using default parameters for Tracker.")
            primary = TrackerParameters()
            filter = FilterParameters()
            secondary = TrackerParameters()
            self.tracker_params = AllTrackerParameters(primary, filter, secondary)
        else:
            self.tracker_params = params_tracker

        if create_directory:
            date_time_directory = "batch_{}".format(datetime.now().strftime("%Y-%m-%d-%H%M%S"))
            self.save_directory = os.path.join(save_directory, date_time_directory)
            if not os.path.exists(self.save_directory):
                os.mkdir(self.save_directory)
        else:
            self.save_directory = save_directory

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

        # If using test file (defined in conf.json)
        if test:
            file = fh.getTestFilePath()
            self.startProcess(file, id, True)
            self.n_processes = 1
            self.total_processes = 1

        # Normal use
        else:
            for file in self.files:
                self.startProcess(file, id, False)
                id += 1
                self.n_processes += 1

        LogObject().print("Total processes:", self.n_processes)

    def startProcess(self, file, id, test):
        parent_conn, child_conn = mp.Pipe()
        bt_info = BatchTrackInfo(id, file, parent_conn)
        self.processes.append(bt_info)

        worker = Worker(self.track, bt_info, child_conn, test)
        self.thread_pool.start(worker)
        LogObject().print("Created Worker for file " + file)

    def track(self, bt_info, child_conn, test):
        """
        Starts a process that runs tp.trackProcess with file as a parameter.
        Waits for the process to finish before exiting. This way thread_pool will
        not start more processes in parallel than is defined.
        """

        self.active_processes.append(bt_info.id)
        self.active_processes_changed_signal.emit()

        process_info = tp.TrackProcessInfo(
            display = self.display,
            file = bt_info.file,
            save_directory = self.save_directory,
            connection = child_conn,
            params_detector_dict = self.detector_params.getParameterDict(),
            params_tracker_dict = self.tracker_params.getParameterDict(),
            secondary_tracking = self.secondary_track,
            test_file = test,
            save_detections = self.save_detections,
            save_tracks = self.save_tracks,
            save_complete = self.save_complete,
            as_binary = self.as_binary
            )

        proc = mp.Process(target=tp.trackProcess, args=(process_info,))
        bt_info.process = proc
        proc.start()

        proc.join()

        self.active_processes.remove(bt_info.id)
        self.active_processes_changed_signal.emit()

        self.processFinished(bt_info)

    def processFinished(self, bt_info):
        """
        Reduces n_processes by one and if none are remaining, emits the exit_signal
        """

        LogObject().print("File {} finished.".format(bt_info.file))
        self.n_processes -= 1
        if self.n_processes <= 0:
            # Let main thread (running communicate) know the process is about to quit
            # and emit exit signal.

            if self.state is not ProcessState.TERMINATING:
                self.state = ProcessState.FINISHED
                self.exit_time = time.time()
                self.exit_signal.emit(True)

    def terminate(self):
        """
        Clears the thread pool and sets system state to TERMINATING,
        which leads to clean shutdown of the processes.
        """
        self.thread_pool.clear()
        LogObject().print("Terminating")
        self.state = ProcessState.TERMINATING

    def communicate(self):
        """
        Polls through all running processes and forwards all messages to LogObject.
        """
        
        while self.state is ProcessState.RUNNING or self.state is ProcessState.INITIALIZING or time.time() < self.exit_time + 1:
            for bt_info in self.processes:
                if(bt_info.process and bt_info.process.is_alive() and bt_info.connection.poll()):
                    LogObject().print(bt_info.id, bt_info.connection.recv(), end="")
            time.sleep(0.01)

        if self.state is ProcessState.TERMINATING:
            self.finishTerminated()

    def finishTerminated(self):
        """
        Handles the shutdown process initiated by method terminate.
        """
        for bt_info in self.processes:
            try:
                bt_info.connection.send((-1, "Terminate"))
            except BrokenPipeError as e:
                # Process not yet active
                pass

            while True:
                try:
                    id, msg = bt_info.connection.recv()
                    if id == -1:
                        break
                except EOFError:
                    break
                except ValueError:
                    # Received message with no id
                    continue
            LogObject().print("File [{}] terminated.".format(bt_info.id))

        for bt_info in self.processes:
            if bt_info.process is not None:
                bt_info.process.terminate()

        self.exit_signal.emit(False)


if __name__ == "__main__":
    import argparse

    app = QtWidgets.QApplication(sys.argv)

    parser = tp.getDefaultParser()
    parser.add_argument('-p', '--parallel', type=int, default=4, help="number of files processed simultaneously in parallel")

    args = parser.parse_args()
    files = tp.getFiles(args)
    save_directory = fh.getLatestSaveDirectory()

    LogObject().print(files)

    batch_track = BatchTrack(args.display, files, save_directory, args.parallel,params_detector=DetectorParameters(None, 15, 15, 9, 15, 15), secondary_track=True)
    batch_track.exit_signal.connect(lambda b: app.exit())

    # Delay beginTrack
    timer = QtCore.QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: batch_track.beginTrack(args.test))
    timer.start(100)

    # Start app for signal brokering
    sys.exit(app.exec_())
