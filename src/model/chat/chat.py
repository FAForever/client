from PyQt5.QtCore import QObject, pyqtSignal
from model.chat.channelchatterset import ChannelChatterRelation


class Chat(QObject):
    new_server_message = pyqtSignal(str)

    def __init__(self, chatterset, channelset, channelchatterset):
        QObject.__init__(self)
        self.chatters = chatterset
        self.channels = channelset
        self.channelchatters = channelchatterset
        self._cc_relation = ChannelChatterRelation(self.channels,
                                                   self.chatters,
                                                   self.channelchatters)

    def add_server_message(self, msg):
        self.new_server_message.emit(msg)
