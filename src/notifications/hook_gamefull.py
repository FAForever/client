"""
Settings for notifications: If a game is full
"""
import notifications as ns
from notifications.ns_hook import NsHook


class NsHookGameFull(NsHook):
    def __init__(self):
        NsHook.__init__(self, ns.Notifications.GAME_FULL)
