import logging
from enum import Enum

from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices

logger = logging.getLogger(__name__)


class BanPeriod(Enum):
    HOUR = 'HOUR'
    DAY = 'DAY'
    WEEK = 'WEEK'
    MONTH = 'MONTH'
    YEAR = 'YEAR'


class PowerActions:
    def __init__(self, lobby_connection, playerset, settings):
        self._lobby_connection = lobby_connection
        self._playerset = playerset
        self._settings = settings

    @classmethod
    def build(cls, lobby_connection, playerset, settings, **kwargs):
        return cls(lobby_connection, playerset, settings)

    def close_fa(self, username):
        player = self._playerset.get(username, None)
        if player is None:
            return False
        logger.info('Closing FA for {}'.format(player.login))
        self._lobby_connection.send({
            "command": "admin",
            "action": "closeFA",
            "user_id": player.id,
        })
        return True

    def kick_player(self, username):
        player = self._playerset.get(username, None)
        if player is None:
            return False
        logger.info('Closing lobby for {}'.format(player.login))
        self._lobby_connection.send({
            "command": "admin",
            "action": "closelobby",
            "user_id": player.id,
        })
        return True

    def ban_player(self, username, reason, duration, period):
        player = self._playerset.get(username, None)
        if player is None:
            return False
        message = {
            "command": "admin",
            "action": "closelobby",
            "ban": {
                "reason": reason,
                "duration": duration,
                "period": period,
            },
            "user_id": player.id,
        }
        self._lobby_connection.send(message)
        return True

    def send_the_orcs(self, username):
        player = self._playerset.get(username, None)
        target = username if player is None else player.id
        route = self._settings.get('mordor/host')
        QDesktopServices.openUrl(QUrl("{}/users/{}".format(route, target)))
