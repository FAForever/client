from PyQt5.QtCore import QObject

from model.game import GameState


class SensitiveMapInfoChecker(QObject):
    def __init__(self, me):
        QObject.__init__(self)
        self._me = me

    @classmethod
    def build(cls, me, **kwargs):
        return cls(me)

    def has_sensitive_data(self, game):
        if game is None or game.closed():
            return False

        if game.featured_mod == "ladder1v1":
            return self._ladder_has_sensitive_data(game)
        return False

    def _ladder_has_sensitive_data(self, game):
        if game.state != GameState.OPEN:
            return False
        if self._me.player is None:
            return False
        return self._me.player.login in game.players
