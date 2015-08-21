from fa import mods

from .process import instance

import util
import os

__author__ = 'Thygrrr'

import logging
logger = logging.getLogger(__name__)

from PyQt4 import QtCore

settings = QtCore.QSettings("ForgedAllianceForever", "FA Lobby")

from . import DEFAULT_WRITE_GAME_LOG
from . import DEFAULT_RECORD_REPLAY


def build_argument_list(game_info, port, arguments=None):
    """
    Compiles an argument list to run the game with POpen style process invocation methods.
    Extends a potentially pre-existing argument list to allow for injection of special parameters
    """
    arguments = arguments or []

    if '/init' in arguments:
        raise ValueError("Custom init scripts no longer supported.")

    #log file
    if settings.value("fa.write_game_log", DEFAULT_WRITE_GAME_LOG, type=bool):
        arguments.append("/log")
        arguments.append('"' + util.LOG_FILE_GAME + '"')

    #live replay
    arguments.append('/savereplay')
    arguments.append('"gpgnet://localhost/' + str(game_info['uid']) + "/" + str(game_info['recorder']) + '.SCFAreplay"')

    #gpg server emulation
    arguments.append('/gpgnet 127.0.0.1:' + str(port))

    return arguments


def run(game_info, port, arguments=None):
    """
    Launches Forged Alliance with the given arguments
    """
    logger.info("Play received arguments: %s" % arguments)
    arguments = build_argument_list(game_info, port, arguments)
    return instance.run(game_info, arguments)
