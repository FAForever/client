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

from fa.lua import InitFile
from fa.path import getGameFolderFA
from fa.game_version import GameVersion

from .process import instance

import util
import os

__author__ = 'Thygrrr'

import logging
logger = logging.getLogger(__name__)

from PyQt4 import QtCore

from . import DEFAULT_WRITE_GAME_LOG
from . import DEFAULT_RECORD_REPLAY

from config import Settings


def build_argument_list(game_info, port, arguments=None):
    """
    Compiles an argument list to run the game with POpen style process invocation methods.
    Extends a potentially pre-existing argument list to allow for injection of special parameters
    """
    logger.info(arguments)
    arguments = []

    if '/init' in arguments:
        raise ValueError("Custom init scripts no longer supported.")

    #log file
    if Settings.get('WRITE_GAME_LOG', 'FA'):
        arguments.append(("log", util.LOG_FILE_GAME))

    #live replay
    arguments.append(('savereplay',
                     '"gpgnet://localhost/' + str(game_info['uid']) + "/" + str(game_info['recorder']) + '.SCFAreplay"'))

    #disable bug reporter
    arguments.append(('nobugreport', None))

    #gpg server emulation
    arguments.append(('gpgnet', '127.0.0.1:' + str(port)))

    return arguments


def run(game_info, port, arguments=None):
    """
    Launches Forged Alliance with the given arguments
    """
    arguments = build_argument_list(game_info, port, arguments)
    init_file = InitFile()
    logger.info("Launching with game_info %r" % game_info)
    game_version = game_info['version']

    init_file.mount(os.path.join(Settings.get("MODS_PATH", 'FA'), game_version.main_mod.identifier), '/')
    init_file.mount(os.path.join(str(getGameFolderFA()), 'gamedata\\*.scd'), '/')
    init_file.mount(str(getGameFolderFA()), '/')

    init_path = os.path.join(Settings.get('BIN', 'FA'), 'init_%s.lua' % game_version.main_mod.name)
    f = file(init_path, 'w')
    f.write(init_file.to_lua())
    f.close()

    arguments.append(('init', init_path))

    return instance.run(game_info, arguments, False, init_file)
