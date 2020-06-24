from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt

import numpy as np
from enum import Enum

fish_header_labels = ["ID", "Length", "Direction"]

class FishManager(QtCore.QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.fishes = list()

    def testPopulate(self):
        self.fishes.clear()
        for i in range(10):
            fish = FishEntry("Fish " + str(i + 1))
            fish.length = np.random.normal(120, 10)
            fish.direction = SwimDirection(np.random.randint(low=1, high=3))
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

    def rowCount(self, index):
        return len(self.fishes)

    def columnCount(self, index):
        return 3;

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return fish_header_labels[section]

class SwimDirection(Enum):
    NONE = 0
    UP = 1
    DOWN = 2

class FishEntry():
    def __init__(self, id):
        self.id = id
        self.length = 0
        self.direction = SwimDirection.NONE

    def __repr__(self):
        return "Fish {}: {:.1f} {}".format(self.id, self.length, self.direction.name)

if __name__ == "__main__":
    fish_manager = FishManager()
    fish_manager.testPopulate()
    for fish in fish_manager.fishes:
        print(fish)
