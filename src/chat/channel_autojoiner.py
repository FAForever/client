from __future__ import annotations

from typing import Self
from typing import cast

from src.chat.chat_controller import ChatController
from src.chat.lang import DEFAULT_LANGUAGE_CHANNELS
from src.client.chat_config import ChatConfig
from src.client.connection import LobbyInfo
from src.client.user import User
from src.config import Settings
from src.model.chat.chat import Chat
from src.model.player import Player
from src.protocol.lobbyprotocol import SocialCommand
from src.util.lang import COUNTRY_TO_LANGUAGE


class ChannelAutojoiner:
    def __init__(
        self,
        base_channels: list[str],
        model: Chat,
        controller: ChatController,
        settings: type[Settings],
        lobby_info: LobbyInfo,
        chat_config: ChatConfig,
        lang_channel_checker: LanguageChannelChecker,
        me: User,
    ) -> None:
        self.base_channels = base_channels
        self._model = model
        self._controller = controller
        self._settings = settings
        self._lobby_info = lobby_info
        self._chat_config = chat_config
        self._me = me
        self._me.playerChanged.connect(self._autojoin_player_dependent)
        self._lang_channel_checker = lang_channel_checker

        self._lobby_info.social.connect(self._autojoin_lobby)
        self._saved_lobby_channels = []

        self._model.connect_event.connect(self._autojoin_all)
        if self._model.connected:
            self._autojoin_all()

    @classmethod
    def build(
        cls,
        base_channels: list[str],
        model: Chat,
        controller: ChatController,
        settings: type[Settings],
        lobby_info: LobbyInfo,
        chat_config: ChatConfig,
        me: User,
    ) -> Self:
        lang_channel_checker = LanguageChannelChecker(settings)
        return cls(
            base_channels, model, controller, settings, lobby_info,
            chat_config, lang_channel_checker, me,
        )

    def _autojoin_all(self) -> None:
        self._autojoin_base()
        self._autojoin_saved_lobby()
        self._autojoin_custom()
        self._autojoin_player_dependent()

    def _autojoin_player_dependent(self) -> None:
        if not self._model.connected:
            return
        if self._me.player is None:
            return
        self._autojoin_newbie()
        self._autojoin_lang()

    def _join_all(self, channels: list[str]) -> None:
        for name in channels:
            self._controller.join_public_channel(name)

    def _autojoin_base(self):
        self._join_all(self.base_channels)

    def _autojoin_custom(self) -> None:
        auto_channels = self._settings.get("chat/auto_join_channels", cast(list[str], []))
        # FIXME - sanity check since QSettings is iffy with lists
        if not isinstance(auto_channels, list):
            return
        self._join_all(auto_channels)

    def _autojoin_lobby(self, message: SocialCommand) -> None:
        channels = message["autojoin"]
        if self._model.connected:
            self._join_all(channels)
        else:
            self._saved_lobby_channels = channels

    def _autojoin_saved_lobby(self) -> None:
        self._join_all(self._saved_lobby_channels)
        self._saved_lobby_channels = []

    def _autojoin_newbie(self) -> None:
        if not self._chat_config.newbies_channel:
            return
        threshold = self._chat_config.newbie_channel_game_threshold
        assert self._me.player is not None
        if self._me.player.number_of_games > threshold:
            return
        self._join_all(["#newbie"])

    def _autojoin_lang(self) -> None:
        assert self._me.player is not None
        self._join_all(self._lang_channel_checker.get_channels(self._me.player))


class LanguageChannelChecker:
    def __init__(self, settings: type[Settings]) -> None:
        self._settings = settings

    def get_channels(self, player: Player) -> list[str]:
        if not self._settings.contains("client/lang_channels"):
            self._set_default_language_channel(player)
        chan = self._settings.get("client/lang_channels")
        if chan is None:
            return []
        return [c for c in chan.split(';') if c]

    def _set_default_language_channel(self, player: Player) -> None:
        from_os = self._channel_from_os_language()
        from_ip = self._channel_from_geoip(player)
        default = from_os or from_ip
        if default is None:
            return
        self._settings.set("client/lang_channels", default)

    def _channel_from_os_language(self) -> str | None:
        lang = self._settings.get("client/language", "")
        return DEFAULT_LANGUAGE_CHANNELS.get(lang)

    def _channel_from_geoip(self, player: Player | None) -> str | None:
        if player is None:
            return None
        flag = player.country or ""
        lang = COUNTRY_TO_LANGUAGE.get(flag, "")
        return DEFAULT_LANGUAGE_CHANNELS.get(lang)
