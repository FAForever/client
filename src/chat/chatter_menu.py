from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING
from typing import Any

from PyQt6.QtWidgets import QWidget

from src.chat._avatarWidget import AvatarWidget
from src.client.aliasviewer import AliasWindow
from src.client.user import User
from src.contextmenu.playercontextmenu import PlayerContextMenu
from src.fa.game_runner import GameRunner
from src.power import PowerTools

if TYPE_CHECKING:
    from src.client._clientwindow import ClientWindow

logger = logging.getLogger(__name__)


class ChatterMenu(PlayerContextMenu):
    # FIXME: ChatterMenu is built in ChattersView's built method
    # by passing both necessary and unnecessary kwargs to the method below
    # (notice **kwargs). But the ChattersView itself is built in this way
    # and the its 'parent's' class and so on. As a result it is hard to
    # extract any of them from the chain of 'builds' without modifying
    # lots of chat-related files.
    # It's better to avoid passing the whole bunch of dependencies arguments
    # into a single build and wonder which of them are needed for this
    # particular class and which are for its dependencies.
    # Many of those build methods (if not all) were created just for the
    # purpose of passing additional unexpected arguments, so that __init__
    # doesn't complain about them. (see 9b14d4e7)
    # Maybe it's fine in some cases, but chat's build chain is very convoluted
    # and hard to grasp
    @classmethod
    def build(
        cls,
        me: User,
        power_tools: PowerTools,
        parent_widget: QWidget,
        avatar_widget_builder: Callable[..., AvatarWidget],
        alias_viewer: AliasWindow,
        client_window: ClientWindow,
        game_runner: GameRunner,
        **kwargs: Any,
    ):
        return cls(
            me, power_tools, parent_widget, avatar_widget_builder,
            alias_viewer, client_window, game_runner,
        )
