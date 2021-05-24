import sys, io
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
    signal = QtCore.pyqtSignal(str)

        
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

    def print(self, *args,**kwargs):
        with io.StringIO() as output:
            kwargs['end'] = ""
            kwargs['file'] = output
            print(*args, **kwargs)
            self.log_signal.signal.emit(output.getvalue())

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
