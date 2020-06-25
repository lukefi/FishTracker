from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt

import numpy as np
from enum import IntEnum

fish_headers = ["ID", "Length", "Direction"]
fish_sort_keys = [lambda f: f.id, lambda f: -f.length, lambda f: f.dirSortValue()]

class FishManager(QtCore.QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.fishes = list()
        self.sort_ind = 0
        self.sort_order = QtCore.Qt.DescendingOrder

    def testPopulate(self):
        self.fishes.clear()
        for i in range(10):
            fish = FishEntry(i + 1)
            fish.length = np.random.normal(120, 10)
            fish.direction = SwimDirection(np.random.randint(low=0, high=2))
            self.fishes.append(fish)


    def data(self, index, role):
        if role == Qt.DisplayRole:
            row = index.row()
            col = index.column()
            if col == 0:
                return self.fishes[row].id
            elif col == 1:
                return self.fishes[row].length
            elif col == 2:
                return self.fishes[row].direction.name
            else:
                return ""
    
    def rowCount(self, index=None):
        return len(self.fishes)

    def columnCount(self, index=None):
        return 3;

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return fish_headers[section]

    def sort(self, col, order=QtCore.Qt.AscendingOrder):
        #self.layoutAboutToBeChanged.emit()

        self.sort_ind = col
        self.sort_order = order

        reverse = order != QtCore.Qt.AscendingOrder
        self.fishes.sort(key = fish_sort_keys[col], reverse = reverse)

        #self.layoutChanged.emit()
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())

    def addFish(self):
        self.fishes.append(FishEntry(len(self.fishes) + 1))
        self.layoutChanged.emit()
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())

    def removeFish(self, rows):
        for row in sorted(rows, reverse=True):
            if row >= len(self.fishes):
                continue

            print(row)
            fish_id = self.fishes[row].id
            del self.fishes[row]
            for fish in self.fishes:
                if fish.id > fish_id:
                    fish.id -= 1


    def mergeFish(self, rows):
        if rows == None or len(rows) == 0:
            return

        id = None
        length = 0
        direction = 0
        count = len(rows)

        for row in sorted(rows):
            fish = self.fishes[row]

            if id is None:
                id = fish.id
            else:
                id = min(id, fish.id)
            length += fish.length
            direction += int(fish.direction)

        fish = FishEntry(len(self.fishes) + 1)
        fish.id = id
        fish.length = length / count
        fish.direction = SwimDirection(np.rint(direction / count))

        self.removeFish(rows)
        self.fishes.append(fish)
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
            fish = self.fishes[row]

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

    def isDropdown(self, index):
        return index.column() == 2

    def dropdown_options(self):
        return [sd.name for sd in list(SwimDirection)]

    def getDropdownIndex(self, index):
        return self.fishes[index.row()].direction


class SwimDirection(IntEnum):
    UP = 0
    DOWN = 1
    NONE = 2

class FishEntry():
    def __init__(self, id):
        self.id = id
        self.length = 0
        self.direction = SwimDirection.NONE

    def __repr__(self):
        return "Fish {}: {:.1f} {}".format(self.id, self.length, self.direction.name)

    def dirSortValue(self):
        return self.direction.value * 10**8 + self.id

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
    fish_manager = FishManager()
    fish_manager.testPopulate()
    for fish in fish_manager.fishes:
        print(fish)
