import util
from config import Settings

from .game_process import instance

__author__ = 'Thygrrr'

import logging

logger = logging.getLogger(__name__)


def build_argument_list(
    game_info,
    port,
    replayPort,
    arguments=None,
    log_suffix=None,
):
    """
    Compiles an argument list to run the game with POpen style process
    invocation methods. Extends a potentially pre-existing argument list
    to allow for injection of special parameters
    """
    arguments = arguments or []

    if '/init' in arguments:
        raise ValueError("Custom init scripts no longer supported.")

    # Init file
    arguments.append('/init')
    arguments.append(
        'init_{}.lua'.format(game_info.get('featured_mod', 'faf')),
    )

    # log file
    if Settings.get("game/logs", False, type=bool):
        arguments.append("/log")
        if log_suffix is None:
            log_file = util.LOG_FILE_GAME
        else:
            log_file = (
                util.LOG_FILE_GAME_PREFIX
                + util.LOG_FILE_GAME_INFIX
                + "{}".format(log_suffix)
                + ".log"
            )
        arguments.append('"{}"'.format(log_file))

    # Disable defunct bug reporter
    arguments.append('/nobugreport')

    # live replay
    arguments.append('/savereplay')
    arguments.append(
        '"gpgnet://localhost:{}/{}/{}.SCFAreplay"'.format(
            replayPort,
            game_info['uid'],
            game_info['recorder'],
        ),
    )

    # gpg server emulation
    arguments.append('/gpgnet 127.0.0.1:' + str(port))

    return arguments


def run(game_info, port, replayPort, arguments=None, log_suffix=None):
    """
    Launches Forged Alliance with the given arguments
    """
    logger.info("Play received arguments: {}".format(arguments))
    arguments = build_argument_list(
        game_info, port, replayPort, arguments, log_suffix,
    )
    return instance.run(game_info, arguments)
