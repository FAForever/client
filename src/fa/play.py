from process import instance

import util

__author__ = 'Thygrrr'

import logging
logger = logging.getLogger(__name__)

from PyQt4 import QtCore

settings = QtCore.QSettings("ForgedAllianceForever", "FA Lobby")


def build_argument_list(game_info, port, arguments=None):
    """
    Compiles an argument list to run the game with POpen style process invocation methods.
    Extends a potentially pre-existing argument list to allow for injection of special parameters
    """
    arguments = arguments or []

    # Proper mod loading code, but allow for custom init by server
    if not '/init' in arguments:
        arguments.append('/init')
        arguments.append("init_" + game_info['featured_mod'] + ".lua")

    #log file
    if settings.value("fa.play.write_game_log", type=bool):
        arguments.append("/log")
        arguments.append('"' + util.LOG_FILE_GAME + '"')

    #live replay
    if settings.value("fa.play.stream_live_replay", type=bool):
        arguments.append('/savereplay')
        arguments.append('gpgnet://localhost/' + str(game_info['uid']) + "/" + str(game_info['recorder']) + '.SCFAreplay')

    #disable bug reporter
    arguments.append('/nobugreport')

    #gpg server
    arguments.append('/gpgnet 127.0.0.1:' + str(port))

    return arguments


def play(game_info, port, arguments=None):
    """
    Launches Forged Alliance with the given arguments
    """
    arguments = build_argument_list(game_info, port, arguments)
    return instance.run(game_info, arguments)
