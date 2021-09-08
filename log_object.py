import sys, io
from datetime import datetime
from PyQt5 import QtCore, QtGui, QtWidgets

class Singleton(type):
    """
    A meta class for singleton type objects.
    """
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
            #print(cls._instances[cls])
        return cls._instances[cls]

class LogSignal(QtCore.QObject):
    signal = QtCore.pyqtSignal(str, int, str)

        
class LogObject(metaclass=Singleton):
    """
    Logging object that is easily accessible.
    Functions/methods can be connected to receive everything printed with method print.
    By default, the standard print function is connected, but this can be removed
    by using disconnectDefault.
    """
    def __init__(self):
        self.log_signal = LogSignal()
        self.connect(print)

    def connect(self, receiver):
        self.log_signal.signal.connect(receiver)

    def disconnect(self, receiver):
        self.log_signal.signal.disconnect(receiver)

    def print_help(self, *args, **kwargs):
        try:
            with io.StringIO() as output:
                kwargs['end'] = ""
                kwargs['file'] = output
                print(*args, **kwargs)
                return output.getvalue(), True, str(datetime.now().time())

        except AttributeError as e:
            print("Potential misuse of LogObject. When calling print, remember to use LogObject() with parenthesis.", e)
            return "", False, ""

    def print(self, *args, **kwargs):
        """
        Default print (verbosity=0) that is always printed.
        """
        output, success, time_stamp = self.print_help(*args, **kwargs)
        if success:
            self.log_signal.signal.emit(output, 0, time_stamp)

    def print1(self, *args, **kwargs):
        """
        Print with verbosity=1. Printed only if verbosity is set to 1 or higher.
        Should include additional information for the user.
        """
        output, success, time_stamp = self.print_help(*args, **kwargs)
        if success:
            self.log_signal.signal.emit(output, 1, time_stamp)

    def print2(self, *args, **kwargs):
        """
        Print with verbosity=2. Printed only if verbosity is set to 2 or higher.
        Should include additional information for the developer.
        """
        output, success, time_stamp = self.print_help(*args, **kwargs)
        if success:
            self.log_signal.signal.emit(output, 2, time_stamp)
            
    def disconnectDefault(self):
        self.disconnect(print)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    f1 = lambda x: print("*** ", x, " ***")
    f2 = lambda x: print("--- ", x, " ---")

    LogObject().connect(f1)
    LogObject().connect(f2)
    LogObject().print("Print via singleton logger")

    print("")

    LogObject().disconnect(f1)
    LogObject().print("Another print")

    print("")

    log = LogObject()
    log.disconnectDefault()
    log.print("Third print")

    sys.exit(app.exec_())
