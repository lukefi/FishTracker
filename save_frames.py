import sys
import cv2
from PyQt5 import QtCore, QtGui, QtWidgets
from playback_manager import PlaybackManager

def saveImage(tuple):
	ind, frame = tuple
	print("ASD")
	cv2.imwrite("out/frame_{:06}.png".format(ind), frame)

if __name__ == "__main__":
	app = QtWidgets.QApplication(sys.argv)
	main_window = QtWidgets.QMainWindow()
	playback_manager = PlaybackManager(app, main_window)
	playback_manager.fps = 1000
	playback_manager.openTestFile()

	playback_manager.playback_thread.signals.mapping_done_signal.connect(lambda: playback_manager.play())
	playback_manager.frame_available.append(saveImage)

	main_window.show()
	sys.exit(app.exec_())
	#main()