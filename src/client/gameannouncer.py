from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from fa import maps
from model.game import GameState


class GameAnnouncer(QObject):
    announce = pyqtSignal(str, str)

    ANNOUNCE_DELAY_SECS = 35

    def __init__(self, gameset, me, colors):
        QObject.__init__(self)
        self._gameset = gameset
        self._me = me
        self._colors = colors

        self._gameset.newLobby.connect(self._announce_hosting)
        self._gameset.newLiveReplay.connect(self._announce_replay)

        self.announce_games = True
        self.announce_replays = True
        self._delayed_host_list = []

    def _is_friend_host(self, game):
        return (game.host_player is not None
                and self._me.relations.model.is_friend(game.host_player.id))

    def _announce_hosting(self, game):
        if not self._is_friend_host(game) or not self.announce_games:
            return
        announce_delay = QTimer()
        announce_delay.setSingleShot(True)
        announce_delay.setInterval(self.ANNOUNCE_DELAY_SECS * 1000)
        announce_delay.timeout.connect(self._delayed_announce_hosting)
        announce_delay.start()
        self._delayed_host_list.append((announce_delay, game))

    def _delayed_announce_hosting(self):
        timer, game = self._delayed_host_list.pop(0)

        if (not self._is_friend_host(game) or
           not self.announce_games or
           game.state != GameState.OPEN):
            return
        self._announce(game, "hosting")

    def _announce_replay(self, game):
        if not self._is_friend_host(game) or not self.announce_replays:
            return
        self._announce(game, "playing live")

    def _announce(self, game, activity):
        if game.host_player is None:
            return
        url = game.url(game.host_player.id).to_url().toString()
        mapname = maps.getDisplayName(game.mapname)
        fmt = 'is {} {}<a class=game_link href="{}">{}</a> (on {})'
        if game.featured_mod == "faf":
            modname = ""
        else:
            modname = game.featured_mod + " "
        msg = fmt.format(activity, modname, url, game.title, mapname)
        self.announce.emit(msg, game.host)
