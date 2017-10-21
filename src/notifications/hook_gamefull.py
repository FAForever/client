from PyQt5 import QtCore
import util
import config
from config import Settings
from notifications.ns_hook import NsHook
import notifications as ns

"""
Settings for notifications: If a game is full
"""


class NsHookGameFull(NsHook):
    def __init__(self):
        NsHook.__init__(self, ns.Notifications.GAME_FULL)