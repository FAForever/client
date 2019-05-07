# system imports
import logging
import string
import sys
from urllib.error import HTTPError
from PyQt5 import QtCore, QtGui
import io
import util
import os
import stat
import struct
import shutil
import urllib.request, urllib.error, urllib.parse
import zipfile
import tempfile
import re
# module imports
import fa
# local imports
from config import Settings
from vault.dialogs import downloadVaultAssetNoMsg

logger = logging.getLogger(__name__)

route = Settings.get('content/host')
VAULT_PREVIEW_ROOT = "{}/faf/vault/map_previews/small/".format(route)
VAULT_DOWNLOAD_ROOT = "{}/faf/vault/".format(route)
VAULT_COUNTER_ROOT = "{}/faf/vault/map_vault/inc_downloads.php".format(route)

from model.game import OFFICIAL_MAPS as maps

__exist_maps = None


def isBase(mapname):
    """
    Returns true if mapname is the name of an official map
    """
    return mapname in maps


def getUserMaps():
    maps = []
    if os.path.isdir(getUserMapsFolder()):
        maps = os.listdir(getUserMapsFolder())
    return maps


def getDisplayName(filename):
    """
    Tries to return a pretty name for the map (for official maps, it looks up the name)
    For nonofficial maps, it tries to clean up the filename
    """
    if str(filename) in maps:
        return maps[filename][0]
    else:
        # cut off ugly version numbers, replace "_" with space.
        pretty = filename.rsplit(".v0", 1)[0]
        pretty = pretty.replace("_", " ")
        pretty = string.capwords(pretty)
        return pretty


def name2link(name):
    """
    Returns a quoted link for use with the VAULT_xxxx Urls
    TODO: This could be cleaned up a little later.
    """
    return urllib.parse.quote("maps/" + name + ".zip")


def link2name(link):
    """
    Takes a link and tries to turn it into a local mapname
    """
    name = link.rsplit("/")[1].rsplit(".zip")[0]
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


def getSaveFile(folder):
    """
    Return the save.lua file
    """
    for infile in os.listdir(folder):
        if infile.lower().endswith("_save.lua"):
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
        baseName + "_script.lua"
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
        return "maps"  # This most likely isn't the valid maps folder, but it's the best guess.


def getUserMapsFolder():
    """
    Returns to folder where the downloaded maps of the user are stored.
    """
    return os.path.join(
        util.PERSONAL_DIR,
        "My Games",
        "Gas Powered Games",
        "Supreme Commander Forged Alliance",
        "Maps")


def genPrevFromDDS(sourcename, destname, small=False):
    """
    this opens supcom's dds file (format: bgra8888) and saves to png
    """
    try:
        img = bytearray()
        buf = bytearray(16)
        file = open(sourcename, "rb")
        file.seek(128)  # skip header
        while file.readinto(buf):
            img += buf[:3] + buf[4:7] + buf[8:11] + buf[12:15]
        file.close()

        size = int((len(img)/3) ** (1.0/2))
        if small:
            imageFile = QtGui.QImage(
                img,
                size,
                size,
                QtGui.QImage.Format_RGB888).rgbSwapped().scaled(
                    100,
                    100,
                    transformMode=QtCore.Qt.SmoothTransformation)
        else:
            imageFile = QtGui.QImage(
                img,
                size,
                size,
                QtGui.QImage.Format_RGB888).rgbSwapped()
        imageFile.save(destname)
    except IOError:
        logger.debug('IOError exception in genPrevFromDDS', exc_info=True)
        raise


