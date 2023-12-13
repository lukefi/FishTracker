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

from enum import Enum, auto
from dataclasses import dataclass
from parameters_base import ParametersBase
from mog_parameters import MOGParameters

class DetectorParameters(ParametersBase):
	@dataclass
	class Parameters:
		detection_size: int = 10 # original default 10
		min_fg_pixels: int = 11 # original default 25
		median_size: int = 3 # original default 3
		dbscan_eps: int = 2 # original default 10
		dbscan_min_samples: int = 10 # original default 10

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
