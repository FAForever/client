import notifications as ns
from notifications.ns_hook import NsHook

"""
Settings for notifications: If a game is full
"""


class NsHookGameFull(NsHook):
    def __init__(self):
        NsHook.__init__(self, ns.Notifications.GAME_FULL)
