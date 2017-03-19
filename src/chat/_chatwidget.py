import logging

logger = logging.getLogger(__name__)

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtNetwork import QNetworkAccessManager
from PyQt5.QtCore import QSocketNotifier, QTimer

from config import Settings, defaults
import util

import sys
import chat
from chat import user2name, parse_irc_source
from chat.channel import Channel
from chat.irclib import SimpleIRCClient
import notifications as ns

PONG_INTERVAL = 60000  # milliseconds between pongs

FormClass, BaseClass = util.loadUiType("chat/chat.ui")


class ChatWidget(FormClass, BaseClass, SimpleIRCClient):

    use_chat = Settings.persisted_property('chat/enabled', type=bool, default_value=True)
    irc_port = Settings.persisted_property('chat/port', type=int, default_value=6667)
    irc_host = Settings.persisted_property('chat/host', type=str, default_value='irc.' + defaults['host'])
    irc_tls = Settings.persisted_property('chat/tls', type=bool, default_value=False)

    """
    This is the chat lobby module for the FAF client.
    It manages a list of channels and dispatches IRC events (lobby inherits from irclib's client class)
    """
    def __init__(self, client, *args, **kwargs):
        if not self.use_chat:
            logger.info("Disabling chat")
            return

        logger.debug("Lobby instantiating.")
        BaseClass.__init__(self, *args, **kwargs)
        SimpleIRCClient.__init__(self)

        self.setupUi(self)

        # CAVEAT: These will fail if loaded before theming is loaded
        import json
        chat.OPERATOR_COLORS = json.loads(util.readfile("chat/formatters/operator_colors.json"))

        self.client = client
        self.channels = {}

        # avatar downloader
        self.nam = QNetworkAccessManager()
        self.nam.finished.connect(self.finishDownloadAvatar)

        # nickserv stuff
        self.identified = False

        # IRC parameters
        self.crucialChannels = ["#aeolus"]
        self.optionalChannels = []

        # We can't send command until the welcome message is received
        self.welcomed = False

        # Load colors and styles from theme
        self.a_style = util.readfile("chat/formatters/a_style.qss")

        # load UI perform some tweaks
        self.tabBar().setTabButton(0, 1, None)

        # add self to client's window
        self.client.chatTab.layout().addWidget(self)
        self.tabCloseRequested.connect(self.closeChannel)

        # Hook with client's connection and autojoin mechanisms
        self.client.authorized.connect(self.connect)
        self.client.autoJoin.connect(self.autoJoin)
        self.channelsAvailable = []

        self._notifier = None
        self._timer = QTimer()
        self._timer.timeout.connect(self.once)

        # disconnection checks
        self.canDisconnect = False

    def disconnect(self):
        self.canDisconnect = True
        self.irc_disconnect()
        if self._notifier:
            self._notifier.activated.disconnect(self.once)
            self._notifier = None

    @QtCore.pyqtSlot(object)
    def connect(self, player):
        try:
            logger.info("Connecting to IRC at: {}:{}. TLS: {}".format(self.irc_host, self.irc_port, self.irc_tls))
            self.irc_connect(self.irc_host,
                             self.irc_port,
                             player.login,
                             ssl=self.irc_tls,
                             ircname=player.login,
                             username=player.id)
            self._notifier = QSocketNotifier(self.ircobj.connections[0]._get_socket().fileno(), QSocketNotifier.Read, self)
            self._notifier.activated.connect(self.once)
            self._timer.start(PONG_INTERVAL)

        except:
            logger.debug("Unable to connect to IRC server.")
            self.serverLogArea.appendPlainText("Unable to connect to the chat server, but you should still be able to host and join games.")
            logger.error("IRC Exception", exc_info=sys.exc_info())

    def finishDownloadAvatar(self, reply):
        """ this take care of updating the avatars of players once they are downloaded """
        img = QtGui.QImage()
        img.loadFromData(reply.readAll())
        pix = util.respix(reply.url().toString())
        if pix:
            pix = QtGui.QIcon(QtGui.QPixmap(img))
        else:
            util.addrespix(reply.url().toString(), QtGui.QPixmap(img))

        for player in util.curDownloadAvatar(reply.url().toString()):
            for channel in self.channels:
                if player in self.channels[channel].chatters :
                    self.channels[channel].chatters[player].avatarItem.setIcon(QtGui.QIcon(util.respix(reply.url().toString())))
                    self.channels[channel].chatters[player].avatarItem.setToolTip(self.channels[channel].chatters[player].avatarTip)

    def addChannel(self, name, channel, index = None):
        self.channels[name] = channel
        if index is None:
            self.addTab(self.channels[name], name)
        else:
            self.insertTab(index, self.channels[name], name)

    def closeChannel(self, index):
        """
        Closes a channel tab.
        """
        channel = self.widget(index)
        for name in self.channels:
                if self.channels[name] is channel:
                    if not self.channels[name].private and self.connection.is_connected():  # Channels must be parted (if still connected)
                        self.connection.part([name], "tab closed")
                    else:
                        # Queries and disconnected channel windows can just be closed
                        self.removeTab(index)
                        del self.channels[name]

                    break

    @QtCore.pyqtSlot(str)
    def announce(self, broadcast):
        """
        Notifies all crucial channels about the status of the client.
        """
        logger.debug("BROADCAST:" + broadcast)
        for channel in self.crucialChannels:
            self.sendMsg(channel, broadcast)

    def setTopic(self,chan,topic):
        self.connection.topic(chan,topic)

    def sendMsg(self, target, text):
        if self.connection.is_connected():
            self.connection.privmsg(target, text)
            return True
        else:
            logger.error("IRC connection lost.")
            for channel in self.crucialChannels:
                if channel in self.channels:
                    self.channels[channel].printRaw("Server", "IRC is disconnected")
            return False

    def sendAction(self, target, text):
        if self.connection.is_connected():
            self.connection.action(target, text)
            return True
        else:
            logger.error("IRC connection lost.")
            for channel in self.crucialChannels:
                if channel in self.channels:
                    self.channels[channel].printAction("IRC", "was disconnected.")
            return False

    def openQuery(self, name, id=-1, activate=False):
        # Ignore ourselves.
        if name == self.client.login:
            return False

        if name not in self.channels:
            self.addChannel(name, Channel(self, name, True))

            # Add participants to private channel
            self.channels[name].addChatter(name, id)
            self.channels[name].addChatter(self.client.login, self.client.me.id)

        if activate:
            self.setCurrentWidget(self.channels[name])

        return True

    @QtCore.pyqtSlot(list)
    def autoJoin(self, channels):
        for channel in channels:
            if channel in self.channels:
                continue
            if (self.connection.is_connected()) and self.welcomed:
                # directly join
                self.connection.join(channel)
            else:
                # Note down channels for later.
                self.optionalChannels.append(channel)

    def join(self, channel):
        if channel not in self.channels:
            self.connection.join(channel)

    def log_event(self, e):
        self.serverLogArea.appendPlainText("[%s: %s->%s]" % (e.eventtype(), e.source(), e.target()) + "\n".join(e.arguments()))

