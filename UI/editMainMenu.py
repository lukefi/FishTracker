"""
This module is used to initialize `Edit` drop down menu
that is placed in the main menu bar.

Functions used are available in the `UI/UI_utils` module.

Takes an instance of class `QMainWindow` which in this case
is called `FMainContainer`
"""
# importing PyQt needed modules
import PyQt5.QtWidgets as pyqtWidget

# uif : (u)ser (i)nterface (f)unction
import UI_utils as uif      # UI/UI_utils

def FEditMenu_init(FMainContainer):
    ## TODO _ : implement undo function
    FMainContainer.undoAction = pyqtWidget.QAction("Undo", FMainContainer)
    FMainContainer.undoAction.setShortcut("Ctrl+Z")
    FMainContainer.undoAction.setEnabled(False)
    FMainContainer.undoAction.setStatusTip("Undoes the last action.")
    FMainContainer.undoAction.triggered.connect(lambda: uif.print_stat_msg("Undo pressed."))

    ## TODO _ : implement redo function
    FMainContainer.redoAction = pyqtWidget.QAction("Redo", FMainContainer)
    FMainContainer.redoAction.setShortcut("Ctrl+Y")
    FMainContainer.redoAction.setEnabled(False)
    FMainContainer.redoAction.setStatusTip("Redoes the last action.")
    FMainContainer.redoAction.triggered.connect(lambda: uif.print_stat_msg("Redo pressed."))

    FMainContainer.editMenu = FMainContainer.mainMenu.addMenu("&Edit")
    FMainContainer.editMenu.addAction(FMainContainer.undoAction)
    FMainContainer.editMenu.addAction(FMainContainer.redoAction)

