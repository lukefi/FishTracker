from PyQt5 import QtCore
from log_object import LogObject
from enum import Enum, auto

class SerializableParameters(QtCore.QObject):

    values_changed_signal = QtCore.pyqtSignal()

    class Parameters(Enum):
        pass

    PARAMETER_TYPES = {}

    def __init__(self):
        self.emit_signal = True
        super().__init__()

    def setParameterDict(self, dictionary):
        emit_signal_temp = self.emit_signal
        self.emit_signal = False

        if type(dictionary) != dict:
            raise TypeError(f"Cannot set values of '{type(self).__name__}' from a '{type(dictionary).__name__}' object.")

        for key, value in dictionary.items():
            self.setKeyValuePair(key, value)

        self.emit_signal = emit_signal_temp
        self.values_changed_signal.emit()
    
    def getParameterDict(self):
        d = dict()
        for key in self.Parameters:
            if hasattr(self, key.name):
                d[key] = getattr(self, key.name)

        return d

    def checkKey(self, key):
        if type(key) == str:
            try:
                key = self.Parameters[key]
                return key
            except KeyError as e:
                return None

        if hasattr(self, key.name):
            return key
        else:
            return None

    def setKeyValuePair(self, key, value):
        key = self.checkKey(key)
        if key is None:
            LogObject().print2(f"Error: Invalid parameters: {key}: {value}")
            return False

        if not key in self.PARAMETER_TYPES:
            LogObject().print2(f"Error: Key [{key}] not in PARAMETER_TYPES of '{type(self).__name__}'")
            return False

        try:
            setattr(self, key.name, self.PARAMETER_TYPES[key](value))
            self.onValuesChanged()
            return True
        except (ValueError, TypeError) as e:
            LogObject().print2(f"Error: Invalid value in '{type(self).__name__}' file,", e)
            return False

    def onValuesChanged(self):
        if self.emit_signal:
            self.values_changed_signal.emit()

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False

        for key in self.Parameters:
            if hasattr(self, key.name):
                if getattr(self, key.name) != getattr(other, key.name):
                    return False

        return True

    def __repr__(self):
        return "{}: {}".format(type(self).__name__, self.getParameterDict())

    def copy(self):
        """
        Creates a new instance of the object with same parameter values.
        """
        return type(self)(*[getattr(self, key.name) for key in self.Parameters if hasattr(self, key.name)])



if __name__ == "__main__":
    from tracker import TrackerParameters

    class TestClass(SerializableParameters):

        class Parameters(Enum):
            test_value = auto()
            without_type = auto()
            wrong_type = auto()

        PARAMETER_TYPES = {
            Parameters.test_value: int,
            Parameters.wrong_type: int
            }

        def __init__(self, test_value=1, without_type=2, wrong_type=3):
            super().__init__()
            self.test_value = test_value
            self.without_type = without_type
            self.wrong_type = wrong_type

    test = TestClass()
    print(test.PARAMETER_TYPES)

    try:
        test.setParameterDict(None)
    except TypeError as e:
        print(e)

    dictionary = {
        "wrong_parameter" : 0,
        "without_type": 0,
        "wrong_type": test,
        "test_value": 5
        }
    test.setParameterDict(dictionary)
    print(test)

    test2 = test.copy()
    print(test == test2)
    test2.setKeyValuePair(TestClass.Parameters.test_value, 0)
    print(test == test2)

