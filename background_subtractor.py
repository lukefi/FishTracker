import numpy as np
import cv2
from math import floor
from PyQt5 import QtCore

from log_object import LogObject
from serializable_parameters import SerializableParameters

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
        if hasattr(self.image_provider, "pausePolarLoading"):
            self.image_provider.pausePolarLoading(True)

        self.mog_ready = False
        self.initializing = True
        self.stop_initializing = False
        self.compute_on_event = True
        self.state_changed_signal.emit()

        self.fgbg_mog = cv2.createBackgroundSubtractorMOG2()
        self.fgbg_mog.setNMixtures(self.mog_parameters.mixture_count)
        self.fgbg_mog.setVarThreshold(self.mog_parameters.mog_var_thresh)
        self.fgbg_mog.setShadowValue(0)

        self.fgbg_mog_debug_initialized_once = True

        nof_frames = self.image_provider.getFrameCount()
        nof_bg_frames = min(nof_frames, self.mog_parameters.nof_bg_frames)

        # Create background model from fixed number of frames.
        # Count step based on number of frames
        step = nof_frames / nof_bg_frames

        for i in range(nof_bg_frames):
            ind = floor(i * step)
            
            if self.stop_initializing:
                LogObject().print2("Stopped initializing (BG subtraction) at", ind)
                self.stop_initializing = False
                self.mog_ready = False
                self.initializing = False
                self.applied_mog_parameters = None
                self.state_changed_signal.emit()
                return

            image_o = self.image_provider.getFrame(ind)
            self.fgbg_mog.apply(image_o, learningRate=self.mog_parameters.learning_rate)

        self.image_height = image_o.shape[0]
        try:
            self.image_width = image_o.shape[1]
        except IndexError:
            self.image_width = 1

        self.mog_ready = True
        self.initializing = False;
        self.applied_mog_parameters = self.mog_parameters.copy()

        self.state_changed_signal.emit()
        LogObject().print2("BG Subtractor Initialized")

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
            LogObject().print2(e, "\nDebug  (FGBG mog initialized):", self.fgbg_mog_debug_initialized_once)
            print(e, "\nDebug (FGBG mog initialized):", self.fgbg_mog_debug_initialized_once)
            return None

    def subtractBGFiltered(self, image, median_size):
        fg_mask_mog = self.fgbg_mog.apply(image, learningRate=0)
        fg_mask_filt = cv2.medianBlur(fg_mask_mog, median_size)
        return fg_mask_filt

    def setParameters(self, parameters):
        self.mog_parameters = parameters
        self.applied_mog_parameters = self.mog_parameters.copy()

    def parametersDirty(self):
        return self.mog_parameters != self.applied_mog_parameters

    def abortComputing(self):
        self.applied_mog_parameters = None

class MOGParameters(SerializableParameters):

    PARAMETER_TYPES = {
        "mog_var_thresh": int,
        "nof_bg_frames": int,
        "learning_rate": float
        }

    def __init__(self, mog_var_thresh=11, nof_bg_frames=100, learning_rate=0.01):
        super().__init__()

        self.mog_var_thresh = mog_var_thresh
        self.nof_bg_frames = nof_bg_frames
        self.learning_rate = learning_rate
        self.mixture_count = 5

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

    def getParameterDict(self):
        return {
	        "mog_var_thresh": self.mog_var_thresh,
	        "nof_bg_frames": self.nof_bg_frames,
	        "learning_rate": self.learning_rate
        }