from PyQt5.QtCore import QObject
from model.chat.channelchatterset import ChannelChatterRelation


class Chat(QObject):
    def __init__(self, chatterset, channelset, channelchatterset):
        QObject.__init__(self)
        self.chatters = chatterset
        self.channels = channelset
        self.channelchatters = channelchatterset
        self._cc_relation = ChannelChatterRelation(self.channels,
                                                   self.chatters,
                                                   self.channelchatters)
