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

import json
import os
from PyQt4 import QtCore, QtGui
import fa
from fa.check import check
from fa.replayparser import replayParser
import util

import logging
logger = logging.getLogger(__name__)

__author__ = 'Thygrrr'


def replay(source, detach=False):
    '''
    Launches FA streaming the replay from the given location. Source can be a QUrl or a string
    '''
    logger.info("replay(" + str(source) + ", detach = " + str(detach))

    if fa.instance.available():
        version = None
        featured_mod_versions = None
        arg_string = None
        replay_id = None
        # Convert strings to URLs
        if isinstance(source, basestring):
            if os.path.isfile(source):
                if source.endswith(".fafreplay"):  # the new way of doing things
                    replay = open(source, "rt")
                    info = json.loads(replay.readline())

                    binary = QtCore.qUncompress(QtCore.QByteArray.fromBase64(replay.read()))
                    logger.info("Extracted " + str(binary.size()) + " bytes of binary data from .fafreplay.")
                    replay.close()

                    if binary.size() == 0:
                        logger.info("Invalid replay")
                        QtGui.QMessageBox.critical(None, "FA Forever Replay", "Sorry, this replay is corrupted.")
                        return False

                    scfa_replay = QtCore.QFile(os.path.join(util.CACHE_DIR, "temp.scfareplay"))
                    scfa_replay.open(QtCore.QIODevice.WriteOnly | QtCore.QIODevice.Truncate)
                    scfa_replay.write(binary)
                    scfa_replay.flush()
                    scfa_replay.close()

                    mapname = info.get('mapname', None)
                    mod = info['featured_mod']
                    replay_id = info['uid']
                    featured_mod_versions = info.get('featured_mod_versions', None)
                    arg_string = scfa_replay.fileName()

                    parser = replayParser(arg_string)
                    version = parser.getVersion()

                elif source.endswith(".scfareplay"):  # compatibility mode
                    filename = os.path.basename(source)
                    if len(filename.split(".")) > 2:
                        mod = filename.rsplit(".", 2)[1]
                        logger.info("mod guessed from " + source + " is " + mod)
                    else:
                        mod = "faf"  #TODO: maybe offer a list of mods for the user.
                        logger.warn("no mod could be guessed, using fallback ('faf') ")

                    mapname = None
                    arg_string = source
                    parser = replayParser(arg_string)
                    version = parser.getVersion()
                else:
                    QtGui.QMessageBox.critical(None, "FA Forever Replay",
                                               "Sorry, FAF has no idea how to replay this file:<br/><b>" + source + "</b>")

                logger.info("Replaying " + str(arg_string) + " with mod " + str(mod) + " on map " + str(mapname))
            else:
                source = QtCore.QUrl(
                    source)  #Try to interpret the string as an actual url, it may come from the command line

        if isinstance(source, QtCore.QUrl):
            url = source
            #Determine if it's a faflive url
            if url.scheme() == "faflive":
                mod = url.queryItemValue("mod")
                mapname = url.queryItemValue("map")
                replay_id = url.path().split("/")[0]
                # whip the URL into shape so ForgedAllianceForever.exe understands it
                arg_url = QtCore.QUrl(url)
                arg_url.setScheme("gpgnet")
                arg_url.setEncodedQuery(QtCore.QByteArray())
                arg_string = arg_url.toString()
            else:
                QtGui.QMessageBox.critical(None, "FA Forever Replay",
                                           "App doesn't know how to play replays from that scheme:<br/><b>" + url.scheme() + "</b>")
                return False

                # We couldn't construct a decent argument format to tell ForgedAlliance for this replay
        if not arg_string:
            QtGui.QMessageBox.critical(None, "FA Forever Replay",
                                       "App doesn't know how to play replays from that source:<br/><b>" + str(
                                           source) + "</b>")
            return False

        # Launch preparation: Start with an empty arguments list
        arguments = []
        arguments.append('/replay')
        arguments.append(arg_string)


        #Proper mod loading code
        mod = "faf" if mod == "ladder1v1" else mod  #hack for feature/new-patcher
        if not '/init' in arguments:
            arguments.append('/init')
            arguments.append("../lua/init_" + mod + ".lua")

        #disable bug reporter and movies
        arguments.append('/nobugreport')

        #log file
        arguments.append("/log")
        arguments.append('"' + util.LOG_FILE_REPLAY + '"')

        if replay_id:
            arguments.append("/replayid")
            arguments.append(str(replay_id))

        # Update the game appropriately
        if not check(mod, mapname, version, featured_mod_versions):
            logger.error("Can't watch replays without an updated Forged Alliance game!")
            return False


        # Finally, run executable
        if fa.instance.run(None, arguments, detach):
            logger.info("Viewing Replay.")
            return True
        else:
            logger.error("Replaying failed.")
            return False