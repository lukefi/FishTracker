from PyQt5 import QtCore, QtGui, QtWidgets
from fish_list import FishList
from parameter_list import ParameterList

class InfoWidget(QtWidgets.QTabWidget):
    def __init__(self, playback_manager, fish_manager):
        super().__init__()
        
        self.playback_manager = playback_manager
        self.fish_manager = fish_manager
        self.setupUi()

    def setupUi(self):
        self.central_widget = QtWidgets.QWidget(self)
        self.verticalLayout = QtWidgets.QVBoxLayout(self.central_widget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.pushButton = QtWidgets.QPushButton(self.central_widget)
        self.pushButton.setObjectName("pushButton")
        self.pushButton.clicked.connect(lambda: self.showWidget(0))
        self.horizontalLayout.addWidget(self.pushButton)
        self.pushButton_2 = QtWidgets.QPushButton(self.central_widget)
        self.pushButton_2.setObjectName("pushButton_2")
        self.pushButton_2.clicked.connect(lambda: self.showWidget(1))
        self.horizontalLayout.addWidget(self.pushButton_2)
        self.pushButton_3 = QtWidgets.QPushButton(self.central_widget)
        self.pushButton_3.setObjectName("pushButton_3")
        self.pushButton_3.clicked.connect(lambda: self.showWidget(2))
        self.horizontalLayout.addWidget(self.pushButton_3)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.fish_list = FishList(self.fish_manager)
        self.fish_list.setObjectName("fishList")

        self.parameter_list = ParameterList(self.fish_manager)
        self.parameter_list.setObjectName("parameterList")

        self.verticalLayout.addWidget(self.fish_list)
        self.current_widget = self.fish_list

        #self.table_view = QtWidgets.QTableView(self.central_widget)
        #self.table_view.setObjectName("tableView")
        #self.verticalLayout.addWidget(self.table_view)
        #MainWindow.setCentralWidget(self.central_widget)
        #self.menubar = QtWidgets.QMenuBar(MainWindow)
        #self.menubar.setGeometry(QtCore.QRect(0, 0, 1074, 26))
        #self.menubar.setObjectName("menubar")
        #MainWindow.setMenuBar(self.menubar)
        #self.statusbar = QtWidgets.QStatusBar(MainWindow)
        #self.statusbar.setObjectName("statusbar")
        #MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi()
        #QtCore.QMetaObject.connectSlotsByName(MainWindow)
        self.setLayout(self.verticalLayout)

    def retranslateUi(self):
        _translate = QtCore.QCoreApplication.translate
        #MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.pushButton.setText(_translate("MainWindow", "PushButton"))
        self.pushButton_2.setText(_translate("MainWindow", "PushButton"))
        self.pushButton_3.setText(_translate("MainWindow", "PushButton"))

    def showWidget(self, ind):
        print(ind, self.current_widget)
        if ind == 0:
            self.verticalLayout.replaceWidget(self.current_widget, self.fish_list)
            self.current_widget = self.fish_list
        elif ind == 1:
            self.verticalLayout.replaceWidget(self.current_widget, self.parameter_list)
            self.current_widget = self.parameter_list
        elif ind == 2:
            pass

if __name__ == "__main__":
    import sys
    from playback_manager import PlaybackManager
    from fish_manager import FishManager

    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    playback_manager.openTestFile()
    fish_manager = FishManager()
    fish_manager.testFill()
    info_w = InfoWidget(playback_manager, fish_manager)
    main_window.setCentralWidget(info_w)
    main_window.show()
    sys.exit(app.exec_())
