__author__ = 'Sheeo'

from fa import check, path

from fa.mod import Mod
from fa.game_version import GameVersion
from git.version import Version
from PyQt4.QtGui import qApp
from PyQt4.QtNetwork import QNetworkAccessManager

from flexmock import flexmock

import os


# TODO:
#  - test check.game
#  - test check.main_mod
#  - test check.mods
#  - test check.map


TEST_GAME_VERSION = Version('FAForever/fa', '3634', None, '791035045345a4c597a92ea0ef50d71fcccb0bb1')
TEST_SIM_MOD = Mod("test-mod", 'tests/data/test-mod', Version('FAForever/test_sim_mod', 'some-branch', None, 'some-hash'))

TEST_ENGINE_VERSION = Version('FAForever/binary-patch', 'master', None, 'a41659780460fd8829fce87b479beaa8ac78e474')
TEST_MAIN_MOD = Mod("Forged Alliance Forever", "faf", TEST_GAME_VERSION)


repo_mock = flexmock(checkout_version=lambda v: True)
updater_mock = flexmock(check_up_to_date=lambda p: True)
version_mock = flexmock(is_stable=lambda: True,
                        is_trusted=lambda: True,
                        engine_repo=repo_mock,
                        engine=TEST_ENGINE_VERSION,
                        main_mod=TEST_MAIN_MOD,
                        main_mod_repo=repo_mock)


def test_check_game_checks_engine_version(qtbot, monkeypatch):
    monkeypatch.setattr('fa.check.Repository', lambda p: repo_mock)
    monkeypatch.setattr('fa.check.Updater', lambda r, p: updater_mock)
    repo_mock.should_receive('has_version').with_args(TEST_ENGINE_VERSION).and_return(True).once()
    repo_mock.should_receive('has_version').with_args(TEST_MAIN_MOD.version).and_return(True).once()
    check.game(qApp, version_mock)


def test_check_game_checks_out_engine_version(qtbot, monkeypatch):
    monkeypatch.setattr('fa.check.Repository', lambda p: repo_mock)
    monkeypatch.setattr('fa.check.Updater', lambda r, p: updater_mock)

    repo_mock.should_receive('has_version').with_args(TEST_ENGINE_VERSION).and_return(True).once()
    repo_mock.should_receive('has_version').with_args(TEST_MAIN_MOD.version).and_return(True).once()

    repo_mock.should_receive('checkout_version').with_args(TEST_ENGINE_VERSION).once()
    repo_mock.should_receive('checkout_version').with_args(TEST_MAIN_MOD.version).once()

    check.game(qApp, version_mock)
