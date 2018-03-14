import logging

logger = logging.getLogger(__name__)

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtNetwork import QNetworkAccessManager
from PyQt5.QtCore import QSocketNotifier, QTimer

from config import Settings, defaults
import util

import re
import sys
import chat
from chat import user2name, parse_irc_source
from chat.channel import Channel
from chat.irclib import SimpleIRCClient, ServerConnectionError

from model.ircuserset import IrcUserset
from model.ircuser import IrcUser

PONG_INTERVAL = 60000  # milliseconds between pongs

FormClass, BaseClass = util.THEME.loadUiType("chat/chat.ui")


class ChatWidget(FormClass, BaseClass, SimpleIRCClient):

    use_chat = Settings.persisted_property('chat/enabled', type=bool, default_value=True)
    irc_port = Settings.persisted_property('chat/port', type=int, default_value=6667)
    irc_host = Settings.persisted_property('chat/host', type=str, default_value='irc.' + defaults['host'])
    irc_tls = Settings.persisted_property('chat/tls', type=bool, default_value=False)

    auto_join_channels = Settings.persisted_property('chat/auto_join_channels', default_value=[])

    """
    This is the chat lobby module for the FAF client.
    It manages a list of channels and dispatches IRC events (lobby inherits from irclib's client class)
    """

    def __init__(self, client, playerset, me, *args, **kwargs):
        if not self.use_chat:
            logger.info("Disabling chat")
            return

        logger.debug("Lobby instantiating.")
        BaseClass.__init__(self, *args, **kwargs)
        SimpleIRCClient.__init__(self)

        self.setupUi(self)

        self.client = client
        self._me = me
        self._chatters = IrcUserset(playerset)
        self.channels = {}

        # avatar downloader
        self.nam = QNetworkAccessManager()
        self.nam.finished.connect(self.finish_download_avatar)

        # nickserv stuff
        self.identified = False

        # IRC parameters
        self.crucialChannels = ["#aeolus"]
        self.optionalChannels = []

        # We can't send command until the welcome message is received
        self.welcomed = False

        # Load colors and styles from theme
        self.a_style = util.THEME.readfile("chat/formatters/a_style.qss")

        # load UI perform some tweaks
        self.tabBar().setTabButton(0, 1, None)

        self.tabCloseRequested.connect(self.close_channel)

        # Hook with client's connection and autojoin mechanisms
        self.client.authorized.connect(self.connect_)
        self.client.autoJoin.connect(self.auto_join)
        self.channelsAvailable = []

        self._notifier = None
        self._timer = QTimer()
        self._timer.timeout.connect(self.once)

        # disconnection checks
        self.canDisconnect = False

    def disconnect_(self):
        self.canDisconnect = True
        try:
            self.irc_disconnect()
        except ServerConnectionError:
            pass
        if self._notifier:
            self._notifier.activated.disconnect(self.once)
            self._notifier = None

    @QtCore.pyqtSlot(object)
    def connect_(self, player):
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

    def finish_download_avatar(self, reply):
        """ this take care of updating the avatars of players once they are downloaded """
        img = QtGui.QImage()
        img.loadFromData(reply.readAll())
        url = reply.url().toString()
        if not util.respix(url):
            util.addrespix(url, QtGui.QPixmap(img))

        for chatter in util.curDownloadAvatar(url):
            # FIXME - hack to prevent touching chatter if it was removed
            channel = chatter.channel
            ircuser = chatter.user
            if ircuser in channel.chatters:
                chatter.update_avatar()
        util.delDownloadAvatar(url)

    def add_channel(self, name, channel, index = None):
        self.channels[name] = channel
        if index is None:
            self.addTab(self.channels[name], name)
        else:
            self.insertTab(index, self.channels[name], name)

    def sort_channels(self):
        for channel in self.channels.values():
            channel.sort_chatters()

    def update_channels(self):
        for channel in self.channels.values():
            channel.update_chatters()

    def close_channel(self, index):
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
            self.send_msg(channel, broadcast)

    def set_topic(self, chan, topic):
        self.connection.topic(chan, topic)

    def send_msg(self, target, text):
        if self.connection.is_connected():
            self.connection.privmsg(target, text)
            return True
        else:
            logger.error("IRC connection lost.")
            for channel in self.crucialChannels:
                if channel in self.channels:
                    self.channels[channel].print_raw("Server", "IRC is disconnected")
            return False

    def send_action(self, target, text):
        if self.connection.is_connected():
            self.connection.action(target, text)
            return True
        else:
            logger.error("IRC connection lost.")
            for channel in self.crucialChannels:
                if channel in self.channels:
                    self.channels[channel].print_action("IRC", "was disconnected.")
            return False

    def open_query(self, chatter, activate=False):
        # Ignore ourselves.
        if chatter.name == self.client.login:
            return False

        if chatter.name not in self.channels:
            priv_chan = Channel(self, chatter.name, self._chatters, self._me, True)
            self.add_channel(chatter.name, priv_chan)

            # Add participants to private channel
            priv_chan.add_chatter(chatter)

            if self.client.me.login is not None:
                my_login = self.client.me.login
                if my_login in self._chatters:
                    priv_chan.add_chatter(self._chatters[my_login])

            if activate:
                self.setCurrentWidget(priv_chan)

        return True

    @QtCore.pyqtSlot(list)
    def auto_join(self, channels):
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

    def should_ignore(self, chatter):
        # Don't ignore mods from any crucial channels
        if any(chatter.is_mod(c) for c in self.crucialChannels):
            return False
        if chatter.player is None:
            return self.client.me.isFoe(name=chatter.name)
        else:
            return self.client.me.isFoe(id_=chatter.player.id)

