from enum import IntEnum


class ClientState(IntEnum):
    """
    Various states the client can be in.
    """

    SHUTDOWN = -666  # Going... DOWN!

    DISCONNECTED = -2
    CONNECTING = -1
    NONE = 0
    CONNECTED = 1
    LOGGED_IN = 2
