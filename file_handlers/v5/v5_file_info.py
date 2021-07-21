"""
Python3 module
provided by the University of Oulu in collaboration with
LUKE-OY. The software is intended to be an open-source.

author: Mina Ghobrial.
date:   April 19th, 2018.

References: 
#   https://github.com/SoundMetrics
#   https://github.com/EminentCodfish/pyARIS

"""
import struct
import file_handlers.v5.v5_frame_info as frame
import os
import json
import file_handlers.utils as utils
import file_handlers.beamLookUp as beamLookUp
import numpy as np
import re
from skimage.transform import warp
import cv2




cwd = os.getcwd()
JSON_FILE_PATH = cwd + "/file_handlers/v5/v5_file_headers_info.json"

class v5_File:
    """
    Abstraction of the ARIS file format.

    The following class contains all the tools needed
    to read, write and modify ARIS file formats. It also
    provides tools to export files and data in several
    file formats

    Example:
    >>> import v5_file_info as v5
    >>> file = v5.v5_File("sample.aris")
    """
    # File related calculated variables
    __FILE_PATH = None
    __FILE_SIZE = None
    __FILE_HEADER_SIZE = 1024
    __FILE_HEADER_NUM = 41
    
    # Frame related calculated variables
    __FRAME_SIZE = None
    __FRAME_HEADER_SIZE = 1024
    FRAME_COUNT = None

    # ARIS File class initializer
    def __init__(self,  filename):
        try:
            with open(filename, 'rb') as fhand:
                self.__FILE_PATH = filename
                self.version = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.__FRAME_COUNT = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.frameRate = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.highResolution = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.numRawBeams = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.sampleRate = struct.unpack(
                    utils.cType["float"], fhand.read(utils.c("float")))[0]
                self.samplesPerChannel = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.receiverGain = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.windowStart = struct.unpack(
                    utils.cType["float"], fhand.read(utils.c("float")))[0]
                self.windowLength = struct.unpack(
                    utils.cType["float"], fhand.read(utils.c("float")))[0]
                self.reverse = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.serialNumber = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.strDate = struct.unpack(
                    utils.cType["char[32]"], fhand.read(utils.c("char[32]")))[0]
                self.strHeaderID = struct.unpack(
                    utils.cType["char[256]"], fhand.read(utils.c("char[256]")))[0]
                self.userID1 = struct.unpack(
                    utils.cType["int32_t"], fhand.read(utils.c("int32_t")))[0]
                self.userID2 = struct.unpack(
                    utils.cType["int32_t"], fhand.read(utils.c("int32_t")))[0]
                self.userID3 = struct.unpack(
                    utils.cType["int32_t"], fhand.read(utils.c("int32_t")))[0]
                self.userID4 = struct.unpack(
                    utils.cType["int32_t"], fhand.read(utils.c("int32_t")))[0]
                self.startFrame = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.endFrame = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.timelapse = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.recordInterval = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.radioSecond = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.frameInterval = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.flags = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.auxFlags = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.soundVelocity = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.flags3D = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.softwareVersion = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.waterTemp = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.salinity = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.pulseLength = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.TxMode = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.versionFPGA = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.versionPSuC = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.thumbnailFI = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.fileSize = struct.unpack(
                    utils.cType["uint64_t"], fhand.read(utils.c("uint64_t")))[0]
                self.optionalHeaderSize = struct.unpack(
                    utils.cType["uint64_t"], fhand.read(utils.c("uint64_t")))[0]
                self.optionalTailSize = struct.unpack(
                    utils.cType["uint64_t"], fhand.read(utils.c("uint64_t")))[0]
                self.versionMinor = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]
                self.largeLens = struct.unpack(
                    utils.cType["uint32_t"], fhand.read(utils.c("uint32_t")))[0]

        except FileNotFoundError as e:
            raise FileNotFoundError(e.errno, e.strerror, filename)

        
        self.__FRAME_SIZE = self.__setFrameSize()
        self.__FILE_SIZE = self.__getFileSize()
        self.__sanityChecks()

        
    #####################################################################
    #       Usable user Functions
    #####################################################################

    def __len__(self):
        """
        __len__ Returns number of frames inside the file.
        
        accesses private variable '__FRAME_COUNT' and returns its value
        to the user.
        
        :return: number of frames in the file.
        :rtype: integer
        """
        return self.__FRAME_COUNT


    def __repr__(self):
        """
        gets the path of the opened file.
        
        :return: returns a string with the file path.
        :rtype: string
        """
        return os.path.abspath(self.__FILE_PATH)

        
    
    def getFileName(self):
        """
        getFileName gets file name.
        
        returns the file name.
        
        :return: file's name without any extensions
        :rtype: string
        """
        fileName = re.search("([a-zA-Z0-9]+).aris", self.__FILE_PATH)
        return fileName.group(0)


    def readFrame(self, frameIndex):
        """
        readFrame Reads a frame from the given file.
        
        creates a frame class with the given frame index, for more
        information aboyt the class frame, refer to 'v5_frame_info.py'
        
        :param frameIndex: number of requested frame. zero indexing.
        :type frameIndex: integer
        :return: returns an instance of frame class
        :rtype: object of type v5_frame
        """
        return frame.v5_Frame(self.__FILE_PATH, frameIndex, self.__FRAME_SIZE)

    def getImages(self):
        images = list()
        for frameIndex in range(self.__FRAME_COUNT):
            wholeFrame = frame.v5_Frame(self.__FILE_PATH, frameIndex, self.__FRAME_SIZE)
            images.append(wholeFrame.IMAGE)
        return images

    
    def getFileHeader(self):
    
        try:
            with open(JSON_FILE_PATH) as json_fhand:
                orderedSet = dict()
                file_headers = json_fhand.read()
                data = json.loads(file_headers)
                checkList = data.get("file").keys()
                headerFields = self.__dict__
                for headerField in headerFields:
                    if(headerField in checkList):
                        headerValue = headerField + " = " + str(headerFields[headerField])
                        index = str(data["file"][headerField]["order"])
                        orderedSet[index] = headerValue
                    else:
                        continue
                for i in range(self.__FILE_HEADER_NUM):
                    print(orderedSet[str(i)])

        except FileNotFoundError as e:
            raise FileNotFoundError(e.errno, e.strerror, JSON_FILE_PATH)
        return

    def getInfo(self):
        Info = {
            "FileName": self.__repr__(),
            "SoftwareVersion": self.softwareVersion,
            "ARIS_SN": self.serialNumber,
            "FileSize": self.__FILE_SIZE,
            "NumberOfFrames": self.__len__(),
            "BeamCount": self.numRawBeams,
            "SamplesPerBeam": self.samplesPerChannel
        }
        return Info


    ##############################################################
    #       Functions called when initializing ARIS File Class
    ##############################################################
    
    def __setFrameSize(self):
        """
        __setFrameSize calculates frame size
        
        a functione that takes an instant of the class and returns
        an integer containing the frame size in the given file.
        
        :return: number of beams * number of samples per channel
        :rtype: integer
        """
        return self.numRawBeams*self.samplesPerChannel

    def __getFileSize(self):
        """
        __getFileSize
        
        Returns the file size on disk
        
        :return: Given file size in bytes
        :rtype: integer
        """
        return os.path.getsize(self.__repr__())


    def __sanityChecks(self):
        """
        __sanityChecks 
        
        Checking file's sanity.
        
        :return: True if everything working, otherwise False
        :rtype: bool
        """

        if ((self.version == 88491076)):
            
            return True
        
        raise TypeError("File is corrupted")

    