# SimpleIRCClient Class Dispatcher Attributes follow here.
    def on_welcome(self, c, e):
        self.log_event(e)
        self.welcomed = True

    def nickservIdentify(self):
        if not self.identified:
            self.serverLogArea.appendPlainText("[Identify as : %s]" % self.client.login)
            self.connection.privmsg('NickServ', 'identify %s %s' % (self.client.login, util.md5text(self.client.password)))

    def on_identified(self):
        if self.connection.get_nickname() != self.client.login :
            self.serverLogArea.appendPlainText("[Retrieving our nickname : %s]" % (self.client.login))
            self.connection.privmsg('NickServ', 'recover %s %s' % (self.client.login, util.md5text(self.client.password)))
        # Perform any pending autojoins (client may have emitted autoJoin signals before we talked to the IRC server)
        self.autoJoin(self.optionalChannels)
        self.autoJoin(self.crucialChannels)

    def nickservRegister(self):
        if hasattr(self, '_nickserv_registered'):
            return
        self.connection.privmsg('NickServ', 'register %s %s' % (util.md5text(self.client.password), '{}@users.faforever.com'.format(self.client.me.login)))
        self._nickserv_registered = True
        self.autoJoin(self.optionalChannels)
        self.autoJoin(self.crucialChannels)

    def on_version(self, c, e):
        self.connection.privmsg(e.source(), "Forged Alliance Forever " + util.VERSION_STRING)

    def on_motd(self, c, e):
        self.log_event(e)
        self.nickservIdentify()

    def on_endofmotd(self, c, e):
        self.log_event(e)

    def on_namreply(self, c, e):
        self.log_event(e)
        channel = e.arguments()[1]
        listing = e.arguments()[2].split()

        for user in listing:
            name = user.strip(chat.IRC_ELEVATION)
            id = self.client.players.getID(name)
            self.channels[channel].addChatter(name, id, user[0] if user[0] in chat.IRC_ELEVATION else None, '')

        logger.debug("Added " + str(len(listing)) + " Chatters")

    def on_whoisuser(self, c, e):
        self.log_event(e)

    def on_join(self, c, e):
        channel = e.target()

        # If we're joining, we need to open the channel for us first.
        if channel not in self.channels:
            newch = Channel(self, channel)
            if channel.lower() in self.crucialChannels:
                self.addChannel(channel, newch, 1)  # CAVEAT: This is assumes a server tab exists.
                self.client.localBroadcast.connect(newch.printRaw)
                newch.printAnnouncement("Welcome to Forged Alliance Forever!", "red", "+3")
                newch.printAnnouncement("Check out the wiki: http://wiki.faforever.com for help with common issues.", "white", "+1")
                newch.printAnnouncement("", "black", "+1")
                newch.printAnnouncement("", "black", "+1")
            else:
                self.addChannel(channel, newch)

            if channel.lower() in self.crucialChannels:  # Make the crucial channels not closeable, and make the last one the active one
                self.setCurrentWidget(self.channels[channel])
                self.tabBar().setTabButton(self.currentIndex(), QtWidgets.QTabBar.RightSide, None)

        name, id, elevation, hostname = parse_irc_source(e.source())
        self.channels[channel].addChatter(name, id, elevation, hostname, True)

        if channel.lower() in self.crucialChannels and name != self.client.login:
            # TODO: search better solution, that html in nick & channel no rendered
            self.client.notificationSystem.on_event(ns.Notifications.USER_ONLINE,
                                                    {'user': id, 'channel': channel})

    def on_part(self, c, e):
        channel = e.target()
        name = user2name(e.source())
        if name == self.client.login:   # We left ourselves.
            self.removeTab(self.indexOf(self.channels[channel]))
            del self.channels[channel]
        else:                           # Someone else left
            self.channels[channel].removeChatter(name, "left.")

    def on_quit(self, c, e):
        name = user2name(e.source())
        for channel in self.channels:
            if (not self.channels[channel].private) or (self.channels[channel].name == user2name(name)):
                self.channels[channel].removeChatter(name, "quit.")

    def on_nick(self, c, e):
        oldnick = user2name(e.source())
        newnick = e.target()
        for channel in self.channels:
            self.channels[channel].renameChatter(oldnick, newnick)

        self.log_event(e)

    def on_mode(self, c, e):
        if len(e.arguments()) < 2:
            return
        name = user2name(e.arguments()[1])
        if e.target() in self.channels:
            self.channels[e.target()].elevateChatter(name, e.arguments()[0])

    def on_umode(self, c, e):
        self.log_event(e)

    def on_notice(self, c, e):
        self.log_event(e)

    def on_topic(self, c, e):
        channel = e.target()
        if channel in self.channels:
            self.channels[channel].setAnnounceText(" ".join(e.arguments()))

    def on_currenttopic(self, c, e):
        channel = e.arguments()[0]
        if channel in self.channels:
            self.channels[channel].setAnnounceText(" ".join(e.arguments()[1:]))

    def on_topicinfo(self, c, e):
        self.log_event(e)

    def on_list(self, c, e):
        self.log_event(e)

    def on_bannedfromchan(self, c, e):
        self.log_event(e)

    def on_pubmsg(self, c, e):
        name, id, elevation, hostname = parse_irc_source(e.source())
        target = e.target()

        if target in self.channels and not self.client.players.isFoe(id):
            self.channels[target].printMsg(name, "\n".join(e.arguments()))

    def on_privnotice(self, c, e):
        source = user2name(e.source())
        notice = e.arguments()[0]
        prefix = notice.split(" ")[0]
        target = prefix.strip("[]")

        if source and source.lower() == 'nickserv':
            if notice.find("registered under your account") >= 0 or \
               notice.find("Password accepted") >= 0:
                if not self.identified:
                    self.identified = True
                    self.on_identified()

            elif notice.find("isn't registered") >= 0:
                self.nickservRegister()

            elif notice.find("RELEASE") >= 0:
                self.connection.privmsg('nickserv', 'release %s %s' % (self.client.login, util.md5text(self.client.password)))

            elif notice.find("hold on") >= 0:
                self.connection.nick(self.client.login)

        message = "\n".join(e.arguments()).lstrip(prefix)
        if target in self.channels:
            self.channels[target].printMsg(source, message)
        elif source == "Global":
            for channel in self.channels:
                if not channel in self.crucialChannels:
                    continue
                self.channels[channel].printAnnouncement(message, "yellow", "+2")
        elif source == "AeonCommander":
            for channel in self.channels:
                if not channel in self.crucialChannels:
                    continue
                self.channels[channel].printMsg(source, message)
        else:
            self.serverLogArea.appendPlainText("%s: %s" % (source, notice))

    def on_disconnect(self, c, e):
        if not self.canDisconnect:
            logger.warn("IRC disconnected - reconnecting.")
            self.serverLogArea.appendPlainText("IRC disconnected - reconnecting.")
            self.identified = False
            self._timer.stop()
            self.connect(self.client.me)

    def on_privmsg(self, c, e):
        name, id, elevation, hostname = parse_irc_source(e.source())

        if self.client.players.isFoe(id):
            return

        # Create a Query if it's not open yet, and post to it if it exists.
        if self.openQuery(name, id):
            self.channels[name].printMsg(name, "\n".join(e.arguments()))

    def on_action(self, c, e):
        name, id, elevation, hostname = parse_irc_source(e.source())  # user2name(e.source())
        target = e.target()

        if self.client.players.isFoe(id):
            return

        # Create a Query if it's not an action intended for a channel
        if target not in self.channels:
            self.openQuery(name,id)
            self.channels[name].printAction(name, "\n".join(e.arguments()))
        else:
            self.channels[target].printAction(name, "\n".join(e.arguments()))

    def on_nosuchnick(self, c, e):
        self.nickservRegister()

    def on_default(self, c, e):
        self.serverLogArea.appendPlainText("[%s: %s->%s]" % (e.eventtype(), e.source(), e.target()) + "\n".join(e.arguments()))
        if "Nickname is already in use." in "\n".join(e.arguments()):
            self.connection.nick(self.client.login + "_")

    def on_kick(self, c, e):
        pass
