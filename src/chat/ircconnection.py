from __future__ import annotations

import logging
import re
import sys

from irc.client import Event
from irc.client import ServerConnection
from irc.client import ServerConnectionError
from irc.client import SimpleIRCClient
from irc.client import is_channel
from PyQt6.QtCore import QObject
from PyQt6.QtCore import QTimer
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtNetwork import QNetworkReply

from src import config
from src import util
from src.api.ApiAccessors import UserApiAccessor
from src.chat.socketadapter import ConnectionFactory
from src.chat.socketadapter import ReactorForSocketAdapter
from src.model.chat.channel import ChannelID
from src.model.chat.channel import ChannelType
from src.model.chat.chatline import ChatLine
from src.model.chat.chatline import ChatLineType

logger = logging.getLogger(__name__)
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
        elevation = ""

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
    new_line = pyqtSignal(object, object, object)
    new_server_message = pyqtSignal(str)
    new_channel_chatters = pyqtSignal(object, list)
    channel_chatter_joined = pyqtSignal(object, object)
    channel_chatter_left = pyqtSignal(object, object)
    chatter_quit = pyqtSignal(object, str)
    quit_channel = pyqtSignal(object)
    chatter_renamed = pyqtSignal(str, str)
    new_chatter_elevation = pyqtSignal(object, object, str, str)
    new_channel_topic = pyqtSignal(object, str)
    connected = pyqtSignal()
    disconnected = pyqtSignal()


class Reconnector(QObject):
    def __init__(self, connection: IrcConnection) -> None:
        QObject.__init__(self)
        self.connection = connection
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.reconnect)
        self.failures = 0

    def on_connect(self) -> None:
        logger.debug("Chat reactor is connected!")
        self.failures = 0
        self.timer.stop()

    def reconnect(self) -> None:
        self.connection.begin_connection_process()

    def on_connect_failure(self, reply: QNetworkReply) -> None:
        self.failures += 1
        self.on_disconnect()

    def on_disconnect(self) -> None:
        if self.failures < 3:
            logger.info("Chat: reconnecting immediately")
            self.reconnect()
        else:
            t = self.failures * 10_000
            self.timer.start(t)
            logger.info("Scheduling chat reconnect in %.2f", t / 1000)


