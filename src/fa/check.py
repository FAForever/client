import binascii
import logging
import os
import zipfile

from PyQt5 import QtWidgets

import config
import fa
import util
from fa.mods import checkMods
from fa.path import validatePath, writeFAPathLua
from fa.wizards import Wizard
from mapGenerator.mapgenUtils import isGeneratedMap

logger = logging.getLogger(__name__)


def map_(mapname, force=False, silent=False):
    """
    Assures that the map is available in FA, or returns false.
    """
    logger.info("Updating FA for map: " + str(mapname))

    if fa.maps.isMapAvailable(mapname):
        logger.info("Map is available.")
        return True

    if isGeneratedMap(mapname):
        import client
        return client.instance.map_generator.generateMap(mapname)

    if force:
        return fa.maps.downloadMap(mapname, silent=silent)

    auto = config.Settings.get('maps/autodownload', default=False, type=bool)
    if not auto:
        msgbox = QtWidgets.QMessageBox()
        msgbox.setWindowTitle("Download Map")
        msgbox.setText(
            "Seems that you don't have the map used this game. Do "
            "you want to download it?<br/><b>{}</b>".format(mapname),
        )
        msgbox.setInformativeText(
            "If you respond 'Yes to All' maps will be "
            "downloaded automatically in the future",
        )
        msgbox.setStandardButtons(
            QtWidgets.QMessageBox.Yes
            | QtWidgets.QMessageBox.YesToAll
            | QtWidgets.QMessageBox.No,
        )
        result = msgbox.exec_()
        if result == QtWidgets.QMessageBox.No:
            return False
        elif result == QtWidgets.QMessageBox.YesToAll:
            config.Settings.set('maps/autodownload', True)

    return fa.maps.downloadMap(mapname, silent=silent)


def featured_mod(featured_mod, version):
    pass


def sim_mod(sim_mod, version):
    pass


def path(parent):
    while not validatePath(
        util.settings.value(
            "ForgedAlliance/app/path", "",
            type=str,
        ),
    ):
        logger.warning(
            "Invalid game path: {}".format(
                util.settings.value("ForgedAlliance/app/path", "", type=str),
            ),
        )
        wizard = Wizard(parent)
        result = wizard.exec_()
        if result == QtWidgets.QWizard.Rejected:
            return False

    logger.info("Writing fa_path.lua config file.")
    writeFAPathLua()
    return True


def game(parent):
    return True


def crc32(fname):
    try:
        with open(fname) as stream:
            return binascii.crc32(stream.read())
    except BaseException:
        logger.exception('CRC check fail!')
        return None


def checkMovies(files):
    """
    Unpacks movies (based on path in zipfile) to the movies folder.
    Movies must be unpacked for FA to be able to play them.
    This is a hack needed because the game updater can only handle bin and
    gamedata.
    """

    logger.info('checking updated files: {}'.format(files))

    # construct dirs
    gd = os.path.join(util.APPDATA_DIR, 'gamedata')

    for fname in files:
        origpath = os.path.join(gd, fname)

        if os.path.exists(origpath) and zipfile.is_zipfile(origpath):
            try:
                zf = zipfile.ZipFile(origpath)
            except BaseException:
                logger.exception(
                    'Failed to open Game File {}'.format(origpath),
                )
                continue

            for zi in zf.infolist():
                if zi.filename.startswith('movies'):
                    tgtpath = os.path.join(util.APPDATA_DIR, zi.filename)
                    # copy only if file is different - check first if file
                    # exists, then if size is changed, then crc
                    if (
                        not os.path.exists(tgtpath)
                        or os.stat(tgtpath).st_size != zi.file_size
                        or crc32(tgtpath) != zi.CRC
                    ):
                        zf.extract(zi, util.APPDATA_DIR)


def check(
    featured_mod,
    mapname=None,
    version=None,
    modVersions=None,
    sim_mods=None,
    silent=False,
):
    """
    This checks whether the mods are properly updated and player has the
    correct map.
    """
    logger.info("Checking FA for: {} and map {}".format(featured_mod, mapname))

    assert featured_mod

    if version is None:
        logger.info("Version unknown, assuming latest")

    # Perform the actual comparisons and updating
    logger.info(
        "Updating FA for mod: {}, version {}".format(featured_mod, version),
    )
    import client  # FIXME: forced by circular imports
    if not path(client.instance):
        return False

    # Spawn an update for the required mod
    game_updater = fa.updater.Updater(
        featured_mod, version, modVersions, silent=silent,
    )
    result = game_updater.run()

    if result != fa.updater.Updater.RESULT_SUCCESS:
        return False

    try:
        if len(game_updater.updatedFiles) > 0:
            checkMovies(game_updater.updatedFiles)
    except BaseException:
        logger.exception('Error checking game files for movies')
        return False

    # Now it's down to having the right map
    if mapname:
        if not map_(mapname, silent=silent):
            return False

    if sim_mods:
        return checkMods(sim_mods)

    return True
