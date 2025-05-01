import json
import logging
import os

import zstandard
from PyQt6 import QtCore
from PyQt6 import QtWidgets

from src import fa
from src import util
from src.fa.check import check
from src.fa.replayparser import ReplayParser
from src.qt.utils import qopen
from src.util.gameurl import GameUrl
from src.util.gameurl import GameUrlType

logger = logging.getLogger(__name__)

__author__ = 'Thygrrr'


def decompressReplayData(fileobj, compressionType):
    if compressionType == "zstd":
        decompressor = zstandard.ZstdDecompressor()
        with decompressor.stream_reader(fileobj) as reader:
            data = QtCore.QByteArray(reader.read())
    else:
        b_data = fileobj.read()
        data = QtCore.qUncompress(QtCore.QByteArray().fromBase64(b_data))
    return data


def replay(source, detach=False):
    """
    Launches FA streaming the replay from the given location.
    Source can be a QUrl or a string
    """
    logger.info("fa.exe.replay(" + str(source) + ", detach = " + str(detach))

    if not fa.instance.available():
        return False

    version = None
    featured_mod_versions = None
    arg_string = None
    replay_id = None
    compression_type = None
    sim_mods = None
    # Convert strings to URLs
    if isinstance(source, str):
        if os.path.isfile(source):
            if source.endswith(".fafreplay"):
                with open(source, "rb") as replay:
                    info = json.loads(replay.readline())
                    compression_type = info.get("compression")
                    try:
                        binary = decompressReplayData(replay, compression_type)
                    except Exception as e:
                        logger.error("Could not decompress replay: %s", e)
                        binary = QtCore.QByteArray()
                    logger.info(
                        "Extracted %d bytes of binary data from "
                        ".fafreplay.", binary.size(),
                    )

                    if binary.size() == 0:
                        logger.info("Invalid replay")
                        QtWidgets.QMessageBox.critical(
                            None,
                            "FA Forever Replay",
                            "Sorry, this replay is corrupted.",
                        )
                        return False

                replay_path = os.path.join(util.CACHE_DIR, "temp.scfareplay")
                open_mode = (
                    QtCore.QIODevice.OpenModeFlag.WriteOnly
                    | QtCore.QIODevice.OpenModeFlag.Truncate
                )
                with qopen(replay_path, open_mode) as scfa_replay:
                    scfa_replay.write(binary)

                mapname = info.get('mapname')
                mod = info['featured_mod']
                replay_id = info['uid']
                featured_mod_versions = info.get('featured_mod_versions')
                arg_string = scfa_replay.fileName()

                parser = ReplayParser(replay_path)
                replay_metadata = parser.parse_header()

                version = replay_metadata["game_version"]
                if mapname == "None":
                    mapname = replay_metadata["mapname"]
                sim_mods = {mod["uid"]: mod["name"] for mod in replay_metadata["sim_mods"].values()}

            elif source.endswith(".scfareplay"):  # compatibility mode
                filename = os.path.basename(source)
                if len(filename.split(".")) > 2:
                    mod = filename.rsplit(".", 2)[1]
                    logger.info("mod guessed from %s is %s", source, mod)
                else:
                    # TODO: maybe offer a list of mods for the user.
                    mod = "faf"
                    logger.warning(
                        "no mod could be guessed, using "
                        "fallback ('faf') ",
                    )

                arg_string = source
                parser = ReplayParser(arg_string)
                replay_metadata = parser.parse_header()
                version = replay_metadata["game_version"]
                mapname = replay_metadata["mapname"]
                sim_mods = {mod["uid"]: mod["name"] for mod in replay_metadata["sim_mods"].values()}
            else:
                QtWidgets.QMessageBox.critical(
                    None,
                    "FA Forever Replay",
                    (
                        "Sorry, FAF has no idea how to replay "
                        "this file:<br/><b>{}</b>".format(source)
                    ),
                )

            logger.info("Replaying %s with mod %s on map %s", arg_string, mod, mapname)

            # Wrap up file path in "" to ensure proper parsing by FA.exe
            arg_string = '"' + arg_string + '"'

        else:
            # Try to interpret the string as an actual url, it may come
            # from the command line
            source = QtCore.QUrl(source)

    if isinstance(source, GameUrl):
        url = source.to_url()
        # Determine if it's a faflive url
        if source.game_type == GameUrlType.LIVE_REPLAY:
            mod = source.mod
            mapname = source.map
            replay_id = source.uid
            sim_mods = source.mods
            # whip the URL into shape so ForgedAllianceForever.exe
            # understands it
            url.setScheme("gpgnet")
            url.setQuery(QtCore.QUrlQuery(""))
            arg_string = url.toString()
        else:
            QtWidgets.QMessageBox.critical(
                None,
                "FA Forever Replay",
                (
                    "App doesn't know how to play replays from "
                    "that scheme:<br/><b>{}</b>".format(url.scheme())
                ),
            )
            return False

    # We couldn't construct a decent argument format to tell
    # ForgedAlliance for this replay
    if not arg_string:
        QtWidgets.QMessageBox.critical(
            None,
            "FA Forever Replay",
            (
                "App doesn't know how to play replays from that "
                "source:<br/><b>{}</b>".format(source)
            ),
        )
        return False

    # Launch preparation: Start with an empty arguments list
    arguments = ['/replay', arg_string]

    # Proper mod loading code
    mod = "faf" if mod == "ladder1v1" else mod

    if '/init' not in arguments:
        arguments.append('/init')
        arguments.append("init_" + mod + ".lua")

    # Disable defunct bug reporter
    arguments.append('/nobugreport')

    # log file
    arguments.append("/log")
    arguments.append('"' + util.LOG_FILE_REPLAY + '"')

    if replay_id:
        arguments.append("/replayid")
        arguments.append(str(replay_id))

    # Update the game appropriately
    if not check(mod, mapname, version, featured_mod_versions, sim_mods):
        msg = "Can't watch replays without an updated Forged Alliance game!"
        logger.error(msg)
        return False

    if fa.instance.run(None, arguments, detach):
        logger.info("Viewing Replay.")
        return True
    else:
        logger.error("Replaying failed. Guru meditation: %s", arguments)
        return False
