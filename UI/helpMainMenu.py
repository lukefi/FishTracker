"""
This module is used to initialize `Help` drop down menu
that is placed in the main menu bar.

Functions used are available in the `UI_utils` module.

Takes an instance of class `QMainWindow` which in this case
is called `FMainContainer`

"""
# importing PyQt needed modules
import PyQt5.QtCore as pyqtCore
import PyQt5.QtGui as pyqtGUI
import PyQt5.QtWidgets as pyqtWidget

# uif : (u)ser (i)nterface (f)unction
import UI_utils as uif                  # UI/UI_utils

def FHelpMenu_init(FMainContainer):
    FMainContainer.aboutLUKEAction = pyqtWidget.QAction("LUKE", FMainContainer)
    FMainContainer.aboutLUKEAction.setStatusTip("Opens a webpage contains all info about LUKE.")
    FMainContainer.aboutLUKEAction.triggered.connect(uif.lukeInfo)

    FMainContainer.aboutUniOuluAction = pyqtWidget.QAction("University of Oulu", FMainContainer)
    FMainContainer.aboutUniOuluAction.setStatusTip("Opens a webpage contains all info about the University of Oulu.")
    FMainContainer.aboutUniOuluAction.triggered.connect(uif.uniOuluInfo)

    FMainContainer.aboutFisherAction = pyqtWidget.QAction("About Fisher", FMainContainer)
    FMainContainer.aboutFisherAction.setStatusTip("Opens a webpage contains all info about the project.")
    FMainContainer.aboutFisherAction.triggered.connect(uif.fisherInfo)

    ## TODO _ : add signal handler to check for updates
    FMainContainer.checkForUpdatesAction = pyqtWidget.QAction("Check for updates", FMainContainer)
    FMainContainer.checkForUpdatesAction.setStatusTip("Check for updates online")
    FMainContainer.checkForUpdatesAction.triggered.connect(lambda: FMainContainer.print_stat_msg("Check for updates pressed."))
    FMainContainer.checkForUpdatesAction.setEnabled(False)

    ## TODO _ : add signal handler to show license file.
    FMainContainer.viewLicenseAction = pyqtWidget.QAction("View License", FMainContainer)
    FMainContainer.viewLicenseAction.setStatusTip("Shows the licenses for the whole software.")
    FMainContainer.viewLicenseAction.triggered.connect(lambda: FMainContainer.print_stat_msg("view license pressed."))
    FMainContainer.viewLicenseAction.setEnabled(False)

    ## TODO _ : add signal handler to report an issue with the software
    FMainContainer.reportAction = pyqtWidget.QAction("Report Issue", FMainContainer)
    FMainContainer.reportAction.setStatusTip("Report an issue to the developers.")
    FMainContainer.reportAction.triggered.connect(lambda : FMainContainer.print_stat_msg("reprot issure pressed."))
    FMainContainer.reportAction.setEnabled(False)
    
    ## TODO _ : add signal handler to show statistics
    FMainContainer.showStatisticsAction = pyqtWidget.QAction("Statistics", FMainContainer)
    FMainContainer.showStatisticsAction.setStatusTip("Shows statistics about old processed files.")
    FMainContainer.showStatisticsAction.triggered.connect(lambda : FMainContainer.print_stat_msg("Statistics pressed."))
    FMainContainer.showStatisticsAction.setEnabled(False)

    FMainContainer.helpMenu = FMainContainer.mainMenu.addMenu("&Help")
    FMainContainer.helpMenu.addAction(FMainContainer.showStatisticsAction)
    FMainContainer.helpMenu.addSeparator()
    FMainContainer.helpMenu.addAction(FMainContainer.reportAction)
    FMainContainer.helpMenu.addAction(FMainContainer.viewLicenseAction)
    FMainContainer.helpMenu.addAction(FMainContainer.checkForUpdatesAction)
    FMainContainer.helpMenu.addSeparator()
    FMainContainer.helpMenu.addAction(FMainContainer.aboutLUKEAction)
    FMainContainer.helpMenu.addAction(FMainContainer.aboutUniOuluAction)
    FMainContainer.helpMenu.addAction(FMainContainer.aboutFisherAction)