class IrcConnection(SimpleIRCClient, IrcSignals):
    reactor_class = ReactorForSocketAdapter

    def __init__(self, host: int, port: int) -> None:
        IrcSignals.__init__(self)
        SimpleIRCClient.__init__(self)

        self.host = host
        self.port = port
        self.api_accessor = UserApiAccessor()
        self.connect_factory = ConnectionFactory()

        self._password = None
        self._nick = None

        self._nickserv_registered = False
        self._connected = False

        self.reconnector = Reconnector(self)
        self.reactor.socket_error.connect(self.reconnector.reconnect)

    @classmethod
    def build(cls, settings: config.Settings, **kwargs) -> IrcConnection:
        port = settings.get("chat/port", 443, int)
        host = settings.get("chat/host", "chat." + config.defaults["host"], str)
        return cls(host, port)

    def setPortFromConfig(self) -> None:
        self.port = config.Settings.get("chat/port", type=int)

    def setHostFromConfig(self):
        self.host = config.Settings.get('chat/host', type=str)

    def disconnect_(self) -> None:
        self.connection.disconnect()

    def set_nick_and_username(self, nick: str, username: str) -> None:
        self._nick = nick
        self._username = username

    def begin_connection_process(self) -> None:
        self.api_accessor.get_by_endpoint(
            "/irc/ergochat/token",
            self.handle_irc_token,
            self.reconnector.on_connect_failure,
        )

    def handle_irc_token(self, data: dict) -> None:
        irc_token = data["value"]
        if self.connect_(self._nick, self._username, f"token:{irc_token}"):
            self.reconnector.on_connect()
        else:
            self.reconnector.reconnect()

    def connect_(self, nick: str, username: str, password: str) -> bool:
        logger.info("Connecting to IRC at: %s:%d", self.host, self.port)

        self._nick = nick
        self._username = username
        self._password = password

        try:
            self.connect(
                self.host,
                self.port,
                nick,
                connect_factory=self.connect_factory,
                ircname=nick,
                sasl_login=username,
                password=password,
            )
            return True
        except ServerConnectionError:
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
        text = '  |  '.join(e.arguments)
        self.new_server_message.emit(
            "[{}: {}->{}] {}".format(e.type, e.source, e.target, text),
        )

    def _log_client_message(self, text):
        self.new_server_message.emit(text)

    def on_welcome(self, c, e):
        self._log_event(e)
        if not self._connected:
            self._connected = True
            self.on_connected()

    def _send_nickserv_creds(self, fmt):
        self._log_client_message(
            fmt.format(
                nick=self._nick,
                password='[password_hash]',
            ),
        )

        msg = fmt.format(
            nick=self._nick,
            password=util.md5text(self._password),
        )
        self.connection.privmsg('NickServ', msg)

    def _nickserv_identify(self):
        self._send_nickserv_creds('identify {nick} {password}')

    def _nickserv_register(self):
        if self._nickserv_registered:
            return
        self._send_nickserv_creds(
            'register {password} {nick}@users.faforever.com',
        )
        self._nickserv_registered = True

    def _nickserv_recover_if_needed(self):
        if self.connection.get_nickname() != self._nick:
            self._send_nickserv_creds('recover {nick} {password}')

    def on_connected(self):
        self._nickserv_recover_if_needed()
        self.connected.emit()

    def on_version(self, c, e):
        msg = "Forged Alliance Forever " + util.VERSION_STRING
        self.connection.privmsg(e.source, msg)

    def on_motd(self, c, e):
        self._log_event(e)

    def on_endofmotd(self, c, e):
        self._log_event(e)
        self.connection.whois(self._nick)
        self._nickserv_identify()

    def on_namreply(self, c, e):
        channel = ChannelID(ChannelType.PUBLIC, e.arguments[1])
        listing = e.arguments[2].split()

        def userdata(data):
            name = data.strip(IRC_ELEVATION)
            elevation = data[0] if data[0] in IRC_ELEVATION else ""
            hostname = ''
            return ChatterInfo(name, hostname, elevation)

        chatters = [userdata(user) for user in listing]
        self.new_channel_chatters.emit(channel, chatters)

    def on_whoisuser(self, c: ServerConnection, e: Event) -> None:
        self._log_event(e)

    def _event_to_chatter(self, e):
        name, _id, elevation, hostname = parse_irc_source(e.source)
        return ChatterInfo(name, hostname, elevation)

    def on_join(self, c, e):
        channel = ChannelID(ChannelType.PUBLIC, e.target)
        chatter = self._event_to_chatter(e)
        self.channel_chatter_joined.emit(channel, chatter)

    def on_part(self, c, e):
        channel = ChannelID(ChannelType.PUBLIC, e.target)
        chatter = self._event_to_chatter(e)
        self.channel_chatter_left.emit(channel, chatter)
        if chatter.name == self._nick:
            self.quit_channel.emit(channel)

    def on_quit(self, c, e):
        chatter = self._event_to_chatter(e)
        self.chatter_quit.emit(chatter, e.arguments[0])

    def on_nick(self, c, e):
        oldnick = user2name(e.source)
        newnick = e.target

        self.chatter_renamed.emit(oldnick, newnick)
        self._log_event(e)

    def on_mode(self, c, e):
        if len(e.arguments) < 2:
            return

        name, _, elevation, hostname = parse_irc_source(e.arguments[1])
        chatter = ChatterInfo(name, hostname, elevation)
        modes = e.arguments[0]
        channel = ChannelID(ChannelType.PUBLIC, e.target)
        added, removed = self._parse_elevation(modes)
        self.new_chatter_elevation.emit(
            channel, chatter, added, removed,
        )

    def _parse_elevation(self, modes):
        add = re.compile(r".*\+([a-z]+)")
        remove = re.compile(r".*\-([a-z]+)")
        mode_to_elevation = {"o": "@", "q": "~", "v": "+"}

        def get_elevations(expr):
            match = re.search(expr, modes)
            if not match:
                return ""
            match = match.group(1)
            return ''.join(mode_to_elevation.get(c, '') for c in match)

        return get_elevations(add), get_elevations(remove)

    def on_umode(self, c, e):
        self._log_event(e)

    def on_notice(self, c, e):
        self._log_event(e)

    def on_topic(self, c, e):
        channel = ChannelID(ChannelType.PUBLIC, e.target)
        announcement = " ".join(e.arguments)
        self.new_channel_topic.emit(channel, announcement)

    def on_currenttopic(self, c, e):
        channel = ChannelID(ChannelType.PUBLIC, e.arguments[0])
        announcement = " ".join(e.arguments[1:])
        self.new_channel_topic.emit(channel, announcement)

    def on_topicinfo(self, c, e):
        self._log_event(e)

    def on_list(self, c, e):
        self._log_event(e)

    def on_bannedfromchan(self, c, e):
        self._log_event(e)

    def _emit_line(
        self, chatter, target, channel_type, text, type_=ChatLineType.MESSAGE,
    ):
        if channel_type == ChannelType.PUBLIC:
            channel_name = target
        else:
            channel_name = chatter.name
        chid = ChannelID(channel_type, channel_name)
        line = ChatLine(chatter.name, text, type_)
        self.new_line.emit(chid, chatter, line)

    def on_pubmsg(self, c, e):
        chatter = self._event_to_chatter(e)
        target = e.target
        text = "\n".join(e.arguments)
        self._emit_line(chatter, target, ChannelType.PUBLIC, text)

    def on_privnotice(self, c, e):
        if e.source == self.host:
            self._log_event(e)
            return

        chatter = self._event_to_chatter(e)
        notice = e.arguments[0]
        if chatter.name.lower() == 'nickserv':
            self._log_event(e)
            self._handle_nickserv_message(notice)
            return

        text = "\n".join(e.arguments)
        msg_target, text = self._parse_target_from_privnotice_message(text)
        if msg_target is not None:
            channel_type = ChannelType.PUBLIC
        else:
            channel_type = ChannelType.PRIVATE
        self._emit_line(
            chatter, msg_target, channel_type, text, ChatLineType.NOTICE,
        )

    # Parsing message to get target channel instead is non-standard.  To limit
    # abuse potential, we match the pattern used by bots as closely as
    # possible, and mark the line as notice so views can display them
    # differently.
    def _parse_target_from_privnotice_message(self, text: str) -> tuple[str, str]:
        if re.match(r'\[[^ ]+\] ', text) is None:
            return None, text
        prefix, rest = text.split(" ", 1)
        prefix = prefix[1:-1]
        target = prefix.strip("[]")
        if not is_channel(target):
            return None, text
        return target, rest

    def _handle_nickserv_message(self, notice):
        if (
            "registered under your account" in notice
            or "You are already identified" in notice
        ):
            if not self._connected:
                self._connected = True
                self.on_connected()
        elif "isn't registered" in notice:
            self._nickserv_register()
        elif "choose a different nick" in notice or "registered." in notice:
            self._nickserv_identify()
        elif "you are now recognized" in notice:
            self._nickserv_recover_if_needed()
        elif "RELEASE" in notice:
            self.connection.privmsg('release {} {}')
        elif "hold on" in notice or "You have regained control" in notice:
            self.connection.nick(self._nick)

    def on_disconnect(self, c: ServerConnection, e: Event) -> None:
        self._connected = False
        self.disconnected.emit()
        message = e.arguments[0]
        logger.info("Disconnected from chat: %s", message)

    def on_privmsg(self, c, e):
        chatter = self._event_to_chatter(e)
        text = "\n".join(e.arguments)
        self._emit_line(chatter, None, ChannelType.PRIVATE, text)

    def on_action(self, c: ServerConnection, e: Event) -> None:
        chatter = self._event_to_chatter(e)
        target = e.target
        text = "\n".join(e.arguments)
        if is_channel(target):
            chtype = ChannelType.PUBLIC
        else:
            chtype = ChannelType.PRIVATE
        self._emit_line(chatter, target, chtype, text, ChatLineType.ACTION)

    def on_nosuchnick(self, c, e):
        self._nickserv_register()

    def on_default(self, c, e):
        self._log_event(e)
        if "Nickname is already in use." in "\n".join(e.arguments):
            self.connection.nick(self._nick + "_")

    def on_kick(self, c, e):
        pass
