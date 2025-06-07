from __future__ import annotations

import logging
from collections.abc import Callable
from collections.abc import Generator
from enum import Enum
from typing import TYPE_CHECKING

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QMenu
from PyQt6.QtWidgets import QWidget

from src.chat._avatarWidget import AvatarWidget
from src.client.aliasviewer import AliasWindow
from src.client.user import User
from src.fa.game_runner import GameRunner
from src.model.game import GameState
from src.model.player import Player
from src.playercard.playerinfodialog import PlayerInfoDialog
from src.power import PowerTools

if TYPE_CHECKING:
    from src.client._clientwindow import ClientWindow

logger = logging.getLogger(__name__)


class PlayerMenuItem(Enum):
    SELECT_AVATAR = "Select avatar"
    SEND_ORCS = "Send the Orcs"
    CLOSE_GAME = "Close Game"
    KICK_PLAYER = "Close FAF Client"
    VIEW_ALIASES = "View aliases"
    JOIN_GAME = "Join hosted Game"
    VIEW_LIVEREPLAY = "View live replay"
    VIEW_REPLAYS = "View Replays in Vault"
    ADD_FRIEND = "Add friend"
    ADD_FOE = "Add foe"
    REMOVE_FRIEND = "Remove friend"
    REMOVE_FOE = "Remove foe"
    ADD_CHATTERBOX = "Ignore"
    REMOVE_CHATTERBOX = "Unignore"
    COPY_USERNAME = "Copy username"
    INVITE_TO_PARTY = "Invite to party"
    KICK_FROM_PARTY = "Kick from party"
    SHOW_PLAYER_INFO = "Show player info"


