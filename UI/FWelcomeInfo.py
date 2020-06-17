import PyQt5.QtCore as pyqtCore
import PyQt5.QtGui as pyqtGUI
import PyQt5.QtWidgets as pyqtWidgets
import iconsLauncher as uiIcons         # UI/iconsLauncher
import os
import webbrowser

import UI_utils as uif                  # UI/UI_utils


class FWelcomeInfo(pyqtWidgets.QDialog):
    """This class will hold information screen about the software
    and its owners and developers.
    
    Arguments:
        pyqtWidgets.QDialog {Class} -- superclass which this is class is
                                    subclassed from.
    """
    
    def __init__(self, parent):
        pyqtWidgets.QDialog.__init__(self)
        self._MAIN_CONTAINER = parent
        self.FParent = parent
        self.FLayout = pyqtWidgets.QGridLayout()

        FOpenFileBTN = pyqtWidgets.QPushButton("OPEN FILE", self)
        FOpenFileBTN.clicked.connect(lambda : uif.FOpenFile(self.FParent))

        # FShowStatsBTN = pyqtWidgets.QPushButton("STATISTICS", self)
        # FShowStatsBTN.clicked.connect(self.FShowStats)

        FAboutBTN = pyqtWidgets.QPushButton("ABOUT", self)
        FAboutBTN.clicked.connect(self.FAbout)

        FInfo = pyqtWidgets.QLabel()
        FInfo.setText("Fisher is an open-source software developed by the University of Oulu, Finland in collaboration with the Natural Resources Institute in Finland.")
        FInfo.setWordWrap(True)

        self.UniOuluImage = pyqtWidgets.QLabel()
        UniOuluImagePath = os.path.join(uiIcons.iconsDir, "welcome_logos", "uni_oulu_300.png")
        self.uniOuluPixmap = pyqtGUI.QPixmap(UniOuluImagePath)
        self.UniOuluImage.setPixmap(self.uniOuluPixmap)
        self.UniOuluImage.setScaledContents(True)
        
        self.LukeImage = pyqtWidgets.QLabel()
        LukeImagePath = os.path.join(uiIcons.iconsDir, "welcome_logos", "luke_300.png")
        self.lukePixmap = pyqtGUI.QPixmap(LukeImagePath)
        self.LukeImage.setPixmap(self.lukePixmap)
        self.LukeImage.setScaledContents(True)
        
        logosLayout = pyqtWidgets.QHBoxLayout()
        logosLayout.addWidget(self.UniOuluImage)
        logosLayout.addWidget(self.LukeImage)
        
        buttonsLayout = pyqtWidgets.QVBoxLayout()
        buttonsLayout.addWidget(FOpenFileBTN)
        # buttonsLayout.addWidget(FShowStatsBTN)
        buttonsLayout.addWidget(FAboutBTN)
        
        self.FLayout.addLayout(logosLayout, 0,1, pyqtCore.Qt.AlignCenter)
        self.FLayout.addWidget(FInfo, 1,1, pyqtCore.Qt.AlignVCenter)

        self.FLayout.addLayout(buttonsLayout, 0,0)

        # self.FLayout.setColumnStretch(0, 1)
        # self.FLayout.setColumnStretch(1, 4)
        self.setLayout(self.FLayout)

    def FShowStats(self):
        ## TODO _ : Implement function to show statistics.
        """Intended statistics include, but not limited to,
            + number of files opened (.ddf, .aris)
            + number of fish captured
            + days with the highest and lowest number of fish
            + Water levels and temperatures

        """

        pass

    def FAbout(self):
        """Opens a new tab in the default webbrowser, and displays the
        documentation of the software.
        """
        url = "https://minamaged113.github.io/fish-tracking/#"
        return webbrowser.open_new_tab(url)

    def resizeEvent(self, event):
        if isinstance(self.lukePixmap, pyqtGUI.QPixmap):
            self.LukeImage.setPixmap(self.lukePixmap.scaled(self.LukeImage.size(), pyqtCore.Qt.KeepAspectRatio))
            self.UniOuluImage.setPixmap(self.uniOuluPixmap.scaled(self.UniOuluImage.size(), pyqtCore.Qt.KeepAspectRatio))

