__author__ = 'Thygrrr'

import pytest
import maps
from PyQt4 import QtGui, QtNetwork, QtCore

TESTMAP_NAME = "faf_test_map"

def test_downloader_has_slot_abort(application):
    assert callable(maps.Downloader(TESTMAP_NAME, parent=application).abort)

