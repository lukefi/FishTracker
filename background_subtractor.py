import numpy as np
import cv2
from math import floor
from log_object import LogObject
from PyQt5 import QtCore

class BackgroundSubtractor(QtCore.QObject):
    """
    Implements background subtraction for Detector / SonarView and Echogram.
    """

    # When mog parameters change.
    state_changed_signal = QtCore.pyqtSignal()

    def __init__(self, image_provider):
        super().__init__()

        self.image_provider = image_provider
        self.image_height = 0
        self.image_width = 0

        self.fgbg_mog = None
        self.fgbg_mog_debug_initialized_once = False

        # [trigger] Terminate initializing process.
        self.stop_initializing = False

        # [flag] Whether MOG is initializing
        self.initializing = False

        # [flag] Whether MOG has been initialized
        self.mog_ready = False

        self.applied_mog_parameters = None
        self.resetParameters()

    def resetParameters(self):
        self.mog_parameters = MOGParameters()

    def initMOG(self):
        LogObject().print("Init mog")
        if hasattr(self.image_provider, "pausePolarLoading"):
            self.image_provider.pausePolarLoading(True)

        self.mog_ready = False
        self.initializing = True
        self.stop_initializing = False
        self.compute_on_event = True
        self.state_changed_signal.emit()

        self.fgbg_mog = cv2.createBackgroundSubtractorMOG2()
        self.fgbg_mog.setNMixtures(5)
        self.fgbg_mog.setVarThreshold(self.mog_parameters.mog_var_thresh)
        self.fgbg_mog.setShadowValue(0)

        self.fgbg_mog_debug_initialized_once = True

        nof_frames = self.image_provider.getFrameCount()
        nof_bg_frames = min(nof_frames, self.mog_parameters.nof_bg_frames)

        # Create background model from fixed number of frames.
        # Count step based on number of frames
        step = nof_frames / nof_bg_frames

        ten_perc = 0.1 * nof_bg_frames
        print_limit = 0

        for i in range(nof_bg_frames):
            if i > print_limit:
                LogObject().print("Initializing:", int(float(print_limit) / nof_bg_frames * 100), "%")
                print_limit += ten_perc

            ind = floor(i * step)
            
            if self.stop_initializing:
                LogObject().print("Stopped initializing at", ind)
                self.stop_initializing = False
                self.mog_ready = False
                self.initializing = False
                self.applied_mog_parameters = None
                self.state_changed_signal.emit()
                return

            image_o = self.image_provider.getFrame(ind)
            self.fgbg_mog.apply(image_o, learningRate=self.mog_parameters.learning_rate)

        self.image_height = image_o.shape[0]
        self.image_width = image_o.shape[1]

        self.mog_ready = True
        self.initializing = False;
        self.applied_mog_parameters = self.mog_parameters.copy()

        self.state_changed_signal.emit()
        LogObject().print("Initializing: 100 %")

        if hasattr(self.image_provider, "pausePolarLoading"):
            self.image_provider.pausePolarLoading(False)

        if hasattr(self.image_provider, "refreshFrame"):
            self.image_provider.refreshFrame()

    def subtractBG(self, image):
		# Get foreground mask, without updating the  model (learningRate = 0)
        try:
            fg_mask_mog = self.fgbg_mog.apply(image, learningRate=0)
            return fg_mask_mog

        except AttributeError as e:
            LogObject().print(e, "\nDebug  (FGBG mog initialized):", self.fgbg_mog_debug_initialized_once)
            print(e, "\nDebug (FGBG mog initialized):", self.fgbg_mog_debug_initialized_once)
            return None

    def setParameters(self, parameters):
        self.mog_parameters = parameters
        self.applied_mog_parameters = self.mog_parameters.copy()

    def parametersDirty(self):
        return self.mog_parameters != self.applied_mog_parameters

    def abortComputing(self):
        self.applied_mog_parameters = None

class MOGParameters:
	def __init__(self, mog_var_thresh=11, nof_bg_frames=1000, learning_rate=0.01,):
		self.mog_var_thresh = mog_var_thresh
		self.nof_bg_frames = nof_bg_frames
		self.learning_rate = learning_rate

	def __eq__(self, other):
		if not isinstance(other, MOGParameters):
			return False

		return self.mog_var_thresh == other.mog_var_thresh \
			and self.nof_bg_frames == other.nof_bg_frames \
			and self.learning_rate == other.learning_rate

	def __repr__(self):
		return "MOG Parameters: {} {} {}".format(self.mog_var_thresh, self.nof_bg_frames, self.learning_rate)

	def copy(self):
		return MOGParameters( self.mog_var_thresh, self.nof_bg_frames, self.learning_rate )