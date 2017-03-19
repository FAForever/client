import json
import os
from PyQt5 import QtCore, QtWidgets
import fa
from fa.check import check
from fa.replayparser import replayParser
import util
from . import mods

import logging
logger = logging.getLogger(__name__)

__author__ = 'Thygrrr'


def replay(source, detach=False):
    '''
    Launches FA streaming the replay from the given location. Source can be a QUrl or a string
    '''
    logger.info("fa.exe.replay(" + str(source) + ", detach = " + str(detach))

    if fa.instance.available():
        version = None
        featured_mod_versions = None
        arg_string = None
        replay_id = None
        # Convert strings to URLs
        if isinstance(source, str):
            if os.path.isfile(source):
                if source.endswith(".fafreplay"):  # the new way of doing things
                    replay = open(source, "rt")
                    info = json.loads(replay.readline())

                    binary = QtCore.qUncompress(QtCore.QByteArray.fromBase64(replay.read().encode('utf-8')))
                    logger.info("Extracted " + str(binary.size()) + " bytes of binary data from .fafreplay.")
                    replay.close()

                    if binary.size() == 0:
                        logger.info("Invalid replay")
                        QtWidgets.QMessageBox.critical(None, "FA Forever Replay", "Sorry, this replay is corrupted.")
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
                    QtWidgets.QMessageBox.critical(None, "FA Forever Replay",
                                               "Sorry, FAF has no idea how to replay this file:<br/><b>" + source + "</b>")

                logger.info("Replaying " + str(arg_string) + " with mod " + str(mod) + " on map " + str(mapname))
                
                #Wrap up file path in "" to ensure proper parsing by FA.exe
                arg_string = '"' + arg_string + '"'
                
            else:
                source = QtCore.QUrl(
                    source)  #Try to interpret the string as an actual url, it may come from the command line

        if isinstance(source, QtCore.QUrl):
            url = source
            # Determine if it's a faflive url
            if url.scheme() == "faflive":
                mod = QtCore.QUrlQuery(url).queryItemValue("mod")
                mapname = QtCore.QUrlQuery(url).queryItemValue("map")
                replay_id = url.path().split("/")[0]
                # whip the URL into shape so ForgedAllianceForever.exe understands it
                arg_url = QtCore.QUrl(url)
                arg_url.setScheme("gpgnet")
                arg_url.setEncodedQuery(QtCore.QByteArray())
                arg_string = arg_url.toString()
            else:
                QtWidgets.QMessageBox.critical(None, "FA Forever Replay",
                                           "App doesn't know how to play replays from that scheme:<br/><b>" + url.scheme() + "</b>")
                return False

                # We couldn't construct a decent argument format to tell ForgedAlliance for this replay
        if not arg_string:
            QtWidgets.QMessageBox.critical(None, "FA Forever Replay",
                                       "App doesn't know how to play replays from that source:<br/><b>" + str(
                                           source) + "</b>")
            return False

        # Launch preparation: Start with an empty arguments list
        arguments = ['/replay', arg_string]

        #Proper mod loading code
        mod = "faf" if mod == "ladder1v1" else mod

        if '/init' not in arguments:
            arguments.append('/init')
            arguments.append("init_" + mod + ".lua")

        # Disable defunct bug reporter
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

        if fa.instance.run(None, arguments, detach):
            logger.info("Viewing Replay.")
            return True
        else:
            logger.error("Replaying failed. Guru meditation: {}".format(arguments))
            return False