def __exportPreviewFromMap(mapname, positions=None):
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
        logger.debug("Can't find mapname in file system: " + mapname)
        return previews

    mapname = os.path.basename(mapdir).lower()
    mapfilename = os.path.join(mapdir, mapname.split(".")[0]+".scmap")

    mode = os.stat(mapdir)[0]
    if not (mode and stat.S_IWRITE):
        logger.debug("Map directory is not writable: " + mapdir)
        logger.debug("Writing into cache instead.")
        mapdir = os.path.join(util.CACHE_DIR, mapname)
        if not os.path.isdir(mapdir):
            os.mkdir(mapdir)

    previewsmallname = os.path.join(mapdir, mapname + ".small.png")
    previewlargename = os.path.join(mapdir, mapname + ".large.png")
    previewddsname = os.path.join(mapdir, mapname + ".dds")
    cachepngname = os.path.join(util.MAP_PREVIEW_SMALL_DIR, mapname + ".png")

    logger.debug("Generating preview from user maps for: " + mapname)
    logger.debug("Using directory: " + mapdir)

    # Unknown / Unavailable mapname?
    if not os.path.isfile(mapfilename):
        logger.warning(
            "Unable to find the .scmap for: {}, was looking here: {}".format(
                mapname, mapfilename
                ))
        return previews

    # Small preview already exists?
    if os.path.isfile(previewsmallname):
        logger.debug(mapname + " already has small preview")
        previews["tozip"].append(previewsmallname)
        smallExists = True
        # save it in cache folder
        shutil.copyfile(previewsmallname, cachepngname)
        # checking if file was copied correctly, just in case
        if os.path.isfile(cachepngname):
            previews["cache"] = cachepngname
        else:
            logger.debug("Couldn't copy preview into cache folder")
            return previews

    # Large preview already exists?
    if os.path.isfile(previewlargename):
        logger.debug(mapname + " already has large preview")
        previews["tozip"].append(previewlargename)
        largeExists = True

    # Preview DDS already exists?
    if os.path.isfile(previewddsname):
        logger.debug(mapname + " already has DDS extracted")
        previews["tozip"].append(previewddsname)
        ddsExists = True

    if not ddsExists:
        logger.debug("Extracting preview DDS from .scmap for: " + mapname)
        mapfile = open(mapfilename, "rb")
        """
        magic = struct.unpack('i', mapfile.read(4))[0]
        version_major = struct.unpack('i', mapfile.read(4))[0]
        unk_edfe = struct.unpack('i', mapfile.read(4))[0]
        unk_efbe = struct.unpack('i', mapfile.read(4))[0]
        width = struct.unpack('f', mapfile.read(4))[0]
        height = struct.unpack('f', mapfile.read(4))[0]
        unk_32 = struct.unpack('i', mapfile.read(4))[0]
        unk_16 = struct.unpack('h', mapfile.read(2))[0]
        """
        mapfile.seek(30)  # Shortcut. Maybe want to clean out some of the magic numbers some day
        size = struct.unpack('i', mapfile.read(4))[0]
        data = mapfile.read(size)
        # version_minor = struct.unpack('i', mapfile.read(4))[0]
        mapfile.close()
        # logger.debug("SCMAP version %i.%i" % (version_major, version_minor))

        try:
            with open(previewddsname, "wb") as previewfile:
                previewfile.write(data)

                # checking if file was created correctly, just in case
                if os.path.isfile(previewddsname):
                    previews["tozip"].append(previewddsname)
                else:
                    logger.debug("Failed to make DDS for: " + mapname)
                    return previews
        except IOError:
            pass

    if not smallExists:
        logger.debug("Making small preview from DDS for: " + mapname)
        try:
            genPrevFromDDS(previewddsname, previewsmallname, small=True)
            previews["tozip"].append(previewsmallname)
            shutil.copyfile(previewsmallname, cachepngname)
            previews["cache"] = cachepngname
        except IOError:
            logger.debug("Failed to make small preview for: " + mapname)
            return previews

    if not largeExists:
        logger.debug("Making large preview from DDS for: " + mapname)
        if not isinstance(positions, dict):
            logger.debug("Icon positions were not passed or they were wrong for: " + mapname)
            return previews
        try:
            genPrevFromDDS(previewddsname, previewlargename, small=False)
            mapimage = util.THEME.pixmap(previewlargename)
            armyicon = util.THEME.pixmap("vault/map_icons/army.png").scaled(8, 9, 1, 1)
            massicon = util.THEME.pixmap("vault/map_icons/mass.png").scaled(8, 8, 1, 1)
            hydroicon = util.THEME.pixmap("vault/map_icons/hydro.png").scaled(10, 10, 1, 1)

            painter = QtGui.QPainter()

            painter.begin(mapimage)
            # icons should be drawn in certain order: first layer is hydros,
            # second - mass, and army on top. made so that previews not
            # look messed up.
            if "hydro" in positions:
                for pos in positions["hydro"]:
                    target = QtCore.QRectF(
                        positions["hydro"][pos][0]-5,
                        positions["hydro"][pos][1]-5, 10, 10)
                    source = QtCore.QRectF(0.0, 0.0, 10.0, 10.0)
                    painter.drawPixmap(target, hydroicon, source)
            if "mass" in positions:
                for pos in positions["mass"]:
                    target = QtCore.QRectF(
                        positions["mass"][pos][0]-4,
                        positions["mass"][pos][1]-4, 8, 8)
                    source = QtCore.QRectF(0.0, 0.0, 8.0, 8.0)
                    painter.drawPixmap(target, massicon, source)
            if "army" in positions:
                for pos in positions["army"]:
                    target = QtCore.QRectF(
                        positions["army"][pos][0]-4,
                        positions["army"][pos][1]-4, 8, 9)
                    source = QtCore.QRectF(0.0, 0.0, 8.0, 9.0)
                    painter.drawPixmap(target, armyicon, source)
            painter.end()

            mapimage.save(previewlargename)
            previews["tozip"].append(previewlargename)
        except IOError:
            logger.debug("Failed to make large preview for: " + mapname)

    return previews

