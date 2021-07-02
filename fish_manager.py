from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt

import numpy as np
import cv2
import seaborn as sns
from bisect import insort
from enum import IntEnum
from tracker import Tracker
from log_object import LogObject

fish_headers = ["", "ID", "Length", "Direction", "Frame in", "Frame out", "Duration", "Detections"]
fish_sort_keys = [lambda f: f.color_ind, lambda f: f.id, lambda f: -f.length, lambda f: f.dirSortValue(), lambda f: f.frame_in, lambda f: f.frame_out, lambda f: f.duration, lambda f: len(f.tracks)]

N_COLORS = 16
color_palette = sns.color_palette('bright', N_COLORS)
pyqt_palette = [QtGui.QColor.fromRgbF(*c) for c in color_palette]

color_palette_deep = sns.color_palette('deep', N_COLORS)
pyqt_palette_deep = [QtGui.QColor.fromRgbF(*c) for c in color_palette_deep]

# Implements functionality to store and manage the tracked fish items.
# Items can be edited with the functions defined here through e.g. fish_list.py.
class FishManager(QtCore.QAbstractTableModel):
    updateContentsSignal = QtCore.pyqtSignal()
    updateSelectionSignal = QtCore.pyqtSignal(QtCore.QItemSelection, QtCore.QItemSelectionModel.SelectionFlags)

    def __init__(self, playback_manager, tracker):
        super().__init__()
        self.playback_manager = playback_manager
        if self.playback_manager is not None:
            self.playback_manager.file_opened.connect(lambda x: self.clear())
            self.playback_manager.file_closed.connect(lambda: self.clear())

        self.tracker = tracker
        if tracker is not None:
            self.tracker.init_signal.connect(self.clear)
            self.tracker.all_computed_signal.connect(self.updateDataFromTracker)

        # All fish items currently stored.
        self.all_fish = {}

        # Fish items that are currently displayed.
        self.fish_list = []

        self.selected_rows = set()

        # Index for fish_sort_keys array, that contains lambda functions to sort the currently shown array.
        # Default: ID
        self.sort_ind = 1

        # Sort direction, ascending or descending
        self.sort_order = QtCore.Qt.DescendingOrder

        # Min number of detections required for a fish to be included in fish_list
        self.min_detections = 2

        # Percentile with which the shown length is determined
        self.length_percentile = 50

        # If fish (tracks) are shown.
        self.show_fish = True

        # If fish (tracks) are shown in Echogram.
        self.show_echogram_fish = True

        self.show_bounding_box = True
        self.show_id = True
        self.show_detection_size = True
        self.update_fish_colors = False

        # Inverted upstream / downstream.
        self.up_down_inverted = False

    def testPopulate(self, frame_count):
        """
        Simple test function.
        """

        self.all_fish = {}
        self.fish_list.clear()
        for i in range(10):
            f = FishEntry(i + 1)
            f.length = round(np.random.normal(1.2, 0.1), 3)
            f.direction = SwimDirection(np.random.randint(low=0, high=2))
            f.frame_in = np.random.randint(frame_count)
            f.frame_out = min(f.frame_in + np.random.randint(100), frame_count)
            f.duration = f.frame_out - f.frame_in + 1
            self.all_fish[f.id] = f

        self.trimFishList()

    def trimFishList(self, force_color_update=False):
        """
        Updates shown table (fish_list) from all instances containing dictionary (all_fish).
        fish_list is trimmed based on the minimum duration.
        """
        fl = [fish for fish in self.all_fish.values() if fish.duration >= self.min_detections]

        reverse = self.sort_order != QtCore.Qt.AscendingOrder
        fl.sort(key=fish_sort_keys[self.sort_ind], reverse=reverse)

        len_new = len(fl)
        len_old = len(self.fish_list)

        if len_new > len_old:
            self.beginInsertRows(QtCore.QModelIndex(), len_old, max(0, len_new-1))
            self.fish_list = fl
            self.endInsertRows()
        elif len_new < len_old:
            self.beginRemoveRows(QtCore.QModelIndex(), max(0, len_new-1), max(0, len_old-1))
            self.fish_list = fl
            self.endRemoveRows()
        else:
            self.fish_list = fl

        if self.update_fish_colors or force_color_update:
            self.updateFishColors()
        self.refreshLayout()

    def clear(self):
        self.all_fish = {}
        self.trimFishList()

    def refreshLayout(self):
        self.layoutChanged.emit()
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        self.updateContentsSignal.emit()

    data_lambda_list = [lambda f: f.color_ind,
                        lambda f: f.id,
                        lambda f: f.length,
                        lambda f: f.direction.name,
                        lambda f: f.frame_in,
                        lambda f: f.frame_out,
                        lambda f: f.duration,
                        lambda f: f.detection_count]

    def data(self, index, role):
        """
        Return data for TableView based on row and column.
        Row: Fish 
        Column: Some parameter of the fish
        """
        if role == Qt.DisplayRole:
            row = index.row()
            col = index.column()

            try:
                return self.data_lambda_list[col](self.fish_list[row])
            except IndexError:
                if row >= len(self.fish_list):
                    LogObject().print("Bad index {}/{}".format(row, len(self.fish_list) - 1))
                return QtCore.QVariant()
        else:
            return QtCore.QVariant()
    
    def rowCount(self, index=None):
        return len(self.fish_list)

    def columnCount(self, index=None):
        return 8;

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return fish_headers[section]

    def sort(self, col, order=QtCore.Qt.AscendingOrder):
        #self.layoutAboutToBeChanged.emit()

        self.sort_ind = col
        self.sort_order = order

        reverse = order != QtCore.Qt.AscendingOrder
        self.fish_list.sort(key = fish_sort_keys[col], reverse = reverse)

        #self.layoutChanged.emit()
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())

    def getShownFish(self, row):
        if row < len(self.fish_list):
            return self.fish_list[row]
        else:
            return None

    def addFish(self):
        """
        Manual addition of fish.
        Currently not supported. Manual fish detection from frames is required,
        i.e. user should be able to select fish location from SonarView for each frame.
        """
        f = FishEntry(self.getNewID())
        self.all_fish[f.id] = f
        self.trimFishList()

    def getNewID(self, ind=1):
        keys = self.all_fish.keys()
        while ind in keys:
            ind += 1
        return ind

    def removeFish(self, rows, update=True):
        if(len(rows) > 0):
            for row in sorted(rows, reverse=True):
                if row >= len(self.fish_list):
                    continue

                fish_id = self.fish_list[row].id
                try:
                    del_f = self.all_fish.pop(fish_id)
                    del del_f
                except KeyError:
                    LogObject().print("KeyError occured when removing entry with id:", fish_id)

            if update:
                self.trimFishList()

    def mergeFish(self, rows):
        if rows == None or len(rows) == 0:
            return

        sorted_rows = sorted(rows)
        new_fish = self.fish_list[sorted_rows[0]].copy()

        for i in range(1, len(sorted_rows)):
            row = sorted_rows[i]
            fish = self.fish_list[row]
            new_fish.merge(fish)

        self.removeFish(rows, False)
        self.all_fish[new_fish.id] = new_fish
        self.trimFishList()

    def splitFish(self, rows, frame):
        if rows == None or len(rows) == 0:
            return

        for row in sorted(rows):
            fish = self.fish_list[row]
            frame_inds = fish.tracks.keys()
            if fish.frame_in < frame and fish.frame_out > frame:
                id = self.getNewID(fish.id)
                new_fish = fish.split(frame, id)
                fish.forceLengthByPercentile(self.length_percentile)
                new_fish.forceLengthByPercentile(self.length_percentile)
                self.all_fish[id] = new_fish

        self.trimFishList()

    def clearMeasurements(self, rows):
        if rows == None or len(rows) == 0:
            return
        for row in rows:
            if row >= len(self.fish_list):
                    continue
            self.fish_list[row].forceLengthByPercentile(self.length_percentile)
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())

    def selectFromEchogram(self, frame_min, frame_max, height_min, height_max):
        """
        Finds fish that are within given frame and height limits and sends a signal
        to select the corresponding rows in table view.
        """
        new_selection = set()
        polar_transform = self.playback_manager.playback_thread.polar_transform
        min_d, max_d = self.playback_manager.getRadiusLimits()

        for ind, fish in enumerate(self.fish_list):
            # Skip fish outside the given range of frames
            if fish.frame_out < frame_min or fish.frame_in > frame_max:
                continue

            for frame, track in fish.tracks.items():
                if frame >= frame_min and frame <= frame_max:
                    track, det = fish.tracks[frame]
                    center = FishEntry.trackCenter(track)
                    distance, angle = polar_transform.cart2polMetric(center[0], center[1], True)

                    if distance >= height_min and distance <= height_max:
                        new_selection.add(ind)
                        break

        self.setSelection(new_selection)

    def setSelection(self, rows):
        """
        Creates a QItemSelection based on given rows (shown fish items)
        and emits updateSelectionSignal with the selection.
        """
        selection = QtCore.QItemSelection()
        for row in rows:
            ind_1 = self.index(row, 0)
            ind_2 = self.index(row, self.columnCount() - 1)
            range = QtCore.QItemSelectionRange(ind_1, ind_2)
            selection.append(range)

        self.updateSelectionSignal.emit(selection, QtCore.QItemSelectionModel.ClearAndSelect)

    def onSelectionChanged(self, selected):
        self.selected_rows = selected
        self.updateContentsSignal.emit()


    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled

        return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled

    def setData(self, index, value, role):
        if index.isValid() and role == Qt.EditRole:
            col = index.column()
            row = index.row()
            fish = self.fish_list[row]

            if col == 1:
                id, success = intTryParse(value)
                if success:
                    if id not in self.all_fish:
                        self.all_fish[id] = self.all_fish.pop(fish.id)
                        fish.id = id
                        self.trimFishList()
                        return True
            elif col == 2:
                length, success = floatTryParse(value)
                if success:
                    fish.length = length
                    self.dataChanged.emit(index, index)
                    return True
            elif col == 3:
                try:
                    fish.direction = SwimDirection[value]
                    self.dataChanged.emit(index, index)
                    return True
                except KeyError:
                    pass

        return False

    def updateDataFromTracker(self):
        """
        Iterates through the results of the tracker and updates the data in FishManager.
        """

        # Iterate through all frames.
        for frame, tracks in self.tracker.tracks_by_frame.items():
            # Iterate through all tracks in a frame.
            for tr, det in tracks:
                id = tr[4]
                if id in self.all_fish:
                    f = self.all_fish[id]
                    f.addTrack(tr, det, frame)
                else:
                    f = FishEntryFromTrack(tr, det, frame)
                    self.all_fish[id] = f

        # TODO: Trim tails here...

        # Refresh values
        for fish in self.all_fish.values():
            fish.setLengthByPercentile(self.length_percentile)
            fish.setDirection(self.up_down_inverted)

        self.trimFishList(force_color_update=True)

    def updateFishColors(self):
        color_ind = 0
        for id, fish in self.all_fish.items():
            fish.color_ind = color_ind
            color_ind = (color_ind + 1) % N_COLORS

    def isColor(self, index):
        return index.column() == 0

    def isDropdown(self, index):
        return index.column() == 3

    def dropdown_options(self):
        return [sd.name for sd in list(SwimDirection)]

    def getDropdownIndex(self, index):
        try:
            return self.fish_list[index.row()].direction
        except IndexError:
            return SwimDirection.NONE

    def setMinDetections(self, value):
        self.min_detections = value
        self.trimFishList()

    def setLengthPercentile(self, value):
        self.length_percentile = value
        for fish in self.all_fish.values():
            fish.setLengthByPercentile(self.length_percentile)
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())

    def toggleUpDownInversion(self):
        self.setUpDownInversion(not self.up_down_inverted)

    def setUpDownInversion(self, value):
        self.up_down_inverted = value
        for fish in self.all_fish.values():
            fish.setDirection(self.up_down_inverted)
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())

    def setShowFish(self):
        self.show_fish = self.show_bounding_box or self.show_id or self.show_detection_size
        if not self.show_fish:
            #self.data_changed_signal.emit(0)
            pass

    def setShowEchogramFish(self, value):
        self.show_echogram_fish = value

    def setShowBoundingBox(self, value):
        self.show_bounding_box = value
        self.setShowFish()

    def setShowTrackingIDs(self, value):
        self.show_id = value
        self.setShowFish()

    def setShowTrackingSize(self, value):
        self.show_detection_size = value
        self.setShowFish()

    def visualize(self, image, ind):
        fish_by_frame = [f for f in self.fish_list if ind in f.tracks.keys()]
        if len(fish_by_frame) == 0:
            return image

        
        #colors = sns.color_palette('deep', max([0] + [d.label + 1 for _, d in fish_by_frame]))
        colors = sns.color_palette('deep', max(0, len(fish_by_frame)))
        for fish in fish_by_frame:
            tr, det = fish.tracks[ind]
            if self.show_id:
                #center = [(tr[0] + tr[2]) / 2, (tr[1] + tr[3]) / 2]
                center = FishEntry.trackCenter(tr)
                image = cv2.putText(image, "ID: " + str(fish.id), (int(center[1])-20, int(center[0])+25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1, cv2.LINE_AA)

            if self.show_detection_size and det is not None:
                det.visualize(image, colors, True, False)

            if self.show_bounding_box:
                corners = np.array([[tr[0], tr[1]], [tr[2], tr[1]], [tr[2], tr[3]], [tr[0], tr[3]]]) #, [tr[0], tr[1]]

                for i in range(0,3):
                    cv2.line(image, (int(corners[i,1]),int(corners[i,0])), (int(corners[i+1,1]),int(corners[i+1,0])),  (255,255,255), 1)
                cv2.line(image, (int(corners[3,1]),int(corners[3,0])), (int(corners[0,1]),int(corners[0,0])),  (255,255,255), 1)

        return image

    def saveToFile(self, path):
        """
        Tries to save all fish information (from all_fish dictionary) to a file.
        """
        if(self.playback_manager.playback_thread is None):
            LogObject().print("No file open, cannot save.")
            return

        try:
            with open(path, "w") as file:
                file.write("id;frame;length;distance;angle;direction;corner1 x;corner1 y;corner2 x;corner2 y;corner3 x;corner3 y;corner4 x;corner4 y; detection\n")

                lines = self.getSaveLines()
                lines.sort(key = lambda l: (l[0].id, l[1]))
                for _, _, line in lines:
                    file.write(line)

                LogObject().print("Tracks saved to path:", path)
        except PermissionError as e:
            LogObject().print("Cannot open file {}. Permission denied.".format(path))

    def getSaveLines(self):
        """
        Iterates through all the fish and returns a list containing the fish object, frames the appear in, and the following information:
        ID, Frame, Length, Angle, Direction, Corner coordinates and wether the values are from a detection or a track.
        Detection information are preferred over tracks.
        """
        lines = []
        polar_transform = self.playback_manager.playback_thread.polar_transform

        f1 = "{:.5f}"
        lineBase1 = "{};{};" + "{};{};{};".format(f1,f1,f1) + "{};"
        lineBase2 = "{};{};" + "{};{};{};".format(f1,f1,f1) + "{};"

        for fish in self.all_fish.values():
            for frame, td in fish.tracks.items():
                track, detection = td

                # Values calculated from detection
                if detection is not None:
                    length = fish.length if fish.length_overwritten else detection.length
                    line = lineBase1.format(fish.id, frame, length, detection.distance, detection.angle, fish.direction.name)
                    if detection.corners is not None:
                        line += self.cornersToString(detection.corners, ";")
                    else:
                        line += ";".join(8 * [" "])
                    line += ";1"

                # Values calculated from track
                else:
                    if fish.length_overwritten:
                        length = fish.length
                    else:
                        length, _ = polar_transform.getMetricDistance(*track[:4])
                    #center = [(track[2]+track[0])/2, (track[3]+track[1])/2]
                    center = FishEntry.trackCenter(track)
                    distance, angle = polar_transform.cart2polMetric(center[0], center[1], True)
                    angle = float(angle / np.pi * 180 + 90)

                    line = lineBase1.format(fish.id, frame, length, distance, angle, fish.direction.name)
                    line += self.cornersToString([[track[0], track[1]], [track[2], track[1]], [track[2], track[3]], [track[0], track[3]]], ";")
                    line += ";0"

                lines.append((fish, frame, line + "\n"))

        return lines

    def cornersToString(self, corners, delim):
        """
        Formats the corner information in a saveable format.
        """
        base = "{:.2f}" + delim + "{:.2f}"
        return delim.join(base.format(cx,cy) for cy, cx in corners[0:4])

    def loadFromFile(self, path):
        with open(path, 'r') as file:
            self.clear()
            header = file.readline()

            for line in file:
                split_line = line.split(';')
                id = int(split_line[0])
                frame = int(split_line[1])
                length = float(split_line[2])
                direction = SwimDirection[split_line[5]]
                track = [float(split_line[7]), float(split_line[6]), float(split_line[11]), float(split_line[10]), id]

                if id in self.all_fish:
                    f = self.all_fish[id]
                    f.addTrack(track, None, frame)
                else:
                    f = FishEntryFromTrack(track, None, frame)
                    f.length = length
                    f.direction = direction
                    self.all_fish[id] = f

            self.trimFishList()

    def convertToWritable(self, frame, label, track):
        return [frame, label, list(map(float, track))]


    def getSaveDictionary(self):
        """
		Returns a dictionary of fish to be saved in SaveManager.
		"""
        fish = {}
        for f in self.all_fish.values():
            fish_tracks = [self.convertToWritable(frame, int(det.label), track[0:4]) if det is not None else
                           self.convertToWritable(frame, None, track[0:4])
                           for frame, (track, det) in f.tracks.items()]
            test = fish_tracks[0]
            fish[str(f.id)] = fish_tracks

        return fish

    def applySaveDictionary(self, data, dets):
        """
		Load fish entries from data provided by SaveManager.
		"""
        self.clear()
        for id, f_data in data.items():
            f = None
            for frame, det_label, track in f_data:
                if f is None:
                    f = FishEntry(id, frame, frame)

                if det_label is not None:
                    # Goes through detections in the same frame and tries to assign the
                    # corresponding detection based on the label.

                    frame_dets = dets[frame]
                    match_found = False
                    for fd in frame_dets:
                        if fd.label == det_label:
                            # Adds track with a matching detection to the FishEntry

                            f.addTrack(track, fd, frame)
                            match_found = True
                            break

                    if not match_found:
                        LogObject().print("Warning: Match not found in frame {} for label {}".format(frame, det_label))
                else:
                    f.addTrack(track, None, frame)

            self.all_fish[id] = f

        self.trimFishList()



class SwimDirection(IntEnum):
    UP = 0
    DOWN = 1
    NONE = 2

def FishEntryFromTrack(track, detection, frame):
    fish = FishEntry(track[4], frame, frame)
    fish.addTrack(track, detection, frame)
    return fish

class FishEntry():
    def __init__(self, id, frame_in=0, frame_out=0):
        self.id = int(id)
        self.length = 0
        self.direction = SwimDirection.NONE
        self.frame_in = frame_in
        self.frame_out = frame_out
        self.duration = frame_out - frame_in + 1

        # tracks: Dictionary {frame index : (track, detection)}
        self.tracks = {}
        self.detection_count = 0

        # lengths: Sorted list [lengths of detections]
        self.lengths = []
        self.length_overwritten = False

        self.color_ind = 0

    def __repr__(self):
        return "Fish {}: {:.1f} {}".format(self.id, self.length, self.direction.name)

    def dirSortValue(self):
        return self.direction.value * 10**8 + self.id

    def setLength(self, value):
        self.length = value
        self.length_overwritten = True

    def setLengthByPercentile(self, percentile):
        if not self.length_overwritten:
            if len(self.lengths) > 0:
                self.length = round(float(np.percentile(self.lengths, percentile)),3)

    def forceLengthByPercentile(self, percentile):
        self.length_overwritten = False
        self.setLengthByPercentile(percentile)

    def addTrack(self, track, detection, frame):
        self.tracks[frame] = (track[0:4], detection)
        if detection is not None:
            insort(self.lengths, detection.length)
        self.setFrames()

    def copy(self):
        f = FishEntry(self.id, self.frame_in, self.frame_out)
        f.length = self.length
        f.direction = self.direction
        f.tracks = self.tracks.copy()
        f.lengths = self.lengths.copy()
        f.length_overwritten = self.length_overwritten
        f.color_ind = self.color_ind
        return f

    def merge(self, other):
        self.frame_in = min(self.frame_in, other.frame_in)
        self.frame_out = max(self.frame_out, other.frame_out)
        self.duration = self.frame_out - self.frame_in + 1
        
        for l in other.lengths:
            insort(self.lengths, l)

        for frame, track in other.tracks.items():
            if frame not in self.tracks:
                self.tracks[frame] = track
            else:
                # TODO: Overlapping tracks.
                # Currently only self.tracks are kept when tracks overlap each other.
                pass

    def split(self, frame, new_id):
        f = FishEntry(new_id, frame, self.frame_out)
        for tr_frame in list(self.tracks.keys()):
            if tr_frame >= frame:
                tr, det = self.tracks.pop(tr_frame)
                f.addTrack(tr, det, tr_frame)

        self.lengths = sorted([det.length for _, det in self.tracks.values() if det is not None])
        self.setFrames()
        return f

    def setFrames(self):
        inds = self.tracks.keys()
        if len(inds) > 0:
            self.frame_in = min(inds)
            self.frame_out = max(inds)
            self.duration = self.frame_out - self.frame_in + 1
        self.detection_count = len([det for _, det in self.tracks.values() if det is not None])

    def setDirection(self, inverted):
        centers = [d.center for _, d in self.tracks.values() if d is not None]
        if len(centers) <= 1:
            self.direction = SwimDirection.NONE
        elif inverted:
            self.direction = SwimDirection.UP if centers[0][1] >= centers[-1][1] else SwimDirection.DOWN
        else:
            self.direction = SwimDirection.UP if centers[0][1] < centers[-1][1] else SwimDirection.DOWN

    @staticmethod
    def trackCenter(track):
        return [(track[2]+track[0])/2, (track[3]+track[1])/2]

def floatTryParse(value):
    try:
        return float(value), True
    except ValueError:
        return value, False

def intTryParse(value):
    try:
        return int(value), True
    except ValueError:
        return value, False

if __name__ == "__main__":
    fish_manager = FishManager(None, None)
    fish_manager.testPopulate(500)
    for fish in fish_manager.fish_list:
        print(fish)
