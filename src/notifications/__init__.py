from PyQt5 import QtCore, QtWidgets

import util
from fa import maps
from notifications.ns_dialog import NotificationDialog
from notifications.ns_settings import NsSettingsDialog, IngameNotification

"""
The Notification Systems reacts on events and displays a popup.
Each event_type has a NsHook to customize it.
"""
class Notifications:
    USER_ONLINE = 'user_online'
    NEW_GAME = 'new_game'

    def __init__(self, client):
        self.client = client

        self.settings = NsSettingsDialog(self.client)
        self.dialog = NotificationDialog(self.client,self.settings)
        self.events = []
        self.disabledStartup = True
        self.game_running = False


        client.gameEnter.connect(self.gameEnter)
        client.gameExit.connect(self.gameExit)

        self.user = util.icon("client/user.png", pix=True)

    def gameEnter(self):
        self.game_running = True

    def gameExit(self):
        self.game_running = False
        # kick the queue
        if self.settings.ingame_notifications == IngameNotification.QUEUE:
            self.checkEvent()

    def isDisabled(self):
        return (
            self.disabledStartup
            or self.game_running and self.settings.ingame_notifications == IngameNotification.DISABLE
            or not self.settings.enabled
        )

    def setNotificationEnabled(self, enabled):
        self.settings.enabled = enabled
        self.settings.saveSettings()

    @QtCore.pyqtSlot()
    def on_event(self, eventType, data):
        """
        Puts an event in a queue, can trigger a popup.
        Keyword arguments:
        eventType -- Type of the event
        data -- Custom data that is used by the system to show a detailed popup
        """
        if self.isDisabled() or not self.settings.popupEnabled(eventType):
            return

        doAdd = False

        if eventType == self.USER_ONLINE:
            userid = data['user']
            if self.settings.getCustomSetting(eventType, 'mode') == 'all' or self.client.players.isFriend(userid):
                doAdd = True
        elif eventType == self.NEW_GAME:
            if self.settings.getCustomSetting(eventType, 'mode') == 'all' or ('host' in data and self.client.players.isFriend(data['host'])):
                doAdd = True

        if doAdd:
            self.events.append((eventType, data))

        self.checkEvent()

    @QtCore.pyqtSlot()
    def on_showSettings(self):
        """ Shows a Settings Dialg with all registered notifications modules  """
        self.settings.show()

    def showEvent(self):
        """
        Display the next event in the queue as popup

        Pops event from queue and checks if it is showable as per settings
        If event is showable, process event data and then feed it into notification dialog

        Returns True if showable event found, False otherwise
        """

        event = self.events.pop(0)

        eventType = event[0]
        data = event[1]
        pixmap = None
        text = str(data)
        if eventType == self.USER_ONLINE:
            userid = data['user']
            pixmap = self.user
            text = '<html>%s<br><font color="silver" size="-2">joined</font> %s</html>' % (self.client.players[userid].login, data['channel'])
        elif eventType == self.NEW_GAME:

            preview = maps.preview(data['mapname'], pixmap=True)
            if preview:
                pixmap = preview.scaled(80, 80)

            #TODO: outsource as function?
            mod = data.get('featured_mod')
            mods = data.get('sim_mods')

            modstr = ''
            if (mod != 'faf' or mods):
                modstr = mod
                if mods:
                    if mod == 'faf':modstr = ", ".join(list(mods.values()))
                    else: modstr = mod + " & " + ", ".join(list(mods.values()))
                    if len(modstr) > 20: modstr = modstr[:15] + "..."

            modhtml = '' if (modstr == '') else '<br><font size="-4"><font color="red">mods</font> %s</font>' % modstr
            text = '<html>%s<br><font color="silver" size="-2">on</font> %s%s</html>' % (data['title'], maps.getDisplayName(data['mapname']), modhtml)

        self.dialog.newEvent(pixmap, text, self.settings.popup_lifetime, self.settings.soundEnabled(eventType))

    def checkEvent(self):
        """
        Checks that we are in correct state to show next notification popup

        This means:
            * There need to be events pending
            * There must be no notification showing right now (i.e. notification dialog hidden)
            * Game isn't running, or ingame notifications are enabled

        """
        if (len(self.events) > 0 and self.dialog.isHidden()
            and (
                not self.game_running
                or self.settings.ingame_notifications == IngameNotification.ENABLE
                )
            ):
            self.showEvent()
