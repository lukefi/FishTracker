from PyQt5 import QtCore, QtGui, QtWidgets
from dropdown_delegate import DropdownDelegate

class FishList(QtWidgets.QDialog):
    def __init__(self, fish_manager):
        super().__init__()
        self.fish_manager = fish_manager

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
            for column in range(fish_manager.columnCount()):
                index=fish_manager.index(row, column)
                if fish_manager.isDropdown(index):
                    self.table.openPersistentEditor(index)

        ###

        self.vertical_layout = QtWidgets.QVBoxLayout()
        self.vertical_layout.setObjectName("verticalLayout")
        self.vertical_layout.addWidget(self.table)
        self.vertical_layout.setSpacing(0)
        self.vertical_layout.setContentsMargins(0,0,0,0)

        self.add_btn = QtWidgets.QPushButton()
        self.add_btn.setObjectName("addButton")
        self.add_btn.setText("Add")
        self.add_btn.clicked.connect(self.fish_manager.addFish)

        self.remove_btn = QtWidgets.QPushButton()
        self.remove_btn.setObjectName("removeButton")
        self.remove_btn.setText("Remove")
        self.remove_btn.clicked.connect(self.removeFishItems)

        self.merge_btn = QtWidgets.QPushButton()
        self.merge_btn.setObjectName("mergeButton")
        self.merge_btn.setText("Merge")
        self.merge_btn.clicked.connect(self.mergeFishItems)

        self.horizontal_layout = QtWidgets.QHBoxLayout()
        self.horizontal_layout.setObjectName("horizontalLayout")
        self.horizontal_layout.setSpacing(7)
        self.horizontal_layout.setContentsMargins(0,0,0,0)

        self.horizontal_layout.addWidget(self.add_btn)
        self.horizontal_layout.addWidget(self.remove_btn)
        self.horizontal_layout.addWidget(self.merge_btn)
        self.horizontal_layout.addStretch()

        self.vertical_layout.addLayout(self.horizontal_layout)

        self.setLayout(self.vertical_layout)

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



if __name__ == "__main__":
    import sys
    from playback_manager import PlaybackManager
    from fish_manager import FishManager

    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    #playback_manager = PlaybackManager(app, main_window)
    #playback_manager.openTestFile()
    fish_manager = FishManager()
    fish_manager.testPopulate()
    #info_w = InfoWidget(playback_manager, fish_manager)
    fish_list =FishList(fish_manager)
    main_window.setCentralWidget(fish_list)
    main_window.show()
    sys.exit(app.exec_())


