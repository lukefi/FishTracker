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

import sys
import file_handler as fh

from PyQt5 import QtGui, QtCore, QtWidgets
from playback_manager import PlaybackManager

from batch_dialog import batchSaveOptions, setupCheckbox
from collapsible_box import CollapsibleBox
from detector_parameters_view import LabeledSlider

def setupSlider(label, tooltip, layout, key, min_v, max_v):
    val = fh.getConfValue(key)
    fun = lambda x: fh.setConfValue(key, x)
    qlabel = QtWidgets.QLabel(label)
    qlabel.setToolTip(tooltip)
    slider = LabeledSlider(qlabel, layout, [fun], val, min_v, max_v)
    slider.slider.setToolTip(tooltip)
    slider.value.setToolTip(tooltip)
    return slider

def addLine(label, tooltip, initial_value, validator, connected, layout):
    qlabel = QtWidgets.QLabel(label)
    qlabel.setToolTip(tooltip)
    line = QtWidgets.QLineEdit()
    line.setAlignment(QtCore.Qt.AlignRight)
    line.setValidator(validator)
    line.setText(str(initial_value))
    line.setToolTip(tooltip)
    for f in connected:
        line.textChanged.connect(f)
    layout.addRow(qlabel, line)
    return line


class UserPreferencesDialog(QtWidgets.QDialog):
    def __init__(self, playback_manager):
        super().__init__()
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)
        self.playback_manager = playback_manager
        self.initUI()
        self.resize(640, 480)

    def initUI(self):
        self.main_layout = QtWidgets.QVBoxLayout(self)

        self.form_layout = QtWidgets.QFormLayout()

        #"log_timestamp": false,
        self.check_timestamps = setupCheckbox("Log timestamp", "If checked, displays timestamps in the logged messages.",
                                              self.form_layout, fh.ConfKeys.log_timestamp)

        #"log_verbosity": 0,
        self.verbose_slider = setupSlider("Log verbosity", "0: Default, 1: Additional information, 2: Developer infromation",
                                          self.form_layout, fh.ConfKeys.log_verbosity, 0, 2)

        #"save_as_binary": false,
        self.check_timestamps = setupCheckbox("Save as binary", "If checked, saves the results in binary format to save space.",
                                              self.form_layout, fh.ConfKeys.log_timestamp)

        #"sonar_height": 1000,
        val = fh.getConfValue(fh.ConfKeys.sonar_height)
        fun = lambda x: fh.setConfValue(fh.ConfKeys.sonar_height, x)
        sh_tooltip = "Determines the image height used in the SonarViewer. This affects the speed of the analysis and the obtained results."
        self.sonar_height_line = addLine("Sonar image height\t\t", sh_tooltip, val, QtGui.QIntValidator(100, 10000), [fun], self.form_layout)


        self.cbox_general = CollapsibleBox("General options", self)
        self.cbox_general.setContentLayout(self.form_layout)
        self.cbox_general.on_pressed()
        self.main_layout.addWidget(self.cbox_general)

        self.cbox_batch = batchSaveOptions("Batch options")
        self.cbox_batch.on_pressed()
        self.main_layout.addWidget(self.cbox_batch)

        self.setLayout(self.main_layout)
        self.setWindowTitle("User preferences")

if __name__ == "__main__":
    def showDialog():
        dialog = UserPreferencesDialog(playback_manager)
        dialog.exec_()

    app = QtWidgets.QApplication(sys.argv)
    w = QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, w)

    b = QtWidgets.QPushButton(w)
    b.setText("Show dialog")
    b.move(50,50)
    b.clicked.connect(showDialog)
    w.setWindowTitle("BatcDialog test")
    w.show()
    showDialog()
    sys.exit(app.exec_())