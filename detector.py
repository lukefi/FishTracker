"""
This file is part of Fish Tracker.
Copyright 2021, VTT Technical research centre of Finland Ltd.
Developed by: Otto Korkalo and Mikael Uimonen.

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

import datetime
import glob
import logging
import sys
import traceback

import cv2
import numpy as np
import pandas as pd
import seaborn as sns
import sklearn.cluster as cluster
from PyQt5 import QtCore, QtWidgets
from tqdm import tqdm

from background_subtractor import BackgroundSubtractor
from detector_parameters import DetectorParameters
from mog_parameters import MOGParameters
from playback_manager import PlaybackManager, TestFigure


def nothing(x):
    pass


def round_up_to_odd(f):
    return np.ceil(f) // 2 * 2 + 1


class Detector(QtCore.QObject):
    # When detector parameters change.
    parameters_changed_signal = QtCore.pyqtSignal()

    # When detector state changes.
    state_changed_signal = QtCore.pyqtSignal()

    # When displayed results change (e.g. when a new frame is displayed).
    # Parameter: number of detections displayed.
    data_changed_signal = QtCore.pyqtSignal(int)

    # When detector has computed all available frames.
    all_computed_signal = QtCore.pyqtSignal()

    def __init__(self, image_provider):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.image_provider = image_provider
        self.bg_subtractor = BackgroundSubtractor(image_provider)
        self.parameters = None
        self.applied_parameters = None

        self.resetParameters()
        self.detections = [None]
        self.vertical_detections = []

        self.current_ind = 0
        self.current_len = 0

        self.bg_subtractor.state_changed_signal.connect(self.state_changed_signal)
        self.bg_subtractor.parameters_changed_signal.connect(
            self.parameters_changed_signal
        )

        self._show_echogram_detections = False
        self.show_bgsub = False

        # [flag] Whether detector is computing all the frames.
        self.computing = False

        # [trigger] Terminate computing process.
        self.stop_computing = False

        # [flag] Calculate detections on event. Otherwise uses precalculated results.
        self.compute_on_event = False

    def resetParameters(self):
        self.setMOGParameters(MOGParameters())
        self.setDetectorParameters(DetectorParameters())

    def setDetectorParameters(self, parameters: DetectorParameters):
        if self.parameters is not None:
            self.parameters.values_changed_signal.disconnect(
                self.parameters_changed_signal
            )

        # self.bg_subtractor.setParameters(parameters.mog_parameters)
        self.parameters = parameters
        self.parameters.values_changed_signal.connect(self.parameters_changed_signal)
        self.parameters_changed_signal.emit()

    def setMOGParameters(self, parameters: MOGParameters):
        self.bg_subtractor.setParameters(parameters)

    def initMOG(self, clear_detections=True):
        if clear_detections:
            self.clearDetections()
        self.bg_subtractor.initMOG()

    def compute_from_event(self, tuple):
        if tuple is None:
            return

        ind, img = tuple
        if self.compute_on_event:
            self.compute(ind, img)
        else:
            self.data_changed(ind)

    def compute(self, ind, image, get_images=False):
        images = self.computeBase(ind, image, get_images)
        self.data_changed(ind)
        if get_images:
            return images

    def data_changed(self, ind):
        dets = self.detections[ind]
        self.current_ind = ind
        self.current_len = 0 if dets is None else len(self.detections[ind])
        self.data_changed_signal.emit(self.current_len)

    def getPolarTransform(self):
        if hasattr(self.image_provider, "playback_thread"):
            return self.image_provider.playback_thread.polar_transform
        else:
            return None

    def computeBase(self, ind, image, get_images=False, show_size=True):
        params = self.parameters

        image_o = image_o_gray = image
        fg_mask_mog = self.bg_subtractor.subtractBG(image_o)
        if fg_mask_mog is None:
            return

        fg_mask_cpy = fg_mask_mog
        fg_mask_filt = cv2.medianBlur(
            fg_mask_cpy,
            params.getParameter(DetectorParameters.ParametersEnum.median_size),
        )

        data_tr = np.nonzero(np.asarray(fg_mask_filt))
        data = np.asarray(data_tr).T
        detections = []

        if get_images:
            image_o_rgb = cv2.applyColorMap(image_o, cv2.COLORMAP_OCEAN)

        if data.shape[0] >= params.getParameter(
            DetectorParameters.ParametersEnum.min_fg_pixels
        ):
            # DBSCAN clusterer, NOTE: parameters should be in UI / read from file
            clusterer = cluster.DBSCAN(
                eps=params.getParameter(DetectorParameters.ParametersEnum.dbscan_eps),
                min_samples=params.getParameter(
                    DetectorParameters.ParametersEnum.dbscan_min_samples
                ),
            )
            labels = clusterer.fit_predict(data)

            data = data[labels != -1]
            labels = labels[labels != -1]

            if labels.shape[0] > 0:
                polar_transform = self.getPolarTransform()

                # Get frame timestamp for this frame
                frame_pc_time = self.getFramePCTime(
                    ind
                )  # getframepctime gets the time of first frame
                frame_pc_time = datetime.datetime.fromtimestamp(
                    frame_pc_time * 1e-6, tz=datetime.UTC
                )

                for label in np.unique(labels):
                    foo = data[labels == label]
                    if foo.shape[0] < 2:
                        continue

                    d = Detection(label)
                    d.init_from_data(
                        foo,
                        params.getParameter(
                            DetectorParameters.ParametersEnum.detection_size
                        ),
                        polar_transform,
                    )
                    fps = self.getFrameRate()
                    if fps is not None and frame_pc_time is not None:
                        current_time_since_start = ind * 1 / fps
                        time = frame_pc_time + datetime.timedelta(
                            seconds=current_time_since_start
                        )
                    else:
                        time = None

                    d.frame_pc_time = time
                    detections.append(d)

                if get_images:
                    colors = sns.color_palette("deep", np.unique(labels).max() + 1)
                    for d in detections:
                        image_o_rgb = d.visualize(
                            image_o_rgb, colors[d.label], show_size
                        )

        self.detections[ind] = detections

        if get_images:
            return (fg_mask_mog, image_o_gray, image_o_rgb, fg_mask_filt)

    def computeAll(self):
        self.computing = True

        if self.bg_subtractor.parametersDirty():
            self.initMOG()
            if self.bg_subtractor.parametersDirty():
                self.logger.info("Stopped before detecting.")
                self.abortComputing(True)
                return

        count = self.image_provider.getFrameCount()
        for ind in tqdm(range(count), desc="Detecting", unit="frames"):
            img = self.image_provider.getFrame(ind)
            self.computeBase(ind, img)

            if self.stop_computing:
                self.logger.info(f"Stopped detecting at {ind}")
                self.abortComputing(False)
                return

        self.computing = False
        # self.detections_clearable = True
        self.applied_parameters = self.parameters.copy()

        self.updateVerticalDetections()

        self.state_changed_signal.emit()
        self.all_computed_signal.emit()

    def updateVerticalDetections(self):
        self.vertical_detections = [
            [d.distance for d in dets if d.center is not None]
            if dets is not None
            else []
            for dets in self.detections
        ]

    def abortComputing(self, mog_aborted):
        self.stop_computing = False
        self.computing = False
        self.compute_on_event = True

        self.state_changed_signal.emit()
        self.applied_parameters = None

        if mog_aborted:
            self.bg_subtractor.abortComputing()

    def clearDetections(self):
        nof_frames = self.image_provider.getFrameCount()
        self.detections = [None] * nof_frames
        self.vertical_detections = []
        # self.detections_clearable = False
        self.applied_parameters = None
        self.compute_on_event = True
        self.state_changed_signal.emit()
        self.data_changed_signal.emit(0)

    def overlayDetections(self, image, detections=None, show_size=True):
        if detections is None:
            detections = self.getCurrentDetection()

        colors = sns.color_palette("deep", max([0] + [d.label + 1 for d in detections]))
        for d in detections:
            image = d.visualize(image, colors[d.label], show_size)

        return image

    def overlayDetectionColors(self, image, detections=None):
        if detections is None:
            detections = self.getCurrentDetection()

        colors = sns.color_palette("deep", max([0] + [d.label + 1 for d in detections]))
        for d in detections:
            image = d.visualizeArea(image, colors[d.label])

        return image

    def setParameter(self, key, value):
        self.parameters.setKeyValuePair(key, value)

    def setShowEchogramDetections(self, value):
        self._show_echogram_detections = value
        if not self._show_echogram_detections:
            self.data_changed_signal.emit(0)

    def toggleShowBGSubtraction(self):
        self.show_bgsub = not self.show_bgsub

    def setShowBGSubtraction(self, value):
        self.show_bgsub = value

    def getDetection(self, ind):
        try:
            dets = self.detections[ind]
            if dets is None:
                return []

            return [d for d in dets if d.center is not None]
        except IndexError:
            self.logger.error(traceback.format_exc())

    def getDetections(self):
        return [
            [d for d in dets if d.center is not None] if dets is not None else []
            for dets in self.detections
        ]

    def getCurrentDetection(self):
        return self.getDetection(self.current_ind)

    def getParameterDict(self):
        if self.parameters is not None:
            detector_params = self.parameters.getParameterDict()
            bg_sub_params = self.bg_subtractor.mog_parameters.getParameterDict()

            return {"bg_subtractor": bg_sub_params, "detector": detector_params}
        else:
            return None

    def setParameterDict(self, param_dict, set_as_applied=False):
        if "detector" in param_dict.keys():
            self.parameters.setParameterDict(param_dict["detector"])
            if set_as_applied:
                self.applied_parameters = self.parameters.copy()
        else:
            self.logger.warning("Detector parameters not found.")

        if "bg_subtractor" in param_dict.keys():
            self.bg_subtractor.mog_parameters.setParameterDict(
                param_dict["bg_subtractor"]
            )
            if set_as_applied:
                self.bg_subtractor.applyParameters()
        else:
            self.logger.warning("Background subtractor parameters not found.")

    def bgSubtraction(self, image):
        median_size = self.parameters.getParameter(
            DetectorParameters.ParametersEnum.median_size
        )
        return self.bg_subtractor.subtractBGFiltered(image, median_size)

    def parametersDirty(self):
        return (
            self.parameters != self.applied_parameters
            or self.bg_subtractor.parametersDirty()
        )

    def allCalculationAvailable(self):
        return self.parametersDirty() and not self.bg_subtractor.initializing

    def saveDetectionsToFile(self, path):
        """
        Writes current detections to a file at path. Values are separated by ';'.
        """

        try:
            rows = []
            for frame, dets in enumerate(self.detections):
                if not dets:
                    continue
                for d in dets:
                    if d.corners is None:
                        continue

                    row = {
                        "frame": frame,
                        "length": d.length,
                        "distance": d.distance,
                        "angle": d.angle,
                        "aspect": d.aspect,
                        "l2aratio": d.l2a_ratio,
                        "time": d.frame_pc_time,
                    }
                    # Add corners as separate columns
                    for i, (cy, cx) in enumerate(d.corners[0:4], 1):
                        row[f"corner{i} x"] = cx
                        row[f"corner{i} y"] = cy
                    rows.append(row)

            # Define columns to ensure consistent CSV structure
            columns = [
                "frame",
                "length",
                "distance",
                "angle",
                "aspect",
                "l2aratio",
                "time",
                "corner1 x",
                "corner1 y",
                "corner2 x",
                "corner2 y",
                "corner3 x",
                "corner3 y",
                "corner4 x",
                "corner4 y",
            ]

            # if rows is empty, create empty DataFrame with defined columns
            if rows:
                df = pd.DataFrame(rows, columns=columns)
            else:
                df = pd.DataFrame(columns=columns)

            df.to_csv(
                path,
                sep=";",
                index=False,
                float_format="%.3f",
                columns=columns,
            )
            self.logger.info(f"Detections saved to path: {path}")

        except PermissionError:
            self.logger.error(f"Cannot open file {path}. Permission denied.")

    def loadDetectionsFromFile(self, path):
        """
        Loads a file from path. Values are expected to be separated by ';'.
        """
        try:
            with open(path) as file:
                self.clearDetections()
                nof_frames = self.image_provider.getFrameCount()
                ignored_dets = 0

                header = file.readline()

                for line in file:
                    split_line = line.split(";")
                    frame = int(split_line[0])

                    if frame >= nof_frames:
                        ignored_dets += 1
                        continue

                    length = float(split_line[1])
                    distance = float(split_line[2])
                    angle = float(split_line[3])
                    aspect = float(split_line[4])
                    l2a_ratio = float(split_line[5])
                    frame_pc_time = int(split_line[6] * 1e6)

                    c1 = [float(split_line[8]), float(split_line[7])]
                    c2 = [float(split_line[10]), float(split_line[9])]
                    c3 = [float(split_line[12]), float(split_line[11])]
                    c4 = [float(split_line[14]), float(split_line[13])]
                    corners = np.array([c1, c2, c3, c4])

                    det = Detection(0)
                    det.init_from_file(
                        corners,
                        length,
                        distance,
                        angle,
                        aspect,
                        l2a_ratio,
                        frame_pc_time,
                    )

                    if self.detections[frame] is None:
                        self.detections[frame] = [det]
                    else:
                        self.detections[frame].append(det)

                self.updateVerticalDetections()
                self.compute_on_event = False
                if ignored_dets > 0:
                    self.logger.warning(
                        f"Encountered {ignored_dets} detections that were out of range "
                        f"{nof_frames}."
                    )

        except PermissionError:
            self.logger.error(f"Cannot open file {path}. Permission denied.")
        except ValueError as e:
            self.logger.error(
                f"Invalid values encountered in {path}, "
                f"when trying to import detections. {e}"
            )

    def getSaveDictionary(self):
        """
        Returns a dictionary of detection data to be saved in SaveManager.
        """
        detections = {}
        for frame, dets in enumerate(self.detections):
            if dets is None:
                continue

            dets_in_frame = [
                d.convertToWritable() for d in dets if d.corners is not None
            ]
            if len(dets_in_frame) > 0:
                detections[str(frame)] = dets_in_frame

        return detections

    def applySaveDictionary(self, parameters, data):
        """
        Load detections from data provided by SaveManager.
        """
        self.clearDetections()

        self.setParameterDict(parameters, True)

        polar_transform = self.getPolarTransform()

        for frame in range(len(self.detections)):
            frame_dets = []
            str_frame = str(frame)
            if str_frame in data.keys():
                for det_data in data[str_frame]:
                    label = det_data[0]
                    det_data = det_data[1]
                    det = Detection(int(label))
                    detection_size = self.parameters.getParameter(
                        DetectorParameters.ParametersEnum.detection_size
                    )
                    det.init_from_data(det_data, detection_size, polar_transform)
                    frame_dets.append(det)

            try:
                self.detections[frame] = frame_dets
            except IndexError as e:
                print(frame, len(self.detections))
                raise e

        self.updateVerticalDetections()
        self.compute_on_event = False
        self.state_changed_signal.emit()
        self.all_computed_signal.emit()

    def getFrameRate(self):
        """
        Get the frame rate (FPS) from the image provider.

        Returns:
            float: Frames per second or None if not available.
        """
        if hasattr(self.image_provider, "frameRate"):
            return self.image_provider.frameRate
        elif hasattr(self.image_provider, "fps"):
            return self.image_provider.fps
        else:
            return None

    def getFPSFromDetections(self):
        """
        Calculate FPS from frame_pc_time values in the detections.
        Returns the calculated FPS or None if not enough data.
        """
        # collect timestamps from detections
        timestamps = []
        for dets in self.detections:
            if dets is not None and len(dets) > 0:
                for d in dets:
                    if hasattr(d, "frame_pc_time") and d.frame_pc_time:
                        timestamps.append(d.frame_pc_time)

        # need at least two timestamps to calculate FPS
        if len(timestamps) < 2:
            return self.getFrameRate()

        # sort timestamps and calculate differences
        timestamps.sort()
        diffs = []
        for i in range(1, len(timestamps)):
            diff_seconds = (timestamps[i] - timestamps[i - 1]).total_seconds()
            if diff_seconds > 0:
                diffs.append(diff_seconds)

        # calculate FPS if we have time differences
        if diffs:
            avg_diff = sum(diffs) / len(diffs)
            if avg_diff > 0:
                return 1.0 / avg_diff

        return self.getFrameRate()

    def getPCTime(self):
        """
        Return frame sonar timestamp from image provider.
        """
        if hasattr(self.image_provider, "getFrameTimeStamp"):
            timestamp = self.image_provider.getFrameTimeStamp()
            return 0 if timestamp is None else timestamp
        else:
            return 0

    def getFramePCTime(self, ind=None):
        """
        Get the PC timestamp for a frame from the image provider.

        Args:
            ind: Frame index. If None, uses current index.

        Returns:
            Frame timestamp or 0 if not available.
        """
        if hasattr(self.image_provider, "getFrameTimeStamp"):
            return self.image_provider.getFrameTimeStamp() or 0
        return 0


class Detection:
    def __init__(self, label):
        self.label = label
        self.data = None
        self.diff = None
        self.center = None
        self.corners = None

        self.length = 0  # detection (fish) length
        self.distance = 0  # range from sonar to detection (center?)
        self.angle = 0  # polar coordinate angle (termed theta in Arisfish)
        self.aspect = 0  # aspect is angle of the main axis of the detetion target
        # relative to the acoustic axis
        self.l2a_ratio = 0
        self.frame_pc_time = 0

    def __repr__(self):
        return f'Detection "{self.label}" d:{self.distance:.1f}, a:{self.angle:.1f}'

    def init_from_data(self, data, detection_size, polar_transform):
        """
        Initialize detection parameters from the pixel data from the clusterer or
        detection algorithm. Saved pixel data can also be used to (re)initialize
        the detection.
        """
        self.data = np.asarray(data)

        ca = np.cov(data, y=None, rowvar=0, bias=1)
        v, vect = np.linalg.eig(ca)
        tvect = np.transpose(vect)
        ar = np.dot(data, np.linalg.inv(tvect))

        # NOTE a fixed parameter --> to UI / file.
        if ar.shape[0] > detection_size:  # 10:
            mina = np.min(ar, axis=0)
            maxa = np.max(ar, axis=0)
            diff = (maxa - mina) * 0.5

            center = mina + diff

            # Get the 4 corners by subtracting and adding half the bounding boxes height
            # and width to the center
            corners = np.array(
                [
                    center + [-diff[0], -diff[1]],
                    center + [diff[0], -diff[1]],
                    center + [diff[0], diff[1]],
                    center + [-diff[0], diff[1]],
                ]
            )  # , \
            # center+[-diff[0],-diff[1]]])

            self.diff = diff

            det_size = ar.shape[0]
            det_length = diff[1] * 2
            self.l2a_ratio = det_length / det_size

            # Use the the eigenvectors as a rotation matrix and rotate the corners and
            # the center back
            self.corners = np.dot(corners, tvect)
            self.center = np.dot(center, tvect)

            if polar_transform is not None:
                metric_diff = polar_transform.pix2metCI(diff[0], diff[1])
                self.length = float(2 * metric_diff[1])
                self.distance, self.angle = polar_transform.cart2polMetric(
                    self.center[0], self.center[1], True
                )
                self.distance = float(self.distance)
                self.angle = float(self.angle / np.pi * 180 + 90)
                # get the aspect angle in degrees from th  eigenvector,
                # 0 means that the length axis of the fish is perpendicular to the
                # sound axis
                self.aspect = float(np.arcsin(tvect[0, 0]) / np.pi * 180 + 90)

    def init_from_file(
        self, corners, length, distance, angle, aspect, l2a_ratio=0, frame_pc_time=0
    ):
        """
        Initialize detection parameters from a csv file. Data is not stored when
        exporting a csv file, which means it cannot be recovered here.
        This mainly affects the visualization of the detection.
        """
        self.corners = np.array(corners)
        self.center = np.average(self.corners, axis=0)
        self.diff = self.center - self.corners[0]
        self.length = length
        self.distance = distance
        self.angle = angle
        self.aspect = aspect
        self.l2a_ratio = l2a_ratio
        self.frame_pc_time = frame_pc_time

    def visualize(self, image, color, show_text, show_detection=True):
        if self.corners is None:
            return image

        # Draw size text
        if show_text:
            if self.length > 0:
                size_txt = self.getSizeText()
                image = cv2.putText(
                    image,
                    size_txt,
                    (int(self.center[1]) - 20, int(self.center[0]) - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )

        # Draw detection area and bounding box
        if show_detection:
            self.visualizeArea(image, color)

            for i in range(0, 3):
                cv2.line(
                    image,
                    (int(self.corners[i, 1]), int(self.corners[i, 0])),
                    (int(self.corners[i + 1, 1]), int(self.corners[i + 1, 0])),
                    (255, 255, 255),
                    1,
                )
            cv2.line(
                image,
                (int(self.corners[3, 1]), int(self.corners[3, 0])),
                (int(self.corners[0, 1]), int(self.corners[0, 0])),
                (255, 255, 255),
                1,
            )

        return image

    def visualizeArea(self, image, color):
        if self.data is not None:
            _color = (int(255 * color[0]), int(255 * color[1]), int(255 * color[2]))
            for i in range(self.data.shape[0]):
                cv2.line(
                    image,
                    (self.data[i, 1], self.data[i, 0]),
                    (self.data[i, 1], self.data[i, 0]),
                    _color,
                    2,
                )

        return image

    def getSizeText(self):
        return "Size: " + str(int(100 * self.length))

    def getMessage(self):
        # This message was used to send data to tracker process (C++) or save detections
        # to file
        if self.diff is None:
            return ""

        return (
            str(int(self.center[1] * 10))
            + " "
            + str(int(self.center[0] * 10))
            + " "
            + str(int(self.diff[1] * 2))
        )

    def cornersToString(self, delim):
        if self.corners is None:
            return ""

        base = "{:.2f}" + delim + "{:.2f}"
        return delim.join(base.format(cx, cy) for cy, cx in self.corners[0:4])

    def convertToWritable(self):
        """
        Returns data in applicable format to be used by SaveManager
        """
        return [int(self.label), list(map(lambda x: [int(x[0]), int(x[1])], self.data))]


class DetectorDisplay:
    def __init__(self):
        self.array = [cv2.imread(file, 0) for file in sorted(glob.glob("out/*.png"))]
        self.detector = Detector(self)
        self.detector._show_detections = True
        self._show_echogram_detections = True

    def run(self):
        self.showWindow()
        self.detector.initMOG()

        for i in range(self.getFrameCount()):
            self.readParameters()
            images = self.detector.compute(i, self.getFrame(i), True)
            self.logger.info(images)
            self.updateWindows(*images)

    def showWindow(self):
        cv2.namedWindow("fg_mask_mog", cv2.WINDOW_NORMAL)
        cv2.namedWindow("image_o_rgb", cv2.WINDOW_NORMAL)
        cv2.namedWindow("image_o_gray", cv2.WINDOW_NORMAL)
        cv2.namedWindow("fg_mask_filt", cv2.WINDOW_NORMAL)

        cv2.createTrackbar("mog_var_thresh", "image_o_rgb", 5, 30, nothing)
        cv2.createTrackbar("median_size", "image_o_rgb", 1, 21, nothing)
        cv2.createTrackbar("min_fg_pixels", "image_o_rgb", 10, 100, nothing)

        mog_var_thresh = self.detector.bg_subtractor.mog_parameters.getParameter(
            MOGParameters.ParametersEnum.mog_var_thresh
        )
        min_fg_pixels = self.detector.parameters.getParameter(
            DetectorParameters.ParametersEnum.min_fg_pixels
        )
        median_size = self.detector.parameters.getParameter(
            DetectorParameters.ParametersEnum.median_size
        )

        cv2.setTrackbarPos("mog_var_thresh", "image_o_rgb", mog_var_thresh)
        cv2.setTrackbarPos("min_fg_pixels", "image_o_rgb", min_fg_pixels)
        cv2.setTrackbarPos("median_size", "image_o_rgb", median_size)

    def updateWindows(self, fg_mask_mog, image_o_gray, image_o_rgb, fg_mask_filt):
        pos_step = 600

        cv2.moveWindow("fg_mask_mog", pos_step * 0, 20)
        cv2.moveWindow("image_o_gray", pos_step * 1, 20)
        cv2.moveWindow("image_o_rgb", pos_step * 2, 20)
        cv2.moveWindow("fg_mask_filt", pos_step * 3, 20)

        cv2.imshow("fg_mask_mog", fg_mask_mog)
        cv2.imshow("image_o_gray", image_o_gray)
        cv2.imshow("image_o_rgb", image_o_rgb)
        cv2.imshow("fg_mask_filt", fg_mask_filt)

        sleep = cv2.getTrackbarPos("sleep", "image_o_rgb")
        key = cv2.waitKey(sleep)
        if key == 32:
            sleep = -sleep

    def readParameters(self):
        # Read parameter values from trackbars
        self.detector.bg_subtractor.mog_parameters.mog_var_thresh = cv2.getTrackbarPos(
            "mog_var_thresh", "image_o_rgb"
        )
        min_fg_pixels = cv2.getTrackbarPos("min_fg_pixels", "image_o_rgb")
        self.detector.parameters.setParameter(
            DetectorParameters.ParametersEnum.min_fg_pixels, min_fg_pixels
        )
        median_size = int(
            round_up_to_odd(cv2.getTrackbarPos("median_size", "image_o_rgb"))
        )
        self.detector.parameters.setParameter(
            DetectorParameters.ParametersEnum.median_size, median_size
        )

    def getFrameCount(self):
        return len(self.array)

    def getFrame(self, ind):
        return self.array[ind]


def simpleTest():
    dd = DetectorDisplay()
    dd.run()


def playbackTest():
    def forwardImage(tuple):
        ind, frame = tuple
        detections = detector.getCurrentDetection()

        image = cv2.applyColorMap(frame, cv2.COLORMAP_OCEAN)
        image = detector.overlayDetections(image, detections)

        figure.displayImage((ind, image))

    def startDetector():
        detector.initMOG()
        playback_manager.play()

    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    playback_manager.fps = 10
    playback_manager.openTestFile()
    playback_manager.frame_available.connect(forwardImage)
    detector = Detector(playback_manager)
    detector.bg_subtractor.mog_parameters.nof_bg_frames = 100
    detector.setShowEchogramDetections(True)
    playback_manager.mapping_done.connect(startDetector)
    playback_manager.frame_available_immediate.append(detector.compute_from_event)

    figure = TestFigure(playback_manager.togglePlay)
    main_window.setCentralWidget(figure)

    main_window.show()
    sys.exit(app.exec_())


def benchmark():
    def runDetector():
        detector.computeAll()
        print("All done.")
        main_window.close()

    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    detector = Detector(playback_manager)
    detector.setNofBGFrames(1000)
    playback_manager.mapping_done.connect(runDetector)
    main_window.show()
    playback_manager.openTestFile()
    sys.exit(app.exec_())


if __name__ == "__main__":
    # simpleTest()
    playbackTest()
    # benchmark()
