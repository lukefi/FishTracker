"""
This file is part of Fish Tracker.
Copyright 2021, VTT Technical research centre of Finland Ltd.
Developed by: Mikael Uimonen.

Fish Tracker is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Fish Tracker is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Fish Tracker.  If not, see <https://www.gnu.org/licenses/>.
"""

import logging
import multiprocessing as mp
import os
import time
from datetime import datetime
from enum import Enum
from pathlib import Path

import hydra
from omegaconf import DictConfig, OmegaConf
from PyQt5 import QtCore

import file_handler as fh
import track_process as tp
from detector_parameters import DetectorParameters
from playback_manager import Worker
from tracker import AllTrackerParameters, FilterParameters, TrackerParameters


class BatchTrackInfo:
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

    active_processes_changed_signal = QtCore.pyqtSignal()
    exit_signal = QtCore.pyqtSignal(bool)

    def __init__(
        self,
        display,
        files,
        save_directory,
        parallel=1,
        create_directory=True,
        params_detector=None,
        params_tracker=None,
        secondary_track=False,
        save_detections=None,
        save_tracks=None,
        save_complete=None,
        flow_direction="left-to-right",
    ):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Display: {display}")

        self.logger.info(params_detector)

        self.files = files
        self.display = display
        self.secondary_track = secondary_track
        self.params_detector = params_detector
        self.params_tracker = params_tracker
        self.flow_direction = flow_direction

        if save_detections is None:
            self.logger.info("Using save_detections from conf.json.")
            self.save_detections = fh.getConfValue(fh.ConfKeys.batch_save_detections)
        else:
            self.save_detections = save_detections
        if save_tracks is None:
            self.logger.info("Using save_tracks from conf.json.")
            self.save_tracks = fh.getConfValue(fh.ConfKeys.batch_save_tracks)
        else:
            self.save_tracks = save_tracks
        if save_complete is None:
            self.logger.info("Using save_complete from conf.json.")
            self.save_complete = fh.getConfValue(fh.ConfKeys.batch_save_complete)
        else:
            self.save_complete = save_complete

        self.as_binary = fh.getConfValue(fh.ConfKeys.save_as_binary)

        if params_detector is None:
            self.logger.info("Using default parameters for Detector.")
            self.detector_params = DetectorParameters()
        else:
            self.detector_params = params_detector

        if params_tracker is None:
            self.logger.info("Using default parameters for Tracker.")
            primary = TrackerParameters()
            filter = FilterParameters()
            secondary = TrackerParameters()
            self.tracker_params = AllTrackerParameters(primary, filter, secondary)
        else:
            self.tracker_params = params_tracker

        if create_directory:
            date_time_directory = "batch_{}".format(
                datetime.now().strftime("%Y-%m-%d-%H%M%S")
            )
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
        For each file in files, creates a Worker that runs track and places it in thread
        pool. Main thread is occupied with a call to communicate method.
        """

        self.state = ProcessState.RUNNING
        id = 0

        worker = Worker(self.communicate)
        self.thread_pool.start(worker)
        self.logger.info(f"Creating workers for {self.total_processes} files")

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

        self.logger.info(f"Total processes: {self.n_processes}")

    def startProcess(self, file, id, test):
        parent_conn, child_conn = mp.Pipe()
        bt_info = BatchTrackInfo(id, file, parent_conn)
        self.processes.append(bt_info)

        worker = Worker(self.track, bt_info, child_conn, test)
        self.thread_pool.start(worker)

    def track(self, bt_info, child_conn, test):
        """
        Starts a process that runs tp.trackProcess with file as a parameter.
        Waits for the process to finish before exiting. This way thread_pool will
        not start more processes in parallel than is defined.
        """

        self.logger.info(f"Starting process: {bt_info.file}")

        self.active_processes.append(bt_info.id)
        self.active_processes_changed_signal.emit()

        process_info = tp.TrackProcessInfo(
            display=self.display,
            file=bt_info.file,
            save_directory=self.save_directory,
            connection=child_conn,
            params_detector_dict=self.detector_params.getParameterDict(),
            params_tracker_dict=self.tracker_params.getParameterDict(),
            secondary_tracking=self.secondary_track,
            test_file=test,
            save_detections=self.save_detections,
            save_tracks=self.save_tracks,
            save_complete=self.save_complete,
            as_binary=self.as_binary,
            flow_direction=self.flow_direction,
        )

        proc = mp.Process(
            target=tp.trackProcess, args=(process_info, self.params_tracker)
        )
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
        self.logger.info(f"File {bt_info.file} finished.")
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
        self.logger.info("Terminating")
        self.state = ProcessState.TERMINATING

    def communicate(self):
        """
        Polls through all running processes and forwards all messages to LogObject.
        """

        while (
            self.state is ProcessState.RUNNING
            or self.state is ProcessState.INITIALIZING
            or time.time() < self.exit_time + 1
        ):
            for bt_info in self.processes:
                if (
                    bt_info.process
                    and bt_info.process.is_alive()
                    and bt_info.connection.poll()
                ):
                    self.logger.info(bt_info.id, bt_info.connection.recv(), end="")
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
            except BrokenPipeError:
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
            self.logger.info(f"File [{bt_info.id}] terminated.")

        for bt_info in self.processes:
            if bt_info.process is not None:
                bt_info.process.terminate()

        self.exit_signal.emit(False)


@hydra.main(version_base=None, config_path="configs", config_name="default.yaml")
def main(cfg: DictConfig) -> None:
    if cfg.input.file_paths is None:
        raise ValueError("No input file paths provided in the configuration.")
    if cfg.output.directory is None or cfg.output.directory == "<output_dir>":
        raise ValueError("No output directory provided in the configuration.")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )
    # this environement varaible needs to be set for Qt to work in headless mode
    # (e.g., when running in a server environment without a display)
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

    logger = logging.getLogger(__name__)

    logger.info("Batch processing started")
    logger.info(f"Configuration:\n{OmegaConf.to_yaml(cfg)}")

    # Accept a list of image paths from the config
    files = [Path(p) for p in cfg.input.file_paths]
    logger.info(f"Found {len(files)} files to process")

    output_path = Path(cfg.output.directory)
    if not output_path.exists():
        logger.info(f"Creating output directory: {output_path}")
        os.makedirs(output_path)

    detector_params = DetectorParameters(**cfg.detector)

    tracker_params = AllTrackerParameters(
        primary=TrackerParameters(**cfg.tracker.primary_tracking),
        filter=FilterParameters(**cfg.tracker.filtering),
        secondary=TrackerParameters(**cfg.tracker.secondary_tracking),
    )

    batch_track = BatchTrack(
        display=False,
        files=files,
        save_directory=cfg.output.directory,
        parallel=cfg.batch_processing.parallel,
        params_detector=detector_params,
        params_tracker=tracker_params,
        secondary_track=True,
        save_detections=cfg.output.save_detections,
        save_tracks=cfg.output.save_tracks,
        save_complete=cfg.output.save_fish,
        flow_direction=cfg.input.flow_direction,
    )

    time.sleep(0.1)
    batch_track.beginTrack()

    while batch_track.state != ProcessState.FINISHED:
        time.sleep(0.1)

    # Start app for signal brokering
    logger.info("Batch processing finished")


if __name__ == "__main__":
    main()
