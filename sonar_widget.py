"""This module is used to display captured SONAR data from DIDOSN or ARIS
files, and also used to show results of the analysis, and details about
the detected fishes.
"""
from PyQt5 import QtCore, QtGui, QtWidgets
from main import MainWindow
from image_manipulation import ImageProcessor
from zoomable_qlabel import ZoomableQLabel

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
from matplotlib import pyplot as plt

class SonarViewer(QtWidgets.QDialog):
    """This class holds the main window which will be used to 
    show the SONAR images, analyze them and edit images.
    
    Arguments:
        QtWidgets.QDialog {Class} -- inheriting from 
                                      PyQt5.QtWidgets.QDialog class.
    """
    _BGS_Threshold = 25
    _fgbg = cv2.createBackgroundSubtractorMOG2(varThreshold = _BGS_Threshold)
    UI_FRAME_INDEX = 0
    subtractBackground = False
    _postAnalysisViewer = False
    play = False
    marker = None

    def __init__(self, main_window, playback_manager, resultsView = False, results=False):
        """Initializes the window and loads the first frame and
        places the UI elements, each in its own place.
        """
        self._postAnalysisViewer = resultsView
        self.FDetectedDict = results
        self.main_window = main_window
        self.playback_manager = playback_manager
        self.playback_manager.frame_available.append(self.displayImage)
        self.playback_manager.playback_ended.append(self.choosePlayIcon)
        self.playback_manager.file_opened.append(self.onFileOpen)
        self.image_processor = ImageProcessor()
        self.show_first_frame = False

        #self.FParent = parent
        #self._MAIN_CONTAINER = parent._MAIN_CONTAINER
        ##  Reading the file
        # self.FLoadSONARFile(self.FParent.FFilePath)
        if isinstance(self.main_window, MainWindow):
            self.main_window.FStatusBarFrameNumber.setText(self.playback_manager.getFrameNumberText())

        QtWidgets.QDialog.__init__(self)
        #self.setWindowTitle("Fisher - " + self.FFilePath)
        self.FLayout = QtWidgets.QGridLayout()

        FNextBTN = QtWidgets.QPushButton(self)
        FNextBTN.clicked.connect(self.playback_manager.showNextImage)
        FNextBTN.setShortcut(QtCore.Qt.Key_Right)
        FNextBTN.setIcon(QtGui.QIcon(uiIcons.FGetIcon('next')))
        
        FPreviousBTN = QtWidgets.QPushButton(self)
        FPreviousBTN.clicked.connect(self.playback_manager.showPreviousImage)
        FPreviousBTN.setShortcut(QtCore.Qt.Key_Left)
        FPreviousBTN.setIcon(QtGui.QIcon(uiIcons.FGetIcon('previous')))
        
        self.FPlayBTN = QtWidgets.QPushButton(self)
        self.FPlayBTN.clicked.connect(self.togglePlayPause) #self.playback_manager.play
        self.FPlayBTN.setShortcut(QtCore.Qt.Key_Space)
        self.FPlayBTN.setIcon(QtGui.QIcon(uiIcons.FGetIcon('play')))
        #self.FPlayBTN.setCheckable(True)
        
        #self.FAutoAnalizerBTN = QtWidgets.QPushButton(self)        
        #self.FAutoAnalizerBTN.setObjectName("Automatic Analyzer")
        #self.FAutoAnalizerBTN.setIcon(QtGui.QIcon(uiIcons.FGetIcon('analyze')))
        #self.FAutoAnalizerBTN.clicked.connect(self.FAutoAnalizer)

        self.F_BGS_BTN = QtWidgets.QPushButton(self)
        self.F_BGS_BTN.setObjectName("Subtract Background")
        self.F_BGS_BTN.setFlat(True)
        self.F_BGS_BTN.setCheckable(True)
        self.F_BGS_BTN.setIcon(QtGui.QIcon(uiIcons.FGetIcon("background_subtraction")))
        self.F_BGS_BTN.clicked.connect(self.FBackgroundSubtract)

        self.F_BGS_Slider = QtWidgets.QSlider(QtCore.Qt.Vertical)
        self.F_BGS_Slider.setMinimum(0)
        self.F_BGS_Slider.setMaximum(100)
        self.F_BGS_Slider.setTickPosition(QtWidgets.QSlider.TicksRight)
        self.F_BGS_Slider.setTickInterval(10)
        self.F_BGS_Slider.setValue(self._BGS_Threshold)
        self.F_BGS_Slider.valueChanged.connect(self.F_BGS_SliderValueChanged)
        self.F_BGS_Slider.setDisabled(True)

        self.F_BGS_ValueLabel = QtWidgets.QLabel()
        
        #self.FFigure = QtWidgets.QLabel("Frame Viewer", self)
        #self.FFigure.setUpdatesEnabled(True)
        
        self.MyFigureWidget = SonarFigure(self)
        # self.MyFigureWidget.setUpdatesEnabled(True)
        self.MyFigureWidget.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.MyFigureWidget.setMouseTracking(True)

        self.FToolbar = QtWidgets.QToolBar(self)
        #self.FToolbar.addWidget(self.FAutoAnalizerBTN)
        self.FToolbar.addWidget(self.F_BGS_BTN)
        self.FToolbar.addWidget(self.F_BGS_ValueLabel)
        # self.FToolbar.add
        self.FToolbar.addWidget(self.F_BGS_Slider)
        self.FToolbar.setOrientation(QtCore.Qt.Vertical)
        self.FToolbar.setFixedWidth(self.FToolbar.minimumSizeHint().width())
        

        self.FSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.updateSliderLimits(0,0,0)
        self.FSlider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.FSlider.valueChanged.connect(self.playback_manager.setFrameInd)

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
        self.FLayout.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)

        if self._postAnalysisViewer:
            self.FListDetected()

        self.setLayout(self.FLayout)
        # self.displayImage()

        
    def FShowNextImage(self):
        """Show the next frame image.
        """
        self.UI_FRAME_INDEX += 1
        if (self.UI_FRAME_INDEX > self.playback_manager.sonar.frameCount-1):
            self.UI_FRAME_INDEX = 0
        
        self.FSlider.setValue(self.UI_FRAME_INDEX+1)

    def FShowPreviousImage(self, image):
        """Show the previous frame image
        """

        self.UI_FRAME_INDEX -= 1
        if (self.UI_FRAME_INDEX < 0 ):
            self.UI_FRAME_INDEX = self.playback_manager.sonar.frameCount-1

        self.FSlider.setValue(self.UI_FRAME_INDEX+1)

    def displayImage(self, frame):
        if frame is not None:
            #self.MyFigureWidget.clear()

            #image = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            #image = QtGui.QImage(image.data, image.shape[1], image.shape[0],  image.strides[0], QtGui.QImage.Format_Indexed8).rgbSwapped() #Format_RGB888

            #figurePixmap = QtGui.QPixmap.fromImage(image)
            #self.MyFigureWidget.setPixmap(figurePixmap)

            ffigure = self.MyFigureWidget
            font = cv2.FONT_HERSHEY_SIMPLEX          
            ffigure.setUpdatesEnabled(False)
            ffigure.clear()

            frame = self.image_processor.processImage(frame)
        
            #if(self.subtractBackground):
            #    frameBlur = cv2.blur(frame, (5,5))
            #    mask = self._fgbg.apply(frameBlur)
            #    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.kernel)
            #    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel)
            #    mask = cv2.threshold(mask, 128, 255, cv2.THRESH_BINARY)[1]
        
            #    if(self.marker):
            #        cv2.circle(frame, literal_eval(self.marker), 30, (255,255,255), 1)
            #        cv2.circle(mask, literal_eval(self.marker), 30, (255,255,255), 1)
                
            #    img = np.hstack((mask, frame))
            #    img = QtGui.QImage(img, img.shape[1], img.shape[0], img.strides[0], qformat)
        
            #else:
            #    img = QtGui.QImage(frame, frame.shape[1], frame.shape[0], frame.strides[0], qformat)
            #img = img.rgbSwapped()

            #img = QtGui.QImage(frame, frame.shape[1], frame.shape[0], frame.strides[0], qformat).rgbSwapped()
            #figurePixmap = QtGui.QPixmap.fromImage(img)
            ffigure.setImage(frame)
            #ffigure.setPixmap(figurePixmap.scaled(ffigure.size(), QtCore.Qt.KeepAspectRatio))
            #ffigure.setAlignment(QtCore.Qt.AlignCenter)
            ffigure.setUpdatesEnabled(True)
            #ffigure.update()
        else:
            self.MyFigureWidget.clear()

        if self.show_first_frame:
            print("First frame shown")
            self.MyFigureWidget.resetView()
            self.MyFigureWidget.applyPixmap()
            self.show_first_frame = False

        if isinstance(self.main_window, MainWindow):
            self.main_window.FStatusBarFrameNumber.setText(self.playback_manager.getFrameNumberText())
        self.updateSliderValue(self.playback_manager.frame_index)

        #rect = self.playback_manager.rect
        #if rect is not None:
        #    #cv2.imshow("Rect400", cv2.resize(self.playback_manager.rect, (400, 800)))
        #    #rect = cv2.resize(self.playback_manager.rect, (1, 800))
        #    #cv2.imshow("Rect1", cv2.resize(rect, (400, 800)))
        #    self.image_processor.distancePlot(rect)



    def updateSliderValue(self, value):
        self.FSlider.blockSignals(True)
        self.FSlider.setValue(value)
        self.FSlider.blockSignals(False)

    def updateSliderLimits(self, s_min, s_max, s_current):
        self.FSlider.blockSignals(True)
        self.FSlider.setMinimum(s_min)
        self.FSlider.setMaximum(s_max)
        self.FSlider.setValue(s_min)
        self.FSlider.setTickInterval(int(0.05 * s_max))
        self.FSlider.blockSignals(False)

    def onFileOpen(self, sonar):
        self.updateSliderLimits(0, sonar.frameCount, 1)
        self.show_first_frame = True

    def FLoadSONARFile(self, filePath):
        self.FFilePath = filePath
        # FH: Sonar File Library
        self.File = FH.FOpenSonarFile(filePath)
        self.FFrames = self.File.FRAMES
    
    def FBackgroundSubtract(self):
        """
        This function enables and disables background subtraction in the
        UI. It is called from F_BGS_BTN QtWidgets.QPushButton.
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
        self.playback_manager.sonar.FRAMES = self.playback_manager.sonar.getFrame(self.UI_FRAME_INDEX)
        if self.marker:
            # print(self.marker)
            cv2.circle(self.playback_manager.sonar.FRAMES, literal_eval(self.marker), 30, (255,255,255), 1)
            
        #self.displayImage(self.MyFigureWidget)

    def F_BGS_SliderValueChanged(self):
        value = self.F_BGS_Slider.value()
        self.F_BGS_ValueLabel.setText(str(value))
        self._fgbg.setVarThreshold(value)

    def FAutoAnalizer(self):
        ## TODO _ : Documentation
        self.popup = QtWidgets.QDialog(self)
        self.popupLayout = QtWidgets.QFormLayout()
        # kernel size and shape {default: ellipse, (10,2)}
        self.morphStructLabel = QtWidgets.QLabel("Morphological Structuring Element")
        self.morphStruct = QtWidgets.QComboBox(self)
        self.morphStruct.addItem("Ellipse")
        self.morphStruct.addItem("Rectangle")
        self.morphStruct.addItem("Cross")
        self.morphStructDim = QtWidgets.QLabel("Structuring Element Dimension")
        self.morphStructDimInp = QtWidgets.QLineEdit()
        self.morphStructDimInp.setPlaceholderText("(10,2)")
        self.popupLayout.addRow(self.morphStructLabel, self.morphStruct)
        self.popupLayout.addRow(self.morphStructDim, self.morphStructDimInp)
        
        # start frame {default: 1}
        self.startFrame = QtWidgets.QLabel("Start Frame")
        self.startFrameInp = QtWidgets.QLineEdit()
        self.startFrameInp.setPlaceholderText("1")
        self.popupLayout.addRow(self.startFrame, self.startFrameInp)
        
        self.blurVal = QtWidgets.QLabel("Blur Value")
        self.blurValInp = QtWidgets.QLineEdit()
        self.blurValInp.setPlaceholderText("(5,5)")
        self.popupLayout.addRow(self.blurVal, self.blurValInp)
        
        self.bgTh = QtWidgets.QLabel("Background Threshold")
        self.bgThInp = QtWidgets.QLineEdit()
        self.bgThInp.setPlaceholderText("25")
        self.popupLayout.addRow(self.bgTh, self.bgThInp)
        
        self.maxApp = QtWidgets.QLabel("Maximum Appearance")
        self.maxAppInp = QtWidgets.QLineEdit()
        self.maxAppInp.setPlaceholderText("30 frames")
        self.popupLayout.addRow(self.maxApp, self.maxAppInp)
        
        self.maxDis = QtWidgets.QLabel("Maximum Disappearance")
        self.maxDisInp = QtWidgets.QLineEdit()
        self.maxDisInp.setPlaceholderText("5 frames")
        self.popupLayout.addRow(self.maxDis, self.maxDisInp)
        
        self.radiusInput = QtWidgets.QLineEdit()
        self.radiusLabel = QtWidgets.QLabel("Search radius (px)")
        self.radiusInput.setPlaceholderText("30 px")
        self.popupLayout.addRow(self.radiusLabel, self.radiusInput)
        
        self.showImages = QtWidgets.QCheckBox("Show images while processing. (takes longer time)")
        self.showImages.setChecked(True)
        self.popupLayout.addRow(self.showImages)
        
        self.loadPresetBTN = QtWidgets.QPushButton("Load Preset")
        self.loadPresetBTN.clicked.connect(lambda : uif.loadTemplate(self))
        
        self.savePresetBTN = QtWidgets.QPushButton("Save Preset")
        self.savePresetBTN.clicked.connect(FH.saveAnalysisPreset)

        self.defaultPresetBTN = QtWidgets.QPushButton("Defaults")
        self.defaultPresetBTN.clicked.connect(lambda: uif.loadTemplate(self, default=True))
        
        self.setAsDefaultBTN = QtWidgets.QPushButton("Set As Defaults")
        self.setAsDefaultBTN.clicked.connect(FH.saveAnalysisPreset)

        self.startAnalysis = QtWidgets.QPushButton("Start")
        self.startAnalysis.clicked.connect(self.handleAnalyzerInput)
        
        rowButtonsLayout1 = QtWidgets.QHBoxLayout()
        rowButtonsLayout2 = QtWidgets.QHBoxLayout()
        
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
            self.FResultsViewer = SonarViewer(self.FParent, resultsView= True, results=self.FDetectedDict)
            self.FParent.setCentralWidget(self.FResultsViewer)
        return

    def togglePlayPause(self):
        self.playback_manager.play()
        self.choosePlayIcon()
            
    def choosePlayIcon(self):
        if self.playback_manager.isPlaying():
            self.FPlayBTN.setIcon(QtGui.QIcon(uiIcons.FGetIcon('pause')))
        else:
            self.FPlayBTN.setIcon(QtGui.QIcon(uiIcons.FGetIcon('play')))

    def FPlay(self, eventQt):
        ## problem
        self.play = not self.play
        if self.play:
            self.FPlayBTN.setIcon(QtGui.QIcon(uiIcons.FGetIcon('pause')))
            self.FShowNextImage()
        else: # pause
            self.FPlayBTN.setIcon(QtGui.QIcon(uiIcons.FGetIcon('play')))


    def FListDetected(self):
        index = 1
        listOfFish = list()
        self.FList = QtWidgets.QListWidget()

        for fish in self.FDetectedDict.keys():
            listItem = FFishListItem(self, self.FDetectedDict[fish], index)
            self.FDetectedDict[fish]["index"] = listItem
            self.FList.addItem(listItem.listItem)
            self.FList.setItemWidget(listItem.listItem, listItem.FWdiget)
            listOfFish.append(listItem)
            index += 1

        # self.FShowSelectedBTN = QtWidgets.QPushButton("Show Selected")
        # self.FShowSelectedBTN.clicked.connect(self.showSelectedFish)

        self.FApplyBTN = QtWidgets.QPushButton("Apply")
        self.FApplyBTN.clicked.connect(self.FApply)

        # self.FLayout.addWidget(self.FApplyAllBTN, 2, 4)
        self.FLayout.addWidget(self.FApplyBTN, 2, 5)
        self.FLayout.addWidget(self.FList, 0,4,2,2, QtCore.Qt.AlignRight)
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
        path = self.playback_manager.sonar.FILE_PATH.split('.')
        path = path[0] + '.json'
        # path = os.path.join(path, fileName)            
        with open(path, 'w') as outFile:
            json.dump(data, outFile)
        
        return

    def setAutomaticContrast(self, value):
        self.automatic_contrast = value

class SonarFigure(ZoomableQLabel):
    __parent = None

    def __init__(self, parent):
        super().__init__(True, True, True)
        self.__parent = parent
        self.setStyleSheet("background-color: black;")
    
    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

        if not isinstance(self.__parent, SonarViewer):
            return

        sonar_viewer = self.__parent
        if not isinstance(sonar_viewer.main_window, MainWindow):
            return

        #print(self.pixmap().width(), self.pixmap().height())
        if self.pixmap():
            marginx = (self.width() - self.pixmap().width()) / 2

            if not sonar_viewer.subtractBackground:
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
            output = sonar_viewer.playback_manager.getBeamDistance(xs, ys)
            if output is not None:
                txt = "Distance: {:.2f} m,\t Angle: {:.2f} deg\t".format(output[0], output[1])
                sonar_viewer.main_window.FStatusBarMousePos.setText(txt)

                # self.mousePosDist = output[0]
                # self.mousePosAng = output[1]
    
    #def resizeEvent(self, event):
    #    super().resizeEvent(event)
    #    if isinstance(self.figurePixmap, QtGui.QPixmap):
    #        self.setPixmap(self.figurePixmap.scaled(self.size(), QtCore.Qt.KeepAspectRatio))

class FFishListItem():
    def __init__(self, cls, inputDict, fishNumber):
        self.fishNumber = fishNumber
        self.inputDict = inputDict
        self.listItem = QtWidgets.QListWidgetItem()
        self.FWdiget = QtWidgets.QWidget()

        self.FWdigetText = QtWidgets.QLabel("Fish #{}".format(self.fishNumber))

        self.avgFishLength = QtWidgets.QLabel()
        self.avgFishLength.setText("Length: {}".format(uif.getAvgLength()))
        
        self.FIfFish = QtWidgets.QCheckBox("is Fish")
        self.FIfFish.setChecked(False)
        
        self.FWdigetBTN = QtWidgets.QPushButton("Show")

        self.linkFish = QtWidgets.QPushButton()
        self.linkFish.setIcon(QtGui.QIcon(uiIcons.FGetIcon("link")))

        self.nameLengthLayout = QtWidgets.QHBoxLayout()
        self.nameLengthLayout.addWidget(self.FWdigetText)
        self.nameLengthLayout.addWidget(self.avgFishLength)

        self.infoLayout = QtWidgets.QHBoxLayout()
        self.infoLayout.addWidget(self.FIfFish)
        self.infoLayout.addWidget(self.linkFish)

        self.FWdigetBTN.clicked.connect(
            lambda: cls.showFish(self.fishNumber, self.inputDict)
        )
        self.FWdigetLayout = QtWidgets.QVBoxLayout()
        self.FWdigetLayout.addLayout(self.nameLengthLayout)
        self.FWdigetLayout.addLayout(self.infoLayout)
        self.FWdigetLayout.addWidget(self.FWdigetBTN)
        self.FWdigetLayout.addStretch()
        # self.FWdigetLayout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self.FWdiget.setLayout(self.FWdigetLayout)
        self.listItem.setSizeHint(self.FWdiget.sizeHint())

if __name__ == "__main__":
    import sys
    from playback_manager import PlaybackManager

    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    sonar_viewer = SonarViewer(main_window, playback_manager)
    main_window.setCentralWidget(sonar_viewer)
    main_window.show()
    playback_manager.openTestFile()
    sys.exit(app.exec_())