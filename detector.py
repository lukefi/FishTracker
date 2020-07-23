import time
import glob
import numpy as np
import cv2
import time
import seaborn as sns
import sklearn.cluster as cluster
import random as rng
import collections
import math
import os
import sys

from PyQt5 import QtCore, QtGui, QtWidgets
from playback_manager import PlaybackManager, TestFigure

def nothing(x):
    pass

def round_up_to_odd(f):
    return np.ceil(f) // 2 * 2 + 1

class Detector:

	def __init__(self, image_provider):
		# Test data, a folder with multiple png frames
		#directory = '/data/ttekoo/data/luke/2_vaihe_kaikki/frames/Teno1_test_6000-6999'
		#body = '*.png'
		#path = directory + '/' + body

		self.resetParameters()
		self.detections = [None]
		self.current_ind = 0
		self.current_len = 0

		self.fgbg_mog = cv2.createBackgroundSubtractorMOG2()
		self.fgbg_mog.setNMixtures(5)
		self.fgbg_mog.setVarThreshold(self.mog_var_thresh)
		self.fgbg_mog.setShadowValue(0)

		self.ts = 0

		self.image_provider = image_provider

		self.show_detections = False
		self.dirty = False

	def resetParameters(self):
		# Some parameters. Should be in UI / read from a config file.
		self.detection_size = 10
		self.mog_var_thresh = 11
		self.min_fg_pixels = 25
		self.median_size = 3
		self.nof_bg_frames = 1000
		self.learning_rate = 0.01

		self.dbscan_eps = 10
		self.dbscan_min_samples = 10


	def initMOG(self):
		# Get frame count
		nof_frames = self.image_provider.getFrameCount()
		self.detections = [None] * nof_frames

		# Create background model from fixed number of frames.
		# Count step based on number of frames
		# NOTE: nof_bg_frames to UI / file
		bg_counter = 0
		step = np.ceil(nof_frames/self.nof_bg_frames)	
		# for file in sorted(glob.glob(path)):
			#image_o = cv2.imread(file, 0)

		for i in range(nof_frames):
			image_o = self.image_provider.getFrame(i)

			# NOTE: now all frames are resized to (500,100).
			# Should be other way. This is now for keping parameter values same.
			# image_o = cv2.resize(image_o, (500,1000), interpolation = cv2.INTER_AREA)

			# NOTE: learningRate to UI / file / compute from nof_bg_frames (learningRate = 1/nof_bg_frames)
			self.fgbg_mog.apply(image_o, learningRate=self.learning_rate)
			bg_counter = bg_counter + step
			if bg_counter == self.nof_bg_frames:
				break;

	def compute(self, ind, image, get_images=False):
		# Update timestamp, TODO read from data
		self.ts += 0.1
		
		# NOTE: now all frames are resized to (500,100).
		# Should be other way. This is now for keping parameter values same.
		#image_o = cv2.resize(image, (500,1000), interpolation = cv2.INTER_AREA)
		#image_o_gray = image_o

		image_o = image_o_gray = image

		# Get foreground mask, without updating the  model (learningRate = 0)
		fg_mask_mog = self.fgbg_mog.apply(image_o, learningRate=0)

		msg = str(self.ts) + ' 9999999999 '

		self.fgbg_mog.setVarThreshold(self.mog_var_thresh)
		fg_mask_cpy = fg_mask_mog
		fg_mask_filt = cv2.medianBlur(fg_mask_cpy, self.median_size)
		image_o_rgb = cv2.applyColorMap(image_o, cv2.COLORMAP_OCEAN)

		data_tr = np.nonzero(np.asarray(fg_mask_filt))
		data = np.asarray(data_tr).T

		detections = []

		if data.shape[0] >= self.min_fg_pixels:

			# DBSCAN clusterer, NOTE: parameters should be in UI / read from file
			clusterer = cluster.DBSCAN(eps=self.dbscan_eps, min_samples=self.dbscan_min_samples)		
			labels = clusterer.fit_predict(data)
		
			data = data[labels != -1]
			labels = labels[labels != -1]

			if labels.shape[0] > 0:
				for label in np.unique(labels):
					foo = data[labels == label]
					if foo.shape[0] < 2:
						continue
			
					d = Detection(label, foo, self)
					msg += " " + d.getMessage()
					detections.append(d)

				if get_images:
					colors = sns.color_palette('deep', np.unique(labels).max() + 1)
					for d in detections:
						image_o_rgb = d.visualize(image_o_rgb, colors)

				
			
		# Print message: [timestamp camera_id position_x position_y length]
		# Position now in pixel coordinates (times 10) for tracker, hould be in metric coordinates
		print(msg)
		self.detections[ind] = detections
		self.current_ind = ind
		self.current_len = len(detections)

		if get_images:
			return detections, (fg_mask_mog, image_o_gray, image_o_rgb, fg_mask_filt)
		else:
			return detections

	def overlayDetections(self, image, detections):
		# labels = [d.label for d in labels]
		colors = sns.color_palette('deep', len(detections))
		for d in detections:
			image = d.visualize(image, colors)

		return image

	def setDetectionSize(self, value):
		try:
			self.detection_size = int(value)
			self.dirty = True
		except ValueError as e:
			print(e)

	def setMOGVarThresh(self, value):
		try:
			self.mog_var_thresh = int(value)
			self.dirty = True
		except ValueError as e:
			print(e)

	def setMinFGPixels(self, value):
		try:
			self.min_fg_pixels = int(value)
			self.dirty = True
		except ValueError as e:
			print(e)

	def setMedianSize(self, value):
		try:
			self.median_size = int(value)
			self.dirty = True
		except ValueError as e:
			print(e)

	def setNofBGFrames(self, value):
		try:
			self.nof_bg_frames = int(value)
			self.dirty = True
		except ValueError as e:
			print(e)

	def setLearningRate(self, value):
		try:
			self.learning_rate = float(value)
			self.dirty = True
		except ValueError as e:
			print(e)

	def setDBScanEps(self, value):
		try:
			self.dbscan_eps = int(value)
			self.dirty = True
		except ValueError as e:
			print(e)

	def setDBScanMinSamples(self, value):
		try:
			self.dbscan_min_samples = int(value)
			self.dirty = True
		except ValueError as e:
			print(e)

	def getCurrentDetection(self):
		dets = self.detections[self.current_ind]
		if dets is None:
			return []

		return [d for d in self.detections[self.current_ind] if d.center is not None]

