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
        with io.StringIO() as output:
            kwargs['end'] = ""
            kwargs['file'] = output
            print(*args, **kwargs)
            return output.getvalue(), str(datetime.now().time())

    def exception_handler(func):
        def inner_function(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except AttributeError as e:
                print("Potential misuse of LogObject. When calling print, remember to use LogObject() with parenthesis.", e)
        return inner_function

    @exception_handler
    def print(self, *args, **kwargs):
        """
        Default print (verbosity=0) that is always printed.
        """
        output, time_stamp = self.print_help(*args, **kwargs)
        self.log_signal.signal.emit(output, 0, time_stamp)            

    @exception_handler
    def print1(self, *args, **kwargs):
        """
        Print with verbosity=1. Printed only if verbosity is set to 1 or higher.
        Should include additional information for the user.
        """
        output, time_stamp = self.print_help(*args, **kwargs)
        self.log_signal.signal.emit(output, 1, time_stamp)

    @exception_handler
    def print2(self, *args, **kwargs):
        """
        Print with verbosity=2. Printed only if verbosity is set to 2 or higher.
        Should include additional information for the developer.
        """
        output, time_stamp = self.print_help(*args, **kwargs)
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

    print("")
    LogObject.print("Invalid print")

    sys.exit(app.exec_())
