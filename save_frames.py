import sys
import cv2
from PyQt5 import QtCore, QtGui, QtWidgets
import argparse
from playback_manager import PlaybackManager

# Save frames using playback_manager

main_window = None
playback_manager = None
base_name = "frame"
max_ind = float("inf")

def checkInd(ind):
	if ind >= max_ind:
		playback_manager.stopAll()
		main_window.close()
		return True
	return False


def saveImage(tuple):
	ind, frame = tuple
	if checkInd(ind):
		return

	cv2.imwrite("out/{}_{:06}.png".format(base_name, ind), frame)
	print("Saved frame:", ind)

def savePolarFrames():
	for ind, frame in enumerate(playback_manager.getPolarBuffer()):
		if checkInd(ind):
			break

		cv2.imwrite("out/{}_{:06}.png".format(base_name, ind), frame)
		print("Saved frame:", ind)

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument('-c', "--count", type=int, required=False, help="How many images are saved (at most)")
	parser.add_argument('-p', "--polar", action="store_true", required=False, help="Output in polar coordinates")
	args = parser.parse_args()

	app = QtWidgets.QApplication(sys.argv)
	main_window = QtWidgets.QMainWindow()
	playback_manager = PlaybackManager(app, main_window)
	playback_manager.fps = 1000

	if args.count is not None:
		max_ind = args.count

	if args.polar:
		print("Saving frames in polar mapping.")
		playback_manager.polars_loaded.connect(savePolarFrames)
	else:
		print("Saving frames in cartesian mapping.")
		playback_manager.playback_thread.signals.mapping_done_signal.connect(lambda: playback_manager.play())
		playback_manager.frame_available.connect(saveImage)

	playback_manager.openFile()
	temp_name = playback_manager.getFileName(extension=False)
	if temp_name != "":
		base_name = temp_name

	if args.polar:
		base_name += "_polar"

	main_window.show()
	sys.exit(app.exec_())
	#main()