class Detection:
	def __init__(self, label, data, detector):
		self.label = label
		self.data = data
		self.diff = None
		self.center = None
		self.corners = None

		ca = np.cov(data, y=None, rowvar=0, bias=1)
		v, vect = np.linalg.eig(ca)
		tvect = np.transpose(vect)
		ar = np.dot(data, np.linalg.inv(tvect))

		# NOTE a fixed parameter --> to UI / file.
		if ar.shape[0] > detector.detection_size: #10:

			mina = np.min(ar, axis=0)
			maxa = np.max(ar, axis=0)
			diff = (maxa - mina) * 0.5
					
			center = mina + diff

			# Get the 4 corners by subtracting and adding half the bounding boxes height and width to the center
			corners = np.array([center+[-diff[0],-diff[1]], \
				center+[diff[0],-diff[1]], \
				center+[diff[0],diff[1]], \
				center+[-diff[0],diff[1]], \
				center+[-diff[0],-diff[1]]])

			self.diff = diff

			# Use the the eigenvectors as a rotation matrix and rotate the corners and the center back
			self.corners = np.dot(corners, tvect)
			self.center = np.dot(center, tvect)

	def visualize(self, image, colors):
		if self.diff is None:
			return image

		# Visualize results	
		test = 'Size (pix): ' + str(int(self.diff[1]*2))
		image = cv2.putText(image, test, (int(self.center[1])-50, int(self.center[0])-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1, cv2.LINE_AA)
		print("Test:", self.data.shape)
		print("Test2:", len(colors), self.label)
		for i in range(self.data.shape[0]):
			cv2.line(image, (self.data[i,1], self.data[i,0]), (self.data[i,1], self.data[i,0]), \
				(int(255*colors[self.label][0]), int(255*colors[self.label][1]), int(255*colors[self.label][2])), 2)						
		for i in range(0,3):
			cv2.line(image, (int(self.corners[i,1]),int(self.corners[i,0])), (int(self.corners[i+1,1]),int(self.corners[i+1,0])),  (255,255,255), 1)
		cv2.line(image, (int(self.corners[3,1]),int(self.corners[3,0])), (int(self.corners[0,1]),int(self.corners[0,0])),  (255,255,255), 1)

		return image
	
	def getMessage(self):
		# This message was used to send data to tracker process (C++) or save detections to file
		if self.diff is None:
			return ""
		
		return str(int(self.center[1]*10)) + ' ' + str(int(self.center[0]*10)) + ' ' + str(int(self.diff[1]*2))


class DetectorDisplay:
	def __init__(self):
		self.array = [cv2.imread(file, 0) for file in sorted(glob.glob("out/*.png"))]
		self.detector = Detector(self)

	def run(self):
		self.showWindow()
		self.detector.initMOG()

		for i in range(self.getFrameCount()):
			self.readParameters()
			_, images = self.detector.compute(i, self.getFrame(i), True)
			self.updateWindows(*images)

	def showWindow(self):
		cv2.namedWindow('fg_mask_mog', 1)
		cv2.namedWindow('image_o_rgb', 1)
		cv2.namedWindow('image_o_gray', 1)
		cv2.namedWindow('fg_mask_filt', 1)

		cv2.createTrackbar('mog_var_thresh', 'image_o_rgb', 5, 30, nothing)
		cv2.createTrackbar('median_size', 'image_o_rgb', 1, 21, nothing)
		cv2.createTrackbar('min_fg_pixels', 'image_o_rgb', 10, 100, nothing)

		cv2.setTrackbarPos('mog_var_thresh','image_o_rgb', self.detector.mog_var_thresh)
		cv2.setTrackbarPos('min_fg_pixels','image_o_rgb', self.detector.min_fg_pixels)
		cv2.setTrackbarPos('median_size','image_o_rgb', self.detector.median_size)

	def updateWindows(self, fg_mask_mog, image_o_gray, image_o_rgb, fg_mask_filt):
		pos_step = 600

		cv2.moveWindow("fg_mask_mog", pos_step*0, 20);
		cv2.moveWindow("image_o_gray", pos_step*1, 20);
		cv2.moveWindow("image_o_rgb", pos_step*2, 20);
		cv2.moveWindow("fg_mask_filt", pos_step*3, 20);

		cv2.imshow("fg_mask_mog", fg_mask_mog)
		cv2.imshow("image_o_gray", image_o_gray)
		cv2.imshow("image_o_rgb", image_o_rgb)
		cv2.imshow("fg_mask_filt", fg_mask_filt)

		sleep = cv2.getTrackbarPos('sleep','image_o_rgb')
		key = cv2.waitKey(sleep)
		if key == 32:
			sleep = -sleep

	def readParameters(self):
		# Read parameter values from trackbars
		self.detector.mog_var_thresh = cv2.getTrackbarPos('mog_var_thresh','image_o_rgb')
		self.detector.min_fg_pixels = cv2.getTrackbarPos('min_fg_pixels','image_o_rgb')
		self.detector.median_size = int(round_up_to_odd(cv2.getTrackbarPos('median_size','image_o_rgb')))

	def getFrameCount(self):
		return len(self.array)

	def getFrame(self, ind):
		return self.array[ind]

def simpleTest():
	dd = DetectorDisplay()
	dd.run()

def playbackTest():

	def forwardImage(tuple):
		ind, frame = tuple
		detections = detector.compute(frame)
		image = cv2.applyColorMap(frame, cv2.COLORMAP_OCEAN)
		image = detector.overlayDetections(image, detections)

		figure.displayImage((ind, image))

	def startDetector():
		detector.initMOG()
		playback_manager.play()

	app = QtWidgets.QApplication(sys.argv)
	main_window = QtWidgets.QMainWindow()
	playback_manager = PlaybackManager(app, main_window)
	playback_manager.fps = 1000
	playback_manager.openTestFile()
	playback_manager.frame_available.append(forwardImage)
	detector = Detector(playback_manager)
	playback_manager.mapping_done.append(startDetector)

	figure = TestFigure()
	main_window.setCentralWidget(figure)

	main_window.show()
	sys.exit(app.exec_())


if __name__ == "__main__":
	simpleTest()
	#playbackTest()