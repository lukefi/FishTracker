"""This module is used to display captured SONAR data from DIDOSN or ARIS
files, and also used to show results of the analysis, and details about
the detected fishes.
"""
# importing PyQt needed modules
import PyQt5.QtCore as pyqtCore
import PyQt5.QtGui as pyqtGUI
import PyQt5.QtWidgets as pyqtWidget

## DEBUG :{ following block of libraries for debug only
import os
import json
## }

import cv2
import iconsLauncher as uiIcons      # UI/iconsLauncher
# uif : (u)ser (i)nterface (f)unction
import UI_utils as uif              # UI/UI_utils
import AutoAnalyzer

## library for reading SONAR files
# FH: File Handler
import file_handler as FH
import numpy as np
import time
from ast import literal_eval


class FFishListItem():
    def __init__(self, cls, inputDict, fishNumber):
        self.fishNumber = fishNumber
        self.inputDict = inputDict
        self.listItem = pyqtWidget.QListWidgetItem()
        self.FWdiget = pyqtWidget.QWidget()

        self.FWdigetText = pyqtWidget.QLabel("Fish #{}".format(self.fishNumber))

        self.avgFishLength = pyqtWidget.QLabel()
        self.avgFishLength.setText("Length: {}".format(uif.getAvgLength()))
        
        self.FIfFish = pyqtWidget.QCheckBox("is Fish")
        self.FIfFish.setChecked(False)
        
        self.FWdigetBTN = pyqtWidget.QPushButton("Show")

        self.linkFish = pyqtWidget.QPushButton()
        self.linkFish.setIcon(pyqtGUI.QIcon(uiIcons.FGetIcon("link")))

        self.nameLengthLayout = pyqtWidget.QHBoxLayout()
        self.nameLengthLayout.addWidget(self.FWdigetText)
        self.nameLengthLayout.addWidget(self.avgFishLength)

        self.infoLayout = pyqtWidget.QHBoxLayout()
        self.infoLayout.addWidget(self.FIfFish)
        self.infoLayout.addWidget(self.linkFish)

        self.FWdigetBTN.clicked.connect(
            lambda: cls.showFish(self.fishNumber, self.inputDict)
        )
        self.FWdigetLayout = pyqtWidget.QVBoxLayout()
        self.FWdigetLayout.addLayout(self.nameLengthLayout)
        self.FWdigetLayout.addLayout(self.infoLayout)
        self.FWdigetLayout.addWidget(self.FWdigetBTN)
        self.FWdigetLayout.addStretch()
        # self.FWdigetLayout.setSizeConstraint(pyqtWidget.QLayout.SetFixedSize)
        self.FWdiget.setLayout(self.FWdigetLayout)
        self.listItem.setSizeHint(self.FWdiget.sizeHint())


    
class MyFigure(pyqtWidget.QLabel):
    __parent = None

    def __init__(self, parent):
        self.__parent = parent
        pyqtWidget.QLabel.__init__(self, parent)

    def paintEvent(self, paintEvent):
        if isinstance(self.__parent, FViewer):
            fviewer = self.__parent
            if fviewer.play:
                fviewer.FShowNextImage()
            
        pyqtWidget.QLabel.paintEvent(self, paintEvent)
    
    def mouseMoveEvent(self, event):
        if isinstance(self.__parent, FViewer):
            fviewer = self.__parent
            #print(self.pixmap().width(), self.pixmap().height())
            if self.pixmap():
                marginx = (self.width() - self.pixmap().width()) / 2

                if not fviewer.subtractBackground:
                    xs = (event.x() - marginx) / self.pixmap().width()
                else:
                    xs = event.x() - marginx

                    real_width = self.pixmap().width() / 2
                    if xs > real_width:
                        xs = (xs - real_width) / real_width
                    else:
                        xs = xs / real_width

                marginy = (self.height() - self.pixmap().height()) / 2
                ys = (event.y() - marginy) / self.pixmap().height()
                output = fviewer.File.getBeamDistance(xs, ys)
                fviewer.FParent.FStatusBarMousePos.setText("distance={}m\t,angle={}deg\t".format(output[0], output[1]))
                # self.mousePosDist = output[0]
                # self.mousePosAng = output[1]
    
    def resizeEvent(self, event):
        if isinstance(self.figurePixmap, pyqtGUI.QPixmap):
            self.setPixmap(self.figurePixmap.scaled(self.size(), pyqtCore.Qt.KeepAspectRatio))


