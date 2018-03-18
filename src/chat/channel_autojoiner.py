class ChannelAutojoiner:
    def __init__(self, base_channels, model, controller, settings, lobby_info,
                 chat_config, me):
        self.base_channels = base_channels
        self._model = model
        self._controller = controller
        self._settings = settings
        self._lobby_info = lobby_info
        self._chat_config = chat_config
        self._me = me
        self._me.playerChanged.connect(self._autojoin_newbie)

        self._lobby_info.social.connect(self._autojoin_lobby)
        self._saved_lobby_channels = []

        self._model.connect_event.connect(self._autojoin_all)
        if self._model.connected:
            self._autojoin_all()

    @classmethod
    def build(cls, base_channels, model, controller, settings, lobby_info,
              chat_config, me, **kwargs):
        return cls(base_channels, model, controller, settings, lobby_info,
                   chat_config, me)

    def _autojoin_all(self):
        self._autojoin_base()
        self._autojoin_saved_lobby()
        self._autojoin_custom()
        self._autojoin_newbie()

    def _join_all(self, channels):
        for name in channels:
            self._controller.join_public_channel(name)

    def _autojoin_base(self):
        self._join_all(self.base_channels)

    def _autojoin_custom(self):
        auto_channels = self._settings.get('chat/auto_join_channels', [])
        # FIXME - sanity check since QSettings is iffy with lists
        if not isinstance(auto_channels, list):
            return
        self._join_all(auto_channels)

    def _autojoin_lobby(self, message):
        channels = message.get("autojoin", None)
        if channels is None:
            return
        if self._model.connected:
            self._join_all(channels)
        else:
            self._saved_lobby_channels = channels

    def _autojoin_saved_lobby(self):
        self._join_all(self._saved_lobby_channels)
        self._saved_lobby_channels = []

    def _autojoin_newbie(self):
        if not self._model.connected:
            return
        if not self._chat_config.newbies_channel:
            return
        if self._me.player is None:
            return
        threshold = self._chat_config.newbie_channel_game_threshold
        if self._me.player.number_of_games > threshold:
            return
        self._join_all(["#newbie"])
