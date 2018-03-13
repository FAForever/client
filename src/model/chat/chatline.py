from enum import Enum
import time


# Notices differ from messages in that notices in public channels are visible
# only to the user. Due to that, it's important to be able to tell the
# difference between the two.
class ChatLineType(Enum):
    MESSAGE = 0
    NOTICE = 1


class ChatLine:
    def __init__(self, sender, text, type_, timestamp=None):
        self.sender = sender
        self.text = text
        if timestamp is None:
            timestamp = time.time()
        self.time = timestamp
        self.type = type_
