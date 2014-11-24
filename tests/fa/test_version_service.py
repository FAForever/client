
from fa.version_service import VersionService
from fa.game_version import GameVersion

from PyQt4.QtGui import qApp
from PyQt4.QtCore import QCoreApplication, QEventLoop
from PyQt4.QtNetwork import QNetworkAccessManager

__author__ = 'Sheeo'


# TODO:
# Have an underlying mock

# def test_returns_default_version_for_faf(qapp, qtbot):
#     def success(result):
#         assert GameVersion(result).is_valid
#
#     def error(err):
#         assert err is False
#
#     version_service = VersionService(QNetworkAccessManager())
#
#     res = version_service.default_version_for("faf")
#     res.done.connect(success)
#     res.error.connect(error)
#
#     qtbot.waitSignal(res.done)
#


