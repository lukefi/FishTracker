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

class FilterParameters(ParametersBase):
    @dataclass
    class Parameters:
        min_duration: int = 2
        mad_limit: int = 0

    class ParametersEnum(Enum):
        min_duration = auto()
        mad_limit = auto()

    def __init__(self, *args, **kwargs):
        """
        Parameters:
        min_duration: int = 2
        mad_limit: int = 0
        """
        super().__init__(self.Parameters(*args, **kwargs))