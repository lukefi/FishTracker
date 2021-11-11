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
    "file type": "FishTracker"
    "version": "0.1",
    "path": "C:\Vetsjoki\Vetsi_2016-06-18_170000.aris",
    "inverted upstream": false,
    "detector": {
        "bg_subtractor": {
            "learning_rate": 0.01,
            "mixture_count": 5,
            "mog_var_thresh": 11,
            "nof_bg_frames": 100
        },
        "detector": {
            "detection_size": 10,
            "min_fg_pixels": 25,
            "median_size": 3,
            "dbscan_eps": 10,
            "dbscan_min_samples": 10
        }
    },
    "tracker": {
        "primary_tracking": {
            "max_age": 10,
            "min_hits": 5,
            "search_radius": 10,
            "trim_tails": true
        },
        "filtering": {
            "min_duration": 2,
            "mad_limit": 0
        },
        "secondary_tracking": {
            "max_age": 10,
            "min_hits": 5,
            "search_radius": 10,
            "trim_tails": true
        }
    },
    "detections":
    {
        frame_1: [[detection_label_0, [[x,y], [x,y], [x,y], [x,y]]]],
        frame_2: [[detection_label_1, [[x,y], [x,y]]], [detection_label_2, [[x,y], [x,y], [x,y]]]]
    },
    "fish":
    {
        track_id_1: [[frame_1, detection_label_0, [min_x, max_x, min_y, max_y]], [frame_2, detection_label_1, [min_x, max_x, min_y, max_y]]],
        track_id_2: [[frame_2, detection_label_2, [min_x, max_x, min_y, max_y]]]
    }
}
"""

class SaveManager(QtCore.QObject):

	file_loaded_event = QtCore.pyqtSignal()

	def __init__(self, playback_manager: PlaybackManager, detector: Detector, tracker: Tracker, fish_manager: FishManager):
		super().__init__()

		self.playback_manager = playback_manager
		self.detector = detector
		self.tracker = tracker
		self.fish_manager = fish_manager

		self.fast_save_enabled = False
		self.previous_path = None

		self.temp_data = None

		self.playback_manager.file_closed.connect(self.onFileClosed)

	def saveFile(self, path: str, binary: bool):
		"""
		Saves the contents of detector and tracker and the corresponding parameters to file.
		"""

		LogObject().print1(f"Saving data to '{path}'")

		self.previous_path = path
		self.fast_save_enabled = True

		dp_dict = self.detector.getParameterDict()

		tp = self.tracker.getAllParameters()
		tp_dict = None if tp is None else tp.getParameterDict()

		detections = self.detector.getSaveDictionary()
		fish = self.fish_manager.getSaveDictionary()

		data = { "file type": "FishTracker", "version": "0.1" }
		data["path"] = os.path.abspath(self.playback_manager.path)
		data["inverted upstream"] = self.fish_manager.up_down_inverted
		data["detector"] = dp_dict
		data["tracker"] = tp_dict
		data["detections"] = detections
		data["fish"] = fish
		self.saveData(path, data, binary)

	def saveData(self, path: str, data: dict, binary: bool, update_dict: bool = True):
		"""
		Write the data (dictionary) to a file.
		"""
		if binary:
			packed = msgpack.packb(data)
			with open(path, "wb") as data_file:
				data_file.write(packed)
		else:
			with open(path, "w") as data_file:
				json.dump(data, data_file, indent=2, separators=(',', ': '))

		fh.setLatestSaveDirectory(os.path.dirname(path))

	def loadFile(self, path: str):
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

	def loadData(self, data: dict, path: str):
		try:
			file_path = os.path.abspath(data["path"])
			secondary_path = os.path.abspath(os.path.join(os.path.dirname(path), os.path.basename(file_path)))
			self.temp_data = data

			if self.playback_manager.checkLoadedFile(file_path, secondary_path, True):
				# If file already open
				self.setLoadedData()
			else:
				self.playback_manager.polars_loaded.connect(self.setLoadedData)

		except ValueError as e:
			LogObject().print("Error: Invalid value(s) in save file,", e)
			self.playback_manager.closeFile()
		except KeyError as e:
			LogObject().print("Error: Invalid key(s) in save file,", e)
			self.playback_manager.closeFile()


	def setLoadedData(self):
		try:
			self.fish_manager.setUpDownInversion(self.temp_data["inverted upstream"])

			self.tracker.setAllParametersFromDict(self.temp_data["tracker"])

			self.detector.applySaveDictionary(self.temp_data["detector"], self.temp_data["detections"])

			dets = self.detector.detections
			self.fish_manager.applySaveDictionary(self.temp_data["fish"], dets)

		except ValueError as e:
			self.playback_manager.closeFile()
			LogObject().print("Error: Invalid value(s) in save file,", e)
		except KeyError as e:
			self.playback_manager.closeFile()
			LogObject().print("Error: Key not found in save file,", e)
		finally:
			self.temp_data = None
			try:
				self.playback_manager.polars_loaded.disconnect(self.setLoadedData)
			except TypeError:
				pass

	def onFileClosed(self):
		self.previous_path = None
		self.fast_save_enabled = False
		try:
			self.playback_manager.polars_loaded.disconnect(self.setLoadedData)
		except TypeError:
			pass


if __name__ == "__main__":
	path = "D:/Projects/VTT/FishTracking/save_test.fish"

	def saveTest():
		def startDetector():
			detector.initMOG()
			detector.computeAll()
			tracker.primaryTrack()

		app = QtWidgets.QApplication(sys.argv)
		main_window = QtWidgets.QMainWindow()
		playback_manager = PlaybackManager(app, main_window)
		detector = Detector(playback_manager)
		tracker = Tracker(detector)
		fish_manager = FishManager(playback_manager, tracker)
	
	
		save_manager = SaveManager(playback_manager, detector, tracker, fish_manager)

		fish_manager.updateContentsSignal.connect(lambda: save_manager.saveFile(path, True))

		playback_manager.openTestFile()
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


