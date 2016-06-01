



# Initialize logging system
import logging
logger = logging.getLogger(__name__)

IRC_ELEVATION = '%@~%+&'

def user2name(user):
    return (user.split('!')[0]).strip(IRC_ELEVATION)

def parse_irc_source(src):
    """
    :param src: IRC source argument
    :return: (username, id, elevation, hostname)
    """
    username, tail = src.split('!')
    if username[0] in IRC_ELEVATION:
        elevation, username = username[0], username[1:]
    else:
        elevation = ''
    id, hostname = tail.split('@')
    try:
        id = int(id)
    except ValueError:
        id = -1
    return username, id, elevation, hostname



from ._chatwidget import ChatWidget as Lobby

# CAVEAT: DO NOT REMOVE! These are promoted widgets and py2exe wouldn't include them otherwise
from chat.chatlineedit import ChatLineEdit

from .colors import OPERATOR_COLORS, CHAT_COLORS


def get_color(kind):
    return CHAT_COLORS.get(kind) or CHAT_COLORS['default']
