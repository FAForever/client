import logging
import os
import shutil
import stat
import string
import sys
import tempfile
import zipfile
from typing import Callable

from PyQt6 import QtCore
from PyQt6 import QtGui

from src import util
from src.config import Settings
from src.fa.maps_.map_utils import get_scmap_file
from src.fa.maps_.preview import create_large_preview
from src.fa.maps_.preview import extract_dds
from src.fa.maps_.preview import image_from_dds
from src.mapGenerator.mapgenUtils import isGeneratedMap
from src.model.game import OFFICIAL_MAPS as maps
from src.vaults.dialogs import downloadVaultAssetNoMsg

logger = logging.getLogger(__name__)

route = Settings.get('content/host')

__exist_maps = None


def isBase(mapname: str) -> bool:
    """
    Returns true if mapname is the name of an official map
    """
    return mapname.lower() in maps


def getUserMaps():
    maps = []
    if os.path.isdir(getUserMapsFolder()):
        for _dir in os.listdir(getUserMapsFolder()):
            maps.append(_dir.lower())
    return maps


def getDisplayName(filename):
    """
    Tries to return a pretty name for the map (for official maps, it looks up
    the name) For nonofficial maps, it tries to clean up the filename
    """
    if str(filename) in maps:
        return maps[filename][0]
    else:
        # cut off ugly version numbers, replace "_" with space.
        pretty = filename.rsplit(".v0", 1)[0]
        pretty = pretty.replace("_", " ")
        pretty = string.capwords(pretty)
        return pretty


def name2link(name: str) -> str:
    """
    Returns a quoted link for use with the VAULT_xxxx Urls
    TODO: This could be cleaned up a little later.
    """
    return Settings.get("vault/map_download_url").format(name=name)


def link2name(link):
    """
    Takes a link and tries to turn it into a local mapname
    """
    name = link.rsplit("/", 1)[1].rsplit(".zip")[0]
    logger.info("Converted link '" + link + "' to name '" + name + "'")
    return name


def getScenarioFile(folder):
    """
    Return the scenario.lua file
    """
    for infile in os.listdir(folder):
        if infile.lower().endswith("_scenario.lua"):
            return infile
    return None


def isMapFolderValid(folder):
    """
    Check if the folder got all the files needed to be a map folder.
    """
    baseName = os.path.basename(folder).split('.')[0]
    files_required = {
        baseName + ".scmap",
        baseName + "_save.lua",
        baseName + "_scenario.lua",
        baseName + "_script.lua",
    }
    files_present = set(os.listdir(folder))

    return files_required.issubset(files_present)


def existMaps(force=False):
    global __exist_maps
    if force or __exist_maps is None:

        __exist_maps = getUserMaps()

        if os.path.isdir(getBaseMapsFolder()):
            if __exist_maps is None:
                __exist_maps = os.listdir(getBaseMapsFolder())
            else:
                __exist_maps.extend(os.listdir(getBaseMapsFolder()))
    return __exist_maps


def isMapAvailable(mapname):
    """
    Returns true if the map with the given name is available on the client
    """
    if isBase(mapname):
        return True

    if os.path.isdir(getUserMapsFolder()):
        for infile in os.listdir(getUserMapsFolder()):
            if infile.lower() == mapname.lower():
                return True

    return False


def folderForMap(mapname):
    """
    Returns the folder where the application could find the map
    """
    if isBase(mapname):
        return os.path.join(getBaseMapsFolder(), mapname)

    if os.path.isdir(getUserMapsFolder()):
        for infile in os.listdir(getUserMapsFolder()):
            if infile.lower() == mapname.lower():
                return os.path.join(getUserMapsFolder(), mapname)

    return None


def getBaseMapsFolder():
    """
    Returns the folder containing all the base maps for this client.
    """
    gamepath = util.settings.value("ForgedAlliance/app/path", None, type=str)
    if gamepath:
        return os.path.join(gamepath, "maps")
    else:
        # This most likely isn't the valid maps folder, but it's the best guess
        return "maps"


