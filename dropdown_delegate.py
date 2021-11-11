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
from fish_manager import pyqt_palette

class ModifiedComboBox(QtWidgets.QComboBox):
    def __init__(self, parent):
        super().__init__(parent)

    def wheelEvent(self, event):
        event.ignore()

    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Enter or key == QtCore.Qt.Key_Return:
            self.showPopup()
        else:
            event.ignore()

class DropdownDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self):
        QtWidgets.QItemDelegate.__init__(self)

    def createEditor(self, parent, option, index):
        if index.model().isColor(index):
            return ColorEditor(parent)
        elif index.model().isDropdown(index):
            combo=ModifiedComboBox(parent)
            return combo
        else:
            return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        if isinstance(editor, ModifiedComboBox):
            editor.clear()
            editor.addItems(index.model().dropdown_options())
            editor.setCurrentIndex(index.model().getDropdownIndex(index))
        else:
            super().setEditorData(editor, index)

        if isinstance(editor, QtWidgets.QLineEdit):
            editor.setText(str(index.model().data(index, QtCore.Qt.DisplayRole)))

    def paint(self, painter, option, index):
        if index.model().isColor(index):            
            if option.state & QtWidgets.QStyle.State_Selected:
                if option.state & QtWidgets.QStyle.State_Active:
                    painter.fillRect(option.rect, option.palette.highlight())
                else:
                    painter.fillRect(option.rect, option.palette.brush(QtGui.QPalette.Window))

            color_label = ColorLabel()
            ind = index.model().data(index, QtCore.Qt.DisplayRole)
            color_label.paint(painter, option.rect, option.palette, pyqt_palette[ind])
        else:
            super().paint(painter, option, index)


class ColorEditor(QtWidgets.QWidget):
    # A signal to tell the delegate when we've finished editing.
    editingFinished = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMouseTracking(True)
        self.setAutoFillBackground(True)
        self.color_label = ColorLabel()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        self.color_label.paint(painter, self.rect(), self.palette(), pyqt_palette[0], isEditable=True)

    def mouseMoveEvent(self, event):
        pass

    def mouseReleaseEvent(self, event):
        self.editingFinished.emit()

class ColorLabel(object):
    def __init__(self, color_count=16):
        self.color_count = color_count
        self.scale = 15

    def paint(self, painter, rect, palette, color, isEditable=False):
        painter.save()

        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        painter.setPen(QtGui.QPen(palette.windowText(), 1, QtCore.Qt.SolidLine))

        painter.setBrush(QtGui.QBrush(color, QtCore.Qt.SolidPattern))

        x_offset = (rect.width() - self.scale) / 2
        y_offset = (rect.height() - self.scale) / 2
        painter.translate(rect.x() + x_offset, rect.y() + y_offset)
        painter.drawEllipse(0, 0, self.scale, self.scale)


        painter.restore()

class Model(QtCore.QAbstractTableModel):
    """
    Used only as a test class for DropdownDelegate
    """

    def __init__(self):
        QtCore.QAbstractTableModel.__init__(self)
        self.items = [[1, 1, 'one', 'ONE'], [2, 2, 'two', 'TWO'], [3, 3, 'three', 'THREE'], [4, 4, 'four', 'FOUR'], [5, 5, 'five', 'FIVE']]

    def flags(self, index):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable
    def rowCount(self, parent=QtCore.QModelIndex()):
        return 5
    def columnCount(self, parent=QtCore.QModelIndex()):
        return 4

    def data(self, index, role):
        if not index.isValid(): return 
        row = index.row()
        column = index.column()
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            return self.items[row][column]

    def isColor(self, index):
        return index.column() == 0

    def isDropdown(self, index):
        return index.column() == 3

    def dropdown_options(self):
        return ["UP", "DOWN", "NONE"]

    def getDropdownIndex(self, index):
        return index.row()

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    tableModel=Model()
    tableView=QtWidgets.QTableView() 
    tableView.setModel(tableModel)
    tableView.setItemDelegate(DropdownDelegate())
    tableView.setColumnWidth(0, 30)

    for row in range(tableModel.rowCount()):
        for column in range(tableModel.columnCount()):
            index=tableModel.index(row, column)
            if tableModel.isDropdown(index):
                tableView.openPersistentEditor(index)

    tableView.show()
    app.exec_()