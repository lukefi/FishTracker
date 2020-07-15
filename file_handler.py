"""
Python3 module
provided by the University of Oulu in collaboration with
LUKE-OY. The software is intended to be an open-source.

author: Mina Ghobrial.
date:   May 28th, 2018.

References: 
#   https://github.com/SoundMetrics
#   https://github.com/EminentCodfish/pyARIS
"""
import sys
import os
import json


import struct
from file_handlers.utils import *

from file_handlers.v3.v3_file_info import *
from file_handlers.v4.v4_file_info import *
from file_handlers.v5.v5_file_info import *

from image_manipulation import ImageManipulation

class FSONAR_File():
    def __init__(self, filename):
        self.FILE_PATH = filename
        self.frameCount = None
        self.BEAM_COUNT = None
        self.largeLens = None
        self.highResolution = None
        self.serialNumber = None
        self.sampleStartDelay = None
        self.soundSpeed = None
        self.samplesPerBeam = None
        self.samplePeriod = None
        self.DATA_SHAPE = None
        self.FRAMES = None
        self.version = None
        self.FILE_HANDLE = None
        self.FRAME_HEADER_SIZE = None
        self.FILE_HEADER_SIZE = None
        # arguments used in image remapping to real-life coordinates
        self.windowStart = None
        self.windowLength = None
        self.firstBeamAngle = None

        self.distanceCompensation = False

    def getPolarFrame(self, FI):
        frameSize = self.DATA_SHAPE[0] * self.DATA_SHAPE[1]
        frameoffset = (self.FILE_HEADER_SIZE + self.FRAME_HEADER_SIZE +(FI*(self.FRAME_HEADER_SIZE+(frameSize))))
        self.FILE_HANDLE.seek(frameoffset, 0)
        strCat = frameSize*"B"
        try:
            frame = np.array(struct.unpack(strCat, self.FILE_HANDLE.read(frameSize)), dtype=np.uint8)
        except:
            return None

        #self.FRAMES = cv2.flip(self.FRAMES.reshape((self.DATA_SHAPE[0], self.DATA_SHAPE[1])), 0)
        #self.FRAMES = self.constructImages()
        #return self.FRAMES

        frame = cv2.flip(frame.reshape((self.DATA_SHAPE[0], self.DATA_SHAPE[1])), 0)
        return frame


    def getFrame(self, FI):
        polar = self.getPolarFrame(FI)
        if polar is None:
            return None, None
        if self.distanceCompensation:
            polar = ImageManipulation.distanceCompensation(polar)
        self.FRAMES = self.constructImages(polar)
        return polar, self.FRAMES

    def constructImages(self, frames, d0 = None, dm = None, am= None):
        """This function works on mapping the original samples
        inside the file frames, to the actual real-life coordinates.
        
        Keyword Arguments:
            d0 {[type]} -- [description] (default: {None})
            dm {[type]} -- [description] (default: {None})
            am {[type]} -- [description] (default: {None})
        
        Returns:
            [type] -- [description]
        """
        ## TODO _
        allAngles = beamLookUp.BeamLookUp(self.BEAM_COUNT, self.largeLens)
        
        # d0 = self.sampleStartDelay * 0.000001 * self.soundSpeed/2
        d0 = self.windowStart   # in meters
        # dm = d0 + self.samplePeriod * self.samplesPerBeam * 0.000001 * self.soundSpeed/2
        dm = self.windowStart + self.windowLength   # in meters
        # am = allAngles[-1]
        am = self.firstBeamAngle    # in degrees
        K = self.samplesPerBeam
        N, M = self.DATA_SHAPE

        xm = dm*np.tan(am/180*np.pi)
        L = int(K/(dm-d0) * 2*xm)

        sx = L/(2*xm)
        sa = M/(2*am)
        sd = N/(dm-d0)
        O = sx*d0
        Q = sd*d0

        def invmap(inp):
            xi = inp[:,0]
            yi = inp[:,1]
            xc = (xi - L/2)/sx
            yc = (K + O - yi)/sx
            dc = np.sqrt(xc**2 + yc**2)
            ac = np.arctan(xc / yc)/np.pi*180
            ap = ac*sa
            dp = dc*sd
            a = ap + M/2
            d = N + Q - dp
            outp = np.array((a,d)).T
            return outp

        #print(d0, dm, am, xm, K)

        out = warp(frames, invmap, output_shape=(K, L))
        out = (out/np.amax(out)*255).astype(np.uint8)
        return out

    def getBeamDistance(self, x, y):
        K = self.samplesPerBeam
        N, M = self.DATA_SHAPE
        d0 = self.windowStart
        # dm = d0 + self.samplePeriod * self.samplesPerBeam * 0.000001 * self.soundSpeed/2
        dm = self.windowStart + self.windowLength
        am = self.firstBeamAngle
        xm = dm*np.tan(am/180*np.pi)

        L = int(K/(dm-d0) * 2*xm)
        sx = L/(2*xm)
        sa = M/(2*am)
        sd = N/(dm-d0)
        O = sx*d0
        Q = sd*d0

        xi = (x*L)
        yi = (y*K)

        xc = (xi - L/2)
        yc = (K + O - yi)
        dc = np.sqrt(xc**2 + yc**2)
        ac = np.arctan(xc / yc)/np.pi*180

        return [dc/sd, ac]

    def setDistanceCompensation(self, value):
        self.distanceCompensation = value



