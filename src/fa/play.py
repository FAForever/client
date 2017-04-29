from .game_process import instance

from config import Settings
import util

import logging
logger = logging.getLogger(__name__)

__author__ = 'Thygrrr'


def build_argument_list(game_info, port, arguments=None):
    """
    Compiles an argument list to run the game with POpen style process invocation methods.
    Extends a potentially pre-existing argument list to allow for injection of special parameters
    """
    import client
    arguments = arguments or []

    if '/init' in arguments:
        raise ValueError("Custom init scripts no longer supported.")

    # Init file
    arguments.append('/init')
    arguments.append('init_{}.lua'.format(game_info.get('featured_mod', 'faf')))

    arguments.append('/numgames {}'.format(client.instance.me.number_of_games))

    # log file
    if Settings.get("game/logs", False, type=bool):
        arguments.append("/log")
        arguments.append('"' + util.LOG_FILE_GAME + '"')

    # Disable defunct bug reporter
    arguments.append('/nobugreport')

    # live replay
    arguments.append('/savereplay')
    arguments.append('"gpgnet://localhost/' + str(game_info['uid']) + "/" + str(game_info['recorder']) + '.SCFAreplay"')

    # gpg server emulation
    arguments.append('/gpgnet 127.0.0.1:' + str(port))

    return arguments


def run(game_info, port, arguments=None):
    """
    Launches Forged Alliance with the given arguments
    """
    logger.info("Play received arguments: %s" % arguments)
    arguments = build_argument_list(game_info, port, arguments)
    return instance.run(game_info, arguments)
