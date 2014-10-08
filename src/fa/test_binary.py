from PyQt4.QtCore import pyqtSlot
import pytest
import os
import pygit2
from PyQt4 import QtGui, QtCore
import binary
import sys

__author__ = 'Thygrrr'

@pytest.fixture(scope="module")
def application(request):
    request.app = QtGui.QApplication(sys.argv)
    request.app.setApplicationName("py.test QApplication for " + __name__)

    def finalize():
        request.app.quit()

    request.addfinalizer(finalize)
    return request.app


def test_copy_rename_copies_all_files(tmpdir, application):
    source_dir = tmpdir.mkdir("source")
    dest_dir = tmpdir.mkdir("dest")

    source_dir.join("a").write("a")
    source_dir.join("b").write("b")

    copy_table = {"a":None, "b":None}

    updater = binary.Updater(application)
    updater.copy_rename(copy_table, str(source_dir), str(dest_dir))
    assert dest_dir.join("a").exists() and dest_dir.join("b").exists()


def test_copy_rename_renames_files(tmpdir, application):
    source_dir = tmpdir.mkdir("source")
    dest_dir = tmpdir.mkdir("dest")

    source_dir.join("a").write("a")

    copy_table = {"a":"b"}

    updater = binary.Updater(application)
    updater.copy_rename(copy_table, str(source_dir), str(dest_dir))
    assert dest_dir.join("b").exists() and dest_dir.join("b").read() == "a"


def test_copy_rename_emits_progress_updates(tmpdir, application):

    class SignalReceiver(QtCore.QObject):

        def __init__(self, parent=None):
            QtCore.QObject.__init__(self, parent)
            self.values = []
            self.tiggered = False

        @pyqtSlot()
        def trigger(self):
            self.tiggered = True

        @pyqtSlot(int)
        def tick(self, value):
            self.values.append(value)

    receiver = SignalReceiver(application)

    source_dir = tmpdir.mkdir("source")
    dest_dir = tmpdir.mkdir("dest")

    source_dir.join("a").write("a")
    source_dir.join("b").write("b")

    copy_table = {"a":None, "b":None}

    updater = binary.Updater(application)
    updater.progress_value.connect(receiver.tick)
    updater.copy_rename(copy_table, str(source_dir), str(dest_dir))

    application.processEvents()
    assert receiver.values[0] == 1 and receiver.values[1] == 2 and len(receiver.values) == 2


def test_guess_install_guesses_steam_if_steam_api_exists(tmpdir):
    tmpdir.join("steam_api.dll").write("I'm steam!")
    assert binary.Updater.guess_install_type(str(tmpdir)) == 'steam'

def test_guess_install_guesses_retail_if_no_steam_api_exists(tmpdir):
    assert binary.Updater.guess_install_type(str(tmpdir)) == 'retail'

