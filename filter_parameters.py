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