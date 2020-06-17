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
import struct
import os
import json

CWD = os.getcwd()

# {CWD}/file_handlers/v0/v0_frame_headers_info.json
# {CWD}/file_handlers/v1/v1_frame_headers_info.json
# {CWD}/file_handlers/v2/v2_frame_headers_info.json
# {CWD}/file_handlers/v3/v3_frame_headers_info.json
# {CWD}/file_handlers/v4/v4_frame_headers_info.json
# {CWD}/file_handlers/v5/v5_frame_headers_info.json
v0_FrameHeaderJSON = os.path.join(CWD, "file_handlers", "v0", "v0_frame_headers_info.json")
v1_FrameHeaderJSON = os.path.join(CWD, "file_handlers", "v1", "v1_frame_headers_info.json")
v2_FrameHeaderJSON = os.path.join(CWD, "file_handlers", "v2", "v2_frame_headers_info.json")
v3_FrameHeaderJSON = os.path.join(CWD, "file_handlers", "v3", "v3_frame_headers_info.json")
v4_FrameHeaderJSON = os.path.join(CWD, "file_handlers", "v4", "v4_frame_headers_info.json")
v5_FrameHeaderJSON = os.path.join(CWD, "file_handlers", "v5", "v5_frame_headers_info.json")

# {CWD}/file_handlers/v0/v0_file_headers_info.json
# {CWD}/file_handlers/v1/v1_file_headers_info.json
# {CWD}/file_handlers/v2/v2_file_headers_info.json
# {CWD}/file_handlers/v3/v3_file_headers_info.json
# {CWD}/file_handlers/v4/v4_file_headers_info.json
# {CWD}/file_handlers/v5/v5_file_headers_info.json
v0_FileHeaderJSON = os.path.join(CWD, "file_handlers", "v0", "v0_file_headers_info.json")
v1_FileHeaderJSON = os.path.join(CWD, "file_handlers", "v1", "v1_file_headers_info.json")
v2_FileHeaderJSON = os.path.join(CWD, "file_handlers", "v2", "v2_file_headers_info.json")
v3_FileHeaderJSON = os.path.join(CWD, "file_handlers", "v3", "v3_file_headers_info.json")
v4_FileHeaderJSON = os.path.join(CWD, "file_handlers", "v4", "v4_file_headers_info.json")
v5_FileHeaderJSON = os.path.join(CWD, "file_handlers", "v5", "v5_file_headers_info.json")

def getFrameHeaderValue(version, attributes):
    """
    Get the byte location of specific frame header value
    """
    versions = {
        4604996:  v0_FrameHeaderJSON,
        21382212: v1_FrameHeaderJSON,
        38159428: v2_FrameHeaderJSON,
        54936644: v3_FrameHeaderJSON,
        71713860: v4_FrameHeaderJSON,
        88491076: v5_FrameHeaderJSON
    }
    locationAndSize = dict()
    filePath = versions[version]
    try:
        JSON = open(filePath)
    except FileNotFoundError as e:
        raise FileNotFoundError(e.errno, e.strerror, filePath)
    
    allFile = JSON.read()
    frameHeaders = json.loads(allFile) 
    for attribute in attributes:
        headerLocation = frameHeaders["frame"][attribute]["location"]
        headerSize = frameHeaders["frame"][attribute]["size"]
        locationAndSize[attribute] = {}
        locationAndSize[attribute]["location"] = headerLocation
        locationAndSize[attribute]["size"] = headerSize
    
    JSON.close()
    return locationAndSize

def getFileHeaderValue(version, attributes):
    """
    Get the byte location of specific file header value
    and its size
    """
    versions = {
        4604996:  v0_FileHeaderJSON,
        21382212: v1_FileHeaderJSON,
        38159428: v2_FileHeaderJSON,
        54936644: v3_FileHeaderJSON,
        71713860: v4_FileHeaderJSON,
        88491076: v5_FileHeaderJSON
    }
    locationAndSize = dict()
    filePath = versions[version]
    try:
        JSON = open(filePath)
    except FileNotFoundError as e:
        raise FileNotFoundError(e.errno, e.strerror, filePath)
    
    allFile = JSON.read()
    fileHeaders = json.loads(allFile)
    for attribute in attributes:
        headerLocation = fileHeaders["file"][attribute]["location"]
        if (headerLocation == None):
            print("Header " + str(attribute) + " is not available in this file type")
        headerSize = fileHeaders["file"][attribute]["size"]
        locationAndSize[attribute] = {}
        locationAndSize[attribute]["location"] = headerLocation
        locationAndSize[attribute]["size"] = headerSize
    
    JSON.close()
    return locationAndSize


def getFrameHeaderSize(version):
    versions = {
        4604996:  v0_FrameHeaderJSON,
        21382212: v1_FrameHeaderJSON,
        38159428: v2_FrameHeaderJSON,
        54936644: v3_FrameHeaderJSON,
        71713860: v4_FrameHeaderJSON,
        88491076: v5_FrameHeaderJSON
    }
    filePath = versions[version]
    try:
        JSON = open(filePath)
    except FileNotFoundError as e:
        raise FileNotFoundError(e.errno, e.strerror, filePath)
    
    allFile = JSON.read()
    frameHeaders = json.loads(allFile) 
    size = frameHeaders["headerSize"]["size"]
    JSON.close()
    return size

def getFileHeaderSize(version):
    versions = {
        4604996:  v0_FileHeaderJSON,
        21382212: v1_FileHeaderJSON,
        38159428: v2_FileHeaderJSON,
        54936644: v3_FileHeaderJSON,
        71713860: v4_FileHeaderJSON,
        88491076: v5_FileHeaderJSON
    }
    locationAndSize = dict()
    filePath = versions[version]
    try:
        JSON = open(filePath)
    except FileNotFoundError as e:
        raise FileNotFoundError(e.errno, e.strerror, filePath)
    
    allFile = JSON.read()
    fileHeaders = json.loads(allFile)

    size = fileHeaders["headerSize"]["size"]
    JSON.close()
    return size



def c(inpStr):
    """
    Takes a variable type from the cType dictionary and returns
    the number of bytes which that exact variable occupies.
    
    Arguments:
        inpStr {string} -- string that indicates the type of
                            variable that we need to calculate
                            the size of
    
    Returns:
        integer -- indicates the number of bytes that this
                        variable occupies

    Reference: https://docs.python.org/3/library/struct.html
    """

    return struct.calcsize(cType[inpStr])


cType = {
    "uint32_t":     "I",
    "float":        "f",
    "int32_t":      "i",
    "uint64_t":     "Q",
    "char[8]":      "8s",
    "char[16]":     "16s",
    "char[32]":     "32s",
    "char[60]":     "60s",
    "char[136]":    "136s",
    "char[256]":    "256s",
    "char[568]":    "568s",
    "char[288]":    "288s",
    "uint16_t":     "H",
    "uint8_t":      "B",
    "double":       "d"
}
