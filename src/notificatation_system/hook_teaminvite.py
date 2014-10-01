from PyQt4 import QtCore
import util
from notificatation_system.ns_hook import NsHook
import notificatation_system as ns

"""
Settings for notifications: if a player receive a team invite
"""
class NsHookTeamInvite(NsHook):
    def __init__(self):
        NsHook.__init__(self, ns.NotificationSystem.TEAM_INVITE)
        self.button.setEnabled(False)


