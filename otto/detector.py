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

def nothing(x):
    pass

def round_up_to_odd(f):
    return np.ceil(f) // 2 * 2 + 1

def main():


	# Test data, a folder with multiple png frames
	directory = '/data/ttekoo/data/luke/2_vaihe_kaikki/frames/Teno1_test_6000-6999'
	body = '*.png'
	path = directory + '/' + body

	# Some parameters. Should be in UI / read from a config file.
	mog_var_thresh = 11
	min_fg_pixels = 25
	median_size = 3
	nof_bg_frames = 1000

	fgbg_mog = cv2.createBackgroundSubtractorMOG2()
	fgbg_mog.setNMixtures(5)
	fgbg_mog.setVarThreshold(mog_var_thresh)
	fgbg_mog.setShadowValue(0)
	
	cv2.namedWindow('fg_mask_mog', 1)
	cv2.namedWindow('image_o_rgb', 1)
	cv2.namedWindow('image_o_gray', 1)
	cv2.namedWindow('fg_mask_filt', 1)

	cv2.createTrackbar('mog_var_thresh', 'image_o_rgb', 5, 30, nothing)
	cv2.createTrackbar('median_size', 'image_o_rgb', 1, 21, nothing)
	cv2.createTrackbar('min_fg_pixels', 'image_o_rgb', 10, 100, nothing)

	cv2.setTrackbarPos('mog_var_thresh','image_o_rgb', mog_var_thresh)
	cv2.setTrackbarPos('min_fg_pixels','image_o_rgb', min_fg_pixels)
	cv2.setTrackbarPos('median_size','image_o_rgb', median_size)

	# Get number of files in path
	nof_frames = len(glob.glob1(directory, body))

	# Create background model from fixed number of frames.
	# Count step based on number of frames
	# NOTE: nof_bg_frames to UI / file
	bg_counter = 0
	step = np.ceil(nof_frames/nof_bg_frames)	
	for file in sorted(glob.glob(path)):
		image_o = cv2.imread(file, 0)
		# NOTE: now all frames are resized to (500,100).
		# Should be other way. This is now for keping parameter values same.
		image_o = cv2.resize(image_o, (500,1000), interpolation = cv2.INTER_AREA)
		# NOTE: learningRate to UI / file / compute from nof_bg_frames (learningRate = 1/nof_bg_frames)
		fgbg_mog.apply(image_o, learningRate=0.01)
		bg_counter = bg_counter + step
		if bg_counter == nof_bg_frames:
			break;
 
	n_step = 0
	ts = 0

	start_time = time.time()
	for file in sorted(glob.glob(path)):
		
		# Uodate timestamp, TODO read from data
		ts = ts + 0.1

		# Get new frame
		image_o = cv2.imread(file, 0)
		
		# NOTE: now all frames are resized to (500,100).
		# Should be other way. This is now for keping parameter values same.
		image_o = cv2.resize(image_o, (500,1000), interpolation = cv2.INTER_AREA)
		image_o_gray = image_o

		# Get foreground mask, without updating the  model (learningRate = 0)
		fg_mask_mog = fgbg_mog.apply(image_o, learningRate=0)

		msg = str(ts) + ' 9999999999 '

		# Read parameter values from trackbars
		mog_var_thresh = cv2.getTrackbarPos('mog_var_thresh','image_o_rgb')
		min_fg_pixels = cv2.getTrackbarPos('min_fg_pixels','image_o_rgb')
		sleep = cv2.getTrackbarPos('sleep','image_o_rgb')
		median_size = int(round_up_to_odd(cv2.getTrackbarPos('median_size','image_o_rgb')))

		fgbg_mog.setVarThreshold(mog_var_thresh)
		fg_mask_cpy = fg_mask_mog
		fg_mask_filt = cv2.medianBlur(fg_mask_cpy, median_size) 
		image_o_rgb = cv2.applyColorMap(image_o, cv2.COLORMAP_OCEAN)

		ind = np.nonzero(np.asarray(fg_mask_filt))
		data = np.asarray(ind).T


		if data.shape[0] >= min_fg_pixels:

			# DBSCAN clusterer, NOTE: parameters should be in UI / read from file
			clusterer = cluster.DBSCAN(eps=10, min_samples=10)		
			labels = clusterer.fit_predict(data)
		
			data = data[labels != -1]			
			labels = labels[labels != -1]

			if labels.shape[0] > 0:

				colors = sns.color_palette('deep', np.unique(labels).max() + 1)

				for label in np.unique(labels):
					foo = data[labels == label]
					if foo.shape[0] < 2:
						continue
					
					ca = np.cov(foo, y=None, rowvar=0, bias=1)
					v, vect = np.linalg.eig(ca)
					tvect = np.transpose(vect)
					ar = np.dot(foo, np.linalg.inv(tvect))

					# NOTE a fixed parameter --> to UI / file.
					if ar.shape[0] > 10:

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

						# Use the the eigenvectors as a rotation matrix and rotate the corners and the center back
						corners = np.dot(corners, tvect)
						center = np.dot(center, tvect)
						
						# This message was used to send data to tracker process (C++) or save detections to file
						msg = msg + ' ' + str(int(center[1]*10)) + ' ' + str(int(center[0]*10)) + ' ' + str(int(diff[1]*2))

						# Visualize results	
						test = 'Size (pix): ' + str(int(diff[1]*2))
						image_o_rgb = cv2.putText(image_o_rgb, test, (int(center[1])-50, int(center[0])-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1, cv2.LINE_AA)
						for i in range(foo.shape[0]):
							cv2.line(image_o_rgb, (foo[i,1], foo[i,0]), (foo[i,1], foo[i,0]), \
								(int(255*colors[label][0]), int(255*colors[label][1]), int(255*colors[label][2])), 2)						
						for i in range(0,3):
							cv2.line(image_o_rgb, (int(corners[i,1]),int(corners[i,0])), (int(corners[i+1,1]),int(corners[i+1,0])),  (255,255,255), 1)
						cv2.line(image_o_rgb, (int(corners[3,1]),int(corners[3,0])), (int(corners[0,1]),int(corners[0,0])),  (255,255,255), 1)
			
		# Print messaage: [timestamp camera_id position_x position_y length]
		# Position now in pixel coordinates (times 10) for tracker, hould be in metric coordinates
		print(msg)

		pos_step = 600

		cv2.moveWindow("fg_mask_mog", pos_step*0, 20);
		cv2.moveWindow("image_o_gray", pos_step*1, 20);
		cv2.moveWindow("image_o_rgb", pos_step*2, 20);
		cv2.moveWindow("fg_mask_filt", pos_step*3, 20);

		cv2.imshow("fg_mask_mog", fg_mask_mog)
		cv2.imshow("image_o_gray", image_o_gray)
		cv2.imshow("image_o_rgb", image_o_rgb)
		cv2.imshow("fg_mask_filt", fg_mask_filt)

		key = cv2.waitKey(sleep)
		if key == 32:
			sleep = -sleep

if __name__ == "__main__":
	main()





