"""
Python3 module
provided by the University of Oulu in collaboration with
LUKE-OY. The software is intended to be an open-source.

author: Mina Ghobrial.
date:   May 28th, 2018.

References: 
#   https://github.com/SoundMetrics
#   https://github.com/EminentCodfish/pyARIS

---------------------------------------------------------------------------

This file is a modified version of the original and used as part of Fish Tracker.
Copyright 2021, VTT Technical research centre of Finland Ltd.
Developed by: Mikael Uimonen.

Fish Tracker is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Fish Tracker is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Fish Tracker.  If not, see <https://www.gnu.org/licenses/>.

---------------------------------------------------------------------------

Modifications in a effort to include mp4-files
author: Lauri Tirkkonen
date: 27.3.2023

"""

import sys
import os
import json
import struct
import platform
import filetype

from PyQt5 import QtCore

from enum import Enum, auto

from file_handlers.utils import *

from file_handlers.v3.v3_file_info import *
from file_handlers.v4.v4_file_info import *
from file_handlers.v5.v5_file_info import *
from file_handlers.MP4.mp4_file_info import *

from image_manipulation import ImageManipulation
from log_object import LogObject


if platform.system() == "Windows":
    APPDATA_PATH = os.path.expandvars(r"%LOCALAPPDATA%\FishTracker")
else:
    # TODO: Set proper path for Linux / OSX
    APPDATA_PATH = os.getcwd()

CONF_PATH = os.path.join(APPDATA_PATH, "conf.json")


def checkAppDataPath():
    if not os.path.isdir(APPDATA_PATH):
        os.mkdir(APPDATA_PATH)

def getFilePathInAppData(file_name: str):
    return os.path.join(APPDATA_PATH, file_name)

conf_lock = QtCore.QReadWriteLock()


