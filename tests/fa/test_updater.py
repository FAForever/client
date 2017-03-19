__author__ = 'Thygrrr'

from fa import updater
from PyQt5 import QtWidgets, QtCore
import pytest
import collections

class NoIsFinished(QtCore.QObject):
    finished = QtCore.pyqtSignal()


class NoOpThread(QtCore.QThread):
    def run(self):
        self.yieldCurrentThread()


def test_updater_is_a_dialog(application):
    assert isinstance(updater.UpdaterProgressDialog(None), QtWidgets.QDialog)


def test_updater_has_progress_bar_game_progress(application):
    assert isinstance(updater.UpdaterProgressDialog(None).gameProgress, QtWidgets.QProgressBar)


def test_updater_has_progress_bar_map_progress(application):
    assert isinstance(updater.UpdaterProgressDialog(None).mapProgress, QtWidgets.QProgressBar)


def test_updater_has_progress_bar_mod_progress(application):
    assert isinstance(updater.UpdaterProgressDialog(None).mapProgress, QtWidgets.QProgressBar)


def test_updater_has_method_append_log(application):
    assert isinstance(updater.UpdaterProgressDialog(None).appendLog, collections.Callable)


def test_updater_append_log_accepts_string(application):
    updater.UpdaterProgressDialog(None).appendLog("Hello Test")


def test_updater_has_method_add_watch(application):
    assert isinstance(updater.UpdaterProgressDialog(None).addWatch, collections.Callable)


def test_updater_append_log_accepts_qobject_with_signals_finished(application):
    updater.UpdaterProgressDialog(None).addWatch(QtCore.QThread())


def test_updater_add_watch_raises_error_on_watch_without_signal_finished(application):
    with pytest.raises(AttributeError):
        updater.UpdaterProgressDialog(None).addWatch(QtCore.QObject())


def test_updater_watch_finished_raises_error_on_watch_without_method_is_finished(application):
    u = updater.UpdaterProgressDialog(None)
    u.addWatch(NoIsFinished())
    with pytest.raises(AttributeError):
        u.watchFinished()


def test_updater_hides_and_accepts_if_all_watches_are_finished(application):
    u = updater.UpdaterProgressDialog(None)
    t = NoOpThread()

    u.addWatch(t)
    u.show()
    t.start()

    while not t.isFinished():
        pass

    application.processEvents()
    assert not u.isVisible()
    assert u.result() == QtWidgets.QDialog.Accepted


def test_updater_does_not_hide_and_accept_before_all_watches_are_finished(application):
    u = updater.UpdaterProgressDialog(None)
    t = NoOpThread()
    t_not_finished = QtCore.QThread()

    u.addWatch(t)
    u.addWatch(t_not_finished)
    u.show()
    t.start()

    while not t.isFinished():
        pass

    application.processEvents()
    assert u.isVisible()
    assert not u.result() == QtWidgets.QDialog.Accepted

