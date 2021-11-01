"""This module is used to display captured SONAR data from DIDOSN or ARIS
files, and also used to show results of the analysis, and details about
the detected fishes.
"""
from PyQt5 import QtCore, QtGui, QtWidgets
from main_window import MainWindow
from image_manipulation import ImageProcessor
from zoomable_qlabel import ZoomableQLabel
from detector import Detector
from tracker import Tracker
from fish_manager import FishManager, FishEntry, pyqt_palette, color_palette_deep, N_COLORS
from playback_manager import Event
from log_object import LogObject

## DEBUG :{ following block of libraries for debug only
import os
import json
## }

import cv2
import seaborn as sns
import iconsLauncher as uiIcons      # UI/iconsLauncher
# uif : (u)ser (i)nterface (f)unction

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

    def __init__(self, main_window, playback_manager, detector, tracker, fish_manager): #, resultsView = False, results=False):
        """Initializes the window and loads the first frame and
        places the UI elements, each in its own place.
        """
        self.measure_event = Event()

        self.main_window = main_window
        self.playback_manager = playback_manager
        self.detector = detector
        self.tracker = tracker
        self.fish_manager = fish_manager
        self.image_processor = ImageProcessor()
        self.polar_transform = None

        self.show_first_frame = False

        self.playback_manager.frame_available.connect(self.displayImage)
        self.playback_manager.playback_ended.connect(self.choosePlayIcon)
        self.playback_manager.file_opened.connect(self.onFileOpen)
        self.playback_manager.mapping_done.connect(self.onMappingDone)
        self.playback_manager.file_closed.connect(self.onFileClose)

        if isinstance(self.main_window, MainWindow):
            self.main_window.FStatusBarFrameNumber.setText(self.playback_manager.getFrameNumberText())

        QtWidgets.QDialog.__init__(self)
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
        self.FPlayBTN.clicked.connect(self.togglePlayPause)
        self.FPlayBTN.setShortcut(QtCore.Qt.Key_Space)
        self.FPlayBTN.setIcon(QtGui.QIcon(uiIcons.FGetIcon('play')))


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
        
        self.sonar_figure = SonarFigure(self)
        self.sonar_figure.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.sonar_figure.setMouseTracking(True)        

        self.FSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.updateSliderLimits(0,0,0)
        self.FSlider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.FSlider.valueChanged.connect(self.playback_manager.setFrameInd)

        self.FLayout.addWidget(self.sonar_figure,0,1,1,3)
        self.FLayout.addWidget(self.FSlider,1,1,1,3)
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

    def displayImage(self, tuple):
        if tuple is None:
            self.MyFigureWidget.clear()

        else:
            ind, frame = tuple

            sfig = self.sonar_figure
            sfig.setUpdatesEnabled(False)
            sfig.clear()
            sfig.visualized_id = ind

            # Apply background subtraction
            if self.detector.show_bgsub:
                image = self.detector.bgSubtraction(frame)
                image = self.image_processor.processGrayscaleImage(image)
            else:
                image = self.image_processor.processImage(ind, frame)

            if sfig.show_tracks or sfig.show_track_id:
                sfig.visualized_tracks = self.fish_manager.getFishInFrame(ind)

            # Overlay detections used in tracking and remove them from other detections
            if sfig.show_tracks:
                dets_in_tracks = set()
                for fish in sfig.visualized_tracks:
                    _, det = fish.tracks[ind]
                    if det is not None:
                        dets_in_tracks.add(det)
                        if sfig.show_detections:
                            image = det.visualizeArea(image, color_palette_deep[fish.color_ind])
                    
                detections = [d for d in self.detector.getCurrentDetection() if d not in dets_in_tracks]
            else:
                detections = self.detector.getCurrentDetection()
            
            # Overlay rest of the detections
            if sfig.show_detections or (sfig.show_detection_size and not sfig.show_tracks):
                sfig.visualized_dets = detections
                if sfig.show_detections:
                    if sfig.show_tracks:
                        for det in detections:
                            image = det.visualizeArea(image, [0.9] * 3)
                    else:
                        colors = sns.color_palette('deep', max([0] + [det.label + 1 for det in detections]))
                        for det in detections:
                            image = det.visualizeArea(image, colors[det.label])
        
            if self.show_first_frame:
                sfig.resetViewToShape(image.shape)

            sfig.setImage(image)
            sfig.setUpdatesEnabled(True)

            if self.show_first_frame:
                LogObject().print2("First frame shown")
                self.sonar_figure.resetView()
                self.show_first_frame = False

            if isinstance(self.main_window, MainWindow):
                self.main_window.FStatusBarFrameNumber.setText(self.playback_manager.getFrameNumberText())
            self.updateSliderValue(self.playback_manager.getFrameInd())



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

    def onFileClose(self):
        self.sonar_figure.clear()
        self.polar_transform = None

    def onMappingDone(self):
        self.polar_transform = self.playback_manager.playback_thread.polar_transform

    def measureDistance(self, value):
        self.sonar_figure.setMeasuring(value)
    
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
        self.playback_manager.togglePlay()
        self.choosePlayIcon()
            
    def choosePlayIcon(self):
        if self.playback_manager.isPlaying():
            self.FPlayBTN.setIcon(QtGui.QIcon(uiIcons.FGetIcon('pause')))
        else:
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

        self.FApplyBTN = QtWidgets.QPushButton("Apply")
        self.FApplyBTN.clicked.connect(self.FApply)

        self.FLayout.addWidget(self.FApplyBTN, 2, 5)
        self.FLayout.addWidget(self.FList, 0,4,2,2, QtCore.Qt.AlignRight)
        return


    def showFish(self, fishNumber, inputDict):
        ## TODO _
        # ffigure = self.MyFigureWidget
        # ffigure.clear()
        # self.MyFigureWidget.clear()
        counter = 0
        LogObject().print("Fish = ", fishNumber)
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
        with open(path, 'w') as outFile:
            json.dump(data, outFile)
        
        return

    def setAutomaticContrast(self, value):
        self.automatic_contrast = value

    def resizeEvent(self, event):
        self.sonar_figure.resizeEvent(event)

    def setStatusBarMousePos(self, x, y):
        if not isinstance(self.main_window, MainWindow):
            return

        if self.playback_manager.isMappingDone():
            dist, angle = self.playback_manager.getBeamDistance(x, y)
            angle = angle / np.pi * 180 + 90
            txt = "Distance: {:.2f} m,\t Angle: {:.1f} deg\t".format(dist, angle)
            self.main_window.FStatusBarMousePos.setText(txt)

    def setStatusBarDistance(self, points):
        if not isinstance(self.main_window, MainWindow):
            return

        if points is None or self.polar_transform is None:
            self.main_window.FStatusBarDistance.setText("")
        else:
            x1, y1, x2, y2 = points
            dist, angle = self.polar_transform.getMetricDistance(y2, x2, y1, x1)
            angle = angle / np.pi * 180
            txt = "Measure: {:.2f} m,\t Angle: {:.1f} deg\t".format(dist, angle)
            self.main_window.FStatusBarDistance.setText(txt)

    def measurementDone(self, points):
        if points is not None:
            x1, y1, x2, y2 = points
            dist, _ = self.polar_transform.getMetricDistance(y1, x1, y2, x2)
            self.measure_event(dist)
        else:
            self.measure_event(None)

        self.setStatusBarDistance(None)

    def getSwimDirection(self):
        return self.fish_manager.up_down_inverted

    def getAxisBase(self):
        """
        Gets the min and max points for the scale (both left and right)
        """
        if self.polar_transform is not None:
            L = self.polar_transform.getOuterEdge(20, False)
            R = self.polar_transform.getOuterEdge(20, True)
            return np.vstack((L,R))
        else:
            return None

    def getDepthMinMax(self):
        if self.polar_transform is not None:
            return self.polar_transform.radius_limits
        else:
            return (0,0)


