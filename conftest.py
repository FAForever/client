__author__ = 'Thygrrr'

import sip

sip.setapi('QString', 2)
sip.setapi('QVariant', 2)
sip.setapi('QStringList', 2)
sip.setapi('QList', 2)
sip.setapi('QProcess', 2)

import pytest
import sys
from PyQt4 import QtGui, QtCore


@pytest.fixture(scope="module")
def application(request):
    request.app = QtGui.QApplication(sys.argv)
    request.app.setApplicationName("py.test QApplication")

    def finalize():
        request.app.quit()

    request.addfinalizer(finalize)
    return request.app


@pytest.fixture(scope="function")
def signal_receiver(application):
    class SignalReceiver(QtCore.QObject):
        def __init__(self, parent=None):
            QtCore.QObject.__init__(self, parent)
            self.int_values = []
            self.generic_values = []

        @QtCore.pyqtSlot()
        def generic_slot(self):
            self.generic_values.append(None)

        @QtCore.pyqtSlot(int)
        def int_slot(self, value):
            self.int_values.append(value)

    return SignalReceiver(application)