class FSONAR_File():
    def __init__(self, filename):
        self.FILE_PATH = filename
        self.frameCount = None
        self.frameRate = None
        self.BEAM_COUNT = None
        self.largeLens = None
        self.highResolution = None
        self.reverse = None
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
        if (self.version == "MP4"):
            vcap = cv2.VideoCapture(self.FILE_PATH)
            while(vcap.isOpened()):
                vcap.set(cv2.CAP_PROP_POS_FRAMES, FI)
                success, color = vcap.read()
                if (success == True):
                    gray = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY) 
                vcap.release()

                if (self.BEAM_COUNT == 135): # Image manipulation for 135-angle
                    pts = np.array([[0,0], [768,0], [768,318], [384,475], [0,318]]) 
                    rect = cv2.boundingRect(pts)
                    x,y,w,h = rect
                    cropped = gray[y:y+h, x:x+w].copy()

                    pts = pts - pts.min(axis=0)
                    mask = np.zeros(cropped.shape[:2], np.uint8)
                    cv2.drawContours(mask, [pts], -1, (255,255,255), -1, cv2.LINE_AA)

                    dst = cv2.bitwise_and(cropped, cropped, mask=mask)

                    dst[mask == 0] = 0

                    frame = np.array(dst, dtype=np.uint8)

                    """
                    # Replace to make excess transparent and reshape to grid dimensions (2267, 135)
                    # Loses pixels and possibly falsifies data
                    if (success == True):
                        gray = cv2.cvtColor(color, cv2.COLOR_BGR2BGRA) #Add alpha layer
                    vcap.release()

                    pts = np.array([[0,0], [768,0], [768,318], [384,475], [0,318]]) 
                    rect = cv2.boundingRect(pts)
                    x,y,w,h = rect
                    cropped = gray[y:y+h, x:x+w].copy()

                    pts = pts - pts.min(axis=0)
                    mask = np.zeros(cropped.shape[:2], np.uint8)
                    cv2.drawContours(mask, [pts], -1, (255,255,255), -1, cv2.LINE_AA)

                    dst = cv2.bitwise_and(cropped, cropped, mask=mask)

                    dst[mask == 0] = 255

                    frame = np.array(dst, dtype=np.uint8)

                    greyedUp = np.all(dst[...,:3] == (255, 255, 255), axis=-1)

                    dst[greyedUp,3] = 0

                    dstGrey = cv2.cvtColor(dst[:,:,0:3], cv2.COLOR_BGRA2GRAY)
                    mask2 = dst[:,:,3]

                    maskidx = (mask2 != 0)
                    
                    frame = np.array(dstGrey[maskidx], dtype=np.uint8)
                    frame = frame.reshape(2267, 135)"""
                if (self.BEAM_COUNT == 18): # Image manipulation for 18-angle
                    frame = np.array(gray, dtype=np.uint8)
                    # todo

        else:
            frameSize = self.DATA_SHAPE[0] * self.DATA_SHAPE[1]
            frameoffset = (self.FILE_HEADER_SIZE + self.FRAME_HEADER_SIZE +(FI*(self.FRAME_HEADER_SIZE+(frameSize))))
            self.FILE_HANDLE.seek(frameoffset, 0)

            frame = np.frombuffer(self.FILE_HANDLE.read(frameSize), dtype=np.uint8)
            if (self.reverse == 0): # check sonar mount direction (from above = 0, from below = 1)
                frame = cv2.flip(frame.reshape((self.DATA_SHAPE[0], self.DATA_SHAPE[1])), 0) # 0 flips around the x-axis, positive value (e.g. 1) flips around y-axis. Negative value (e.g. -1) flips around both axes (the desired behaviour for self.reverse == 1). 
            else:
                frame = cv2.flip(frame.reshape((self.DATA_SHAPE[0], self.DATA_SHAPE[1])), -1) # 0 flips around the x-axis, positive value (e.g. 1) flips around y-axis. Negative value (e.g. -1) flips around both axes (the desired behaviour for self.reverse == 1). 

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

        #LogObject().print2(d0, dm, am, xm, K)

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
        88491076: lambda: DIDSON_v5(fhand, version, SONAR_File),
        00000000: lambda: MP4(fhand, version, SONAR_File)
    }
    try:
        fhand = open(filename, 'rb')
        
    except FileNotFoundError as e:
            raise FileNotFoundError(e.errno, e.strerror, filename)
    # read the first 4 bytes in the file to decide the version
    version = struct.unpack(cType["uint32_t"], fhand.read(c("uint32_t")))[0]
    # if not DIDSON, check if mp4
    if (version not in (4604996, 21382212, 38159428, 54936644, 71713860, 88491076)):
        kind = filetype.guess(filename)
        version = kind.extension
        if (version == "mp4"):
            version = 00000000
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
    LogObject().print2("inside DIDSON v3")
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
    LogObject().print2("inside DIDSON v4")
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
    LogObject().print2("inside DIDSON v5")
    cls.FRAME_HEADER_SIZE = getFrameHeaderSize(version)
    cls.FILE_HEADER_SIZE = getFileHeaderSize(version)
    v5_getAllFramesData(fhand, version, cls)
    cls.FILE_PATH = fhand.name
    cls.FILE_HANDLE = fhand
    return


def MP4(fhand, version, cls):
    LogObject().print2("inside MP4")
    print("inside MP4")
    mp4_getAllFramesData(fhand, version, cls)
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
        return None


def loadConf():
    try:
        locker = QtCore.QReadLocker(conf_lock)
        with open(CONF_PATH, "r") as file:
            conf = json.load(file)
            return conf
    except FileNotFoundError:
        locker.unlock()
        return createDefaultConfFile()


def writeConf(conf):
    checkAppDataPath()
    locker = QtCore.QWriteLocker(conf_lock)
    with open(CONF_PATH, 'w') as f:
        json.dump(conf, f, sort_keys=True, indent=2, separators=(',', ': '))


def confExists():
    return os.path.exists(CONF_PATH)

def checkConfFile():
    try:
        loadConf()
    except:
        LogObject().print2(f"Reading conf file failed, {sys.exc_info()[1]}")
        createDefaultConfFile()


def createDefaultConfFile():
    conf = dict()
    for key in ConfKeys:
        conf[key.name] = conf_default_values[key]

    writeConf(conf)
    return conf


class ConfKeys(Enum):
    batch_double_track = auto()
    batch_save_detections = auto()
    batch_save_tracks = auto()
    batch_save_complete = auto()

    filter_tracks_on_save = auto()
    latest_batch_directory = auto()
    latest_directory = auto()
    latest_save_directory = auto()
    log_timestamp = auto()
    log_verbosity = auto()
    parallel_processes = auto()
    save_as_binary = auto()
    sonar_height = auto()
    test_file_path = auto()


