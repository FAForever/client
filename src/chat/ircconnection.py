from PyQt5.QtCore import QObject, QSocketNotifier, QTimer, pyqtSignal
import logging
import sys

from chat import irclib
from chat.irclib import SimpleIRCClient, IRCError
from model.chat.chatline import ChatLine
from model.chat.channel import ChannelID, ChannelType
import util
import re

logger = logging.getLogger(__name__)
PONG_INTERVAL = 60000  # milliseconds between pongs
IRC_ELEVATION = '%@~%+&'


def user2name(user):
    return (user.split('!')[0]).strip(IRC_ELEVATION)


def parse_irc_source(src):
    """
    :param src: IRC source argument
    :return: (username, id, elevation, hostname)
    """
    try:
        username, tail = src.split('!')
    except ValueError:
        username = src.split('!')[0]
        tail = None

    if username[0] in IRC_ELEVATION:
        elevation, username = username[0], username[1:]
    else:
        elevation = None

    if tail is not None:
        id, hostname = tail.split('@')
        try:
            id = int(id)
        except ValueError:
            id = -1
    else:
        id = -1
        hostname = None

    return username, id, elevation, hostname


class ChatterInfo:
    def __init__(self, name, hostname, elevation):
        self.name = name
        self.hostname = hostname
        self.elevation = elevation


class IrcSignals(QObject):
    new_line = pyqtSignal(object, object)
    new_server_message = pyqtSignal(str)
    new_channel_chatters = pyqtSignal(object, list)
    channel_chatters_left = pyqtSignal(object, list)
    chatters_quit = pyqtSignal(list)
    quit_channel = pyqtSignal(object)
    chatter_renamed = pyqtSignal(str, str)
    new_chatter_elevation = pyqtSignal(object, object, str, str)
    new_channel_topic = pyqtSignal(object, str)
    connected = pyqtSignal()
    disconnected = pyqtSignal()

    def __init__(self):
        QObject.__init__(self)


