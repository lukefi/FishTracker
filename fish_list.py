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

from PyQt5 import QtCore, QtGui, QtWidgets
from dropdown_delegate import DropdownDelegate
from detector_parameters_view import LabeledSlider
from collapsible_box import CollapsibleBox
from log_object import LogObject

# UI element for viewing and editing the tracked fish.
# Tracked fish are stored and managed by fish_manager.py.
#
class FishList(QtWidgets.QWidget):
    selectionRowsChanged = QtCore.pyqtSignal(set)

    def __init__(self, fish_manager, playback_manager, sonar_viewer=None):
        super().__init__()
        self.fish_manager = fish_manager
        self.playback_manager = playback_manager
        self.sonar_viewer = sonar_viewer
        self.measure_fish = None
        self.initialized_rows = 0
        self.show_fish = False

        #self.scroll = QtWidgets.QScrollArea(self)
        #self.scroll.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.table = QtWidgets.QTableView(self)
        self.table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.table.setModel(fish_manager)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(1, QtCore.Qt.AscendingOrder);
        self.table.setItemDelegate(DropdownDelegate())
        self.table.setStyleSheet("QTableView\n"
                                 "{\n"
                                 "border: none;\n"
                                 "}\n"
                                 "")
        widths = [80 for i in range(self.fish_manager.columnCount())]
        widths[0] = 40
        widths[1] = 60
        for i, w in enumerate(widths):
            self.table.setColumnWidth(i, w)


        self.fish_manager.layoutChanged.connect(self.checkDropdowns)
        self.fish_manager.dataChanged.connect(self.onDataChanged)
        self.fish_manager.updateSelectionSignal.connect(self.table.selectionModel().select)
        self.fish_manager.updateSelectionSignal.connect(lambda x, y: self.table.setFocus())
        self.table.selectionModel().selectionChanged.connect(self.onSelectionChanged)

        ### Enables easier interaction with dropdown fields.
        ### Can be disabled if turns out to break things.

        #for row in range(fish_manager.rowCount()):
        #    self.setPersistentDropdown(row)

        ###

        self.vertical_layout = QtWidgets.QVBoxLayout()
        self.vertical_layout.setObjectName("verticalLayout")
        self.vertical_layout.setSpacing(0)
        self.vertical_layout.setContentsMargins(0,0,0,0)

        self.statistics_layout = QtWidgets.QHBoxLayout()
        self.statistics_layout.setObjectName("statisticsLayout")
        self.statistics_layout.setSpacing(0)
        self.statistics_layout.setContentsMargins(0,7,0,7)

        self.total_fish_label = QtWidgets.QLabel()
        self.total_fish_label.setAlignment(QtCore.Qt.AlignCenter)
        self.statistics_layout.addWidget(self.total_fish_label)

        self.up_fish_label = QtWidgets.QLabel()
        self.up_fish_label.setAlignment(QtCore.Qt.AlignCenter)
        self.statistics_layout.addWidget(self.up_fish_label)

        self.down_fish_label = QtWidgets.QLabel()
        self.down_fish_label.setAlignment(QtCore.Qt.AlignCenter)
        self.statistics_layout.addWidget(self.down_fish_label)

        self.none_fish_label = QtWidgets.QLabel()
        self.none_fish_label.setAlignment(QtCore.Qt.AlignCenter)
        self.statistics_layout.addWidget(self.none_fish_label)

        self.updateCountLabels()
        self.vertical_layout.addLayout(self.statistics_layout)
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine);
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.vertical_layout.addWidget(line)
        self.vertical_layout.addWidget(self.table)

        self.collapsible = CollapsibleBox("Filters")
        self.form_layout = QtWidgets.QFormLayout()
        self.form_layout.setContentsMargins(7,7,7,7)

        self.min_detections_slider = LabeledSlider("Min duration", self.form_layout, [self.fish_manager.setMinDetections], self.fish_manager.min_detections, 1, 50, self)
        self.mad_slider = LabeledSlider("MAD", self.form_layout, [self.fish_manager.setMAD], self.fish_manager.mad_limit, 0, 50, self)
        self.length_percentile_slider = LabeledSlider("Length percentile", self.form_layout, [self.fish_manager.setLengthPercentile], self.fish_manager.length_percentile, 1, 100, self)

        self.collapsible.setContentLayout(self.form_layout)
        self.vertical_layout.addWidget(self.collapsible)

        self.button_layout = QtWidgets.QGridLayout()
        self.button_layout.setObjectName("measureLayout")
        self.button_layout.setContentsMargins(7,7,7,7)

        self.display_btn = QtWidgets.QPushButton()
        self.display_btn.setObjectName("displayFish")
        self.display_btn.setText("Go to frame")
        self.display_btn.clicked.connect(self.displayFish)
        self.display_btn.setToolTip("Go to the frame where the selected fish is first detected.")

        self.measure_btn = QtWidgets.QPushButton()
        self.measure_btn.setObjectName("measureFish")
        self.measure_btn.setText("Measure")
        self.measure_btn.clicked.connect(self.measureFish)
        self.measure_btn.setToolTip("Draw a line on Sonar View to measure the length of the selected fish.")

        self.clear_measure_btn = QtWidgets.QPushButton()
        self.clear_measure_btn.setObjectName("clearMeasurement")
        self.clear_measure_btn.setText("Clear measurement")
        self.clear_measure_btn.clicked.connect(self.clearMeasurements)
        self.clear_measure_btn.setToolTip("Clear measured lengths on all selected fish.")

        self.btn_spacer = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        #self.add_btn = QtWidgets.QPushButton()
        #self.add_btn.setObjectName("addButton")
        #self.add_btn.setText("Add")
        #self.add_btn.clicked.connect(self.addFishItem)
        #self.add_btn.setToolTip("Add a new fish to the list. (Not supported yet)")
        #self.add_btn.setEnabled(False)

        self.remove_btn = QtWidgets.QPushButton()
        self.remove_btn.setObjectName("removeButton")
        self.remove_btn.setText("Remove")
        self.remove_btn.clicked.connect(self.removeFishItems)
        self.remove_btn.setToolTip("Remove all selected fish.")

        self.merge_btn = QtWidgets.QPushButton()
        self.merge_btn.setObjectName("mergeButton")
        self.merge_btn.setText("Merge")
        self.merge_btn.clicked.connect(self.mergeFishItems)
        self.merge_btn.setToolTip("Merge all selected fish into one.")

        self.split_btn = QtWidgets.QPushButton()
        self.split_btn.setObjectName("splitButton")
        self.split_btn.setText("Split")
        self.split_btn.clicked.connect(self.splitFishItem)
        self.split_btn.setToolTip("Split all selected fish in two at the current frame.")

        self.button_layout.addWidget(self.display_btn, 0, 0)
        self.button_layout.addWidget(self.measure_btn, 0, 1)
        self.button_layout.addWidget(self.clear_measure_btn, 1, 1)
        self.button_layout.addItem(self.btn_spacer, 0, 2, 1, 2)
        self.button_layout.addWidget(self.merge_btn, 0, 3)
        self.button_layout.addWidget(self.split_btn, 1, 3)
        self.button_layout.addWidget(self.remove_btn, 0, 4)


        self.vertical_layout.addLayout(self.button_layout)

        self.setLayout(self.vertical_layout)

    def addFishItem(self):
        self.fish_manager.addFish()

    def removeFishItems(self):
        rows = self.getSelectionRows()
        self.fish_manager.removeFish(rows)

    def mergeFishItems(self):
        rows = self.getSelectionRows()
        self.fish_manager.mergeFish(rows)

    def splitFishItem(self):
        rows = self.getSelectionRows()
        self.fish_manager.splitFish(rows, self.playback_manager.getFrameInd() + 1)

    def getSelectionRows(self):
        selection = self.table.selectionModel().selection().indexes();
        return list(set([s.row() for s in selection]))

    def onSelectionChanged(self, selected, deselected):
        selection = self.table.selectionModel().selection().indexes();
        selection = set([s.row() for s in selection])
        self.fish_manager.onSelectionChanged(selection)

    def displayFish(self):
        try:
            selection = self.table.selectionModel().selection().indexes();
            ind = self.fish_manager.getShownFish(selection[0].row()).frame_in
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
                self.measure_fish = self.fish_manager.getShownFish(selection[0].row())
            except IndexError:
                self.measurementDone()

        if self.sonar_viewer:
            self.sonar_viewer.measureDistance(self.measure_fish is not None)

    def setMeasurementResult(self, value):
        if self.measure_fish:
            if value is not None:
                self.measure_fish.setLength(float(round(value, 3)))
                self.fish_manager.refreshLayout()

        self.measurementDone()

    def measurementDone(self):
        self.measure_fish = None
        self.measure_btn.setText("Measure")

    def clearMeasurements(self):
        rows = self.getSelectionRows()
        self.fish_manager.clearMeasurements(rows)

    def checkDropdowns(self):
        for row in range(self.fish_manager.rowCount()):
            self.setPersistentDropdown(row)

    def onDataChanged(self, parents, hint):
        self.updateCountLabels()

    def updateCountLabels(self):
        tc, uc, dc, nc = self.fish_manager.directionCounts()

        self.total_fish_label.setText("Total: {}".format(tc))
        self.up_fish_label.setText("Up: {}".format(uc))
        self.down_fish_label.setText("Down: {}".format(dc))
        self.none_fish_label.setText("None: {}".format(nc))

    def setPersistentDropdown(self, row):
        for column in range(self.fish_manager.columnCount()):
            index=self.fish_manager.index(row, column)
            if self.fish_manager.isDropdown(index):
                self.table.openPersistentEditor(index)
            else:
                self.table.closePersistentEditor(index)          


