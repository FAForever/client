# CAVEAT: DO NOT REMOVE! These are promoted widgets and py2exe wouldn't include them otherwise
from chat.chatlineedit import ChatLineEdit

from model.chat.chat import Chat
from model.chat.channelset import Channelset
from model.chat.chatterset import Chatterset
from model.chat.channelchatterset import ChannelChatterset
from .ircconnection import IrcConnection
from .chat_view import ChatView
from .chat_controller import ChatController

import config


class ChatMVC:
    irc_port = config.Settings.persisted_property('chat/port', type=int, default_value=6667)
    irc_host = config.Settings.persisted_property('chat/host', type=str, default_value='irc.' + config.defaults['host'])

    def __init__(self, playerset):
        channels = Channelset()
        chatters = Chatterset(playerset)
        channelchatters = ChannelChatterset()
        self.model = Chat(chatters, channels, channelchatters)
        self.connection = IrcConnection(self.irc_host, self.irc_port)
        self.controller = ChatController(self.connection, self.model)
        self.view = ChatView(self.model)
