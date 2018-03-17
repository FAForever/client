# CAVEAT: DO NOT REMOVE! These are promoted widgets and py2exe wouldn't include them otherwise
from chat.chatlineedit import ChatLineEdit
from chat.chatterlistview import ChatterListView


class ChatMVC:
    def __init__(self, model, connection, controller, autojoiner, restorer,
                 view):
        self.model = model
        self.connection = connection
        self.controller = controller
        # Technically part of controller?
        self.autojoiner = autojoiner
        # Ditto, also don't confuse with the other Restorer
        self.restorer = restorer
        self.view = view
