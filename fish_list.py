from PyQt5 import QtCore, QtGui, QtWidgets
from dropdown_delegate import DropdownDelegate

class FishList(QtWidgets.QWidget):
    def __init__(self, fish_manager, playback_manager, sonar_viewer=None):
        super().__init__()
        self.fish_manager = fish_manager
        self.playback_manager = playback_manager
        self.sonar_viewer = sonar_viewer
        self.measure_fish = None
        self.initialized_rows = 0

        #self.scroll = QtWidgets.QScrollArea(self)
        #self.scroll.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.table = QtWidgets.QTableView(self)
        self.table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.table.setModel(fish_manager)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, QtCore.Qt.AscendingOrder);
        self.table.setItemDelegate(DropdownDelegate())
        self.table.setStyleSheet("QTableView\n"
                                 "{\n"
                                 "border: none;\n"
                                 "}\n"
                                 "")

        ### Enables easier interaction with dropdown fields.
        ### Can be disabled if turns out to break things.

        for row in range(fish_manager.rowCount()):
            self.setPersistentDropdown(row)

        ###

        self.vertical_layout = QtWidgets.QVBoxLayout()
        self.vertical_layout.setObjectName("verticalLayout")
        self.vertical_layout.addWidget(self.table)
        self.vertical_layout.setSpacing(0)
        self.vertical_layout.setContentsMargins(0,0,0,0)

        self.display_btn = QtWidgets.QPushButton()
        self.display_btn.setObjectName("displayFish")
        self.display_btn.setText("Go to frame")
        self.display_btn.clicked.connect(self.displayFish)

        self.measure_btn = QtWidgets.QPushButton()
        self.measure_btn.setObjectName("measureFish")
        self.measure_btn.setText("Measure")
        self.measure_btn.clicked.connect(self.measureFish)

        self.btn_spacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        self.add_btn = QtWidgets.QPushButton()
        self.add_btn.setObjectName("addButton")
        self.add_btn.setText("Add")
        self.add_btn.clicked.connect(self.addFishItem)

        self.remove_btn = QtWidgets.QPushButton()
        self.remove_btn.setObjectName("removeButton")
        self.remove_btn.setText("Remove")
        self.remove_btn.clicked.connect(self.removeFishItems)

        self.merge_btn = QtWidgets.QPushButton()
        self.merge_btn.setObjectName("mergeButton")
        self.merge_btn.setText("Merge")
        self.merge_btn.clicked.connect(self.mergeFishItems)

        self.split_btn = QtWidgets.QPushButton()
        self.split_btn.setObjectName("splitButton")
        self.split_btn.setText("Split")
        self.split_btn.clicked.connect(self.splitFishItem)

        self.horizontal_layout = QtWidgets.QHBoxLayout()
        self.horizontal_layout.setObjectName("horizontalLayout")
        self.horizontal_layout.setSpacing(7)
        self.horizontal_layout.setContentsMargins(0,0,0,0)

        self.horizontal_layout.addWidget(self.display_btn)
        self.horizontal_layout.addWidget(self.measure_btn)
        self.horizontal_layout.addItem(self.btn_spacer)
        self.horizontal_layout.addWidget(self.add_btn)
        self.horizontal_layout.addWidget(self.remove_btn)
        self.horizontal_layout.addWidget(self.merge_btn)
        self.horizontal_layout.addWidget(self.split_btn)
        self.horizontal_layout.addStretch()

        self.vertical_layout.addLayout(self.horizontal_layout)

        self.setLayout(self.vertical_layout)

    def addFishItem(self):
        self.fish_manager.addFish()
        self.checkDropdowns()

    def removeFishItems(self):
        selection = self.table.selectionModel().selection().indexes();
        rows = list(set([s.row() for s in selection]))
        self.fish_manager.removeFish(rows)
        self.fish_manager.refreshLayout()

    def mergeFishItems(self):
        selection = self.table.selectionModel().selection().indexes();
        rows = list(set([s.row() for s in selection]))
        self.fish_manager.mergeFish(rows)
        self.fish_manager.refreshLayout()

    def splitFishItem(self):
        selection = self.table.selectionModel().selection().indexes();
        rows = list(set([s.row() for s in selection]))
        self.fish_manager.splitFish(rows, self.playback_manager.getFrameInd())
        self.fish_manager.refreshLayout()
        self.checkDropdowns()

    def displayFish(self):
        try:
            selection = self.table.selectionModel().selection().indexes();
            ind = self.fish_manager.fishes[selection[0].row()].frame_in
            self.playback_manager.setFrameInd(ind)
        except IndexError:
            return

    def measureFish(self):
        if self.measure_fish:
            self.measurementDone()
        else:
            self.measure_btn.setText("Cancel")
            try:
                selection = self.table.selectionModel().selection().indexes();
                self.measure_fish = self.fish_manager.fishes[selection[0].row()]
            except IndexError:
                self.measurementDone()

        if self.sonar_viewer:
            self.sonar_viewer.measureDistance(self.measure_fish is not None)

    def setMeasurementResult(self, value):
        if self.measure_fish:
            if value is not None:
                self.measure_fish.length = float(round(value, 3))
                self.fish_manager.refreshLayout()

        self.measurementDone()

    def measurementDone(self):
        self.measure_fish = None
        self.measure_btn.setText("Measure")

    def checkDropdowns(self):
        count = self.fish_manager.rowCount()
        if count > self.initialized_rows:
            for row in range(self.initialized_rows, count):
                self.setPersistentDropdown(row)
        self.initialized_rows = count

    def setPersistentDropdown(self, row):
        self.initialized_rows = max(self.initialized_rows, row)
        for column in range(self.fish_manager.columnCount()):
            index=self.fish_manager.index(row, column)
            if self.fish_manager.isDropdown(index):
                self.table.openPersistentEditor(index)
            



if __name__ == "__main__":
    import sys
    from playback_manager import PlaybackManager
    from fish_manager import FishManager

    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    # playback_manager.openTestFile()
    fish_manager = FishManager()
    fish_manager.testPopulate(500)
    #info_w = InfoWidget(playback_manager, fish_manager)
    fish_list = FishList(fish_manager, playback_manager)
    main_window.setCentralWidget(fish_list)
    main_window.show()
    sys.exit(app.exec_())


