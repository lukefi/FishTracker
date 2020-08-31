from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt

import numpy as np
from bisect import insort
from enum import IntEnum
from tracker import Tracker

fish_headers = ["ID", "Length", "Direction", "Frame in", "Frame out", "Duration", "Detections"]
fish_sort_keys = [lambda f: f.id, lambda f: -f.length, lambda f: f.dirSortValue(), lambda f: f.frame_in, lambda f: f.frame_out, lambda f: f.duration, lambda f: len(f.tracks)]

class FishManager(QtCore.QAbstractTableModel):
    updateContentsSignal = QtCore.pyqtSignal()

    def __init__(self, tracker):
        super().__init__()
        self.tracker = tracker
        if tracker is not None:
            self.tracker.init_signal.connect(self.clear)
            self.tracker.all_computed_signal.connect(self.updateDataFromTracker)

        self.all_fish = {}
        self.fish_list = []
        self.sort_ind = 0
        self.sort_order = QtCore.Qt.DescendingOrder
        self.min_detections = 2
        self.length_percentile = 50

        self.show_fish = False
        self.up_down_inverted = False

    def testPopulate(self, frame_count):
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

    def trimFishList(self):
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
        self.refreshLayout()

    def clear(self):
        self.all_fish = {}
        self.trimFishList()

    def refreshLayout(self):
        self.layoutChanged.emit()
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        self.updateContentsSignal.emit()


    def data(self, index, role):
        if role == Qt.DisplayRole:
            row = index.row()
            col = index.column()

            if row >= len(self.fish_list):
                print("Bad index {}/{}".format(row, len(self.fish_list) - 1))
                return QtCore.QVariant()

            if col == 0:
                return self.fish_list[row].id
            elif col == 1:
                return self.fish_list[row].length
            elif col == 2:
                return self.fish_list[row].direction.name
            elif col == 3:
                return self.fish_list[row].frame_in
            elif col == 4:
                return self.fish_list[row].frame_out
            elif col == 5:
                return self.fish_list[row].duration
            elif col == 6:
                return len(self.fish_list[row].tracks)
            else:
                return QtCore.QVariant()
        else:
            return QtCore.QVariant()
    
    def rowCount(self, index=None):
        return len(self.fish_list)

    def columnCount(self, index=None):
        return 7;

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
                    print("KeyError occured when removing entry with id:", fish_id)

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

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled

        return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled

    def setData(self, index, value, role):
        if index.isValid() and role == Qt.EditRole:
            col = index.column()
            row = index.row()
            fish = self.fish_list[row]

            if col == 0:
                id, success = intTryParse(value)
                if success:
                    if id not in self.all_fish:
                        self.all_fish[id] = self.all_fish.pop(fish.id)
                        fish.id = id
                        self.trimFishList()
                        return True
            elif col == 1:
                length, success = floatTryParse(value)
                if success:
                    fish.length = length
                    self.dataChanged.emit(index, index)
                    return True
            elif col == 2:
                try:
                    fish.direction = SwimDirection[value]
                    self.dataChanged.emit(index, index)
                    return True
                except KeyError:
                    pass

        return False

    def updateDataFromTracker(self):
        for frame, tracks in self.tracker.tracks_by_frame.items():
            for tr, det in tracks:
                id = tr[4]
                if id in self.all_fish:
                    f = self.all_fish[id]
                    f.addTrack(tr, det, frame)
                else:
                    f = FishEntryFromTrack(tr, det, frame)
                    self.all_fish[id] = f

        for fish in self.all_fish.values():
            fish.setLengthByPercentile(self.length_percentile)
            fish.setDirection(self.up_down_inverted)
        self.trimFishList()


    def isDropdown(self, index):
        return index.column() == 2

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

    def setShowFish(self, value):
        self.show_fish = value

    def toggleUpDownInversion(self):
        self.up_down_inverted = not self.up_down_inverted
        for fish in self.all_fish.values():
            fish.setDirection(self.up_down_inverted)
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())

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

        # lengths: Sorted list [lengths of detections]
        self.lengths = []
        self.length_overwritten = False

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
        insort(self.lengths, detection.length)
        self.setFrames()

    def copy(self):
        f = FishEntry(self.id, self.frame_in, self.frame_out)
        f.length = self.length
        f.direction = self.direction
        f.tracks = self.tracks.copy()
        f.lengths = self.lengths.copy()
        f.length_overwritten = self.length_overwritten
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
                print("TODO: Overlapping tracks.")

    def split(self, frame, new_id):
        f = FishEntry(new_id, frame, self.frame_out)
        for tr_frame in list(self.tracks.keys()):
            if tr_frame >= frame:
                tr, det = self.tracks.pop(tr_frame)
                f.addTrack(tr, det, tr_frame)

        self.lengths = sorted([det.length for _, det in self.tracks.values()])
        self.setFrames()
        return f

    def setFrames(self):
        inds = self.tracks.keys()
        if len(inds) > 0:
            self.frame_in = min(inds)
            self.frame_out = max(inds)
            self.duration = self.frame_out - self.frame_in + 1

    def setDirection(self, inverted):
        centers = [d.center for _, d in self.tracks.values()]
        if len(centers) == 1:
            self.direction = SwimDirection.NONE
        elif inverted:
            self.direction = SwimDirection.UP if centers[0][1] >= centers[-1][1] else SwimDirection.DOWN
        else:
            self.direction = SwimDirection.UP if centers[0][1] < centers[-1][1] else SwimDirection.DOWN

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
    fish_manager = FishManager(None)
    fish_manager.testPopulate(500)
    for fish in fish_manager.fish_list:
        print(fish)
