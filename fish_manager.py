from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt

import numpy as np
from enum import IntEnum
from tracker import Tracker

fish_headers = ["ID", "Length", "Direction", "Frame in", "Frame out", "Duration"]
fish_sort_keys = [lambda f: f.id, lambda f: -f.length, lambda f: f.dirSortValue(), lambda f: f.frame_in, lambda f: f.frame_out, lambda f: f.duration]

class FishManager(QtCore.QAbstractTableModel):
    def __init__(self, tracker):
        super().__init__()
        self.tracker = tracker
        if tracker is not None:
            self.tracker.all_computed_event.append(self.updateDataFromTracker)

        self.all_fish = {}
        self.fish_list = []
        self.sort_ind = 0
        self.sort_order = QtCore.Qt.DescendingOrder
        self.min_detections = 1

    def testPopulate(self, frame_count):
        self.all_fish = {}
        self.fish_list.clear()
        for i in range(10):
            f = FishEntry(i + 1)
            f.length = round(np.random.normal(1.2, 0.1), 3)
            f.direction = SwimDirection(np.random.randint(low=0, high=2))
            f.frame_in = np.random.randint(frame_count)
            f.frame_out = min(f.frame_in + np.random.randint(100), frame_count)
            f.duration = f.frame_out - f.frame_in
            self.all_fish[f.id] = f

        self.trimFishList()

    def trimFishList(self):
        self.fish_list = [fish for fish in self.all_fish.values() if fish.frame_out - fish.frame_in >= self.min_detections]

        reverse = self.sort_order != QtCore.Qt.AscendingOrder
        self.fish_list.sort(key=fish_sort_keys[self.sort_ind], reverse=reverse)


    def data(self, index, role):
        if role == Qt.DisplayRole:
            row = index.row()
            col = index.column()
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
            else:
                return ""
    
    def rowCount(self, index=None):
        return len(self.fish_list)

    def columnCount(self, index=None):
        return 6;

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

    def addFish(self):
        f = FishEntry(self.getNewID())
        self.all_fish[f.id] = f
        self.trimFishList()
        self.layoutChanged.emit()
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())

    def getNewID(self):
        keys = self.all_fish.keys()
        i = 1
        while i in keys:
            print("Key:",i)
            i += 1

        return i


    def removeFish(self, rows):
        if(len(rows) > 0):
            self.beginRemoveRows(QtCore.QModelIndex(), min(rows), max(rows))

            for row in sorted(rows, reverse=True):
                if row >= len(self.fish_list):
                    continue

                print(row)
                fish_id = self.fish_list[row].id
                try:
                    del_f = self.all_fish.pop(fish_id)
                    del self.fish_list[row]
                    del del_f
                except KeyError:
                    print("KeyError occured when removing entry with id:", fish_id)

            self.trimFishList()
            self.endRemoveRows()

            #del self.fish_list[row]
            #for fish in self.fish_list:
            #    if fish.id > fish_id:
            #        fish.id -= 1


    def mergeFish(self, rows):
        if rows == None or len(rows) == 0:
            return

        id = None
        length = 0
        direction = 0
        frame_in = None
        frame_out = None
        count = len(rows)

        for row in sorted(rows):
            fish = self.fish_list[row]

            if id is None:
                id = fish.id
                frame_in = fish.frame_in
                frame_out = fish.frame_out
            else:
                id = min(id, fish.id)
                frame_in = min(frame_in, fish.frame_in)
                frame_out = max(frame_out, fish.frame_out)
            length += fish.length
            direction += int(fish.direction)

        fish = FishEntry(len(self.fish_list) + 1)
        fish.id = id
        fish.length = length / count
        fish.direction = SwimDirection(np.rint(direction / count))
        fish.frame_in = frame_in
        fish.frame_out = frame_out

        for f in self.fish_list:
            if f.id >= id:
                f.id += 1

        self.removeFish(rows)
        self.fish_list.append(fish)
        self.sort(self.sort_ind, self.sort_order)

    def splitFish(self, rows, frame):
        if rows == None or len(rows) == 0:
            return

        for row in sorted(rows):
            fish = self.fish_list[row]
            if fish.frame_in < frame and fish.frame_out > frame:
                id = len(self.fish_list) + 1

                # Make room for the new fish
                for f in self.fish_list:
                    if f.frame_in > frame:
                        id = min(f.id, id)
                        f.id += 1


                new_fish = FishEntry(id)
                new_fish.length = fish.length
                new_fish.direction = fish.direction
                new_fish.frame_in = frame
                new_fish.frame_out = fish.frame_out

                fish.frame_out = frame-1

                self.fish_list.append(new_fish)

        self.sort(self.sort_ind, self.sort_order)



    def refreshLayout(self):
        self.layoutChanged.emit()
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
                    fish.id = id
            elif col == 1:
                length, success = floatTryParse(value)
                if success:
                    fish.length = length
            elif col == 2:
                try:
                    fish.direction = SwimDirection[value]
                except KeyError:
                    pass

            self.dataChanged.emit(index, index)
            return True
        return False

    def updateDataFromTracker(self):
        for frame, tracks in self.tracker.tracks_by_frame.items():
            for tr in tracks:
                existing_fish_with_id = [f for f in self.fish_list if f.id == tr[4]]
                if len(existing_fish_with_id) > 0:
                    f = existing_fish_with_id[0]
                    f.addTrack(tr, frame)
                else:
                    f = FishEntryFromTrack(tr, frame)
                    self.fish_list.append(f)

        self.refreshLayout()


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
        self.layoutChanged.emit()
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())

class SwimDirection(IntEnum):
    UP = 0
    DOWN = 1
    NONE = 2

def FishEntryFromTrack(track, frame):
    fish = FishEntry(track[4], frame, frame)
    fish.tracks[frame] = track[0:4]
    return fish

class FishEntry():
    def __init__(self, id, frame_in=0, frame_out=0):
        self.id = int(id)
        self.length = 0
        self.direction = SwimDirection.NONE
        self.frame_in = frame_in
        self.frame_out = frame_out
        self.duration = 0
        self.tracks = {}

    def __repr__(self):
        return "Fish {}: {:.1f} {}".format(self.id, self.length, self.direction.name)

    def dirSortValue(self):
        return self.direction.value * 10**8 + self.id

    def setLength(self, value):
        self.length = value

    def addTrack(self, track, frame):
        self.tracks[frame] = track[0:4]
        self.frame_in = min(frame, self.frame_in)
        self.frame_out = max(self.frame_out, frame)
        self.duration = self.frame_out - self.frame_in

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