class IrcConnection(IrcSignals, SimpleIRCClient):

    def __init__(self, host, port, ssl=False):
        IrcSignals.__init__(self)
        SimpleIRCClient.__init__(self)

        self.host = host
        self.port = port
        self.ssl = ssl
        self._password = None
        self._nick = None

        self._notifier = None
        self._timer = QTimer()
        self._timer.timeout.connect(self.once)

        self._nickserv_registered = False
        self._identified = False

    def disconnect(self):
        self.irc_disconnect()
        if self._notifier is not None:
            self._notifier.activated.disconnect(self.once)
            self._notifier = None

    def connect(self, nick, username, password):
        logger.info("Connecting to IRC at: {}:{}. TLS: {}".format(
            self.host, self.port, self.ssl))

        self._nick = nick
        self._username = username
        self._password = password

        try:
            self.irc_connect(self.host, self.port, nick, ssl=self.ssl,
                             ircname=nick, username=username)
            self._notifier = QSocketNotifier(
                    self.ircobj.connections[0]._get_socket().fileno(),
                    QSocketNotifier.Read,
                    self)
            self._notifier.activated.connect(self.once)
            self._timer.start(PONG_INTERVAL)
            return True
        except IRCError:
            logger.debug("Unable to connect to IRC server.")
            logger.error("IRC Exception", exc_info=sys.exc_info())
            return False

    def is_connected(self):
        return self.connection.is_connected()

    def _only_if_connected(fn):
        def _if_connected(self, *args, **kwargs):
            if not self.connection.is_connected():
                return False
            fn(self, *args, **kwargs)
            return True
        return _if_connected

    @_only_if_connected
    def set_topic(self, channel, topic):
        self.connection.topic(channel, topic)

    @_only_if_connected
    def send_message(self, target, text):
        self.connection.privmsg(target, text)

    @_only_if_connected
    def send_action(self, target, text):
        self.connection.action(target, text)

    @_only_if_connected
    def join(self, channel):
        self.connection.join(channel)

    @_only_if_connected
    def part(self, channel, reason=""):
        self.connection.part([channel], reason)

    @property
    def nickname(self):
        return self._nick

    def _log_event(self, e):
        text = '\n'.join(e.arguments())
        self.new_server_message.emit("[{}: {}->{}] {}".format(e.eventtype(),
                                                              e.source(),
                                                              e.target(),
                                                              text))

    def _log_client_message(self, text):
        self.new_server_message.emit(text)

    def on_welcome(self, c, e):
        self._log_event(e)

    def _send_nickserv_creds(self, fmt):
        self._log_client_message(fmt.format(self._nick,
                                            '[password_hash]'))

        msg = fmt.format(self._nick, util.md5text(self._password))
        self.connection.privmsg('NickServ', msg)

    def _nickserv_identify(self):
        if self._identified:
            return
        self._send_nickserv_creds('identify {} {}')

    def _nickserv_register(self):
        if self._nickserv_registered:
            return
        self._send_nickserv_creds('register {} {}@users.faforever.com')
        self._nickserv_registered = True

    def on_identified(self):
        if self.connection.get_nickname != self._nick:
            self._send_nickserv_creds('recover {} {}')
        self.connected.emit()

    def on_version(self, c, e):
        msg = "Forged Alliance Forever " + util.VERSION_STRING
        self.connection.privmsg(e.source(), msg)

    def on_motd(self, c, e):
        self._log_event(e)
        self._nickserv_identify()

    def on_endofmotd(self, c, e):
        self._log_event(e)

    def on_namreply(self, c, e):
        self._log_event(e)
        channel = ChannelID(ChannelType.PUBLIC, e.arguments()[1])
        listing = e.arguments()[2].split()

        def userdata(data):
            name = data.strip(IRC_ELEVATION)
            elevation = data[0] if data[0] in IRC_ELEVATION else None
            hostname = ''
            return ChatterInfo(name, hostname, elevation)

        chatters = [userdata(user) for user in listing]
        self.new_channel_chatters.emit(channel, chatters)

    def on_whoisuser(self, c, e):
        self._log_event(e)

    def _event_to_chatter(self, e):
        name, _id, elevation, hostname = parse_irc_source(e.source())
        return ChatterInfo(name, hostname, elevation)

    def on_join(self, c, e):
        channel = ChannelID(ChannelType.PUBLIC, e.target())
        chatter = self._event_to_chatter(e)
        self.new_channel_chatters.emit(channel, [chatter])

    def on_part(self, c, e):
        channel = ChannelID(ChannelType.PUBLIC, e.target())
        chatter = self._event_to_chatter(e)
        self.channel_chatters_left.emit(channel, [chatter])
        if chatter.name == self._nick:
            self.quit_channel.emit(channel)

    def on_quit(self, c, e):
        chatter = self._event_to_chatter(e)
        self.chatters_quit.emit([chatter])

    def on_nick(self, c, e):
        oldnick = user2name(e.source())
        newnick = e.target()

        self.chatter_renamed(oldnick, newnick)
        self._log_event(e)

    def on_mode(self, c, e):
        if len(e.arguments()) < 2:
            return

        name, _, elevation, hostname = parse_irc_source(e.arguments()[1])
        chatter = ChatterInfo(name, hostname, elevation)
        modes = e.arguments()[0]
        channel = ChannelID(ChannelType.PUBLIC, e.target())
        added, removed = self._parse_elevation(modes)
        self.new_chatter_elevation.emit(channel, chatter,
                                        added, removed)

    def _parse_elevation(self, modes):
        add = re.compile(".*\+([a-z]+)")
        remove = re.compile(".*\-([a-z]+)")
        mode_to_elevation = {"o": "Q", "q": "~", "v": "+"}

        def get_elevations(expr):
            match = re.search(expr, modes)
            if not match:
                return ""
            match = match.group(1)
            return ''.join(mode_to_elevation[c] for c in match)

        return get_elevations(add), get_elevations(remove)

    def on_umode(self, c, e):
        self._log_event(e)

    def on_notice(self, c, e):
        self._log_event(e)

    def on_topic(self, c, e):
        channel = ChannelID(ChannelType.PUBLIC, e.target())
        announcement = " ".join(e.arguments())
        self.new_channel_topic.emit(channel, announcement)

    def on_currenttopic(self, c, e):
        channel = ChannelID(ChannelType.PUBLIC, e.arguments()[0])
        announcement = " ".join(e.arguments()[1:])
        self.new_channel_topic.emit(channel, announcement)

    def on_topicinfo(self, c, e):
        self._log_event(e)

    def on_list(self, c, e):
        self._log_event(e)

    def on_bannedfromchan(self, c, e):
        self._log_event(e)

    def _emit_line(self, chatter, target, channel_type, text):
        if channel_type == ChannelType.PUBLIC:
            channel_name = target
        else:
            channel_name = chatter.name
        chid = ChannelID(channel_type, channel_name)
        line = ChatLine(chatter.name, text)
        self.new_line.emit(line, chid)

    def on_pubmsg(self, c, e):
        chatter = self._event_to_chatter(e)
        target = e.target()
        text = "\n".join(e.arguments())

        self._emit_line(chatter, target, ChannelType.PUBLIC, text)

    def on_privnotice(self, c, e):
        chatter = self._event_to_chatter(e)
        notice = e.arguments()[0]
        prefix = notice.split(" ")[0]
        target = prefix.strip("[]")

        if chatter.name.lower() == 'nickserv':
            self._log_event(e)
            self._handle_nickserv_message(notice)
            return

        if target == '*':
            self._log_event(e)
        else:
            text = "\n".join(e.arguments()).lstrip(prefix)
            self._emit_line(chatter, target, ChannelType.PRIVATE, text)

    def _handle_nickserv_message(self, notice):
        if (notice.find("registered under your account") >= 0 or
           notice.find("Password accepted") >= 0):
            if not self._identified:
                self._identified = True
                self.on_identified()
        elif notice.find("isn't registered") >= 0:
            self._nickserv_register()
        elif notice.find("RELEASE") >= 0:
            self.connection.privmsg('release {} {}')
        elif notice.find("hold on") >= 0:
            self.connection.nick(self._nick)

    def on_disconnect(self, c, e):
        self._identified = False
        self._timer.stop()
        self.disconnected.emit()

    def on_privmsg(self, c, e):
        chatter = self._event_to_chatter(e)
        text = "\n".join(e.arguments())
        self._emit_line(chatter.name, None, ChannelType.PRIVATE, text)

    def on_action(self, c, e):
        chatter = self._event_to_chatter(e)
        target = e.target()
        text = "\n".join(e.arguments())
        chtype = (ChannelType.PUBLIC if irclib.is_channel(target)
                  else ChannelType.PRIVATE)
        self._emit_line(chatter, target, chtype, text)

    def on_nosuchnick(self, c, e):
        self._nickserv_register()

    def on_default(self, c, e):
        self._log_event(e)
        if "Nickname is already in use." in "\n".join(e.arguments()):
            self.connection.nick(self._nick + "_")

    def on_kick(self, c, e):
        pass