def v5_getAllFramesData(fhand, version, cls):
    """Opens a .aris file and extracts all bytes for all frames and returns a
    list containing all frames data, to be used in drawing the images.
    For images to be drawn from frames, the following attributes are needed
    from this function:
        - SONAR Sample Data     --> `allFrames`
        - Number of Beams [fl]  --> `numRawBeams`
        - Samples Per Beam [fl] --> `samplesPerChannel`
        - Type of Lens  [fr]    --> `largeLens`
        - Sample Start Delay[fr]--> `sampleStartDelay`
        - Sound Velocity[fr]    --> `soundSpeed`
        - Sample Period[fr]     --> `samplePeriod`

    """
    
    ## TODO _
    
    cls.version = "ARIS"
    fileAttributesList = ["numRawBeams", "samplesPerChannel", "frameCount"]
    frameAttributesList = ["largeLens", "sampleStartDelay", "soundSpeed", "samplePeriod", "frameRate"]

    fileHeader = utils.getFileHeaderValue(version, fileAttributesList)
    frameHeader = utils.getFrameHeaderValue(version, frameAttributesList)
    print("inside v5_getAllFramesData(fhand)")
    #   Reading Number of frames in the file [from file header]
    fhand.seek(fileHeader["frameCount"]["location"], 0)
    cls.frameCount = struct.unpack(
            utils.cType[fileHeader["frameCount"]["size"]],
            fhand.read(utils.c(fileHeader["frameCount"]["size"])))[0]

    #   Reading number of beams in each frame [from file header]
    fhand.seek(fileHeader["numRawBeams"]["location"], 0)
    cls.BEAM_COUNT = struct.unpack(
            utils.cType[fileHeader["numRawBeams"]["size"]],
            fhand.read(utils.c(fileHeader["numRawBeams"]["size"])))[0]

    #   Reading number of samples in each beam [from file header]
    fhand.seek(fileHeader["samplesPerChannel"]["location"], 0)
    cls.samplesPerBeam = struct.unpack(
            utils.cType[fileHeader["samplesPerChannel"]["size"]],
            fhand.read(utils.c(fileHeader["samplesPerChannel"]["size"])))[0]

    #   Reading Frame Rate [from frame header]
    fhand.seek(cls.FILE_HEADER_SIZE + fhand.seek(frameHeader["frameRate"]["location"], 0))
    cls.frameRate = struct.unpack(
            utils.cType[frameHeader["frameRate"]["size"]],
            fhand.read(utils.c(frameHeader["frameRate"]["size"])))[0]

    #   Reading Sample Period [from frame header]
    fhand.seek(cls.FILE_HEADER_SIZE + fhand.seek(frameHeader["samplePeriod"]["location"], 0))
    cls.samplePeriod = struct.unpack(
            utils.cType[frameHeader["samplePeriod"]["size"]],
            fhand.read(utils.c(frameHeader["samplePeriod"]["size"])))[0]

    #   Reading Sound Velocity in Water [from frame header]
    fhand.seek(cls.FILE_HEADER_SIZE + fhand.seek(frameHeader["soundSpeed"]["location"], 0))
    cls.soundSpeed = struct.unpack(
            utils.cType[frameHeader["soundSpeed"]["size"]],
            fhand.read(utils.c(frameHeader["soundSpeed"]["size"])))[0]
    
    #   Reading Sample Start Delay [from frame header]
    fhand.seek(cls.FILE_HEADER_SIZE + fhand.seek(frameHeader["sampleStartDelay"]["location"], 0))
    cls.sampleStartDelay = struct.unpack(
            utils.cType[frameHeader["sampleStartDelay"]["size"]],
            fhand.read(utils.c(frameHeader["sampleStartDelay"]["size"])))[0]

    #   Reading availability of large lens [from frame header]
    fhand.seek(cls.FILE_HEADER_SIZE + fhand.seek(frameHeader["largeLens"]["location"], 0))
    cls.largeLens = struct.unpack(
            utils.cType[frameHeader["largeLens"]["size"]],
            fhand.read(utils.c(frameHeader["largeLens"]["size"])))[0]

    frameSize = cls.BEAM_COUNT * cls.samplesPerBeam
    # the first frame data offset from file start is 2048
    frameoffset = 2048
    fhand.seek(frameoffset, 0)
    strCat = frameSize*"B"
    cls.FRAMES = np.array(struct.unpack(strCat, fhand.read(frameSize)), dtype=np.uint8)
    cls.FRAMES = cv2.flip(cls.FRAMES.reshape((cls.samplesPerBeam, cls.BEAM_COUNT)), 0)
    cls.DATA_SHAPE = cls.FRAMES.shape
    cls.windowStart = cls.sampleStartDelay * 0.000001 * cls.soundSpeed/2
    cls.windowLength = cls.samplePeriod * cls.samplesPerBeam * 0.000001 * cls.soundSpeed/2
    cls.firstBeamAngle = beamLookUp.BeamLookUp(cls.BEAM_COUNT, cls.largeLens)[-1]
    #cls.FRAMES = cls.constructImages()
    cls.FRAMES = cls.constructImages(cls.FRAMES)

    
    return


