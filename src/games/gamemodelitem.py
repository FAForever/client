from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from model.game import GameState
from downloadManager import PreviewDownloadRequest
from fa import maps


class GameModelItem(QObject):
    """
    UI representation of a running game. Tracks and signals changes that game
    display widgets would like to know about.
    """
    updated = pyqtSignal(object)

    def __init__(self, game, me, preview_dler):
        QObject.__init__(self)

        self.game = game
        self.game.gameUpdated.connect(self._game_updated)
        self.hosted_at = None  # put here as long it's not coming from server
        self._me = me
        self._me.relationsUpdated.connect(self._check_host_relation_changed)
        self._preview_dler = preview_dler
        self._preview_dl_request = PreviewDownloadRequest()
        self._preview_dl_request.done.connect(self._at_preview_downloaded)

        # Update highlight
        self._highlight_timer = QTimer()
        self._highlight_timer.setSingleShot(True)
        self._highlight_timer.setInterval(250)
        self._highlight_timer.timeout.connect(self._reset_highlight)
        self.highlight = False

    def _game_updated(self):
        self._set_highlight()
        self.updated.emit(self)

    def _set_highlight(self):
        if self.game.state != GameState.OPEN:
            return
        if self._highlight_timer.isActive():
            return
        self.highlight = True
        self._highlight_timer.start()

    def _reset_highlight(self):
        self.highlight = False
        self.updated.emit(self)
        self._download_preview_if_needed()

    def _check_host_relation_changed(self, players):
        # This should never happen bar server screwups.
        if self.game.host_player is None:
            return
        if self.game.host_player.id in players:
            self.updated.emit(self)

    def _download_preview_if_needed(self):
        if self.game.mapname is None:
            return
        name = self.game.mapname.lower()
        if self.game.password_protected or maps.preview(name) is not None:
            return
        self._preview_dler.download_preview(name, self._preview_dl_request)

    def _at_preview_downloaded(self, mapname):
        if mapname == self.game.mapname:
            self.updated.emit(self)
