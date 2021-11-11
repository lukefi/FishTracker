"""
This file is part of Fish Tracker.
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
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import numpy as np

class ImageManipulation:
    @staticmethod
    def CLAHE(img):
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

    @staticmethod
    def distanceCompensation(img):
        avg = np.mean(img, axis=1).astype(np.single)
        x = np.arange(len(avg))
        z = np.polyfit(x, avg, 2)
        p = np.poly1d(z)
        
        col = np.expand_dims(p(x)**-1, axis=1)
        m = np.tile(col, (1, img.shape[1]))
        img2 = np.multiply(img, m)
        
        min_value = np.amin(img2)
        max_value = np.amax(img2)
        
        img2 = (255 * (img2 - min_value) / float(max_value - min_value)).astype(np.uint8)
        return img2

    @staticmethod
    def adjustGamma(image, gamma):
        invGamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
        return cv2.LUT(image, table)

class ImageProcessor:
    def __init__(self):
        self.use_any = True
        self.use_clahe = False
        self.use_colormap = True

        self.additional = []

        self.gamma = 1
        self.fig = plt.figure()
        x1 = np.linspace(0, 47, 48)
        y1 = np.cos(2 * np.pi * x1) * np.exp(-x1)
        self.line, = plt.plot(x1, y1, 'ko-')

    def processImage(self, ind, image):
        if not self.use_any:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        if self.use_clahe:
            image = ImageManipulation.CLAHE(image)

        if self.gamma != 1:
            image = ImageManipulation.adjustGamma(image, self.gamma)

        if self.use_colormap:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            image = cv2.applyColorMap(image, cv2.COLORMAP_OCEAN)

        if len(self.additional) > 0:
            for f in self.additional:
                image = f((ind, image))

        return image

    def processGrayscaleImage(self, image):
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    def distancePlot(self, image):
        print(image.shape)
        avg = np.mean(image, axis=1)
        self.line.set_ydata(avg)
        self.fig.canvas.draw()
        img = np.fromstring(fig.canvas.tostring_rgb(), dtype=np.uint8,
        sep='')
        img  = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        img = cv2.cvtColor(img,cv2.COLOR_RGB2BGR)
        cv2.imshow("plot",img)


    def setAny(self):
        self.use_any = self.use_clahe or self.use_colormap or self.gamma != 1 or len(self.additional) > 0

    def addAdditional(self, f):
        if not f in self.additional:
            self.additional.append(f)
        self.setAny()

    def removeAdditional(self, f):
        if f in self.additional:
            self.additional.remove(f)
        self.setAny()

    def setAutomaticContrast(self, value):
        self.use_clahe = value
        self.setAny()

    def setColorMap(self, value):
        self.use_colormap = value
        self.setAny()

    def setGamma(self, value):
        self.gamma = value
        self.setAny()