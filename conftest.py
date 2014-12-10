__author__ = 'Thygrrr'

import sip

sip.setapi('QString', 2)
sip.setapi('QVariant', 2)
sip.setapi('QStringList', 2)
sip.setapi('QList', 2)
sip.setapi('QProcess', 2)

import sys

sys.path.insert(0, "lib")
sys.path.insert(0, "lib/pygit2")

import pytest

from PyQt4 import QtGui, QtCore

@pytest.fixture(scope="function")
def application(qtbot, request):
    return QtGui.qApp

@pytest.fixture(scope="function")
def signal_receiver(application):
    class SignalReceiver(QtCore.QObject):
        def __init__(self, parent=None):
            QtCore.QObject.__init__(self, parent)
            self.int_values = []
            self.generic_values = []
            self.string_values = []

        @QtCore.pyqtSlot()
        def generic_slot(self):
            self.generic_values.append(None)

        @QtCore.pyqtSlot(str)
        def string_slot(self, value):
            self.string_values.append(value)

        @QtCore.pyqtSlot(int)
        def int_slot(self, value):
            self.int_values.append(value)

    return SignalReceiver(application)
