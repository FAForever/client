



# Initialize logging system
import logging
logger = logging.getLogger(__name__)

def user2name(user):
    return (user.split('!')[0]).strip('&@~%+')
    

from _chatwidget import ChatWidget as Lobby

# CAVEAT: DO NOT REMOVE! These are promoted widgets and py2exe wouldn't include them otherwise
from chat.chatlineedit import ChatLineEdit

from .colors import OPERATOR_COLORS, CHAT_COLORS