class FViewer(pyqtWidget.QDialog):
    """This class holds the main window which will be used to 
    show the SONAR images, analyze them and edit images.
    
    Arguments:
        pyqtWidget.QDialog {Class} -- inheriting from 
                                      PyQt5.QtWidgets.QDialog class.
    """
    _BGS_Threshold = 25
    _fgbg = cv2.createBackgroundSubtractorMOG2(varThreshold = _BGS_Threshold)
    UI_FRAME_INDEX = 0
    subtractBackground = False
    _postAnalysisViewer = False
    play = False
    marker = None

    def __init__(self, parent, resultsView = False, results=False):
        """Initializes the window and loads the first frame and
        places the UI elements, each in its own place.
        """
        self._postAnalysisViewer = resultsView
        self.FDetectedDict = results
        self.FParent = parent
        self._MAIN_CONTAINER = parent._MAIN_CONTAINER
        ##  Reading the file
        self.FLoadSONARFile(self.FParent.FFilePath)
        self.FParent.FStatusBarFrameNumber.setText("Frame : "+str(self.UI_FRAME_INDEX+1)+"/"+str(self.File.frameCount))
        pyqtWidget.QDialog.__init__(self)
        self.setWindowTitle("Fisher - " + self.FFilePath)
        self.FLayout = pyqtWidget.QGridLayout()

        FNextBTN = pyqtWidget.QPushButton(self)
        FNextBTN.clicked.connect(self.FShowNextImage)
        FNextBTN.setShortcut(pyqtCore.Qt.Key_Right)
        FNextBTN.setIcon(pyqtGUI.QIcon(uiIcons.FGetIcon('next')))
        
        FPreviousBTN = pyqtWidget.QPushButton(self)
        FPreviousBTN.clicked.connect(self.FShowPreviousImage)
        FPreviousBTN.setShortcut(pyqtCore.Qt.Key_Left)
        FPreviousBTN.setIcon(pyqtGUI.QIcon(uiIcons.FGetIcon('previous')))
        
        self.FPlayBTN = pyqtWidget.QPushButton(self)
        self.FPlayBTN.clicked.connect(self.FPlay)
        self.FPlayBTN.setShortcut(pyqtCore.Qt.Key_Space)
        self.FPlayBTN.setIcon(pyqtGUI.QIcon(uiIcons.FGetIcon('play')))
        #self.FPlayBTN.setCheckable(True)
        
        self.FAutoAnalizerBTN = pyqtWidget.QPushButton(self)        
        self.FAutoAnalizerBTN.setObjectName("Automatic Analyzer")
        self.FAutoAnalizerBTN.setIcon(pyqtGUI.QIcon(uiIcons.FGetIcon('analyze')))
        self.FAutoAnalizerBTN.clicked.connect(self.FAutoAnalizer)

        self.F_BGS_BTN = pyqtWidget.QPushButton(self)
        self.F_BGS_BTN.setObjectName("Subtract Background")
        self.F_BGS_BTN.setFlat(True)
        self.F_BGS_BTN.setCheckable(True)
        self.F_BGS_BTN.setIcon(pyqtGUI.QIcon(uiIcons.FGetIcon("background_subtraction")))
        self.F_BGS_BTN.clicked.connect(self.FBackgroundSubtract)

        self.F_BGS_Slider = pyqtWidget.QSlider(pyqtCore.Qt.Vertical)
        self.F_BGS_Slider.setMinimum(0)
        self.F_BGS_Slider.setMaximum(100)
        self.F_BGS_Slider.setTickPosition(pyqtWidget.QSlider.TicksRight)
        self.F_BGS_Slider.setTickInterval(10)
        self.F_BGS_Slider.setValue(self._BGS_Threshold)
        self.F_BGS_Slider.valueChanged.connect(self.F_BGS_SliderValueChanged)
        self.F_BGS_Slider.setDisabled(True)

        self.F_BGS_ValueLabel = pyqtWidget.QLabel()
        
        #self.FFigure = pyqtWidget.QLabel("Frame Viewer", self)
        #self.FFigure.setUpdatesEnabled(True)
        
        self.MyFigureWidget = MyFigure(self)
        # self.MyFigureWidget.setUpdatesEnabled(True)
        self.MyFigureWidget.setSizePolicy(pyqtWidget.QSizePolicy.Ignored, pyqtWidget.QSizePolicy.Ignored)
        self.MyFigureWidget.setMouseTracking(True)

        self.FToolbar = pyqtWidget.QToolBar(self)
        self.FToolbar.addWidget(self.FAutoAnalizerBTN)
        self.FToolbar.addWidget(self.F_BGS_BTN)
        self.FToolbar.addWidget(self.F_BGS_ValueLabel)
        # self.FToolbar.add
        self.FToolbar.addWidget(self.F_BGS_Slider)
        self.FToolbar.setOrientation(pyqtCore.Qt.Vertical)
        self.FToolbar.setFixedWidth(self.FToolbar.minimumSizeHint().width())
        
        self.FSlider = pyqtWidget.QSlider(pyqtCore.Qt.Horizontal)
        self.FSlider.setMinimum(1)
        self.FSlider.setMaximum(self.File.frameCount)
        self.FSlider.setTickPosition(pyqtWidget.QSlider.TicksBelow)
        self.FSlider.setTickInterval(int(0.05*self.File.frameCount))
        self.FSlider.valueChanged.connect(self.FSliderValueChanged)

        self.FLayout.addWidget(self.FToolbar,0,0,3,1)
        self.FLayout.addWidget(self.MyFigureWidget,0,1,1,3)
        self.FLayout.addWidget(self.FSlider,1,1,1,3)
        #self.FLayout.addLayout(self.LowerToolbar, 2,1, Qt.AlignBottom)
        self.FLayout.addWidget(FPreviousBTN, 2,1)
        self.FLayout.addWidget(self.FPlayBTN, 2,2)
        self.FLayout.addWidget(FNextBTN, 2,3)
        
        self.FLayout.setContentsMargins(0,0,0,0)
        self.FLayout.setColumnStretch(0,0)
        self.FLayout.setColumnStretch(1,1)
        self.FLayout.setColumnStretch(2,1)
        self.FLayout.setColumnStretch(3,1)
        self.FLayout.setRowStretch(0,1)
        self.FLayout.setRowStretch(1,0)
        self.FLayout.setRowStretch(2,0)
        self.FLayout.setSizeConstraint(pyqtWidget.QLayout.SetMinimumSize)

        if self._postAnalysisViewer:
            self.FListDetected()

        self.setLayout(self.FLayout)
        self.FDisplayImage()

        
    def FShowNextImage(self):
        """Show the next frame image.
        """
        self.UI_FRAME_INDEX +=1
        if (self.UI_FRAME_INDEX > self.File.frameCount-1):
            self.UI_FRAME_INDEX = 0
        
        self.FSlider.setValue(self.UI_FRAME_INDEX+1)

    def FShowPreviousImage(self):
        """Show the previous frame image
        """

        self.UI_FRAME_INDEX -= 1
        if (self.UI_FRAME_INDEX < 0 ):
            self.UI_FRAME_INDEX = self.File.frameCount-1

        self.FSlider.setValue(self.UI_FRAME_INDEX+1)

    def FDisplayImage(self, ffigure = None):
        font = cv2.FONT_HERSHEY_SIMPLEX
        if ffigure is None:
            ffigure = self.MyFigureWidget

        ffigure.setUpdatesEnabled(False)
        ffigure.clear()

        qformat = pyqtGUI.QImage.Format_Indexed8

        if len(self.FFrames.shape)==3:
            if self.FFrames.shape[2]==4:
                qformat = pyqtGUI.QImage.Format_RGBA8888
            else:
                qformat = pyqtGUI.QImage.Format_RGB888
        
        if(self.subtractBackground):
            frameBlur = cv2.blur(self.FFrames, (5,5))
            mask = self._fgbg.apply(frameBlur)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel)
            mask = cv2.threshold(mask, 128, 255, cv2.THRESH_BINARY)[1]
        
            if(self.marker):
                cv2.circle(self.FFrames, literal_eval(self.marker), 30, (255,255,255), 1)
                cv2.circle(mask, literal_eval(self.marker), 30, (255,255,255), 1)
                
            img = np.hstack((mask, self.FFrames))
            img = pyqtGUI.QImage(img, img.shape[1], img.shape[0], img.strides[0], qformat)
        
        else:
            img = pyqtGUI.QImage(self.FFrames, self.FFrames.shape[1], self.FFrames.shape[0], self.FFrames.strides[0], qformat)
        
        img = img.rgbSwapped()
        ffigure.figurePixmap = pyqtGUI.QPixmap.fromImage(img)
        ffigure.setPixmap(ffigure.figurePixmap.scaled(ffigure.size(), pyqtCore.Qt.KeepAspectRatio))
        ffigure.setAlignment(pyqtCore.Qt.AlignCenter)
        self.FParent.FStatusBarFrameNumber.setText("Frame : "+str(self.UI_FRAME_INDEX+1)+"/"+str(self.File.frameCount))
        ffigure.setUpdatesEnabled(True)


    def FLoadSONARFile(self, filePath):
        self.FFilePath = filePath
        # FH: Sonar File Library
        self.File = FH.FOpenSonarFile(filePath)
        self.FFrames = self.File.FRAMES
    
    def FBackgroundSubtract(self):
        """
        This function enables and disables background subtraction in the
        UI. It is called from F_BGS_BTN pyqtWidget.QPushButton.
        """
        if (self.F_BGS_BTN.isChecked()):
            self.subtractBackground = True
            self.F_BGS_Slider.setDisabled(False)
            self.F_BGS_ValueLabel.setDisabled(False)
            self.F_BGS_ValueLabel.setText(str(self.F_BGS_Slider.value))
            self.kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (10,2))
        else:
            self.subtractBackground = False
            self.F_BGS_Slider.setDisabled(True)
            self.F_BGS_ValueLabel.setDisabled(True)

    def FSliderValueChanged(self, value):
        self.UI_FRAME_INDEX = value - 1
        self.FFrames = self.File.getFrame(self.UI_FRAME_INDEX)
        if self.marker:
            # print(self.marker)
            cv2.circle(self.FFrames, literal_eval(self.marker), 30, (255,255,255), 1)
            
        self.FDisplayImage()

    def F_BGS_SliderValueChanged(self):
        value = self.F_BGS_Slider.value()
        self.F_BGS_ValueLabel.setText(str(value))
        self._fgbg.setVarThreshold(value)

    def FAutoAnalizer(self):
        ## TODO _ : Documentation
        self.popup = pyqtWidget.QDialog(self)
        self.popupLayout = pyqtWidget.QFormLayout()
        # kernel size and shape {default: ellipse, (10,2)}
        self.morphStructLabel = pyqtWidget.QLabel("Morphological Structuring Element")
        self.morphStruct = pyqtWidget.QComboBox(self)
        self.morphStruct.addItem("Ellipse")
        self.morphStruct.addItem("Rectangle")
        self.morphStruct.addItem("Cross")
        self.morphStructDim = pyqtWidget.QLabel("Structuring Element Dimension")
        self.morphStructDimInp = pyqtWidget.QLineEdit()
        self.morphStructDimInp.setPlaceholderText("(10,2)")
        self.popupLayout.addRow(self.morphStructLabel, self.morphStruct)
        self.popupLayout.addRow(self.morphStructDim, self.morphStructDimInp)
        
        # start frame {default: 1}
        self.startFrame = pyqtWidget.QLabel("Start Frame")
        self.startFrameInp = pyqtWidget.QLineEdit()
        self.startFrameInp.setPlaceholderText("1")
        self.popupLayout.addRow(self.startFrame, self.startFrameInp)
        
        self.blurVal = pyqtWidget.QLabel("Blur Value")
        self.blurValInp = pyqtWidget.QLineEdit()
        self.blurValInp.setPlaceholderText("(5,5)")
        self.popupLayout.addRow(self.blurVal, self.blurValInp)
        
        self.bgTh = pyqtWidget.QLabel("Background Threshold")
        self.bgThInp = pyqtWidget.QLineEdit()
        self.bgThInp.setPlaceholderText("25")
        self.popupLayout.addRow(self.bgTh, self.bgThInp)
        
        self.maxApp = pyqtWidget.QLabel("Maximum Appearance")
        self.maxAppInp = pyqtWidget.QLineEdit()
        self.maxAppInp.setPlaceholderText("30 frames")
        self.popupLayout.addRow(self.maxApp, self.maxAppInp)
        
        self.maxDis = pyqtWidget.QLabel("Maximum Disappearance")
        self.maxDisInp = pyqtWidget.QLineEdit()
        self.maxDisInp.setPlaceholderText("5 frames")
        self.popupLayout.addRow(self.maxDis, self.maxDisInp)
        
        self.radiusInput = pyqtWidget.QLineEdit()
        self.radiusLabel = pyqtWidget.QLabel("Search radius (px)")
        self.radiusInput.setPlaceholderText("30 px")
        self.popupLayout.addRow(self.radiusLabel, self.radiusInput)
        
        self.showImages = pyqtWidget.QCheckBox("Show images while processing. (takes longer time)")
        self.showImages.setChecked(True)
        self.popupLayout.addRow(self.showImages)
        
        self.loadPresetBTN = pyqtWidget.QPushButton("Load Preset")
        self.loadPresetBTN.clicked.connect(lambda : uif.loadTemplate(self))
        
        self.savePresetBTN = pyqtWidget.QPushButton("Save Preset")
        self.savePresetBTN.clicked.connect(FH.saveAnalysisPreset)

        self.defaultPresetBTN = pyqtWidget.QPushButton("Defaults")
        self.defaultPresetBTN.clicked.connect(lambda: uif.loadTemplate(self, default=True))
        
        self.setAsDefaultBTN = pyqtWidget.QPushButton("Set As Defaults")
        self.setAsDefaultBTN.clicked.connect(FH.saveAnalysisPreset)

        self.startAnalysis = pyqtWidget.QPushButton("Start")
        self.startAnalysis.clicked.connect(self.handleAnalyzerInput)
        
        rowButtonsLayout1 = pyqtWidget.QHBoxLayout()
        rowButtonsLayout2 = pyqtWidget.QHBoxLayout()
        
        rowButtonsLayout1.addWidget(self.loadPresetBTN)
        rowButtonsLayout1.addWidget(self.savePresetBTN)
        rowButtonsLayout1.addWidget(self.setAsDefaultBTN)
        
        rowButtonsLayout2.addWidget(self.defaultPresetBTN)
        rowButtonsLayout2.addWidget(self.startAnalysis)
        
        self.popupLayout.addRow(rowButtonsLayout1)
        self.popupLayout.addRow(rowButtonsLayout2)

        self.popup.setLayout(self.popupLayout)
        self.popup.show()
        return

    def handleAnalyzerInput(self):
        ## TODO _ : function to take input from popup dialog box
        
        # handling kernel shape type from drop down menu 
        kernel = self.morphStruct.currentText()
        
        # handling kernel dimensions
        if self.morphStructDimInp.text() == "":
            kernelDim = None
        else:
            kernelDim = literal_eval(self.morphStructDimInp.text())

        # handling start frame index
        if self.startFrameInp.text() == "":
            startFrame = None
        else:
            startFrame = int(self.startFrameInp.text())

        # handling blur dimensions
        if self.blurValInp.text() == "":
            blurDim = None
        else:
            blurDim = literal_eval(self.blurValInp.text())

        # handling background threshold
        if self.bgThInp.text() == "":
            bgTh = None
        else:
            bgTh = int(self.bgThInp.text())

        # handling minimum appearance
        if self.maxAppInp.text() == "":
            minApp = None
        else:
            minApp = int(self.maxAppInp.text())

        # handling maximum disappearance
        if self.maxDisInp.text() == "" :
            maxDis = None
        else:
            maxDis = int(self.maxDisInp.text())

        # handling radius input
        if self.radiusInput.text() == "":
            searchRadius = None
        else:
            searchRadius = int(self.radiusInput.text())

        # handling show images checkbox
        if self.showImages.isChecked():
            imshow = True
        else:
            imshow = False

        print(kernel, type(kernel))
        print(kernelDim, type(kernelDim))
        print(startFrame, type(startFrame))
        print(blurDim, type(blurDim))
        print(bgTh, type(bgTh))
        print(minApp, type(minApp))
        print(maxDis, type(maxDis))
        print(searchRadius, type(searchRadius))
        print(imshow, type(imshow))

        ## DEBUG: { toggle next blocks
        # block 1
        dump = open(os.path.join(os.getcwd(), "data_all.json"))
        dump = dump.read()
        dump = json.loads(dump)
        self.FDetectedDict = dump['data']

        # block 2
        # self.FDetectedDict = AutoAnalyzer.FAnalyze(self, kernel = kernel, 
        #                                     kernelDim = kernelDim,
        #                                     startFrame = startFrame,
        #                                     blurDim = blurDim,
        #                                     bgTh= bgTh,
        #                                     minApp= minApp, 
        #                                     maxDis = maxDis,
        #                                     searchRadius= searchRadius,
        #                                     imshow = imshow)
        # }
        self.popup.close()
        if(len(self.FDetectedDict)):
            self.FResultsViewer = FViewer(self.FParent, resultsView= True, results=self.FDetectedDict)
            self.FParent.setCentralWidget(self.FResultsViewer)
        return

    def FPlay(self, eventQt):
        ## problem
        self.play = not self.play
        if self.play:
            self.FPlayBTN.setIcon(pyqtGUI.QIcon(uiIcons.FGetIcon('pause')))
            self.FShowNextImage()
        else: # pause
            self.FPlayBTN.setIcon(pyqtGUI.QIcon(uiIcons.FGetIcon('play')))
            
        return

    def FListDetected(self):
        index = 1
        listOfFish = list()
        self.FList = pyqtWidget.QListWidget()

        for fish in self.FDetectedDict.keys():
            listItem = FFishListItem(self, self.FDetectedDict[fish], index)
            self.FDetectedDict[fish]["index"] = listItem
            self.FList.addItem(listItem.listItem)
            self.FList.setItemWidget(listItem.listItem, listItem.FWdiget)
            listOfFish.append(listItem)
            index += 1

        # self.FShowSelectedBTN = pyqtWidget.QPushButton("Show Selected")
        # self.FShowSelectedBTN.clicked.connect(self.showSelectedFish)

        self.FApplyBTN = pyqtWidget.QPushButton("Apply")
        self.FApplyBTN.clicked.connect(self.FApply)

        # self.FLayout.addWidget(self.FApplyAllBTN, 2, 4)
        self.FLayout.addWidget(self.FApplyBTN, 2, 5)
        self.FLayout.addWidget(self.FList, 0,4,2,2, pyqtCore.Qt.AlignRight)
        return


    def showFish(self, fishNumber, inputDict):
        ## TODO _
        # ffigure = self.MyFigureWidget
        # ffigure.clear()
        # self.MyFigureWidget.clear()
        counter = 0
        print("Fish = ", fishNumber)
        for i in inputDict["frames"]:
            # ffigure.setUpdatesEnabled(False)
            self.UI_FRAME_INDEX = i
            x = int( inputDict["locations"][counter][0])
            y = int( inputDict["locations"][counter][1])
            
            self.marker = str(x)+','+str(y)
            self.FSlider.setValue(self.UI_FRAME_INDEX)
            
            self.marker = None
            self.repaint()
            counter +=1
        self.marker = None
        return


    def FApply(self):
        ## TODO _
        inputDict = self.FDetectedDict
        dictToBeSaved = dict()
        data = dict()
        for i in inputDict.keys():
            if inputDict[i]['index'].FIfFish.isChecked():
                dictToBeSaved[i] = inputDict[i]

        for n in dictToBeSaved.keys():
            data[str(n)] = {
                "ID" : dictToBeSaved[n]["ID"],
                "locations" : tuple(map(tuple, dictToBeSaved[n]["locations"])),
                "frames" : dictToBeSaved[n]["frames"],
                "left": list(map(int, dictToBeSaved[n]["left"])),
                "top": list(map(int, dictToBeSaved[n]["top"])),
                "width": list(map(int, dictToBeSaved[n]["width"])),
                "height" : list(map(int, dictToBeSaved[n]["height"])),
                "area": list(map(int, dictToBeSaved[n]["area"]))

            }
        path = self.File.FILE_PATH.split('.')
        path = path[0] + '.json'
        # path = os.path.join(path, fileName)            
        with open(path, 'w') as outFile:
            json.dump(data, outFile)
        
        return