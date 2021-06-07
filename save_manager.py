import sys, os, cv2
import json
from PyQt5 import QtCore, QtGui, QtWidgets
import msgpack
import time

import file_handler as fh
from playback_manager import PlaybackManager
from detector import Detector
from tracker import Tracker
from fish_manager import FishManager
from log_object import LogObject

"""
File format as follows:
{
	"file type": "FishTracking"
	"version": "0.1",
	"path": "C:\Vetsjoki\Vetsi_2016-06-18_170000.aris",
	"inverted upstream": False,
	"detector":
	{
		"Detection size": 10,
		"Min foreground pixels": 25,
		"Median size": 3,
		"Clustering epsilon:" 10,
		"Clustering min samples": 10,
		"MOG var threshold": 11,
		"Background frames": 100
		"Learning rate": 0.01
	},
	"tracker":
	{
		"Max age": 10,
		"Min hits": 5,
		"Search radius": 10
	},
	"detections":
	{
		frame1: [(1, [(x,y), (x,y)])],
		frame2: [(2, [(x,y), (x,y), (x,y)]), (3, [(x,y), (x,y)])]
	},
	"fish":
	{
		1: [(frame1, (min_x, max_x, min_y, max_y)), (frame2, (min_x, max_x, min_y, max_y))],
		2: [(frame2, (min_x, max_x, min_y, max_y))],
	}
}
"""

class SaveManager(QtCore.QObject):

	file_loaded_event = QtCore.pyqtSignal()

	def __init__(self, playback_manager, detector, tracker, fish_manager):
		super().__init__()

		self.playback_manager = playback_manager
		self.detector = detector
		self.tracker = tracker
		self.fish_manager = fish_manager

		self.fast_save_enabled = False
		self.previous_path = None

		self.playback_manager.file_closed.connect(self.onFileClosed)

	def saveFile(self, path, binary):
		self.previous_path = path
		self.fast_save_enabled = True

		dp = self.detector.parameters
		dp_dict = None if dp is None else dp.getParameterDict()

		tp = self.tracker.parameters
		tp_dict = None if tp is None else tp.getParameterDict()

		detections = self.detector.getSaveDictionary()
		fish = self.fish_manager.getSaveDictionary()

		data = { "file type": "FishTracking", "version": "0.1" }
		data["path"] = os.path.abspath(self.playback_manager.path)
		data["detector"] = dp_dict
		data["tracker"] = tp_dict
		data["detections"] = detections
		data["fish"] = fish

		if binary:
			packed = msgpack.packb(data)
			with open(path, "wb") as data_file:
				data_file.write(packed)
		else:
			with open(path, "w") as data_file:
				json.dump(data, data_file, indent=2, separators=(',', ': '))

	def loadFile(self, path):
		try:
			try:
				with open(path, "r") as data_file:
					data = json.load(data_file)
					self.loadData(data, path)

			except UnicodeDecodeError:
				with open(path, "rb") as data_file:
					byte_data = data_file.read()
					data = msgpack.unpackb(byte_data)
					self.loadData(data, path)

		except FileNotFoundError:
			LogObject().print("File {} not found".format(path))
			return False

		except json.JSONDecodeError:
			LogObject().print("Invalid JSON file".format(path))
			return False

		#except:
		#	LogObject().print("Unexpected error:", sys.exc_info()[1])
		#	return False

		self.previous_path = path
		self.fast_save_enabled = True
		self.file_loaded_event.emit()
		return True

	def loadData(self, data, path):
		file_path = os.path.abspath(data["path"])
		secondary_path = os.path.abspath(os.path.join(os.path.dirname(path), os.path.basename(file_path)))
		self.playback_manager.checkLoadedFile(file_path, secondary_path, True)

		self.detector.parameters.setParameterDict(data["detector"])
		self.tracker.parameters.setParameterDict(data["tracker"])
		self.detector.applySaveDictionary(data["detections"])
		dets = self.detector.detections
		self.fish_manager.applySaveDictionary(data["fish"], dets)

	def onFileClosed(self):
		self.previous_path = None
		self.fast_save_enabled = False


if __name__ == "__main__":
	path = "D:/Projects/VTT/FishTracking/save_test.fish"

	def saveTest():
		def startDetector():
			detector.initMOG()
			detector.computeAll()
			tracker.trackAll(detector.detections)

		app = QtWidgets.QApplication(sys.argv)
		main_window = QtWidgets.QMainWindow()
		playback_manager = PlaybackManager(app, main_window)
		detector = Detector(playback_manager)
		tracker = Tracker(detector)
		fish_manager = FishManager(playback_manager, tracker)
	
	
		save_manager = SaveManager(playback_manager, detector, tracker, fish_manager)

		fish_manager.updateContentsSignal.connect(lambda: save_manager.saveFile(path, True))

		playback_manager.openTestFile()
		detector.mog_parameters.nof_bg_frames = 500
		detector._show_detections = True
		playback_manager.mapping_done.connect(startDetector)

		main_window.show()
		sys.exit(app.exec_())

	def loadTest():
		app = QtWidgets.QApplication(sys.argv)
		main_window = QtWidgets.QMainWindow()
		playback_manager = PlaybackManager(app, main_window)
		detector = Detector(playback_manager)
		tracker = Tracker(detector)
		fish_manager = FishManager(playback_manager, tracker)
	
		save_manager = SaveManager(playback_manager, detector, tracker, fish_manager)
		save_manager.loadFile(path)

		main_window.show()
		sys.exit(app.exec_())

	#saveTest()
	loadTest()


