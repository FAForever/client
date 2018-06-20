from PyQt5 import QtCore

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
    GAME_FULL = 'game_full'

    def __init__(self, client, gameset, playerset, me):
        self.client = client
        self.me = me

        self.settings = NsSettingsDialog(self.client)
        self.dialog = NotificationDialog(self.client, self.settings)
        self.events = []
        self.disabledStartup = True
        self.game_running = False

        client.game_enter.connect(self.gameEnter)
        client.game_exit.connect(self.gameExit)
        client.game_full.connect(self._gamefull)
        gameset.newLobby.connect(self._newLobby)
        playerset.added.connect(self._newPlayer)

        self.user = util.THEME.icon("client/user.png", pix=True)

    def _newPlayer(self, player):
        if self.isDisabled() or not self.settings.popupEnabled(self.USER_ONLINE):
            return

        if self.me.player is not None and self.me.player == player:
            return

        notify_mode = self.settings.getCustomSetting(self.USER_ONLINE, 'mode')
        if notify_mode != 'all' and not self.me.relations.model.is_friend(player.id):
            return

        self.events.append((self.USER_ONLINE, player.copy()))
        self.checkEvent()

    def _newLobby(self, game):
        if self.isDisabled() or not self.settings.popupEnabled(self.NEW_GAME):
            return

        host = game.host_player
        notify_mode = self.settings.getCustomSetting(self.NEW_GAME, 'mode')
        if notify_mode != 'all':
            if host is None or not self.me.relations.model.is_friend(host):
                return

        self.events.append((self.NEW_GAME, game.copy()))
        self.checkEvent()

    def _gamefull(self):
        if self.isDisabled() or not self.settings.popupEnabled(self.GAME_FULL):
            return
        self.events.append((self.GAME_FULL, None))
        self.checkEvent()

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
            player = data
            pixmap = self.user
            text = '<html>%s<br><font color="silver" size="-2">is online</font></html>' % \
                   (player.login)
        elif eventType == self.NEW_GAME:
            game = data
            preview = maps.preview(game.mapname, pixmap=True)
            if preview:
                pixmap = preview.scaled(80, 80)

            # TODO: outsource as function?
            mod = game.featured_mod
            mods = game.sim_mods

            modstr = ''
            if mod != 'faf' or mods:
                modstr = mod
                if mods:
                    if mod == 'faf':
                        modstr = ", ".join(list(mods.values()))
                    else:
                        modstr = mod + " & " + ", ".join(list(mods.values()))
                    if len(modstr) > 20:
                        modstr = modstr[:15] + "..."

            modhtml = '' if (modstr == '') else '<br><font size="-4"><font color="red">mods</font> %s</font>' % modstr
            text = '<html>%s<br><font color="silver" size="-2">on</font> %s%s</html>' % \
                   (game.title, maps.getDisplayName(game.mapname), modhtml)
        elif eventType == self.GAME_FULL:
            pixmap = self.user
            text = '<html><br><font color="silver" size="-2">Game is full.</font></html>'
        self.dialog.newEvent(pixmap, text, self.settings.popup_lifetime, self.settings.soundEnabled(eventType))

    def checkEvent(self):
        """
        Checks that we are in correct state to show next notification popup

        This means:
            * There need to be events pending
            * There must be no notification showing right now (i.e. notification dialog hidden)
            * Game isn't running, or ingame notifications are enabled

        """
        if (len(self.events) > 0 and self.dialog.isHidden() and
                (not self.game_running or self.settings.ingame_notifications == IngameNotification.ENABLE)):
            self.showEvent()
