from PyQt4 import QtCore
import util
from notifications.ns_hook import NsHook
import notifications as ns

"""
Settings for notifications: if a my joined game is full.
"""
class NsHookTeamFull(NsHook):
    def __init__(self):
        NsHook.__init__(self, ns.NotificationSystem.GAME_FULL)
        self.button.setEnabled(False)
