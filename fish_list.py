from PyQt5 import QtCore, QtGui, QtWidgets

class FishList(QtWidgets.QDialog):
    def __init__(self, fish_manager):
        super().__init__()
        self.fish_manager = fish_manager

        #self.scroll = QtWidgets.QScrollArea(self)
        #self.scroll.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.table = QtWidgets.QTableView(self)
        self.table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.table.setModel(fish_manager)

        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.addWidget(self.table)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setContentsMargins(0,0,0,0)
        self.setLayout(self.verticalLayout)


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


