from PyQt5.QtCore import QObject, pyqtSignal
from model.chat.channelset import Channelset
from model.chat.chatterset import Chatterset
from model.chat.channelchatterset import ChannelChatterset
from model.chat.channelchatterset import ChannelChatterRelation


class Chat(QObject):
    new_server_message = pyqtSignal(str)

    def __init__(self, channelset, chatterset, channelchatterset, cc_relation):
        QObject.__init__(self)
        self.channels = channelset
        self.chatters = chatterset
        self.channelchatters = channelchatterset
        self._cc_relation = cc_relation

    @classmethod
    def build(cls, playerset, **kwargs):
        channels = Channelset()
        chatters = Chatterset(playerset)
        channelchatters = ChannelChatterset()
        cc_relation = ChannelChatterRelation(channels, chatters,
                                             channelchatters)
        return cls(channels, chatters, channelchatters, cc_relation)

    def add_server_message(self, msg):
        self.new_server_message.emit(msg)
