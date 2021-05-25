# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'sonar_view3.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1113, 845)
        MainWindow.setStyleSheet("QSplitter::handle:horizontal {\n"
"background: qlineargradient(x1:0, y1:0, x2:1, y2:1,\n"
"    stop:0 #eee, stop:1 #ccc);\n"
"border: 0px solid #777;\n"
"width: 3px;\n"
"border-radius: 4px;\n"
"}\n"
"\n"
"QSplitter::handle:vertical {\n"
"background: qlineargradient(x1:0, y1:0, x2:1, y2:1,\n"
"    stop:0 #eee, stop:1 #ccc);\n"
"border: 0px solid #777;\n"
"height: 3px;\n"
"border-radius: 4px;\n"
"}\n"
"")
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.centralwidget.setStyleSheet("")
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.tool_bar = QtWidgets.QWidget(self.centralwidget)
        self.tool_bar.setMaximumSize(QtCore.QSize(30, 16777215))
        self.tool_bar.setObjectName("tool_bar")
        self.horizontalLayout_2.addWidget(self.tool_bar)
        self.splitter_2 = QtWidgets.QSplitter(self.centralwidget)
        self.splitter_2.setOrientation(QtCore.Qt.Vertical)
        self.splitter_2.setObjectName("splitter_2")
        self.echogram_widget = QtWidgets.QWidget(self.splitter_2)
        self.echogram_widget.setMaximumSize(QtCore.QSize(16777215, 250))
        self.echogram_widget.setObjectName("echogram_widget")
        self.splitter = QtWidgets.QSplitter(self.splitter_2)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.sonar_widget = QtWidgets.QWidget(self.splitter)
        self.sonar_widget.setObjectName("sonar_widget")
        self.info_widget = QtWidgets.QTabWidget(self.splitter)
        self.info_widget.setTabShape(QtWidgets.QTabWidget.Rounded)
        self.info_widget.setObjectName("info_widget")
        self.tab_1 = QtWidgets.QWidget()
        self.tab_1.setObjectName("tab_1")
        self.info_widget.addTab(self.tab_1, "")
        self.horizontalLayout_2.addWidget(self.splitter_2)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1113, 21))
        self.menubar.setObjectName("menubar")
        self.menu_File = QtWidgets.QMenu(self.menubar)
        self.menu_File.setObjectName("menu_File")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.action_Open = QtWidgets.QAction(MainWindow)
        self.action_Open.setObjectName("action_Open")
        self.menu_File.addAction(self.action_Open)
        self.menubar.addAction(self.menu_File.menuAction())

        self.menu_Run = QtWidgets.QMenu(self.menubar)
        self.menu_Run.setObjectName("menu_Run")
        self.action_Batch = QtWidgets.QAction(MainWindow)
        self.action_Batch.setObjectName("action_Batch")
        self.menu_Run.addAction(self.action_Batch)
        self.menubar.addAction(self.menu_Run.menuAction())

        self.retranslateUi(MainWindow)
        self.info_widget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.info_widget.setTabText(self.info_widget.indexOf(self.tab_1), _translate("MainWindow", "Tab 1"))
        self.menu_File.setTitle(_translate("MainWindow", "&File"))
        self.menu_Run.setTitle(_translate("MainWindow", "&Run"))
        self.action_Open.setText(_translate("MainWindow", "&Open"))
        self.action_Batch.setText(_translate("MainWindow", "&Batch"))

