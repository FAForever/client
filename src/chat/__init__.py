# CAVEAT: DO NOT REMOVE! These are promoted widgets and py2exe wouldn't include them otherwise
from chat.chatlineedit import ChatLineEdit
from chat.chatterlistview import ChatterListView

from model.chat.chat import Chat
from model.chat.channelset import Channelset
from model.chat.chatterset import Chatterset
from model.chat.channelchatterset import ChannelChatterset
from .ircconnection import IrcConnection
from .chat_view import ChatView
from .chat_controller import ChatController

import config


class ChatMVC:
    def __init__(self, model, connection, controller, view):
        self.model = model
        self.connection = connection
        self.controller = controller
        self.view = view

    @classmethod
    def build(cls, settings, **kwargs):
        model = Chat.build(**kwargs)
        irc_port = settings.get('chat/port', 6667, int)
        irc_host = settings.get('chat/host', 'irc.' + config.defaults['host'], str)
        connection = IrcConnection.build(irc_host, irc_port, ssl=False, **kwargs)
        controller = ChatController.build(connection, model, **kwargs)
        view = ChatView.build(model, controller, **kwargs)
        return cls(model, connection, controller, view)