if __name__ == "__main__":
    import sys
    from playback_manager import PlaybackManager
    from fish_manager import FishManager
    from detector import Detector
    from tracker import Tracker

    def uiTest():
        app = QtWidgets.QApplication(sys.argv)
        main_window = QtWidgets.QMainWindow()
        playback_manager = PlaybackManager(app, main_window)
        fish_manager = FishManager(None, None)
        fish_manager.testPopulate(500)
        fish_list = FishList(fish_manager, playback_manager)

        main_window.setCentralWidget(fish_list)
        main_window.show()

        sys.exit(app.exec_())

    def dataTest():
        def startDetector():
            detector.initMOG()
            detector.computeAll()
            tracker.primaryTrack()

        app = QtWidgets.QApplication(sys.argv)
        main_window = QtWidgets.QMainWindow()
        playback_manager = PlaybackManager(app, main_window)
        detector = Detector(playback_manager)
        tracker = Tracker(detector)
        fish_manager = FishManager(playback_manager, tracker)
        fish_list = FishList(fish_manager, playback_manager)

        playback_manager.openTestFile()
        detector.bg_subtractor.mog_parameters.nof_bg_frames = 500
        detector._show_detections = True
        playback_manager.mapping_done.connect(lambda: playback_manager.runInThread(startDetector))

        main_window.setCentralWidget(fish_list)
        main_window.show()
        sys.exit(app.exec_())

    def loadTest():
        app = QtWidgets.QApplication(sys.argv)
        main_window = QtWidgets.QMainWindow()
        playback_manager = PlaybackManager(app, main_window)
        fish_manager = FishManager(None, None)

        file = playback_manager.selectLoadFile()
        fish_manager.loadFromFile(file)
        fish_list = FishList(fish_manager, playback_manager)

        main_window.setCentralWidget(fish_list)
        main_window.show()
        sys.exit(app.exec_())

    #uiTest()
    dataTest()
    #loadTest()
