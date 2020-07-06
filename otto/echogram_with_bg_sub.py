import glob
import numpy as np
import cv2

def main():

	# Test data, a folder with multiple png frames
	directory = '/data/ttekoo/data/luke/2_vaihe_kaikki/frames/Teno1_test_6000-6999'
	body = '*.png'
	path = directory + '/' + body

	echogram = []
	echogram_foreground = []

	# Background subtractor for echogram. Parameter values to UI / file at some point.
	fgbg = cv2.createBackgroundSubtractorMOG2()
	fgbg.setNMixtures(3)
	fgbg.setShadowValue(0)
	fgbg.setVarThreshold(10)

	# Iterate folder
	for file in sorted(glob.glob(path)):
	
		print(file)

		# Read image
		image = cv2.imread(file, 0)

		if type(image) is not np.ndarray:
			continue
		
		# Check if echogram not initialized
		if len(echogram) == 0:
			shape = list(image.shape)
			shape[1] = 1
			echogram = np.zeros(tuple(shape), np.uint8)
			echogram_foreground = np.zeros(tuple(shape), np.uint8)

		# Append column to echogram
		col_im = np.max(np.asarray(image), axis=1)
		echogram = np.c_[echogram, col_im]

		# Update background model & foreground mask
		foreground = fgbg.apply(col_im, learningRate=0.01)
		echogram_foreground = np.c_[echogram_foreground, foreground]


	# Show results
	cv2.imshow("echogram", echogram)
	cv2.imshow("echogram_foreground", echogram_foreground)
	cv2.waitKey(0)

if __name__ == "__main__":
	main()

