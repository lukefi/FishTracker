import cv2
import os
import numpy as np
import copy
import json
# SF: Sonar File Library
import file_handler as SF
import numpy as np
from time import sleep

def FAnalyze(cls, kernel = None , kernelDim = None,
            startFrame = None, blurDim = None,
            bgTh = None, minApp = None, maxDis = None,
            searchRadius = None,
            imshow = False):

    # kernel = np.ones((5,5),np.uint8)
    # kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (10,5))
    if kernelDim is not None:
        kernelDim = kernelDim
    else:
        kernelDim = (10,2)

    if (kernel == "Rectangle"):
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, kernelDim)
    elif (kernel == "Ellipse") or (kernel is None):
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, kernelDim)
    elif (kernel == "Cross"):
        kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, kernelDim)
    else:
        raise ValueError("Unknown structuring element `{}`".format(kernel))
        return False

    if startFrame is None:
        count = 1
    else:
        count = startFrame

    if blurDim is None:
        blurDim = (5,5)

    if bgTh is None:
        threshold = 25
    else:
        threshold = bgTh

    if minApp is not None:
        Fish.minAppear = minApp

    if maxDis is not None:
        Fish.maxDisappear = maxDis

    if searchRadius is not None:
        centroidTracker.searchArea = searchRadius


    fgbg = cv2.createBackgroundSubtractorMOG2(varThreshold=threshold)
    font = cv2.FONT_HERSHEY_SIMPLEX

    ## variables for displaying frames
    
    # for the key presses {
    # dummy: for getting key hex values,
    # k : for inputing key strokes}
    dummy = 0
    k = 30

    # for the Play|Pause operations {
    # play = False --> pause,
    # play = True --> playing}
    play = True

    # playing in desc|asce orders {
    # desc = False --> playing in ascending order,
    # }
    desc = False

    # variables for trakcers:
    tracker = centroidTracker()

    while (True):
    # while (count<100):
        # read the image from disk
        readFromFile = cls.File
        img = fetchFrame(count, readFromFile= readFromFile)
        if(img is None):
            if readFromFile:
                FSaveOutput(tracker, "./", os.path.basename(cls.FFilePath).split(".")[0] + ".json")
                break
            else:
                FSaveOutput(tracker, "./", "test.json")
                break
        
        # Blur the image to help in object detection
        frameBlur = cv2.blur(img, blurDim)
        
        # apply background subtraction to get moving objects
        # the image produced has the objects and shadows
        # background value #0
        # shadow value #127
        # objects value #255
        mask = fgbg.apply(frameBlur)
        
        # perform morphological operations to visualize objects better
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # remove shadows
        # function returns tuple, with the image mask as second arg
        mask = cv2.threshold(mask, 128, 255, cv2.THRESH_BINARY)[1]

        candidatesInfo = cv2.connectedComponentsWithStats(mask)
        
        ret         = candidatesInfo[0] - 1 # number of objects
        labels      = candidatesInfo[1] # labeled image
        stats       = np.delete(candidatesInfo[2],0, axis = 0) # statistics matrix of each label (deleting the first row --> backgorund)
        centroids   = np.delete(candidatesInfo[3], 0, axis = 0) # floating point centroid (x,y) output for each label, including the background label

        # if the program can not detect any objects, continue; 
        if ret == 0:
            if (desc):
                count = count - 1
            else:
                count = count + 1
            continue

        fishes = tracker.update(stats, centroids, count)

        if(imshow):
            label_hue = np.uint8(179*labels/np.max(labels))
            blank_ch = 255*np.ones_like(label_hue)
            labeled_img = cv2.merge([label_hue, blank_ch, blank_ch])
            labeled_img = cv2.cvtColor(labeled_img, cv2.COLOR_HSV2BGR)
            labeled_img[label_hue==0] = 0
    
            colored_img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR )
            if (bool(fishes['objects'])):
                for fish in fishes['objects'].keys():
                    x = int(fishes['objects'][fish].locations[-1][0])
                    y = int(fishes['objects'][fish].locations[-1][1])
                    center = (x,y)
                    cv2.circle(labeled_img, center, tracker.searchArea, (0,255,0), 1)
                    cv2.circle(colored_img, center, tracker.searchArea, (0,255,0), 1)
    
            cv2.putText(labeled_img,"Objects: "+str(fishes["objects"].__len__()),(10,100), font, 1,(255,255,255),2,cv2.LINE_AA)
            cv2.putText(labeled_img,str(count),(10,50), font, 1,(255,255,255),2,cv2.LINE_AA)
            cv2.namedWindow("frames and BGS frames", cv2.WND_PROP_FULLSCREEN)
            # cv2.setWindowProperty("frames and BGS frames", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            # cv2.imshow("frames and BGS frames",np.hstack((mask, img)))
            cv2.imshow("frames and BGS frames",np.hstack((labeled_img, colored_img)))
    
            
            k = cv2.waitKey(1 * play) & 0xff
    
            if k == 27:
                break
            elif k == 0x6e:
                print("right")
                desc = False
                count = count + 1
                continue
            elif k == 0x62:
                print("left")
                desc = True
                count = count - 1
                continue
            # elif k == 0x52:
            #     print("up")
            # elif k == 0x54:
            #     print("down")
            elif k == 0x20:
                print("Pause/Play")
                play = not play
            elif k!= dummy:
                dummy = k
                print(hex(k))
    
            count = count + 1
            # if count > number-1:
            #     count = 
    if readFromFile:
        detectedFish = FSaveOutput(tracker, "./", os.path.basename(cls.FFilePath).split(".")[0] + ".json")
    else:
        detectedFish = FSaveOutput(tracker, "./", "test.json")
    cv2.destroyWindow("frames and BGS frames")
    return detectedFish

