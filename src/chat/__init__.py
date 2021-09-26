# CAVEAT: DO NOT REMOVE! These are promoted widgets and py2exe wouldn't
# include them otherwise
from chat.chatlineedit import ChatLineEdit
from chat.chatterlistview import ChatterListView

__all__ = (
    "ChatLineEdit",
    "ChatterListView",
)


class ChatMVC:
    def __init__(
        self, model, line_metadata_builder, connection, controller,
        autojoiner, restorer, greeter, announcer, view,
    ):
        self.model = model
        self.line_metadata_builder = line_metadata_builder
        self.connection = connection
        self.controller = controller
        # Technically part of controller?
        self.autojoiner = autojoiner
        # Ditto, also don't confuse with the other Restorer
        self.restorer = restorer
        # Ditto
        self.announcer = announcer
        # Ditto
        self.greeter = greeter
        self.view = view
