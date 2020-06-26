import cv2
import numpy as np

class ImageManipulation:
    @staticmethod
    def CLAHE(img):
        print(img.dtype)
        #-----Converting image to LAB Color model----------------------------------- 
        lab= cv2.cvtColor(img, cv2.COLOR_BGR2LAB)

        #-----Splitting the LAB image to different channels-------------------------
        l, a, b = cv2.split(lab)

        #-----Applying CLAHE to L-channel-------------------------------------------
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        cl = clahe.apply(l)

        #-----Merge the CLAHE enhanced L-channel with the a and b channel-----------
        limg = cv2.merge((cl,a,b))

        #-----Converting image from LAB Color model to RGB model--------------------
        final = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

        return final

class ImageProcessor:
    def __init__(self):
        self.use_any = False
        self.use_clahe = False

    def processImage(self, img):
        if not self.use_any:
            return img

        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        if self.use_clahe:
            img = ImageManipulation.CLAHE(img)

        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        return img

    def setAny(self):
        self.use_any = self.use_clahe

    def setAutomaticContrast(self, value):
        self.use_clahe = value
        self.setAny()