class centroidTracker():
    # number of pixels around centroid to look at
    searchArea = 30
    def __init__(self):
        self.objects = {
            'objects' :{}
        }
        self.psuedoObjects = {
            'objects': {}
        }
        self.archive = {
            'objects': {}
        }

    def update(self, npArrayOfObjects, npArrayOfCentroids, frameIndex):
        #** npArrayOfCentroids [centroids] > array of arrays with float entries 
        # example:
        #   [0:3] :[array([202.42857143,...57142857]), array([268.84, 885.72]), array([262.20689655,...65517241])]
        #   0:array([202.42857143, 462.57142857])
        #   1:array([268.84, 885.72])
        #   2:array([262.20689655, 956.65517241])

        #** npArrayOfObjects [stats]  > array of arrays with float entries 
        # array entries description:
        #   0: The leftmost (x) coordinate which is the inclusive start of the bounding box in the horizontal direction.
        #   1: The topmost (y) coordinate which is the inclusive start of the bounding box in the vertical direction.
        #   2: The horizontal size of the bounding box.
        #   3: The vertical size of the bounding box.
        #   4: The total area (in pixels) of the connected component.
        # example:
        #   [0:3] :[array([197, 462,  12...ype=int32), array([263, 885,  12...ype=int32), array([254, 956,  17...ype=int32)]
        #   0:array([197, 462,  12,   3,  21], dtype=int32)
        #   1:array([263, 885,  12,   3,  25], dtype=int32)
        #   2:array([254, 956,  17,   3,  29], dtype=int32)

        everything = {}
        # looping on all objects to register them as new objects
        for i in range(npArrayOfObjects.shape[0]):
            NNLocation = self.NAN(npArrayOfCentroids[i])
            if not NNLocation:
                newFish = Fish(npArrayOfCentroids[i], frameIndex, npArrayOfObjects[i])
                self.psuedoObjects['objects'][newFish.id] = newFish
            else:
                self.psuedoObjects['objects'][NNLocation].updateInfo(npArrayOfCentroids[i], frameIndex, npArrayOfObjects[i])
        

        self.delete(frameIndex)
        self.archiveObject(frameIndex)

        return self.objects


    def NAN(self, centroid):
        # (N)earest (A)ctive (N)eighbour
        allObjectsLocations = np.array([0,0])
        location = list()
        if (bool(self.psuedoObjects['objects'])):
            for key in self.psuedoObjects['objects'].keys():
                location.append(key)
                objectHandler = self.psuedoObjects['objects'][key]
                allObjectsLocations = np.vstack((allObjectsLocations, objectHandler.getLastLocation()) )
            allObjectsLocations = np.delete(allObjectsLocations, 0, axis=0)
            distances = np.linalg.norm((allObjectsLocations - centroid), axis=1)
            distanceToNN = np.min(distances)
            if (distanceToNN<self.searchArea):
                index = np.argmin(distances)
                # it returns the key of the nearest neighbor in the `self.psuedoObjects['objects']`
                return location[index]
            else:
                return False
        else:
            return False

    def register(self):
        return

    def delete(self, currentFrame):
        copyOfPsuedo = copy.deepcopy(self.psuedoObjects['objects'])
        for fish in copyOfPsuedo.keys():
            fishHandle = self.psuedoObjects['objects'][fish]
            if (len(fishHandle.frames) < fishHandle.minAppear):
                if (np.abs(fishHandle.frames[-1] - currentFrame) > 2*fishHandle.minAppear):
                    del self.psuedoObjects['objects'][fish]
            if (len(fishHandle.frames) > 2*fishHandle.minAppear):
                self.objects['objects'][fish] = self.psuedoObjects['objects'][fish]
        return
    
    def archiveObject(self, currentFrame):
        copyOfObjects = copy.deepcopy(self.objects['objects'])
        for fish in copyOfObjects.keys():
            fishHandle = self.objects['objects'][fish]
            if (np.abs(fishHandle.frames[-1] - currentFrame) > 2*fishHandle.maxDisappear):
                self.archive['objects'][fish] = self.objects['objects'][fish]
                del self.objects['objects'][fish]
        return
    
