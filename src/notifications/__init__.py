from PyQt4 import QtCore

import util
from fa import maps
from multiprocessing import Lock
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
        self.lock = Lock()


        client.gameEnter.connect(self.gameEnter)
        client.gameExit.connect(self.gameExit)

        self.user = util.icon("client/user.png", pix=True)

    def gameEnter(self):
        self.game_running = True

    def gameExit(self):
        self.game_running = False
        # kick the queue
        if self.settings.ingame_notifications == IngameNotification.QUEUE:
            self.nextEvent()

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
        self.events.append((eventType, data))
        if self.dialog.isHidden() and not (self.settings.ingame_notifications == IngameNotification.QUEUE and self.game_running):
            self.showEvent()

    @QtCore.pyqtSlot()
    def on_showSettings(self):
        """ Shows a Settings Dialg with all registered notifications modules  """
        self.settings.show()

    def showEvent(self):
        """ Display the next event in the queue as popup  """
        self.lock.acquire()
        event = self.events[0]
        del self.events[0]
        self.lock.release()

        eventType = event[0]
        data = event[1]
        pixmap = None
        text = str(data)
        if eventType == self.USER_ONLINE:
            userid = data['user']
            if self.settings.getCustomSetting(eventType, 'mode') == 'friends' and not self.client.players.isFriend(userid):
                self.nextEvent()
                return
            pixmap = self.user
            text = '<html>%s<br><font color="silver" size="-2">joined</font> %s</html>' % (self.client.players[userid].login, data['channel'])
        elif eventType == self.NEW_GAME:
            if self.settings.getCustomSetting(eventType, 'mode') == 'friends' and ('host' not in data or not self.client.players.isFriend(data['host'])):
                self.nextEvent()
                return

            preview = maps.preview(data['mapname'], pixmap=True)
            if preview:
                pixmap = preview.scaled(80, 80)

            #TODO: outsource as function?
            mod = None if 'featured_mod' not in data else data['featured_mod']
            mods = None if 'sim_mods' not in data else data['sim_mods']

            modstr = ''
            if (mod != 'faf' or mods):
                modstr = mod
                if mods:
                    if mod == 'faf':modstr = ", ".join(mods.values())
                    else: modstr = mod + " & " + ", ".join(mods.values())
                    if len(modstr) > 20: modstr = modstr[:15] + "..."

            modhtml = '' if (modstr == '') else '<br><font size="-4"><font color="red">mods</font> %s</font>' % modstr
            text = '<html>%s<br><font color="silver" size="-2">on</font> %s%s</html>' % (data['title'], maps.getDisplayName(data['mapname']), modhtml)

        self.dialog.newEvent(pixmap, text, self.settings.popup_lifetime, self.settings.soundEnabled(eventType))

    def nextEvent(self):
        if self.events:
            self.showEvent()
