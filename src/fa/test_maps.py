__author__ = 'Thygrrr'

import pytest
import maps
from PyQt4 import QtGui, QtNetwork, QtCore


def test_downloader_has_signal_finished(application):
    assert type(maps.Downloader(None, application).finished) == QtCore.pyqtBoundSignal


def test_downloader_has_signal_failed(application):
    assert type(maps.Downloader(None, application).failed) == QtCore.pyqtBoundSignal


def test_downloader_has_signal_progress_reset(application):
    assert type(maps.Downloader(None, application).progress_reset) == QtCore.pyqtBoundSignal


def test_downloader_has_signal_progress_value(application):
    assert type(maps.Downloader(None, application).progress_value) == QtCore.pyqtBoundSignal


def test_downloader_has_signal_progress_maximum(application):
    assert type(maps.Downloader(None, application).progress_maximum) == QtCore.pyqtBoundSignal


def test_downloader_has_slot_abort(application):
    assert callable(maps.Downloader(None, application).abort)

