from PyQt5 import QtCore, QtGui, QtWidgets
from fish_manager import pyqt_palette

class MyComboBox(QtWidgets.QComboBox):
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
    #color_default = QtGui.QColor("#aaedff")

    def __init__(self):
        QtWidgets.QItemDelegate.__init__(self)

    def createEditor(self, parent, option, index):
        if index.model().isColor(index):
            return ColorEditor(parent)
        elif index.model().isDropdown(index):
            combo=MyComboBox(parent)
            return combo
        else:
            return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        if isinstance(editor, MyComboBox):
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

    #def paint(self, painter, option, index):
    #    if option.state & QtWidgets.QStyle.State_Selected:
    #        option.palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
    #        color = self.combineColors(self.color_default, self.background(option, index))
    #        option.palette.setColor(QtGui.QPalette.Highlight, color)
    #    super().paint(painter, option, index)

    #def background(self, option, index):
    #    return option.palette.color(QtGui.QPalette.Base)

    #@staticmethod
    #def combineColors(c1, c2):
    #    c3 = QtGui.QColor()
    #    c3.setRed((c1.red() + c2.red()) / 2)
    #    c3.setGreen((c1.green() + c2.green()) / 2)
    #    c3.setBlue((c1.blue() + c2.blue()) / 2)

    #    return c3


    #def setModelData(self, editor, model, index):
    #    if isinstance(editor, QtWidgets.QComboBox):
    #        model.setData(index, )

    #    if isinstance(editor, QtWidgets.QLineEdit):
    #        editor.setText(str(index.model().data(index, QtCore.Qt.DisplayRole)))

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

    #def sizeHint(self):
    #    return QtCore.QSize(self.scale, self.scale)

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