iconExtensions = ["png"]  # "jpg" removed to have fewer of those costly 404 misses.


def preview(mapname, pixmap=False):
    try:
        # Try to load directly from cache
        for extension in iconExtensions:
            img = os.path.join(util.MAP_PREVIEW_SMALL_DIR, mapname + "." + extension)
            if os.path.isfile(img):
                logger.log(5, "Using cached preview image for: " + mapname)
                return util.THEME.icon(img, False, pixmap)

        # Try to find in local map folder
        img = __exportPreviewFromMap(mapname)

        if img and 'cache' in img and img['cache'] and os.path.isfile(img['cache']):
            logger.debug("Using fresh preview image for: " + mapname)
            return util.THEME.icon(img['cache'], False, pixmap)

        return None
    except:
        logger.error("Error raised in maps.preview(...) for " + mapname)
        logger.error("Map Preview Exception", exc_info=sys.exc_info())


def downloadMap(name, silent=False):
    """
    Download a map from the vault with the given name
    """
    link = name2link(name)
    ret, msg = _doDownloadMap(name, link, silent)
    if not ret:
        name = name.replace(" ", "_")
        link = name2link(name)
        ret, msg = _doDownloadMap(name, link, silent)
        if not ret:
            msg()
            return ret

    # Count the map downloads
    try:
        url = VAULT_COUNTER_ROOT + "?map=" + urllib.parse.quote(link)
        req = urllib.request.Request(url, headers={'User-Agent': "FAF Client"})
        urllib.request.urlopen(req)
        logger.debug("Successfully sent download counter request for: " + url)
    except:
        logger.warning("Request to map download counter failed for: " + url)
        logger.error("Download Count Exception", exc_info=sys.exc_info())

    return True


def _doDownloadMap(name, link, silent):
    url = VAULT_DOWNLOAD_ROOT + link
    logger.debug("Getting map from: " + url)
    return downloadVaultAssetNoMsg(url, getUserMapsFolder(), lambda m, d: True,
                                   name, "map", silent)


def processMapFolderForUpload(mapDir, positions):
    """
    Zipping the file and creating thumbnails
    """
    # creating thumbnail
    files = __exportPreviewFromMap(mapDir, positions)["tozip"]
    # abort zipping if there is insufficient previews
    if len(files) != 3:
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
        zipped.write(filename, os.path.join(os.path.basename(mapDir), os.path.basename(filename)))

    temp.flush()

    return temp
