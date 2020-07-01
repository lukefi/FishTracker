import sys, os, time, cv2
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from random import uniform

from file_handler import FOpenSonarFile

FRAME_COUNT = 100
BUFFER_SIZE = 5

class PlaybackThread(QRunnable):
	def __init__(self, threadpool, figure):
		super().__init__()
		self.run = True
		self.first_ind = 0
		self.previous = time.time()
		self.next_frame = 0
		self.frame_count = 0
		self.new_frames = []
		self.threadpool = threadpool
		self.figure = figure

		self.sonar = self.openTestFile()
		self.buffer = [None] * FRAME_COUNT
		prev = None
		for i in range(FRAME_COUNT):
			wrap = FrameWrapper(i, prev)
			self.buffer[i] = wrap
			prev = wrap

		for i in range(FRAME_COUNT):
			frame = FrameDisplayThread(self.sonar, i)
			frame.signals.frame_signal.connect(self.frameReady)
			self.threadpool.start(frame)
			
		
	def run(self):
		while(self.run):
			if len(self.new_frames) > 0:
				for frame_tuple in self.new_frames:
					ind, frame = frame_tuple
					frame = frame
					self.buffer[ind].frame = frame
				self.new_frames.clear()
			
			try:
				wrap = self.buffer[self.next_frame]
				if wrap.frame is not None:			
					print("Frame:", wrap.ind, (time.time() - self.previous))
					self.previous = time.time()
					self.next_frame += 1
					self.frame_count += 1
					self.displayFrame(wrap.frame)
					
					while self.frame_count > BUFFER_SIZE:
						self.remove_first()		
			except IndexError as e:
				print(e)
				self.run = False
				self.printAll()
				print(self.buffer)

			time.sleep(0.1)
			
	def frameReady(self, frame_tuple):
		print("Ready:", frame_tuple[0])
		self.new_frames.append(frame_tuple)
		
	def remove_first(self):
		print("Removed:", self.first_ind)
		new_first = self.buffer[self.first_ind].next.ind
		self.buffer[self.first_ind].frame = None
		self.first_ind = new_first
		self.frame_count -= 1
		
	def printAll(self):
		wrap = self.buffer[self.first_ind]
		while wrap:
			print(wrap)
			wrap = wrap.next

	def getFilePath(self):
		homeDirectory = str(os.path.expanduser("~"))
		filePathTuple = QFileDialog.getOpenFileName(self.main_window,
                                                    "Open File",
                                                    homeDirectory,
                                                    "Sonar Files (*.aris *.ddf)")
		if filePathTuple[0] != "" : 
			# if the user has actually chosen a specific file.
			return filePathTuple[0]

	def openTestFile(self):
		path = "D:/Projects/VTT/FishTracking/Teno1_2019-07-02_153000.aris"
		if not os.path.exists(path):
			path = "C:/data/LUKE/Teno1_2019-07-02_153000.aris"
		if not os.path.exists(path):
			path = self.getFilePath()
		return FOpenSonarFile(path)

	def displayFrame(self, frame):        
		self.figure.setUpdatesEnabled(False)
		self.figure.clear()
		qformat = QImage.Format_Indexed8
		if len(frame.shape)==3:
			if frame.shape[2]==4:
				qformat = QImage.Format_RGBA8888
			else:
				qformat = QImage.Format_RGB888

		img = QImage(frame, frame.shape[1], frame.shape[0], frame.strides[0], qformat).rgbSwapped()
		figurePixmap = QPixmap.fromImage(img)
		self.figure.setPixmap(figurePixmap.scaled(self.figure.size(), Qt.KeepAspectRatio))
		self.figure.setAlignment(Qt.AlignCenter)
		self.figure.setUpdatesEnabled(True)

			
class FrameDisplayThread(QRunnable):
	def __init__(self, sonar, ind):
		super().__init__()
		self.signals = FDSignals()
		self.ind = ind
		self.sonar = sonar
		self.polar = sonar.getPolarFrame(ind)
		
	def run(self):
		frame = self.sonar.constructImages(self.polar)
		self.signals.frame_signal.emit((self.ind, frame))
		
class FDSignals(QObject):
	frame_signal = pyqtSignal(tuple)
	
class FrameWrapper:
	def __init__(self, ind, previous):
		self.ind = ind
		self.next = None
		self.frame = None
		
		if previous:
			previous.next = self
	
	def __repr__(self):
		if self.frame is not None:
			return "FW " + str(self.ind)
		else:
			return "Empty"

class TestFigure(QLabel):

	def __init__(self):
		super().__init__()
		self.figurePixmap = None

	def resizeEvent(self, event):
		if isinstance(self.figurePixmap, QPixmap):
			self.setPixmap(self.figurePixmap.scaled(self.size(), Qt.KeepAspectRatio))


if __name__ == "__main__":
	app = QApplication(sys.argv)
	main_window = QMainWindow()
	figure = TestFigure()
	main_window.setCentralWidget(figure)

	threadpool = QThreadPool()
	thread = PlaybackThread(threadpool, figure)
	threadpool.start(thread)
	
	main_window.show()
	sys.exit(app.exec_())