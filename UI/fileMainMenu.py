"""
This module is used to initialize `File` drop down menu that is placed in
the main menu bar.

Functions used are available in the `UI_utils` module.

Takes an instance of class `QMainWindow` which in this case is called
`FMainContainer`
"""
# importing PyQt needed modules
import PyQt5.QtCore as pyqtCore
import PyQt5.QtGui as pyqtGUI
import PyQt5.QtWidgets as pyqtWidget

# uif : (u)ser (i)nterface (f)unction
import UI_utils as uif      # UI/UI_utils


def FFileMenu_init(FMainContainer):
    """Function called at the launch of the program
    ## TODO _ : Documentation
    Arguments:
        FMainContainer {[type]} -- [description]
    """

    FMainContainer.openFileAction = pyqtWidget.QAction(FMainContainer.tr("&Open File"),
                                                       FMainContainer)
    FMainContainer.openFileAction.setShortcut("Ctrl+O")
    FMainContainer.openFileAction.setStatusTip(
        "Loads a new file to the program.")
    FMainContainer.openFileAction.triggered.connect(
        lambda: FOpenFile(FMainContainer.centralWidget()))

    # TODO _ : load a folder for a day processing
    FMainContainer.openFolderAction = pyqtWidget.QAction(FMainContainer.tr("Open Folder"),
                                                         FMainContainer)
    FMainContainer.openFolderAction.setShortcut("Ctrl+Shift+O")
    FMainContainer.openFolderAction.setStatusTip(
        "Opens a whole folder and loads it to the program.")
    FMainContainer.openFolderAction.triggered.connect(
        lambda: print_stat_msg("Open Folder pressed."))
    FMainContainer.openFolderAction.setEnabled(False)

    # TODO _ : add signal handler to save file after editing.
    FMainContainer.saveFileAction = pyqtWidget.QAction(FMainContainer.tr(
                                                       "&Save"),
                                                       FMainContainer)
    FMainContainer.saveFileAction.setShortcut("Ctrl+S")
    FMainContainer.saveFileAction.setStatusTip("Saves the current file.")
    FMainContainer.saveFileAction.triggered.connect(lambda: print_stat_msg(
                                                    "save file pressed."))
    FMainContainer.saveFileAction.setEnabled(False)

    # TODO _ : add signal handler to save file as new file
    FMainContainer.saveFileAsAction = pyqtWidget.QAction(
        FMainContainer.tr("Save as ..."),
        FMainContainer
    )
    FMainContainer.saveFileAsAction.setShortcut("Ctrl+Shift+S")
    FMainContainer.saveFileAsAction.setStatusTip(
        "Saves current work as new file.")
    FMainContainer.saveFileAsAction.triggered.connect(
        lambda: print_stat_msg("Save file as pressed.")
    )
    FMainContainer.saveFileAsAction.setEnabled(False)

    # TODO _ : setEnabled(True) only when the user opens a new file.
    FMainContainer.exportAsJPGAction = pyqtWidget.QAction(
        "Export as JPG", FMainContainer)
    FMainContainer.exportAsJPGAction.setStatusTip(
        "Saves number of images on the drive in a given directory.")
    FMainContainer.exportAsJPGAction.triggered.connect(
        uif.exportAsJPGActionFunction)
    FMainContainer.exportAsJPGAction.setEnabled(False)

    # TODO _ : setEnabled(True) only when the user opens a new file.
    FMainContainer.export_BGS_AsJPGAction = pyqtWidget.QAction(
        FMainContainer.tr("Export BGS as JPG"),
        FMainContainer
    )
    FMainContainer.export_BGS_AsJPGAction.setStatusTip(
        "Saves number of background \
                                            subtracted images on the drive \
                                            in a given directory."
    )
    FMainContainer.export_BGS_AsJPGAction.triggered.connect(
        uif.export_BGS_AsJPGActionFunction)
    FMainContainer.export_BGS_AsJPGAction.setEnabled(False)

    FMainContainer.exitAction = pyqtWidget.QAction("Exit", FMainContainer)
    FMainContainer.exitAction.setShortcut("Ctrl+Q")
    FMainContainer.exitAction.setStatusTip("Exits the application.")
    FMainContainer.exitAction.triggered.connect(
        pyqtCore.QCoreApplication.instance().quit)

    FMainContainer.fileMenu = FMainContainer.mainMenu.addMenu("&File")
    FMainContainer.fileMenu.addAction(FMainContainer.openFileAction)
    FMainContainer.fileMenu.addAction(FMainContainer.openFolderAction)
    FMainContainer.fileMenu.addAction(FMainContainer.saveFileAction)
    FMainContainer.fileMenu.addAction(FMainContainer.saveFileAsAction)
    # Adding openRecent drop-down menu inside file menu.
    ## TODO _ : store recent files and be able to read them
    ## add them later to the list of open recent.
    openRecentMenu = FMainContainer.fileMenu.addMenu(
        FMainContainer.tr("Open Recent"))
    recentItem1 = pyqtWidget.QAction(
        "Not implemented", FMainContainer)
    recentItem1.setEnabled(False)
    openRecentMenu.addAction(recentItem1)
    # Adding export drop-down menu inside file menu.
    exportMenu = FMainContainer.fileMenu.addMenu(FMainContainer.tr("Export"))
    exportMenu.addAction(FMainContainer.exportAsJPGAction)
    exportMenu.addAction(FMainContainer.export_BGS_AsJPGAction)

    FMainContainer.fileMenu.addSeparator()
    # ---------------------------------------
    FMainContainer.fileMenu.addAction(FMainContainer.exitAction)