class PlayerContextMenu:
    def __init__(
            self,
            me: User,
            power_tools: PowerTools,
            parent_widget: QWidget,
            avatar_widget_builder: Callable[..., AvatarWidget],
            alias_viewer: AliasWindow,
            client_window: ClientWindow,
            game_runner: GameRunner,
    ) -> None:
        self._me = me
        self._power_tools = power_tools
        self._parent_widget = parent_widget
        self._avatar_widget_builder = avatar_widget_builder
        self._alias_viewer = alias_viewer
        self._client_window = client_window
        self._game_runner = game_runner

    def actions(self, login: str, player_id: int) -> Generator[list[PlayerMenuItem]]:
        if player_id == -1 or self._me.player is None:
            is_me = False
        else:
            is_me = player_id == self._me.player.id

        yield list(self.user_actions(player_id))
        yield list(self.me_actions(is_me=is_me))
        yield list(self.power_actions(self._power_tools.power))
        yield list(self.chatter_actions(player_id))
        yield list(self.player_actions(player_id, is_me=is_me))
        yield list(self.friend_actions(player_id, login, is_me=is_me))
        yield list(self.ignore_actions(player_id, login, is_me=is_me))
        yield list(self.party_actions(player_id, is_me=is_me))

    def user_actions(self, player_id: int) -> Generator[PlayerMenuItem]:
        if player_id != -1:
            yield PlayerMenuItem.SHOW_PLAYER_INFO

    def chatter_actions(self, player_id: int) -> Generator[PlayerMenuItem]:
        yield PlayerMenuItem.COPY_USERNAME
        if player_id != -1:
            yield PlayerMenuItem.VIEW_ALIASES

    def me_actions(self, *, is_me: bool) -> Generator[PlayerMenuItem]:
        if is_me:
            yield PlayerMenuItem.SELECT_AVATAR

    def power_actions(self, power: int) -> Generator[PlayerMenuItem]:
        if power == 2:
            yield PlayerMenuItem.SEND_ORCS
            yield PlayerMenuItem.CLOSE_GAME
            yield PlayerMenuItem.KICK_PLAYER

    def _get_online_player_by_id(self, player_id: int) -> Player | None:
        try:
            return self._client_window.players[player_id]
        except KeyError:
            return None

    def player_actions(
            self,
            player_id: int,
            *,
            is_me: bool,
    ) -> Generator[PlayerMenuItem]:
        if player_id != -1:
            yield PlayerMenuItem.VIEW_REPLAYS

        online_player = self._get_online_player_by_id(player_id)

        if online_player is None:
            return

        game = online_player.currentGame

        if game is not None and not is_me:
            if game.state == GameState.OPEN:
                yield PlayerMenuItem.JOIN_GAME
            elif game.state == GameState.PLAYING:
                yield PlayerMenuItem.VIEW_LIVEREPLAY

    def friend_actions(
            self,
            player_id: int,
            login: str,
            *,
            is_me: bool,
    ) -> Generator[PlayerMenuItem]:
        if is_me:
            return
        if self._client_window.user_relations.model.is_friend(player_id, login):
            yield PlayerMenuItem.REMOVE_FRIEND
        elif self._client_window.user_relations.model.is_foe(player_id, login):
            yield PlayerMenuItem.REMOVE_FOE
        else:
            yield PlayerMenuItem.ADD_FRIEND
            yield PlayerMenuItem.ADD_FOE

    def ignore_actions(
            self,
            player_id: int,
            login: str,
            *,
            is_me: bool,
    ) -> Generator[PlayerMenuItem]:
        if is_me:
            return
        if self._client_window.user_relations.model.is_chatterbox(player_id, login):
            yield PlayerMenuItem.REMOVE_CHATTERBOX
        else:
            yield PlayerMenuItem.ADD_CHATTERBOX

    def party_actions(
            self,
            player_id: int,
            *,
            is_me: bool,
    ) -> Generator[PlayerMenuItem]:
        if is_me:
            return

        online_player = self._get_online_player_by_id(player_id)
        if online_player is None:
            return

        if online_player.id in self._client_window.games.party.member_ids:
            if self._me.player.id == self._client_window.games.party.owner_id:
                yield PlayerMenuItem.KICK_FROM_PARTY
        elif online_player.currentGame is not None:
            return
        else:
            yield PlayerMenuItem.INVITE_TO_PARTY

    def get_context_menu(self, login: str, player_id: int) -> QMenu:
        return self.menu(login, player_id)

    def menu(self, login: str, player_id: int) -> QMenu:
        menu = QMenu(self._parent_widget)

        def add_entry(item):
            action = QAction(item.value, menu)
            action.triggered.connect(self.handler(login, player_id, item))
            menu.addAction(action)

        for category in self.actions(login, player_id):
            if not category:
                continue
            for item in category:
                add_entry(item)
            menu.addSeparator()
        return menu

    def handler(self, login: str, player_id: int, kind: PlayerMenuItem) -> Callable[[], None]:
        return lambda: self._handle_action(login, player_id, kind)

    def _handle_action(self, login: str, player_id: int, kind: PlayerMenuItem) -> None:
        Items = PlayerMenuItem
        if kind == Items.COPY_USERNAME:
            self._copy_username(login)
        elif kind == Items.SEND_ORCS:
            self._power_tools.actions.send_the_orcs(login)
        elif kind == Items.CLOSE_GAME:
            self._power_tools.view.close_game_dialog.show(login)
        elif kind == Items.KICK_PLAYER:
            self._power_tools.view.kick_dialog(login)
        elif kind == Items.SELECT_AVATAR:
            self._avatar_widget_builder().show()
        elif kind in [
            Items.ADD_FRIEND, Items.ADD_FOE, Items.REMOVE_FRIEND,
            Items.REMOVE_FOE, Items.ADD_CHATTERBOX, Items.REMOVE_CHATTERBOX,
        ]:
            self._handle_social(login, player_id, kind)
        elif kind == Items.VIEW_ALIASES:
            self._view_aliases(login)
        elif kind == Items.SHOW_PLAYER_INFO:
            self._show_player_info(player_id)
        elif kind == Items.VIEW_REPLAYS:
            self._client_window.view_replays(login)
        elif kind in [Items.JOIN_GAME, Items.VIEW_LIVEREPLAY]:
            self._handle_game(player_id)
        elif kind == Items.INVITE_TO_PARTY:
            self._client_window.invite_to_party(player_id)
        elif kind == Items.KICK_FROM_PARTY:
            self._client_window.games.kickPlayerFromParty(player_id)

    def _handle_game(self, player_id: int) -> None:
        online_player = self._get_online_player_by_id(player_id)
        if online_player is None:
            return

        game = online_player.currentGame
        if game is None:
            return

        self._game_runner.run_game_with_url(game, player_id)

    def _copy_username(self, login: str) -> None:
        clip = QApplication.clipboard()
        if clip is not None:
            clip.setText(login)

    def _handle_social(self, login: str, player_id: int, kind: PlayerMenuItem) -> None:
        ctl = self._client_window.user_relations.controller

        if player_id == -1:
            ctl = ctl.irc
            uid = login
        else:
            ctl = ctl.faf
            uid = player_id

        social_handlers = {
            PlayerMenuItem.ADD_FRIEND: ctl.friends.add,
            PlayerMenuItem.REMOVE_FRIEND: ctl.friends.remove,
            PlayerMenuItem.ADD_FOE: ctl.foes.add,
            PlayerMenuItem.REMOVE_FOE: ctl.foes.remove,
            PlayerMenuItem.ADD_CHATTERBOX: ctl.chatterboxes.add,
            PlayerMenuItem.REMOVE_CHATTERBOX: ctl.chatterboxes.remove,
        }
        handler = social_handlers.get(kind)
        if handler is not None:
            handler(uid)

    def _view_aliases(self, login: str) -> None:
        self._alias_viewer.view_aliases(login)

    def _show_player_info(self, player_id: int) -> None:
        dialog = PlayerInfoDialog(self._client_window.avatar_downloader, str(player_id))
        dialog.run()
