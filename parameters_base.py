from dataclasses import dataclass, fields, asdict
from enum import Enum, auto
from PyQt5 import QtCore
from log_object import LogObject

class ParametersBase(QtCore.QObject):
    """
    Base class for parameters that can be saved to and loaded from JSON.
    Wrapper for a dataclass Parameters, that should be implemented when inheriting this class.
    Examples of this can be found at the end of this file, as well as in mog_parameters and detector_parameters.
    """

    # Emitted when data values change.
    values_changed_signal = QtCore.pyqtSignal()

    # "Abstract class" / placeholder. Should inherit dataclass when implemented in an inheriting class.
    class Parameters:
        pass

    # "Abstract class" / placeholder. Should inherit Enum with items corresponding to fields defined in Parameters.
    class ParametersEnum:
        pass

    def __init__(self, data: Parameters):
        super().__init__()
        self.data = data
        self.emit_signal = True
        self.fields = { self.ParametersEnum[field.name]: field for field in fields(self.data) }

    def getParameterDict(self):
        """
        Returns the data as a dictionary.
        """
        return asdict(self.data)

    def setParameterDict(self, dictionary: dict):
        """
        Sets attributes of data based on a dictionary.
        Keys are expected to be the names of the fields in Parameters dataclass.
        Values are expected to match the types defined in Parameters dataclass.
        """
        emit_signal_temp = self.emit_signal
        self.emit_signal = False

        if type(dictionary) != dict:
            raise TypeError(f"Cannot set values of '{type(self).__name__}' from a '{type(dictionary).__name__}' object.")

        for key, value in dictionary.items():
            self.setKeyValuePair(key, value)

        self.emit_signal = emit_signal_temp
        self.onValuesChanged()

    def getParameter(self, key: ParametersEnum):
        return getattr(self.data, self.fields[key].name)

    def setParameter(self, key: ParametersEnum, value):
        self.setKeyValuePair(key, value)

    def setKeyValuePair(self, key, value):
        """
        Tries to set an attribute based on a key value pair.
        Key: str or ParametersEnum, name of the attribute.
        Value: New value of the attribute.
        """
        try:
            key = self.keyAsEnum(key)
        except KeyError as e:
            LogObject().print2(f"Error: Invalid key '{key}' in '{type(self).__name__}'")
            return False

        try:
            setattr(self.data, key.name, self.fields[key].type(value))
            self.onValuesChanged()
            return True
        except (ValueError, TypeError) as e:
            LogObject().print2(f"Error: Invalid value '{value}' for key '{key}' in '{type(self).__name__}',", e)
            return False

    def keyAsEnum(self, key):
        """
        Takes a key (string or enum) as an argument.
        Returns the corresponding enum if the key is valid, otherwise raises KeyError.
        """
        if type(key) == str:
            return self.ParametersEnum[key]

        if key in self.ParametersEnum._value2member_map_.values():
            return key
        else:
            raise KeyError(f"Invalid key '{key}' for '{type(self).__name__}'")

    def onValuesChanged(self):
        if self.emit_signal:
            self.values_changed_signal.emit()

    def copy(self):
        """
        Creates a new instance of the object with same parameter values.
        """
        params = [getattr(self.data, key.name) for key in self.ParametersEnum if hasattr(self.data, key.name)]
        return type(self)(*params)

    def __eq__(self, other):
        """
        Objects are equal if their data is equal.
        """
        if not isinstance(other, type(self)):
            return False
        else:
            return self.data == other.data

    def __repr__(self):
        fields = [f for f in self.fields.values()]
        repr = f"{type(self).__name__} ({fields[0].name}={getattr(self.data, fields[0].name)}"
        for i in range(1, len(fields)):
            repr += f", {fields[i].name}={getattr(self.data, fields[i].name)}"
        return repr + ")"


if __name__ == "__main__":
    class TestParameters(ParametersBase):

        @dataclass
        class Parameters:
            test_value: int = 1
            wrong_type: float = 1.5

        class ParametersEnum(Enum):
            test_value = auto()
            wrong_type = auto()

        def __init__(self, *args, **kwargs):
            """
            Parameters:
            test_value: int
            wrong_type: float
            """
            super().__init__(self.Parameters(*args, **kwargs))

    test = TestParameters()
    print(test)

    try:
        test.setParameterDict(None)
    except TypeError as e:
        print(e)

    dictionary = {
        "wrong_parameter" : 0,
        "wrong_type": test,
        "test_value": 5
        }
    test.setParameterDict(dictionary)

    print("")
    print(test)
    print(test.getParameterDict())
    print("")

    test2 = test.copy()
    assert test == test2, "Copied parameters are not equal"
    key = TestParameters.ParametersEnum.test_value
    test2.setKeyValuePair(key, 0)
    assert test != test2, "Modified parameters should not be equal"
