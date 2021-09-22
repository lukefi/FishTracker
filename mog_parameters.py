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
