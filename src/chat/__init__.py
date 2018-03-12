# CAVEAT: DO NOT REMOVE! These are promoted widgets and py2exe wouldn't include them otherwise
from chat.chatlineedit import ChatLineEdit
from chat.chatterlistview import ChatterListView


class ChatMVC:
    def __init__(self, model, connection, controller, autojoiner, view):
        self.model = model
        self.connection = connection
        self.controller = controller
        self.autojoiner = autojoiner    # Technically part of controller?
        self.view = view
