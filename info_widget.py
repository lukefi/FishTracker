from PyQt5 import QtCore, QtGui, QtWidgets

class InfoWidget(QtWidgets.QDialog):
    def __init__(self, playback_manager):
        super().__init__()

        self.playback_manager = playback_manager

        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")

        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.testBtn1 = QtWidgets.QPushButton(self)
        self.testBtn2 = QtWidgets.QPushButton(self)
        self.testBtn3 = QtWidgets.QPushButton(self)

        self.testBtn1.setText("Button 1")
        self.testBtn2.setText("Button 2")
        self.testBtn3.setText("Button 3")

        self.testBtn1.setMaximumHeight(30)
        self.testBtn2.setMaximumHeight(30)
        self.testBtn3.setMaximumHeight(30)

        self.horizontalLayout.addWidget(self.testBtn1)
        self.horizontalLayout.addWidget(self.testBtn2)
        self.horizontalLayout.addWidget(self.testBtn3)

        self.verticalLayout.addLayout(self.horizontalLayout)

        self.setLayout(self.verticalLayout)

if __name__ == "__main__":
    import sys
    from playback_manager import PlaybackManager

    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    playback_manager.openTestFile()
    info_w = InfoWidget(playback_manager)
    main_window.setCentralWidget(info_w)
    main_window.show()
    sys.exit(app.exec_())
