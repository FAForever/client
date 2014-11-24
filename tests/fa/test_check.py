__author__ = 'Sheeo'

from fa import check
from fa.mod import Mod
from fa.game_version import GameVersion
from git.version import Version
from PyQt4.QtGui import qApp
from PyQt4.QtNetwork import QNetworkAccessManager

from flexmock import flexmock

import fa.check


# TODO:
#  - test check.game
#  - test check.main_mod
#  - test check.mods
#  - test check.map

repo_mock = flexmock(checkout_version=lambda v: True)
fa.check.Repository = repo_mock

version_service = flexmock()
TEST_GAME_VERSION = Version('FAForever/fa', '3634', None, '791035045345a4c597a92ea0ef50d71fcccb0bb1')
TEST_SIM_MOD = Mod("test-mod", "test-path", Version('FAForever/test_sim_mod', 'some-branch', None, 'some-hash'))
VALID_BINARY_PATCH = Version('FAForever/binary-patch', 'master', None, 'a41659780460fd8829fce87b479beaa8ac78e474')

TEST_VERSION = GameVersion.from_dict({
    "engine": VALID_BINARY_PATCH,
    "main_mod": Mod("faf", "test-path", TEST_GAME_VERSION),
    "mods": [TEST_SIM_MOD],
    "map": {"name": "scmp_0009", "version": "builtin"}
})


fa.check.ENGINE_PATH = "repo/binary-patch"


def test_check_game_checks_engine_version(qtbot):
    repo_mock.should_receive('has_version').with_args(TEST_VERSION.main_mod.version).and_return(True)
    repo_mock.should_receive('has_version').with_args(TEST_VERSION.engine).and_return(True)
    check.game(qApp, TEST_VERSION)


def test_check_game_checks_out_engine_version(qtbot):
    repo_mock.should_receive('has_version').with_args(TEST_VERSION.main_mod.version).and_return(True)
    repo_mock.should_receive('has_version').with_args(TEST_VERSION.engine).and_return(True)

    repo_mock.should_receive('checkout_version').with_args(TEST_VERSION.main_mod.version)
    repo_mock.should_receive('checkout_version').with_args(TEST_VERSION.engine)
    check.game(qApp, TEST_VERSION)
