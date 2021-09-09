from PyQt5 import QtCore
from log_object import LogObject

class SerializableParameters(QtCore.QObject):

    values_changed_signal = QtCore.pyqtSignal()
    PARAMETER_TYPES = {}

    def __init__(self):
        super().__init__()

    def setParameterDict(self, dictionary):
        if type(dictionary) != dict:
            raise TypeError(f"Cannot set values of '{type(self).__name__}' from a '{type(dictionary).__name__}' object.")

        for key, value in dictionary.items():
            self.setKeyValuePair(key, value)


    def setKeyValuePair(self, key, value):
        if not hasattr(self, key):
            LogObject().print2(f"Error: Invalid parameters: {key}: {value}")
            return False

        if not key in self.PARAMETER_TYPES:
            LogObject().print2(f"Error: Key [{key}] not in PARAMETER_TYPES of '{type(self).__name__}'")
            return False

        try:
            setattr(self, key, self.PARAMETER_TYPES[key](value))
            return True
        except (ValueError, TypeError) as e:
            LogObject().print2(f"Error: Invalid value in '{type(self).__name__}' file,", e)
            return False



if __name__ == "__main__":
    from tracker import TrackerParameters

    class TestClass(SerializableParameters):

        PARAMETER_TYPES = { "test_value": int, "wrong_type": int }

        def __init__(self):
            super().__init__()
            self.test_value = 1
            self.without_type = 2
            self.wrong_type = 3

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
    print(test.test_value)
