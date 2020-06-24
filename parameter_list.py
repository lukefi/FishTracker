from PyQt5 import QtCore, QtGui, QtWidgets

class ParameterList(QtWidgets.QDialog):
    def __init__(self, fish_manager):
        super().__init__()
        self.fish_manager = fish_manager

        self.label = QtWidgets.QLabel(self)
        self.label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.label.setText("Parameters")

        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.addWidget(self.label)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setContentsMargins(0,0,0,0)
        self.setLayout(self.verticalLayout)