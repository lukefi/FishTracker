from enum import Enum, auto
from dataclasses import dataclass
from parameters_base import ParametersBase
from mog_parameters import MOGParameters

class DetectorParameters(ParametersBase):
	@dataclass
	class Parameters:
		detection_size: int = 10
		min_fg_pixels: int = 25
		median_size: int = 3
		dbscan_eps: int = 10
		dbscan_min_samples: int = 10

	class ParametersEnum(Enum):
		detection_size = auto()
		min_fg_pixels = auto()
		median_size = auto()
		dbscan_eps = auto()
		dbscan_min_samples = auto()

	def __init__(self, *args, **kwargs):
		"""
		Parameters:
		detection_size: int = 10
		min_fg_pixels: int = 25
		median_size: int = 3
		dbscan_eps: int = 10
		dbscan_min_samples: int = 10
		"""
		super().__init__(self.Parameters(*args, **kwargs))
