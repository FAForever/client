import json

import fa
from fa.replay import replay
from model.game import GameState

import logging
logger = logging.getLogger(__name__)


class GameRunner:
    def __init__(self, gameset, client_window):
        self._gameset = gameset
        self._client_window = client_window     # FIXME

    def run_game_with_url(self, game, pid):
        gurl = game.url(pid)
        if gurl is None:
            return
        self.run_game_from_url(gurl)

    def run_game_from_url(self, gurl):
        game = self._gameset.get(gurl.uid, None)
        if game is None or game.closed():
            return

        if game.state == GameState.OPEN:
            self._join_game_from_url(gurl)
        elif game.state == GameState.PLAYING:
            replay(gurl)

    def _join_game_from_url(self, gurl):
        logger.debug("Joining game from URL: " + gurl.to_url().toString())
        if fa.instance.available():
            if gurl.mods is None:
                add_mods = []
            else:
                try:
                    add_mods = json.loads(gurl.mods)  # should be a list
                except (json.JSONDecodeError, TypeError):
                    logger.info("Failed to decode game mods!")
            if fa.check.game(self):
                if fa.check.check(gurl.mod, gurl.map, sim_mods=add_mods):
                    self._client_window.join_game(gurl.uid)
