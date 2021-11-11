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

class MOGParameters(ParametersBase):
    @dataclass
    class Parameters:
        learning_rate: float = 0.01
        mixture_count: int = 5
        mog_var_thresh: int = 11
        nof_bg_frames: int = 100

    class ParametersEnum(Enum):
        learning_rate = auto()
        mixture_count = auto()
        mog_var_thresh = auto()
        nof_bg_frames = auto()

    def __init__(self, *args, **kwargs):
        """
        Parameters:
        learning_rate: float = 0.01
        mixture_count: int = 5
        mog_var_thresh: int = 11
        nof_bg_frames: int = 100
        """
        super().__init__(self.Parameters(*args, **kwargs))
