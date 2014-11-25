# -------------------------------------------------------------------------------
# Copyright (c) 2012 Gael Honorez.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#-------------------------------------------------------------------------------
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
        raise ValueError("Custom init scripts no longer supportes.")

    # Proper mod loading code, but allow for custom init by server
    mods.fix_init_luas()
    arguments.append("/init")
    arguments.append(mods.init_lua_for_featured_mod(game_info['featured_mod']))

    #log file
    if settings.value("fa.write_game_log", DEFAULT_WRITE_GAME_LOG, type=bool):
        arguments.append("/log")
        arguments.append('"' + util.LOG_FILE_GAME + '"')

    #live replay
    arguments.append('/savereplay')
    arguments.append('"gpgnet://localhost/' + str(game_info['uid']) + "/" + str(game_info['recorder']) + '.SCFAreplay"')

    #disable bug reporter
    arguments.append('/nobugreport')

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