class Fish():
    ID = 0
    maxDisappear = 5
    minAppear = 30
    
    def __init__(self, centroid, firstFrame, connectedLabelsWStats):
        # ID given to the fish during first detection
        self.id = Fish.ID
        # Maximum number of frames the fish has to disappear to be deleted from the list
        self.maxDisappear = Fish.maxDisappear
        # Minimum number of frames the fish has to disappear to be added to the list
        self.minAppear = Fish.minAppear

        self.activeToggler = False
        self.locations = list()
        self.locations.append(centroid)
        self.frames = list()
        self.frames.append(firstFrame)
        self.left = list()
        self.left.append(connectedLabelsWStats[0])
        self.top = list()
        self.top.append(connectedLabelsWStats[1])
        self.width = list()
        self.width.append(connectedLabelsWStats[2])
        self.height = list()
        self.height.append(connectedLabelsWStats[3])
        self.area = list()
        self.area.append(connectedLabelsWStats[4])
        Fish.ID += 1
        
        return 

    def getLastLocation(self):
        return self.locations[-1]

    def updateInfo(self, centroid = None, currentFrame= None, objProps = None):
        if ( (centroid is not None) and (currentFrame is not None) and (objProps is not None)):
            self.locations.append(centroid)
            self.frames.append(currentFrame)
            self.left.append(objProps[0])
            self.top.append(objProps[1])
            self.width.append(objProps[2])
            self.height.append(objProps[3])
            self.area.append(objProps[4])
            self.minAppear -= 1
            return
    
def fetchFrame(count, readFromFile=False, filePath = False):
    if not readFromFile:
        # filesPath = "/home/mghobria/Pictures/SONAR_Images" ## laptop
        # filesPath = "C:\\Users\\mghobria\\Downloads\\aris\\F" ## windows home PC
        filesPath = "C:\\Users\\Mina Ghobrial\\Downloads\\SONAR" ## windows Laptop PC

        imagesList = os.listdir(filesPath)
        imagesList.sort()
        # maximum number of images
        number = max(enumerate(imagesList,1))[0]
        imgList = list(enumerate(imagesList,1))
        
        # get image path
        try:
            imgPath = os.path.join(filesPath, imgList[count][1]) 
            img = cv2.imread(imgPath, cv2.IMREAD_GRAYSCALE)
        except:
            raise Exception("Could not load image from disk.\nDirectory to load from: {}\n".format(filesPath))
        
        # read the image from disk
        

    else:
        img = readFromFile.getFrame(count-1)

    return img

def FSaveOutput(cls, path, fileName):
    """
    Takes the ouput of the tracking process and saves it into
    the same path as the stored images.
    Data saved is in the form of a JSON file.
    the data has the following format:
    {
        "fishes": {
            <fishNumber> : {
                "ID": cls.id,
                "locations": cls.locations,
                "frames": cls.frames,
                "objProps": cls.objProps
            }
            .
            .
            .
        }
    }
    """
    print(cls.archive)
    print(cls.objects)
    data = dict()
    for n in cls.archive['objects'].keys():
        data[str(n)] = {
                "ID" : cls.archive['objects'][n].id,
                "locations" : tuple(map(tuple, cls.archive['objects'][n].locations)),
                "frames" : cls.archive['objects'][n].frames,
                "left": list(map(int, cls.archive['objects'][n].left)),
                "top": list(map(int, cls.archive['objects'][n].top)),
                "width": list(map(int, cls.archive['objects'][n].width)),
                "height" : list(map(int, cls.archive['objects'][n].height)),
                "area": list(map(int, cls.archive['objects'][n].area))

            }
    for n in cls.objects['objects'].keys():
        if str(n) not in data:
            data[str(n)] = {
                "ID" : cls.objects['objects'][n].id,
                "locations" : tuple(map(tuple, cls.objects['objects'][n].locations)),
                "frames" : cls.objects['objects'][n].frames,
                "left": list(map(int, cls.objects['objects'][n].left)),
                "top": list(map(int, cls.objects['objects'][n].top)),
                "width": list(map(int, cls.objects['objects'][n].width)),
                "height" : list(map(int, cls.objects['objects'][n].height)),
                "area": list(map(int, cls.objects['objects'][n].area))

            }
    path = os.path.join(path, fileName)            
    with open(path, 'w') as outFile:
        json.dump(data, outFile)
    return data
