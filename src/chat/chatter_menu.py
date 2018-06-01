from enum import Enum
from PyQt5.QtWidgets import QMenu, QAction, QApplication

from model.game import GameState

import logging
logger = logging.getLogger(__name__)


class ChatterMenuItems(Enum):
    SELECT_AVATAR = "Select avatar"
    SEND_ORCS = "Send the Orcs"
    CLOSE_GAME = "Close Game"
    KICK_PLAYER = "Close FAF Client"
    VIEW_ALIASES = "View aliases"
    VIEW_IN_LEADERBOARDS = "View in Leaderboards"
    JOIN_GAME = "Join hosted Game"
    VIEW_LIVEREPLAY = "View live replay"
    VIEW_REPLAYS = "View Replays in Vault"
    ADD_FRIEND = "Add friend"
    ADD_FOE = "Add foe"
    REMOVE_FRIEND = "Remove friend"
    REMOVE_FOE = "Remove foe"
    COPY_USERNAME = "Copy username"


class ChatterMenu:
    def __init__(self, me, power_tools, parent_widget, avatar_widget_builder,
                 alias_viewer, client_window, game_runner):
        self._me = me
        self._power_tools = power_tools
        self._parent_widget = parent_widget
        self._avatar_widget_builder = avatar_widget_builder
        self._alias_viewer = alias_viewer
        self._client_window = client_window
        self._game_runner = game_runner

    @classmethod
    def build(cls, me, power_tools, parent_widget, avatar_widget_builder,
              alias_viewer, client_window, game_runner, **kwargs):
        return cls(me, power_tools, parent_widget, avatar_widget_builder,
                   alias_viewer, client_window, game_runner)

    def actions(self, cc):
        chatter = cc.chatter
        player = chatter.player
        game = None if player is None else player.currentGame

        if player is None or self._me.player is None:
            is_me = False
        else:
            is_me = player.id == self._me.player.id

        yield list(self.me_actions(is_me))
        yield list(self.power_actions(self._power_tools.power))
        yield list(self.chatter_actions())
        yield list(self.player_actions(player, game, is_me))
        yield list(self.friend_actions(player, chatter, cc, is_me))

    def chatter_actions(self):
        yield ChatterMenuItems.COPY_USERNAME
        yield ChatterMenuItems.VIEW_ALIASES

    def me_actions(self, is_me):
        if is_me:
            yield ChatterMenuItems.SELECT_AVATAR

    def power_actions(self, power):
        if power == 2:
            yield ChatterMenuItems.SEND_ORCS
            yield ChatterMenuItems.CLOSE_GAME
            yield ChatterMenuItems.KICK_PLAYER

    def player_actions(self, player, game, is_me):
        if game is not None and not is_me:
            if game.state == GameState.OPEN:
                yield ChatterMenuItems.JOIN_GAME
            elif game.state == GameState.PLAYING:
                yield ChatterMenuItems.VIEW_LIVEREPLAY

        if player is not None:
            if int(player.ladder_estimate()) != 0:
                yield ChatterMenuItems.VIEW_IN_LEADERBOARDS
            yield ChatterMenuItems.VIEW_REPLAYS

    def friend_actions(self, player, chatter, cc, is_me):
        if is_me:
            return
        id_ = -1 if player is None else player.id
        name = chatter.name
        if self._me.relations.model.is_friend(id_, name):
            yield ChatterMenuItems.REMOVE_FRIEND
        elif self._me.relations.model.is_foe(id_, name):
            yield ChatterMenuItems.REMOVE_FOE
        else:
            yield ChatterMenuItems.ADD_FRIEND
            if not cc.is_mod() and not chatter.is_base_channel_mod():
                yield ChatterMenuItems.ADD_FOE

    def get_context_menu(self, data, point):
        return self.menu(data.cc)

    def menu(self, cc):
        menu = QMenu(self._parent_widget)

        def add_entry(item):
            action = QAction(item.value, menu)
            action.triggered.connect(self.handler(cc, item))
            menu.addAction(action)

        first = True
        for category in self.actions(cc):
            if not category:
                continue
            if not first:
                menu.addSeparator()
            for item in category:
                add_entry(item)
            first = False
        return menu

    def handler(self, cc, kind):
        chatter = cc.chatter
        player = chatter.player
        game = None if player is None else player.currentGame
        return lambda: self._handle_action(chatter, player, game, kind)

    def _handle_action(self, chatter, player, game, kind):
        Items = ChatterMenuItems
        if kind == Items.COPY_USERNAME:
            self._copy_username(chatter)
        elif kind == Items.SEND_ORCS:
            self._power_tools.actions.send_the_orcs(chatter.name)
        elif kind == Items.CLOSE_GAME:
            self._power_tools.view.close_game_dialog.show(chatter.name)
        elif kind == Items.KICK_PLAYER:
            self._power_tools.view.kick_dialog(chatter.name)
        elif kind == Items.SELECT_AVATAR:
            self._avatar_widget_builder().show()
        elif kind in [Items.ADD_FRIEND, Items.ADD_FOE, Items.REMOVE_FRIEND,
                      Items.REMOVE_FOE]:
            self._handle_friends(chatter, player, kind)
        elif kind == Items.VIEW_ALIASES:
            self._view_aliases(chatter, player)
        elif kind == Items.VIEW_REPLAYS:
            self._client_window.view_replays(player.login)
        elif kind == Items.VIEW_IN_LEADERBOARDS:
            self._client_window.view_in_leaderboards(player)
        elif kind in [Items.JOIN_GAME, Items.VIEW_LIVEREPLAY]:
            self._game_runner.run_game_with_url(game, player.id)

    def _copy_username(self, chatter):
        QApplication.clipboard().setText(chatter.name)

    def _handle_friends(self, chatter, player, kind):
        ctl = self._me.relations.controller
        ctl = ctl.faf if player is not None else ctl.irc
        uid = player.id if player is not None else chatter.name

        Items = ChatterMenuItems
        if kind == Items.ADD_FRIEND:
            ctl.friends.add(uid)
        elif kind == Items.REMOVE_FRIEND:
            ctl.friends.remove(uid)
        if kind == Items.ADD_FOE:
            ctl.foes.add(uid)
        elif kind == Items.REMOVE_FOE:
            ctl.foes.remove(uid)

    def _view_aliases(self, chatter, player):
        id_ = None if player is None else player.id
        self._alias_viewer.view_aliases(chatter.name, id_)