# SimpleIRCClient Class Dispatcher Attributes follow here.
    def on_welcome(self, c, e):
        self.log_event(e)
        self.welcomed = True

    def nickserv_identify(self):
        if not self.identified:
            self.serverLogArea.appendPlainText("[Identify as : %s]" % self.client.login)
            self.connection.privmsg('NickServ', 'identify %s %s' % (self.client.login, util.md5text(self.client.password)))

    def on_identified(self):
        if self.connection.get_nickname() != self.client.login :
            self.serverLogArea.appendPlainText("[Retrieving our nickname : %s]" % (self.client.login))
            self.connection.privmsg('NickServ', 'recover %s %s' % (self.client.login, util.md5text(self.client.password)))
        # Perform any pending autojoins (client may have emitted autoJoin signals before we talked to the IRC server)
        self.auto_join(self.optionalChannels)
        self.auto_join(self.crucialChannels)
        self.auto_join(self.auto_join_channels)
        self._schedule_actions_at_player_available()

    def _schedule_actions_at_player_available(self):
        self._me.playerAvailable.connect(self._at_player_available)
        if self._me.player is not None:
            self._at_player_available()

    def _at_player_available(self):
        self._me.playerAvailable.disconnect(self._at_player_available)
        self._autojoin_newbie_channel()

    def _autojoin_newbie_channel(self):
        if not self.client.useNewbiesChannel:
            return
        game_number_threshold = 50
        if self.client.me.player.number_of_games <= game_number_threshold:
            self.auto_join(["#newbie"])

    def nickserv_register(self):
        if hasattr(self, '_nickserv_registered'):
            return
        self.connection.privmsg('NickServ', 'register %s %s' % (util.md5text(self.client.password), '{}@users.faforever.com'.format(self.client.me.login)))
        self._nickserv_registered = True
        self.auto_join(self.optionalChannels)
        self.auto_join(self.crucialChannels)

    def on_version(self, c, e):
        self.connection.privmsg(e.source(), "Forged Alliance Forever " + util.VERSION_STRING)

    def on_motd(self, c, e):
        self.log_event(e)
        self.nickserv_identify()

    def on_endofmotd(self, c, e):
        self.log_event(e)

    def on_namreply(self, c, e):
        self.log_event(e)
        channel = e.arguments()[1]
        listing = e.arguments()[2].split()

        for user in listing:
            name = user.strip(chat.IRC_ELEVATION)
            elevation = user[0] if user[0] in chat.IRC_ELEVATION else None
            hostname = ''
            self._add_chatter(name, hostname)
            self._add_chatter_channel(self._chatters[name], elevation,
                                      channel, False)

        logger.debug("Added " + str(len(listing)) + " Chatters")

    def _add_chatter(self, name, hostname):
        if name not in self._chatters:
            self._chatters[name] = IrcUser(name, hostname)
        else:
            self._chatters[name].update(hostname=hostname)

    def _remove_chatter(self, name):
        if name not in self._chatters:
            return
        del self._chatters[name]
        # Channels listen to 'chatter removed' signal on their own

    def _add_chatter_channel(self, chatter, elevation, channel, join):
        chatter.set_elevation(channel, elevation)
        self.channels[channel].add_chatter(chatter, join)

    def _remove_chatter_channel(self, chatter, channel, msg):
        chatter.set_elevation(channel, None)
        self.channels[channel].remove_chatter(msg)

    def on_whoisuser(self, c, e):
        self.log_event(e)

    def on_join(self, c, e):
        channel = e.target()

        # If we're joining, we need to open the channel for us first.
        if channel not in self.channels:
            newch = Channel(self, channel, self._chatters, self._me)
            if channel.lower() in self.crucialChannels:
                self.add_channel(channel, newch, 1)  # CAVEAT: This is assumes a server tab exists.
                self.client.localBroadcast.connect(newch.print_raw)
                newch.print_announcement("Welcome to Forged Alliance Forever!", "red", "+3")
                wiki_link = Settings.get("WIKI_URL")
                wiki_msg = "Check out the wiki: {} for help with common issues.".format(wiki_link)
                newch.print_announcement(wiki_msg, "white", "+1")
                newch.print_announcement("", "black", "+1")
                newch.print_announcement("", "black", "+1")
            else:
                self.add_channel(channel, newch)

            if channel.lower() in self.crucialChannels:  # Make the crucial channels not closeable, and make the last one the active one
                self.setCurrentWidget(self.channels[channel])
                self.tabBar().setTabButton(self.currentIndex(), QtWidgets.QTabBar.RightSide, None)

        name, _id, elevation, hostname = parse_irc_source(e.source())
        self._add_chatter(name, hostname)
        self._add_chatter_channel(self._chatters[name], elevation,
                                  channel, True)

    def on_part(self, c, e):
        channel = e.target()
        name = user2name(e.source())
        if name not in self._chatters:
            return
        chatter = self._chatters[name]

        if name == self.client.login:   # We left ourselves.
            self.removeTab(self.indexOf(self.channels[channel]))
            del self.channels[channel]
        else:                           # Someone else left
            self._remove_chatter_channel(chatter, channel, "left.")

    def on_quit(self, c, e):
        name = user2name(e.source())
        self._remove_chatter(name)

    def on_nick(self, c, e):
        oldnick = user2name(e.source())
        newnick = e.target()
        if oldnick not in self._chatters:
            return

        self._chatters[oldnick].update(name=newnick)
        self.log_event(e)

    def on_mode(self, c, e):
        if e.target() not in self.channels:
            return
        if len(e.arguments()) < 2:
            return
        name = user2name(e.arguments()[1])
        if name not in self._chatters:
            return
        chatter = self._chatters[name]

        self.elevate_chatter(chatter, e.target(), e.arguments()[0])

    def elevate_chatter(self, chatter, channel, modes):
        add = re.compile(".*\+([a-z]+)")
        remove = re.compile(".*\-([a-z]+)")

        addmatch = re.search(add, modes)
        if addmatch:
            modes = addmatch.group(1)
            mode = None
            if "v" in modes:
                mode = "+"
            if "o" in modes:
                mode = "@"
            if "q" in modes:
                mode = "~"
            if mode is not None:
                chatter.set_elevation(channel, mode)

        removematch = re.search(remove, modes)
        if removematch:
            modes = removematch.group(1)
            el = chatter.elevation[channel]
            chatter_mode = {"@": "o", "~": "q", "+": "v"}[el]
            if chatter_mode in modes:
                chatter.set_elevation(channel, None)

    def on_umode(self, c, e):
        self.log_event(e)

    def on_notice(self, c, e):
        self.log_event(e)

    def on_topic(self, c, e):
        channel = e.target()
        if channel in self.channels:
            self.channels[channel].set_announce_text(" ".join(e.arguments()))

    def on_currenttopic(self, c, e):
        channel = e.arguments()[0]
        if channel in self.channels:
            self.channels[channel].set_announce_text(" ".join(e.arguments()[1:]))

    def on_topicinfo(self, c, e):
        self.log_event(e)

    def on_list(self, c, e):
        self.log_event(e)

    def on_bannedfromchan(self, c, e):
        self.log_event(e)

    def on_pubmsg(self, c, e):
        name, id, elevation, hostname = parse_irc_source(e.source())
        target = e.target()
        if name not in self._chatters or target not in self.channels:
            return

        if not self.should_ignore(self._chatters[name]):
            self.channels[target].print_msg(name, "\n".join(e.arguments()))

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
                self.nickserv_register()

            elif notice.find("RELEASE") >= 0:
                self.connection.privmsg('nickserv', 'release %s %s' % (self.client.login, util.md5text(self.client.password)))

            elif notice.find("hold on") >= 0:
                self.connection.nick(self.client.login)

        message = "\n".join(e.arguments()).lstrip(prefix)
        if target in self.channels:
            self.channels[target].print_msg(source, message)
        elif source == "Global":
            for channel in self.channels:
                if not channel in self.crucialChannels:
                    continue
                self.channels[channel].print_announcement(message, "yellow", "+2")
        elif source == "AeonCommander":
            for channel in self.channels:
                if not channel in self.crucialChannels:
                    continue
                self.channels[channel].print_msg(source, message)
        else:
            self.serverLogArea.appendPlainText("%s: %s" % (source, notice))

    def on_disconnect(self, c, e):
        if not self.canDisconnect:
            logger.warning("IRC disconnected - reconnecting.")
            self.serverLogArea.appendPlainText("IRC disconnected - reconnecting.")
            self.identified = False
            self._timer.stop()
            self.connect_(self.client.me.player)

    def on_privmsg(self, c, e):
        name, id, elevation, hostname = parse_irc_source(e.source())
        if name not in self._chatters:
            return
        chatter = self._chatters[name]

        if self.should_ignore(chatter):
            return

        # Create a Query if it's not open yet, and post to it if it exists.
        if self.open_query(chatter):
            self.channels[name].print_msg(name, "\n".join(e.arguments()))

    def on_action(self, c, e):
        name, id, elevation, hostname = parse_irc_source(e.source())
        if name not in self._chatters:
            return
        chatter = self._chatters[name]
        target = e.target()

        if self.should_ignore(chatter):
            return

        # Create a Query if it's not an action intended for a channel
        if target not in self.channels:
            self.open_query(chatter)
            self.channels[name].print_action(name, "\n".join(e.arguments()))
        else:
            self.channels[target].print_action(name, "\n".join(e.arguments()))

    def on_nosuchnick(self, c, e):
        self.nickserv_register()

    def on_default(self, c, e):
        self.serverLogArea.appendPlainText("[%s: %s->%s]" % (e.eventtype(), e.source(), e.target()) + "\n".join(e.arguments()))
        if "Nickname is already in use." in "\n".join(e.arguments()):
            self.connection.nick(self.client.login + "_")

    def on_kick(self, c, e):
        pass
