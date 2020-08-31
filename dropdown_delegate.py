from PyQt5 import QtCore, QtGui, QtWidgets

class MyComboBox(QtWidgets.QComboBox):
    def __init__(self, parent):
        super().__init__(parent)

    def wheelEvent(self, event):
        event.ignore()

class DropdownDelegate(QtWidgets.QItemDelegate):
    def __init__(self):
        QtWidgets.QItemDelegate.__init__(self)

    def createEditor(self, parent, option, index):
        if index.model().isDropdown(index):
            combo=MyComboBox(parent)
            return combo
        else:
            lineedit=QtWidgets.QLineEdit(parent)
            return lineedit

    def setEditorData(self, editor, index):
        if isinstance(editor, MyComboBox):
            editor.clear()
            editor.addItems(index.model().dropdown_options())
            editor.setCurrentIndex(index.model().getDropdownIndex(index))

        if isinstance(editor, QtWidgets.QLineEdit):
            editor.setText(str(index.model().data(index, QtCore.Qt.DisplayRole)))

    #def setModelData(self, editor, model, index):
    #    if isinstance(editor, QtWidgets.QComboBox):
    #        model.setData(index, )

    #    if isinstance(editor, QtWidgets.QLineEdit):
    #        editor.setText(str(index.model().data(index, QtCore.Qt.DisplayRole)))


class Model(QtCore.QAbstractTableModel):
    """
    Used only as a test class for DropdownDelegate
    """

    def __init__(self):
        QtCore.QAbstractTableModel.__init__(self)
        self.items = [[1, 'one', 'ONE'], [2, 'two', 'TWO'], [3, 'three', 'THREE']]

    def flags(self, index):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable
    def rowCount(self, parent=QtCore.QModelIndex()):
        return 3 
    def columnCount(self, parent=QtCore.QModelIndex()):
        return 3

    def data(self, index, role):
        if not index.isValid(): return 
        row = index.row()
        column = index.column()
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            return self.items[row][column]

    def isDropdown(self, index):
        return index.column() == 2

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

    for row in range(tableModel.rowCount()):
        for column in range(tableModel.columnCount()):
            index=tableModel.index(row, column)
            if tableModel.isDropdown(index):
                tableView.openPersistentEditor(index)

    tableView.show()
    app.exec_()