def getUserMapsFolder():
    """
    Returns to folder where the downloaded maps of the user are stored.
    """
    return os.path.join(
        util.PERSONAL_DIR,
        "My Games",
        "Gas Powered Games",
        "Supreme Commander Forged Alliance",
        "Maps",
    )


def gen_prev_from_dds(sourcename: str, destname: str, small: bool = False) -> None:
    """
    this opens supcom's dds file (format: bgra8888) and saves to png
    """
    try:
        image = image_from_dds(sourcename)
        if small:
            image = image.scaled(
                100,
                100,
                aspectRatioMode=QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                transformMode=QtCore.Qt.TransformationMode.SmoothTransformation,
            )
        image.save(destname)
    except IOError:
        logger.debug('IOError exception in genPrevFromDDS', exc_info=True)
        raise


def export_preview_from_map(
        mapname: str | None,
) -> None | dict[str, None | str | list[str]]:
    """
    This method auto-upgrades the maps to have small and large preview images
    """
    if mapname is None or mapname == "":
        return
    smallExists = False
    largeExists = False
    ddsExists = False
    previews = {"cache": None, "tozip": list()}

    if os.path.isdir(mapname):
        mapdir = mapname
    elif os.path.isdir(os.path.join(getUserMapsFolder(), mapname)):
        mapdir = os.path.join(getUserMapsFolder(), mapname)
    elif os.path.isdir(os.path.join(getBaseMapsFolder(), mapname)):
        mapdir = os.path.join(getBaseMapsFolder(), mapname)
    else:
        logger.log(5, f"Can't find mapname in file system: {mapname}")
        return previews

    mapname = os.path.basename(mapdir).lower()
    mapname_no_version, *_ = mapname.partition(".")
    mapfilename = get_scmap_file(mapdir) or ""

    mode = os.stat(mapdir)[0]
    if not (mode and stat.S_IWRITE):
        logger.debug("Map directory is not writable: " + mapdir)
        logger.debug("Writing into cache instead.")
        mapdir = os.path.join(util.CACHE_DIR, mapname)
        if not os.path.isdir(mapdir):
            os.mkdir(mapdir)

    def plausible_mapname_preview_name(suffix: str) -> str:
        casefold_names = (
            f"{mapname}{suffix}".casefold(),
            f"{mapname_no_version}{suffix}".casefold(),
        )
        for entry in os.listdir(mapdir):
            plausible_preview = os.path.join(mapdir, entry)
            if os.path.isfile(plausible_preview) and entry.casefold() in casefold_names:
                return plausible_preview
        return os.path.join(mapdir, f"{mapname}{suffix}")

    previewsmallname = plausible_mapname_preview_name(".small.png")
    previewlargename = plausible_mapname_preview_name(".large.png")
    previewddsname = plausible_mapname_preview_name(".dds")
    cachepngname = os.path.join(util.MAP_PREVIEW_SMALL_DIR, mapname + ".png")

    logger.debug("Generating preview from user maps for: '%s'. Directory: '%s'", mapname, mapdir)

    if not os.path.isfile(mapfilename):
        logger.warning(
            "Unable to find the .scmap for: '%s', was looking here: '%s'",
            mapname,
            mapfilename,
        )
        return previews

    if os.path.isfile(previewsmallname):
        previews["tozip"].append(previewsmallname)
        smallExists = True
        shutil.copyfile(previewsmallname, cachepngname)
        if os.path.isfile(cachepngname):
            previews["cache"] = cachepngname
        else:
            logger.warning("Couldn't copy preview into cache folder")
            return previews

    if os.path.isfile(previewlargename):
        previews["tozip"].append(previewlargename)
        largeExists = True

    if os.path.isfile(previewddsname):
        previews["tozip"].append(previewddsname)
        ddsExists = True

    if not ddsExists:
        logger.debug("Extracting preview DDS from .scmap for: '%s'", mapname)
        try:
            if extract_dds(mapfilename, previewddsname):
                previews["tozip"].append(previewddsname)
            else:
                logger.debug("Failed to make DDS for: '%s'", mapname)
                return previews
        except IOError:
            pass

    if not smallExists:
        logger.debug("Making small preview from DDS for: '%s'", mapname)
        try:
            gen_prev_from_dds(previewddsname, previewsmallname, small=True)
            previews["tozip"].append(previewsmallname)
            shutil.copyfile(previewsmallname, cachepngname)
            previews["cache"] = cachepngname
        except IOError:
            logger.debug("Failed to make small preview for: '%s'", mapname)
            return previews

    if not largeExists:
        logger.debug("Making large preview from DDS for: '%s'", mapname)
        try:
            mappixmap = create_large_preview(mapdir)
            mappixmap.save(previewlargename)
            previews["tozip"].append(previewlargename)
        except IOError:
            logger.debug("Failed to make large preview for: '%s'", mapname)

    return previews


