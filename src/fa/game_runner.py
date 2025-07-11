from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from typing import NamedTuple

from src import fa
from src.fa.replay import replay
from src.model.game import Game
from src.model.game import GameState
from src.model.gameset import Gameset
from src.util.gameurl import GameUrl

if TYPE_CHECKING:
    from src.client._clientwindow import ClientWindow

logger = logging.getLogger(__name__)


class GameLaunchArguments(NamedTuple):
    info: dict[str, str | int]
    arguments: list[str]


class GameRunner:
    def __init__(self, gameset: Gameset, client_window: ClientWindow) -> None:
        self._gameset = gameset
        self._client_window = client_window     # FIXME
        self._launch_args: GameLaunchArguments | None = None

    def set_launch_args(self, args: GameLaunchArguments) -> None:
        self._launch_args = args

    def run_game_with_arguments(
        self,
        gpg_port: int,
        replay_port: int,
        game_log_filename: str,
        args: GameLaunchArguments | None = None,
    ) -> None:
        arguments = args or self._launch_args
        if arguments is None:
            logger.error("Game launch arguments are not set. Can't launch a game.")
            return
        fa.run(
            arguments.info,
            gpg_port,
            replay_port,
            arguments.arguments,
            game_log_filename,
        )

    def run_game_with_url(self, game: Game, pid: int) -> None:
        gurl = game.url(pid)
        if gurl is None:
            return
        self.run_game_from_url(gurl)

    def run_game_from_url(self, gurl: GameUrl) -> None:
        game = self._gameset.get(gurl.uid, None)
        if game is None or game.closed():
            return

        if game.state == GameState.OPEN:
            self._join_game_from_url(gurl)
        elif game.state == GameState.PLAYING:
            replay(gurl)

    def _join_game_from_url(self, gurl: GameUrl) -> None:
        logger.debug("Joining game from URL: " + gurl.to_url().toString())
        if fa.instance.available():
            add_mods = gurl.mods or {}
            if fa.check.game(self):
                if fa.check.check(gurl.mod, gurl.map, sim_mods=add_mods):
                    self._client_window.join_game(gurl.uid)