conf_default_values = {
    ConfKeys.batch_double_track: False,
    ConfKeys.batch_save_detections: False,
    ConfKeys.batch_save_tracks: False,
    ConfKeys.batch_save_complete: True,

    ConfKeys.filter_tracks_on_save: True,
    ConfKeys.latest_batch_directory: str(os.path.expanduser("~")),
    ConfKeys.latest_directory: str(os.path.expanduser("~")),
    ConfKeys.latest_save_directory: str(os.path.expanduser("~")),
    ConfKeys.log_timestamp: False,
    ConfKeys.log_verbosity: 0,
    ConfKeys.parallel_processes: 1,
    ConfKeys.save_as_binary: False,
    ConfKeys.sonar_height: 1000,
    ConfKeys.test_file_path: ""
    }

conf_types = {
    ConfKeys.batch_double_track: bool,
    ConfKeys.batch_save_detections: bool,
    ConfKeys.batch_save_tracks: bool,
    ConfKeys.batch_save_complete: bool,

    ConfKeys.filter_tracks_on_save: bool,
    ConfKeys.latest_batch_directory: str,
    ConfKeys.latest_directory: str,
    ConfKeys.latest_save_directory: str,
    ConfKeys.log_timestamp: bool,
    ConfKeys.log_verbosity: int,
    ConfKeys.parallel_processes: int,
    ConfKeys.save_as_binary: bool,
    ConfKeys.sonar_height: int,
    ConfKeys.test_file_path: str
    }


def getConfValue(key: ConfKeys):
    """
    Unified solution for getting any of the conf file entries.
    """
    try:
        conf = loadConf()
        if key.name in conf.keys():
            return conf[key.name]
        else:
            return conf_default_values[key]
    except:
        LogObject().print2(f"Reading failed for parameter: {key}, {sys.exc_info()[1]}")
        if key in conf_default_values:
            return conf_default_values[key]
        else:
           return None


def setConfValue(key: ConfKeys, value):
    """
    Unified solution for setting any of the conf file entries.
    """
    try:
        conf = loadConf()
        conf[key.name] = conf_types[key](value)
        writeConf(conf)
    except:
        LogObject().print2(f"Writing conf file failed for key: {key}, sys.exc_info()[1]")


def getTestFilePath():
    try:
        conf = loadConf()
        if os.path.exists(conf["test_file_path"]):
            return conf["test_file_path"]
        else:
            return None
    except:
        LogObject().print2("Reading test file path failed", sys.exc_info()[1])
        return None


def getLatestDirectory():
    try:
        conf = loadConf()
        if os.path.exists(conf["latest_directory"]):
            return conf["latest_directory"]
        else:
            return str(os.path.expanduser("~"))
    except:
        LogObject().print2("Reading directory path failed:", sys.exc_info()[1])
        return str(os.path.expanduser("~"))


def setLatestDirectory(path):
    if path is None or path == "":
        return
    try:
        conf = loadConf()
        conf["latest_directory"] = path
        writeConf(conf)
    except:
        LogObject().print2("Writing conf file failed:", sys.exc_info()[1])


def getLatestSaveDirectory():
    try:
        conf = loadConf()
        if os.path.exists(conf["latest_save_directory"]):
            return conf["latest_save_directory"]
        else:
            return str(os.path.expanduser("~"))
    except:
        LogObject().print2("Reading save directory path failed:", sys.exc_info()[1])
        return str(os.path.expanduser("~"))


def setLatestSaveDirectory(path):
    if path is None or path == "":
        return
    try:
        conf = loadConf()
        conf["latest_save_directory"] = path
        writeConf(conf)
    except:
        LogObject().print2("Writing conf file failed:", sys.exc_info()[1])


def getSonarHeight():
    try:
        conf = loadConf()
        return int(conf["sonar_height"])
    except:
        LogObject().print2("Reading sonar height failed", sys.exc_info()[1])
        return 1000


def setSonarHeight(value):
    try:
        conf = loadConf()
        conf["sonar_height"] = int(value)
        writeConf(conf)
    except:
        LogObject().print2("Writing conf file failed:", sys.exc_info()[1])


def getParallelProcesses():
    try:
        conf = loadConf()
        return int(conf["parallel_processes"])
    except:
        LogObject().print2("Reading parallel process count failed", sys.exc_info()[1])
        return 1


def setParallelProcesses(value):
    try:
        conf = loadConf()
        conf["parallel_processes"] = int(value)
        writeConf(conf)
    except:
        LogObject().print2("Writing conf file failed:", sys.exc_info()[1])
            

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