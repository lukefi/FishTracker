"""
This file has been added to FishTracker in a effort to include mp4-files
author: Lauri Tirkkonen
date: 27.3.2023

"""

import cv2
import file_handlers.beamLookUp as beamLookUp
import numpy as np
import sys
from PyQt5 import QtCore, QtGui, QtWidgets


class InputDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.first = QtWidgets.QSpinBox(self)
        self.second = QtWidgets.QSpinBox(self)
        self.third = QtWidgets.QComboBox(self)
        buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok, self);

        self.first.setRange(0,100)
        self.first.setValue(0)

        self.second.setRange(0,100)
        self.second.setValue(30)
        self.second.setToolTip("80m, 60m, 40m, 30m, 20m, 10m")
        
        self.third.addItems(["135", "18"])
        self.third.setCurrentIndex(0)

        layout = QtWidgets.QFormLayout(self)
        self.setWindowTitle("User input")
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        layout.addRow('Window Start (m)', self.first)
        layout.addRow('Window Length (m)', self.second)
        layout.addRow('Angle (°)', self.third)
        layout.addWidget(buttonBox)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

    def getInputs(self):
        return (self.first.value(), self.second.value(), self.third.currentText())


def mp4_getAllFramesData(fhand, version, cls):

    cls.version = "MP4"
    cls.largeLens = 0 # 1 or 0 # DIDSON-files related, 0 for all MP4 files

    ### Values not used ###

    #cls.BEAM_COUNT = 135 # Number of beams
    cls.samplesPerBeam = 2267 # Number of downrange samples in each beam. Used for counting windowLength. For MP4, beam count 135 = 2267
    cls.samplePeriod = 30 # Downrange sample rate. Used for counting windowLength. Values 4 - 100 microseconds. No idea of value for MP4. In MP4 can change during emitting, 
                          # if zoom +-
    cls.soundSpeed = 1480 # speed of sound. Used for counting windowLength. About 1480 in water
    cls.sampleStartDelay = 0 # DIDSON-files related, delay till sonar starts emitting. AFAIK 0 for all MP4 files. Used for counting WindowStart
    
    ### Values not used ###

    dialog = InputDialog()
    if dialog.exec():
        ws, wl, angle = dialog.getInputs()
        cls.windowStart = ws
        cls.windowLength = wl
        if (angle == "135"):
            cls.BEAM_COUNT = 135
        if (angle == "18"):
            cls.BEAM_COUNT = 18
    else:
        sys.exit() # Exiting dialog results in exiting whole application

    vid_capture = cv2.VideoCapture(fhand.name)
    gray = None
    
    if (vid_capture.isOpened() == False):
       sys.exit() 
    # Read fps and frame count
    else:
    # Get frame rate information
    # 5 = cv2.CAP_PROP_FPS 
        cls.frameRate = vid_capture.get(5) 
 
        # Get frame count
        # 7 = cv2.CAP_PROP_FRAME_COUNT 
        # cls.frameCount = int(vid_capture.get(7))
        # Library has inconsistencies, but we can work around
        framecount = int(vid_capture.get(7)) 
        MSEC = (framecount / cls.frameRate) * 1000 # get length in milliseconds
        vid_capture.set(0, MSEC) # go to last position
        cls.frameCount = int(vid_capture.get(cv2.CAP_PROP_POS_FRAMES)) # 1 = cv2.CAP_PROP_POS_FRAMES # get 0-based index of frame number
        vid_capture.set(0,0) # go to start
        
        # vid_capture.read() methods returns a tuple, first element is a bool 
        # and the second is frame
        ret, frame = vid_capture.read()
        
        if ret == True:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # BGR2BGRA for alpha layer # BGR2GRAY to erase z-dimension/colors (n, n, n) => (n, n)
   
    # Release the video capture object
    # Destroyig windows is not necessary as we don't open any windows
    vid_capture.release()
    #cv2.destroyAllWindows()
    
    # Image manipulation for 135-angle
    if (cls.BEAM_COUNT == 135):
        pts = np.array([[0,0], [768,0], [768,318], [384,475], [0,318]]) # points for mask
        rect = cv2.boundingRect(pts)
        x,y,w,h = rect
        cropped = gray[y:y+h, x:x+w].copy() 

        pts = pts - pts.min(axis=0)
        mask = np.zeros(cropped.shape[:2], np.uint8)
        cv2.drawContours(mask, [pts], -1, (255,255,255), -1, cv2.LINE_AA) # make a white mask

        dst = cv2.bitwise_and(cropped, cropped, mask=mask) # fill the mask with cropped

        dst[mask == 0] = 0 # make background black

        cls.FRAMES = np.array(dst, dtype=np.uint8)

        """
        # Replace to make excess transparent and reshape to grid dimensions (2267, 135)
        # Loses pixels and possibly falsifies data
        # gray needs to changed to BGR2BGRA as well
        pts = np.array([[0,0], [768,0], [768,318], [384,475], [0,318]]) #768,480   475, 318
        rect = cv2.boundingRect(pts)
        x,y,w,h = rect
        cropped = gray[y:y+h, x:x+w].copy()

        pts = pts - pts.min(axis=0)
        mask = np.zeros(cropped.shape[:2], np.uint8)
        cv2.drawContours(mask, [pts], -1, (255,255,255), -1, cv2.LINE_AA)

        dst = cv2.bitwise_and(cropped, cropped, mask=mask)

        dst[mask == 0] = 0

        cls.FRAMES = np.array(dst, dtype=np.uint8)

        
        whiteUp = np.all(dst[...,:3] == (255, 255, 255), axis=-1)

        dst[whiteUp,3] = 0

        dstGrey = cv2.cvtColor(dst[:,:,0:3], cv2.COLOR_BGRA2GRAY)
        mask2 = dst[:,:,3]

        maskidx = (mask2 != 0)
        
        cls.FRAMES = np.array(dstGrey[maskidx], dtype=np.uint8)
        print(cls.FRAMES.shape) #306045
        cls.FRAMES = cls.FRAMES.reshape(2267, 135)  #2267, 135"""

        cls.DATA_SHAPE = cls.FRAMES.shape
        cls.firstBeamAngle = beamLookUp.BeamLookUp(cls.BEAM_COUNT, cls.largeLens)[-1] 
    
    # Image manipulation for 18-angle
    if (cls.BEAM_COUNT == 18):
        cls.FRAMES = np.array(gray, dtype=np.uint8)
        # todo

    return