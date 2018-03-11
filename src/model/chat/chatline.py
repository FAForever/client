import time


class ChatLine:
    def __init__(self, sender, text, timestamp=None):
        self.sender = sender
        self.text = text
        if timestamp is None:
            timestamp = time.time()
        self.time = timestamp
