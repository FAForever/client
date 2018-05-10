class ChannelAutojoiner:
    DEFAULT_LANGUAGE_CHANNELS = {
        "#french": ["fr"],
        "#russian": ["ru", "be"],    # Be conservative here
        "#german": ["de"]
    }

    # Flip around for easier use
    DEFAULT_LANGUAGE_CHANNELS = {
        code: channel
        for channel, codes in DEFAULT_LANGUAGE_CHANNELS.items()
        for code in codes
    }

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
        self._autojoin_lang()

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

    def _autojoin_lang(self):
        if not self._settings.contains('client/lang_channels'):
            self._set_default_language_channel()
        lang_channels = self._settings.get('client/lang_channels', None)
        if lang_channels is None:
            return
        lang_channels = lang_channels.split(';')
        self._join_all(l for l in lang_channels if l)

    def _set_default_language_channel(self):
        lang = self._settings.get('client/language', None)
        if lang is None:
            return
        chan = self.DEFAULT_LANGUAGE_CHANNELS.get(lang, None)
        if chan is None:
            return
        self._settings.set('client/lang_channels', chan)
