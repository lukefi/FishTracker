from enum import Enum, auto
from dataclasses import dataclass
from parameters_base import ParametersBase

class TrackerParameters(ParametersBase):
    @dataclass
    class Parameters:
        max_age: int = 10
        min_hits: int = 5
        search_radius: int = 10
        trim_tails: bool = True

    class ParametersEnum(Enum):
        max_age = auto()
        min_hits = auto()
        search_radius = auto()
        trim_tails = auto()

    def __init__(self, *args, **kwargs):
        """
        Parameters:
        max_age: int = 10
        min_hits: int = 5
        search_radius: int = 10
        trim_tails: bool = True
        """
        super().__init__(self.Parameters(*args, **kwargs))
