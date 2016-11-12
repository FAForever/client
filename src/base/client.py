from abc import ABCMeta


class Client:
    def __init__(self):
        pass

    __metaclass__ = ABCMeta
    
    def send(self, message):
        pass
