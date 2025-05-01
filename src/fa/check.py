from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6 import QtWidgets

from src import config
from src import fa
from src import util
from src.fa.game_updater.misc import UpdaterResult
from src.fa.game_updater.updater import Updater
from src.fa.mods import checkMods
from src.fa.path import validatePath
from src.fa.path import writeFAPathLua
from src.fa.wizards import Wizard
from src.mapGenerator.mapgenUtils import isGeneratedMap

if TYPE_CHECKING:
    from src.client._clientwindow import ClientWindow

logger = logging.getLogger(__name__)


def map_(mapname: str, force: bool = False, silent: bool = False) -> bool:
    """
    Assures that the map is available in FA, or returns false.
    """
    logger.info("Updating FA for map: " + str(mapname))

    if fa.maps.isMapAvailable(mapname):
        logger.info("Map is available.")
        return True

    if isGeneratedMap(mapname):
        from src import client

        # FIXME: generateMap, downloadMap should also return bool
        return bool(client.instance.map_generator.generateMap(mapname))

    if force:
        return bool(fa.maps.downloadMap(mapname, silent=silent))

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
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.YesToAll
            | QtWidgets.QMessageBox.StandardButton.No,
        )
        result = msgbox.exec()
        if result == QtWidgets.QMessageBox.StandardButton.No:
            return False
        elif result == QtWidgets.QMessageBox.StandardButton.YesToAll:
            config.Settings.set('maps/autodownload', True)

    return bool(fa.maps.downloadMap(mapname, silent=silent))


def featured_mod(featured_mod, version):
    pass


def sim_mod(sim_mod, version):
    pass


def path(parent: ClientWindow) -> bool:
    while not validatePath(
        util.settings.value(
            "ForgedAlliance/app/path", "",
            type=str,
        ),
    ):
        logger.warning(
            "Invalid game path: %s", util.settings.value("ForgedAlliance/app/path", "", type=str),
        )
        wizard = Wizard(parent)
        result = wizard.exec()
        if result == QtWidgets.QWizard.DialogCode.Rejected:
            return False

    logger.info("Writing fa_path.lua config file.")
    writeFAPathLua()
    return True


def game(parent):
    return True


def check(
        featured_mod: str,
        mapname: str | None = None,
        version: int | None = None,
        modVersions: dict | None = None,
        sim_mods: dict[str, str] | None = None,
        silent: bool = False,
):
    """
    This checks whether the mods are properly updated and player has the
    correct map.
    """
    logger.info("Checking FA for: %s and map %s", featured_mod, mapname)

    assert featured_mod

    if version is None:
        logger.info("Version unknown, assuming latest")

    # Perform the actual comparisons and updating
    logger.info("Updating FA for mod: %s, version %s", featured_mod, version)
    from src import client  # FIXME: forced by circular imports
    if not path(client.instance):
        return False

    # Spawn an update for the required mod
    game_updater = Updater(featured_mod, version, modVersions, silent=silent)
    result = game_updater.run()

    if result != UpdaterResult.SUCCESS:
        return False

    # Now it's down to having the right map
    if mapname:
        if not map_(mapname, silent=silent):
            return False

    if sim_mods:
        return checkMods(sim_mods)

    return True
