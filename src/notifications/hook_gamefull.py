from PyQt5 import QtCore

import config
import notifications as ns
import util
from config import Settings
from notifications.ns_hook import NsHook

"""
Settings for notifications: If a game is full
"""


class NsHookGameFull(NsHook):
    def __init__(self):
        NsHook.__init__(self, ns.Notifications.GAME_FULL)