class SonarFigure(ZoomableQLabel):
    def __init__(self, sonar_viewer):
        super().__init__(True, True, True)
        self.sonar_viewer = sonar_viewer
        self.init_measuring = False
        self.measure_origin = None
        self.measure_point = None
        self.setStyleSheet("background-color: black;")

        self.measure_toggle = Event()

        self.visualized_dets = []
        self.visualized_tracks = []
        self.visualized_id = 0

        self.show_detections = True
        self.show_tracks = True
        self.show_detection_size = True
        self.show_track_id = True
        self.show_track_bounding_box = True

        self.font_metrics = None

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

        if event.button() == QtCore.Qt.LeftButton:
            xs = self.view2imageX(event.x())
            ys = self.view2imageY(event.y())

            if self.init_measuring and self.pixmap():
                self.measure_origin = (xs, ys)
                self.init_measuring = False

            elif self.measure_origin is not None:
                self.measure_toggle(True)

                self.sonar_viewer.measurementDone((self.measure_origin[1], self.measure_origin[0], ys, xs))
                self.measure_origin = None
                self.update()

    def setMeasuring(self, value):
        self.init_measuring = value
        if value:
            self.measure_toggle(False)
        else:
            self.sonar_viewer.measurementDone(None)
            self.measure_toggle(True)

            self.measure_origin = None
            self.measure_point = None
            self.update()
    
    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

        xs = self.view2imageX(event.x())
        ys = self.view2imageY(event.y())
        self.measure_point = (self.view2imageX(event.x()), self.view2imageY(event.y()))

        if self.sonar_viewer:
            if self.measure_origin is not None:
                self.update()
                self.sonar_viewer.setStatusBarDistance((self.measure_origin[1], self.measure_origin[0], ys, xs))

            if self.pixmap():
                self.sonar_viewer.setStatusBarMousePos(xs,ys)

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QtGui.QPainter(self)
        font = painter.font()
        self.font_metrics = QtGui.QFontMetrics(font)
        
        self.drawUpDown(painter)
        self.drawDepthAxis(painter)
        self.drawMeasurementLine(painter)

        self.visualizeDetections(painter, self.visualized_dets)
        self.visualizeFishTracks(painter, self.visualized_tracks)


    def drawUpDown(self, painter):
        painter.setPen(QtCore.Qt.white)
        if self.sonar_viewer.getSwimDirection():
            painter.drawText(max(20, 0.05 * self.window_width), 0.95 * self.window_height, "UP")
            painter.drawText(self.window_width - max(20, 0.05 * self.window_width) - 30, 0.95 * self.window_height, "DOWN")
        else:
            painter.drawText(max(20, 0.05 * self.window_width), 0.95 * self.window_height, "DOWN")
            painter.drawText(self.window_width - max(20, 0.05 * self.window_width) - 10, 0.95 * self.window_height, "UP")

    def drawDepthAxis(self, painter):
        # Draw depth axis
        painter.setPen(QtCore.Qt.white)
        axisBase = self.sonar_viewer.getAxisBase()
        if axisBase is not None:

            depthMin, depthMax = self.sonar_viewer.getDepthMinMax()

            y = self.image2viewY(axisBase[:,0])
            x = self.image2viewX(axisBase[:,1])
            l0 = np.array((x[0],y[0]))
            l1 = np.array((x[1],y[1]))
            r0 = np.array((x[2],y[2]))
            r1 = np.array((x[3],y[3]))

            painter.drawLine(*l0, *l1)
            painter.drawLine(*r0, *r1)

            count = 5

            for i in range(count):
                if i == 0 or i == 4:
                    len = 10
                else:
                    len = 5

                t = float(i)/(count-1)
                depth = depthMin + t * (depthMax - depthMin)

                li = (1-t) * l0 + t * l1
                ri = (1-t) * r0 + t * r1

                painter.drawLine(*li, *(li - np.array((len,0))))
                painter.drawLine(*ri, *(ri + np.array((len,0))))

                text = "%.1f" % depth
                text_width = QtGui.QFontMetrics(self.font()).width(text)

                painter.drawText(*li + np.array((-15 - text_width, 5)), text)
                painter.drawText(*ri + np.array((15, 5)), text)

    def drawMeasurementLine(self, painter):
        if self.measure_origin is None or self.measure_point is None:
            return

        painter.setPen(QtCore.Qt.darkRed)
        x = self.image2viewX(np.array((self.measure_origin[0], self.measure_point[0])))
        y = self.image2viewY(np.array((self.measure_origin[1], self.measure_point[1])))

        painter.drawLine(x[0], y[0] ,x[1] ,y[1])

    def visualizeDetections(self, painter, detections):
        painter.setPen(QtCore.Qt.white)

        for det in detections:
            if det.corners is None:
                continue

            # Draw size text
            if self.show_detection_size:
                self.drawDetectionSizeText(painter, det)

            # Draw detection bounding box
            if self.show_detections:
                corners_x = self.image2viewX(det.corners[:,1])
                corners_y = self.image2viewY(det.corners[:,0])
                for i in range(0,3):
                    painter.drawLine(corners_x[i], corners_y[i], corners_x[i+1], corners_y[i+1])
                painter.drawLine(corners_x[3], corners_y[3], corners_x[0], corners_y[0])

    def visualizeFishTracks(self, painter, fish_by_frame):
        for fish in fish_by_frame:
            tr, det = fish.tracks[self.visualized_id]

            painter.setPen(QtCore.Qt.white)
            center = FishEntry.trackCenter(tr)

            # Draw track ID
            if self.show_track_id:
                text = f"ID: {fish.id}"
                text_width = self.font_metrics.boundingRect(text).width()

                x = self.image2viewX(center[1]) - text_width / 2
                y = self.image2viewY(center[0] + 10) + 11
                point = QtCore.QPoint(x, y)

                painter.drawText(point, text)

            if self.show_tracks:
                # Draw detection size
                if self.show_detection_size and det is not None:
                    x = self.image2viewX(center[1])
                    y = self.image2viewY(center[0] - 10) - 1
                    self.drawDetectionSizeText(painter, det, (x,y))

                # Draw track bounding box
                corners_x = self.image2viewX(np.array([tr[1], tr[3]]))
                corners_y = self.image2viewY(np.array([tr[0], tr[2]]))

                painter.setPen(pyqt_palette[fish.color_ind])
                painter.drawLine(corners_x[0], corners_y[0], corners_x[0], corners_y[1])
                painter.drawLine(corners_x[0], corners_y[1], corners_x[1], corners_y[1])
                painter.drawLine(corners_x[1], corners_y[1], corners_x[1], corners_y[0])
                painter.drawLine(corners_x[1], corners_y[0], corners_x[0], corners_y[0])

    def drawDetectionSizeText(self, painter, det, pos=None):
        if det.length > 0:
            text = det.getSizeText()
            text_width = self.font_metrics.boundingRect(text).width()

            if pos is None:
                x = self.image2viewX(int(det.center[1])) - text_width / 2
                y = self.image2viewY(int(det.center[0] - det.diff[0])) - 6
            else:
                x,y = pos
                x -= text_width / 2
            point = QtCore.QPoint(x, y)
            painter.drawText(point, text)

    def clear(self):
        super().clear()
        self.visualized_dets = []
        self.visualized_tracks = []
        self.visualized_id = 0

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
        self.FWdiget.setLayout(self.FWdigetLayout)
        self.listItem.setSizeHint(self.FWdiget.sizeHint())

if __name__ == "__main__":
    import sys
    from playback_manager import PlaybackManager

    def startDetector():
        detector.initMOG()
        detector.setShowBGSubtraction(False)


    def test():
        LogObject().print("Polars loaded test print")

    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    playback_manager = PlaybackManager(app, main_window)
    detector = Detector(playback_manager)
    detector.nof_bg_frames = 100
    tracker = Tracker(detector)
    fish_manager = FishManager(playback_manager, tracker)
    playback_manager.mapping_done.connect(test)
    playback_manager.mapping_done.connect(startDetector)
    playback_manager.frame_available_immediate.append(detector.compute_from_event)
    sonar_viewer = SonarViewer(main_window, playback_manager, detector, tracker, fish_manager)
    sonar_viewer.sonar_figure.show_detections = True
    sonar_viewer.image_processor.setColorMap(False)

    main_window.setCentralWidget(sonar_viewer)
    main_window.show()
    playback_manager.openTestFile()
    sys.exit(app.exec_())