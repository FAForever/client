from PyQt5.QtCore import QObject, pyqtSignal


class GameModelItem(QObject):
    """
    UI representation of a running game. Tracks and signals changes that game
    display widgets would like to know about.
    """
    updated = pyqtSignal(object)

    def __init__(self, game, me):
        QObject.__init__(self)

        self.game = game
        self.game.gameUpdated.connect(self._game_updated)

        self._me = me
        self._me.relationsUpdated.connect(self._check_host_relation_changed)

    def _game_updated(self):
        self.updated.emit(self)

    def _check_host_relation_changed(self, players):
        # This should never happen bar server screwups.
        if self.game.host_player is None:
            return
        if self.game.host_player.id in players:
            self.updated.emit(self)
