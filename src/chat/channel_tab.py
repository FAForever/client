from PyQt5.QtCore import QTimer
from enum import IntEnum
from chat.chat_widget import TabIcon


class TabInfo(IntEnum):
    IDLE = 0
    NEW_MESSAGES = 1
    IMPORTANT = 2


class ChannelTab:
    def __init__(self, cid, widget, theme, chat_config):
        self._cid = cid
        self._widget = widget
        self._theme = theme
        self._chat_config = chat_config
        self._info = TabInfo.IDLE

        self._timer = QTimer()
        self._timer.setInterval(self._chat_config.channel_blink_interval)
        self._timer.timeout.connect(self._switch_blink)
        self._blink_phase = False
        self._chat_config.updated.connect(self._config_updated)

        self._ping_timer = QTimer()
        self._ping_timer.setSingleShot(True)
        self._ping_timer.setInterval(self._chat_config.channel_ping_timeout)

    def _config_updated(self, option):
        c = self._chat_config
        if option == "channel_blink_interval":
            self._timer.setInterval(c.channel_blink_interval)
        if option == "channel_ping_timeout":
            self._ping_timer.setInterval(c.channel_ping_timeout)

    @classmethod
    def builder(cls, theme, chat_config, **kwargs):
        def make(cid, widget):
            return cls(cid, widget, theme, chat_config)
        return make

    @property
    def info(self):
        return self._info

    @info.setter
    def info(self, info):
        if self._info == info:
            return
        if self._info > info and info != TabInfo.IDLE:
            return
        self._info = info

        if info == TabInfo.IMPORTANT:
            self._start_blinking()
            return
        self._stop_blinking()
        if info == TabInfo.NEW_MESSAGES:
            self._widget.set_tab_icon(self._cid, TabIcon.NEW_MESSAGE)
        if info == TabInfo.IDLE:
            self._widget.set_tab_icon(self._cid, TabIcon.IDLE)

    def _start_blinking(self):
        if not self._timer.isActive():
            self._switch_blink(False)
            self._timer.start()
        self._ping()

    def _ping(self):
        if not self._chat_config.soundeffects:
            return
        if self._ping_timer.isActive():
            return
        self._ping_timer.start()
        self._theme.sound("chat/sfx/query.wav")

    def _stop_blinking(self):
        self._timer.stop()
        self._ping_timer.stop()

    def _switch_blink(self, val=None):
        if val is None:
            val = not self._blink_phase
        self._blink_phase = val
        icon = TabIcon.BLINK_ACTIVE if val else TabIcon.BLINK_INACTIVE
        self._widget.set_tab_icon(self._cid, icon)