def FOpenSonarFile(filename):
    """
    Opens a sonar file and decides which DIDSON version it is.
    DIDSON version 0: 0x0464444
    DIDSON version 1: 0x1464444
    DIDSON version 2: 0x2464444
    DIDSON version 3: 0x3464444
    DIDSON version 4: 0x4464444
    DIDSON version 5 [ARIS]: 0x05464444
    Then calls the extract images function from each file-type file.
    """
    # Initializing Class
    SONAR_File = FSONAR_File(filename)
    # versions [Key] = [Value]()
    # all version numbers as Keys
    # all functions to read files as Values
    versions = {
        4604996: lambda: DIDSON_v0(fhand, version, SONAR_File),
        21382212: lambda: DIDSON_v1(fhand, version, SONAR_File),
        38159428: lambda: DIDSON_v2(fhand, version, SONAR_File),
        54936644: lambda: DIDSON_v3(fhand, version, SONAR_File),
        71713860: lambda: DIDSON_v4(fhand, version, SONAR_File),
        88491076: lambda: DIDSON_v5(fhand, version, SONAR_File)
    }
    try:
        fhand = open(filename, 'rb')
        
    except FileNotFoundError as e:
            raise FileNotFoundError(e.errno, e.strerror, filename)
    # read the first 4 bytes in the file to decide the version
    version = struct.unpack(cType["uint32_t"], fhand.read(c("uint32_t")))[0]
    versions[version]()
    return SONAR_File

def DIDSON_v0(fhand, version, cls):
    """
    This function will handle version 0 DIDSON Files
    """
    ## TODO _
    return cls


def DIDSON_v1(fhand, version, cls):
    """
    This function will handle version 1 DIDSON Files
    """
    ## TODO _
    pass

def DIDSON_v2(fhand, version, cls):
    """
    This function will handle version 2 DIDSON Files
    """
    ## TODO _
    pass

def DIDSON_v3(fhand, version, cls):
    """
    This function will handle version 3 DIDSON Files
    """
    print("inside DIDSON v3")
    cls.FRAME_HEADER_SIZE = getFrameHeaderSize(version)
    cls.FILE_HEADER_SIZE = getFileHeaderSize(version)
    v3_getAllFramesData(fhand, version, cls)
    cls.FILE_PATH = fhand.name
    cls.FILE_HANDLE = fhand
    
    
    return


def DIDSON_v4(fhand, version, cls):
    """
    This function will handle version 4 DIDSON Files
    """
    print("inside DIDSON v4")
    cls.FRAME_HEADER_SIZE = getFrameHeaderSize(version)
    cls.FILE_HEADER_SIZE = getFileHeaderSize(version)
    v4_getAllFramesData(fhand, version, cls)
    cls.FILE_PATH = fhand.name
    cls.FILE_HANDLE = fhand
    
    return


def DIDSON_v5(fhand, version, cls):
    """
    This function will handle version 5 DIDSON Files
    version 5 of DIDSON format is also known as ARIS
        dataAndParams = {
            "data": allFrames,
            "parameters":{
                "frameCount": frameCount,
                "numRawBeams" : numRawBeams,
                "samplesPerChannel" : samplesPerChannel,
                "samplePeriod" : samplePeriod,
                "soundSpeed" : soundSpeed,
                "sampleStartDelay" : sampleStartDelay,
                "largeLens" : largeLens,
                "DATA_SHAPE" : data.shape
            }
        }
    """
    print("inside DIDSON v5")
    cls.FRAME_HEADER_SIZE = getFrameHeaderSize(version)
    cls.FILE_HEADER_SIZE = getFileHeaderSize(version)
    v5_getAllFramesData(fhand, version, cls)
    cls.FILE_PATH = fhand.name
    cls.FILE_HANDLE = fhand
    return

def loadJSON(jsonFilePath):
    """This function will be used to load JSON files.
    
    Arguments:
        jsonFilePath {string} -- path to the JSON file to load

    Returns:
        dict -- containing the data from JSON file.
    """
    try:
        with open(jsonFilePath, "r") as template:
            config = json.load(template)
            return config
    except:
        return False

def pathFromList(listOfDirectories):
    """This function generates a sting path suitable for the used OS.
    Example:
    To get the path of file2.txt from a directory tree that looks like the
    following:
    {CWD}
    ├── dir1
    │   └── dirA
    │       └── file1.txt
    └── dir2
        └── dirB
            ├── file2.txt
            └── file3.txt
    the input list should be in the following form
    ["dir1", "dirB", "file2.txt"]
    and it returns a string holding the full path to that file.
    
    Arguments:
        listOfDirectories {list} -- list of strings, each of which is a
                                    part of the relative path to the 
                                    specified file.
    
    Returns:
        string -- full path to the specified file
    """
    return os.path.join(os.getcwd(), *listOfDirectories)

def saveAnalysisPreset(presetName):
    ## TODO _ : Finish this function
    pass