def get_preview_for_generated_map(mapname: str) -> QtGui.QIcon:
    mapdir = os.path.join(getUserMapsFolder(), mapname)
    preview_name = f"{mapname}_preview.png"
    preview_path = os.path.join(mapdir, preview_name)

    if os.path.isfile(preview_path):
        return util.THEME.icon(preview_path)

    return util.THEME.icon("games/generated_map.png")


def preview(mapname: str, *, pixmap: bool = False) -> QtGui.QIcon | QtGui.QPixmap | None:
    if isGeneratedMap(mapname):
        return get_preview_for_generated_map(mapname)
    try:
        # Try to load directly from cache
        encode_option = QtCore.QUrl.ComponentFormattingOption.EncodeSpaces
        encoded = QtCore.QUrl(mapname).fileName(encode_option)
        img = os.path.join(util.MAP_PREVIEW_SMALL_DIR, f"{encoded}.png")
        if os.path.isfile(img):
            logger.log(5, f"Using cached preview image for: {mapname}")
            return util.THEME.icon(img, False, pixmap)

        # Try to find in local map folder
        img = export_preview_from_map(mapname)

        if (
            img
            and 'cache' in img
            and img['cache']
            and os.path.isfile(img['cache'])
        ):
            logger.debug("Using fresh preview image for: " + mapname)
            return util.THEME.icon(img['cache'], False, pixmap)
    except Exception:
        logger.debug("Map Preview Exception ('%s')", mapname, exc_info=sys.exc_info())
    return None


def downloadMap(name: str, silent: bool = False) -> bool:
    """
    Download a map from the vault with the given name
    """
    link = name2link(name)
    ret, msg = _doDownloadMap(name, link, silent)
    if not ret and msg is None:
        name = name.replace(" ", "_")
        link = name2link(name)
        ret, msg = _doDownloadMap(name, link, silent)
    if not ret and msg is not None:
        msg()
    return ret


def _doDownloadMap(name: str, link: str, silent: bool) -> tuple[bool, Callable[[], None] | None]:
    logger.debug("Getting map from: %s", link)
    return downloadVaultAssetNoMsg(
        url=link,
        target_dir=getUserMapsFolder(),
        exist_handler=lambda m, d: True,
        name=name,
        category="map",
        silent=silent,
    )


def processMapFolderForUpload(mapDir: str) -> None:
    """
    Zipping the file and creating thumbnails
    """
    # creating thumbnail
    exported = export_preview_from_map(mapDir)

    if exported is None:
        return

    files = exported["tozip"]
    # abort zipping if there is insufficient previews
    if files is None or len(files) != 3:
        logger.debug("Insufficient previews for making an archive.")
        return None

    # mapName = os.path.basename(mapDir).split(".v")[0]

    # making sure we pack only necessary files and not random garbage
    for filename in os.listdir(mapDir):
        endings = ['.lua', 'preview.jpg', '.scmap', '.dds']
        # stupid trick: False + False == 0, True + False == 1
        if sum([filename.endswith(x) for x in endings]) > 0:
            files.append(os.path.join(mapDir, filename))

    temp = tempfile.NamedTemporaryFile(mode='w+b', suffix=".zip", delete=False)

    # creating the zip
    zipped = zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED)

    for filename in files:
        zipped.write(
            filename,
            os.path.join(os.path.basename(mapDir), os.path.basename(filename)),
        )

    temp.flush()

    return temp
