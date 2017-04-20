# system imports
import logging
import string
import sys
from urllib.error import HTTPError
from PyQt4 import QtCore, QtGui, QtNetwork
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

logger = logging.getLogger(__name__)

route = Settings.get('content/host')
VAULT_PREVIEW_ROOT = "{}/faf/vault/map_previews/small/".format(route)
VAULT_DOWNLOAD_ROOT = "{}/faf/vault/".format(route)
VAULT_COUNTER_ROOT = "{}/faf/vault/map_vault/inc_downloads.php".format(route)

maps = { # A Lookup table for info (names, sizes, players) of the official Forged Alliance Maps
    "scmp_001" : ["Burial Mounds", "1024x1024", 8],
    "scmp_002" : ["Concord Lake", "1024x1024", 8],
    "scmp_003" : ["Drake's Ravine", "1024x1024", 4],
    "scmp_004" : ["Emerald Crater", "1024x1024", 4],
    "scmp_005" : ["Gentleman's Reef", "2048x2048", 7],
    "scmp_006" : ["Ian's Cross", "1024x1024", 4],
    "scmp_007" : ["Open Palms", "512x512", 6],
    "scmp_008" : ["Seraphim Glaciers", "1024x1024", 8],
    "scmp_009" : ["Seton's Clutch", "1024x1024", 8],
    "scmp_010" : ["Sung Island", "1024x1024", 5],
    "scmp_011" : ["The Great Void", "2048x2048", 8],
    "scmp_012" : ["Theta Passage", "256x256", 2],
    "scmp_013" : ["Winter Duel", "256x256", 2],
    "scmp_014" : ["The Bermuda Locket", "1024x1024", 8],
    "scmp_015" : ["Fields Of Isis", "512x512", 4],
    "scmp_016" : ["Canis River", "256x256", 2],
    "scmp_017" : ["Syrtis Major", "512x512", 4],
    "scmp_018" : ["Sentry Point", "256x256", 3],
    "scmp_019" : ["Finn's Revenge", "512x512", 2],
    "scmp_020" : ["Roanoke Abyss", "1024x1024", 6],
    "scmp_021" : ["Alpha 7 Quarantine", "2048x2048", 8],
    "scmp_022" : ["Artic Refuge", "512x512", 4],
    "scmp_023" : ["Varga Pass", "512x512", 2],
    "scmp_024" : ["Crossfire Canal", "1024x1024", 6],
    "scmp_025" : ["Saltrock Colony", "512x512", 6],
    "scmp_026" : ["Vya-3 Protectorate", "512x512", 4],
    "scmp_027" : ["The Scar", "1024x1024", 6],
    "scmp_028" : ["Hanna oasis", "2048x2048", 8],
    "scmp_029" : ["Betrayal Ocean", "4096x4096", 8],
    "scmp_030" : ["Frostmill Ruins", "4096x4096", 8],
    "scmp_031" : ["Four-Leaf Clover", "512x512", 4],
    "scmp_032" : ["The Wilderness", "512x512", 4],
    "scmp_033" : ["White Fire", "512x512", 6],
    "scmp_034" : ["High Noon", "512x512", 4],
    "scmp_035" : ["Paradise", "512x512", 4],
    "scmp_036" : ["Blasted Rock", "256x256", 4],
    "scmp_037" : ["Sludge", "256x256", 3],
    "scmp_038" : ["Ambush Pass", "256x256", 4],
    "scmp_039" : ["Four-Corners", "256x256", 4],
    "scmp_040" : ["The Ditch", "1024x1024", 6],
    "x1mp_001" : ["Crag Dunes", "256x256", 2],
    "x1mp_002" : ["Williamson's Bridge", "256x256", 2],
    "x1mp_003" : ["Snoey Triangle", "512x512", 3],
    "x1mp_004" : ["Haven Reef", "512x512", 4],
    "x1mp_005" : ["The Dark Heart", "512x512", 6],
    "x1mp_006" : ["Daroza's Sanctuary", "512x512", 4],
    "x1mp_007" : ["Strip Mine", "1024x1024", 4],
    "x1mp_008" : ["Thawing Glacier", "1024x1024", 6],
    "x1mp_009" : ["Liberiam Battles", "1024x1024", 8],
    "x1mp_010" : ["Shards", "2048x2048", 8],
    "x1mp_011" : ["Shuriken Island", "2048x2048", 8],
    "x1mp_012" : ["Debris", "4096x4096", 8],
    "x1mp_014" : ["Flooded Strip Mine", "1024x1024", 4],
    "x1mp_017" : ["Eye Of The Storm", "512x512", 4],
}

__exist_maps = None



def isBase(mapname):
    '''
    Returns true if mapname is the name of an official map
    '''
    return mapname in maps

def getUserMaps():
    maps = []
    if os.path.isdir(getUserMapsFolder()):
        maps = os.listdir(getUserMapsFolder())
    return maps

def getDisplayName(filename):
    '''
    Tries to return a pretty name for the map (for official maps, it looks up the name)
    For nonofficial maps, it tries to clean up the filename
    '''
    if str(filename) in maps:
        return maps[filename][0]
    else:
        #cut off ugly version numbers, replace "_" with space.
        pretty = filename.rsplit(".v0", 1)[0]
        pretty = pretty.replace("_", " ")
        pretty = string.capwords(pretty)
        return pretty

def name2link(name):
    '''
    Returns a quoted link for use with the VAULT_xxxx Urls
    TODO: This could be cleaned up a little later.
    '''
    return urllib.parse.quote("maps/" + name + ".zip")

def link2name(link):
    '''
    Takes a link and tries to turn it into a local mapname
    '''
    name = link.rsplit("/")[1].rsplit(".zip")[0]
    logger.info("Converted link '" + link + "' to name '" + name + "'")
    return name

def getScenarioFile(folder):
    '''
    Return the scenario.lua file
    '''
    for infile in os.listdir(folder):
        if infile.lower().endswith("_scenario.lua"):
            return infile
    return None

def getSaveFile(folder):
    '''
    Return the save.lua file
    '''
    for infile in os.listdir(folder):
        if infile.lower().endswith("_save.lua"):
            return infile
    return None

def isMapFolderValid(folder):
    '''
    Check if the folder got all the files needed to be a map folder.
    '''
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
    '''
    Returns true if the map with the given name is available on the client
    '''
    if isBase(mapname):
        return True

    if os.path.isdir(getUserMapsFolder()):
        for infile in os.listdir(getUserMapsFolder()):
            if infile.lower() == mapname.lower():
                return True

    return False

def folderForMap(mapname):
    '''
    Returns the folder where the application could find the map
    '''
    if isBase(mapname):
        return os.path.join(getBaseMapsFolder(), mapname)

    if os.path.isdir(getUserMapsFolder()):
        for infile in os.listdir(getUserMapsFolder()):
            if infile.lower() == mapname.lower():
                return os.path.join(getUserMapsFolder(), mapname)

    return None

def getBaseMapsFolder():
    '''
    Returns the folder containing all the base maps for this client.
    '''
    gamepath = util.settings.value("ForgedAlliance/app/path", None, type=str)
    if gamepath:
        return os.path.join(gamepath, "maps")
    else:
        return "maps" #This most likely isn't the valid maps folder, but it's the best guess.


def getUserMapsFolder():
    '''
    Returns to folder where the downloaded maps of the user are stored.
    '''
    return os.path.join(
        util.PERSONAL_DIR,
        "My Games",
        "Gas Powered Games",
        "Supreme Commander Forged Alliance",
        "Maps")


def genPrevFromDDS(sourcename, destname, small=False):
    '''
    this opens supcom's dds file (format: bgra8888) and saves to png
    '''
    try:
        img = bytearray()
        buf = bytearray(16)
        file = open(sourcename, "rb")
        file.seek(128) # skip header
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
    '''
    This method auto-upgrades the maps to have small and large preview images
    '''
    if mapname is None or mapname == "":
        return
    smallExists = False
    largeExists = False
    ddsExists = False
    previews = {"cache":None, "tozip":list()}

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
    cachepngname = os.path.join(util.CACHE_DIR, mapname + ".png")

    logger.debug("Generating preview from user maps for: " + mapname)
    logger.debug("Using directory: " + mapdir)

    #Unknown / Unavailable mapname?
    if not os.path.isfile(mapfilename):
        logger.warning(
            "Unable to find the .scmap for: {}, was looking here: {}".format(
                mapname, mapfilename
                ))
        return previews

    #Small preview already exists?
    if os.path.isfile(previewsmallname):
        logger.debug(mapname + " already has small preview")
        previews["tozip"].append(previewsmallname)
        smallExists = True
        #save it in cache folder
        shutil.copyfile(previewsmallname, cachepngname)
        #checking if file was copied correctly, just in case
        if os.path.isfile(cachepngname):
            previews["cache"] = cachepngname
        else:
            logger.debug("Couldn't copy preview into cache folder")
            return previews

    #Large preview already exists?
    if os.path.isfile(previewlargename):
        logger.debug(mapname + " already has large preview")
        previews["tozip"].append(previewlargename)
        largeExists = True

    #Preview DDS already exists?
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
        mapfile.seek(30)    #Shortcut. Maybe want to clean out some of the magic numbers some day
        size = struct.unpack('i', mapfile.read(4))[0]
        data = mapfile.read(size)
        #version_minor = struct.unpack('i', mapfile.read(4))[0]
        mapfile.close()
        #logger.debug("SCMAP version %i.%i" % (version_major, version_minor))

        try:
            with open(previewddsname, "wb") as previewfile:
                previewfile.write(data)

                #checking if file was created correctly, just in case
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
            mapimage = util.pixmap(previewlargename)
            armyicon = util.pixmap("vault/map_icons/army.png").scaled(8, 9, 1, 1)
            massicon = util.pixmap("vault/map_icons/mass.png").scaled(8, 8, 1, 1)
            hydroicon = util.pixmap("vault/map_icons/hydro.png").scaled(10, 10, 1, 1)

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

iconExtensions = ["png"] #, "jpg" removed to have fewer of those costly 404 misses.

def preview(mapname, pixmap=False):
    try:
        # Try to load directly from cache
        for extension in iconExtensions:
            img = os.path.join(util.CACHE_DIR, mapname + "." + extension)
            if os.path.isfile(img):
                logger.log(5,"Using cached preview image for: " + mapname)
                return util.icon(img, False, pixmap)

        # Try to find in local map folder
        img = __exportPreviewFromMap(mapname)

        if img and 'cache' in img and img['cache'] and os.path.isfile(img['cache']):
            logger.debug("Using fresh preview image for: " + mapname)
            return util.icon(img['cache'], False, pixmap)

        return None
    except:
        logger.error("Error raised in maps.preview(...) for " + mapname)
        logger.error("Map Preview Exception", exc_info=sys.exc_info())


def downloadMap(name, silent=False):
    '''
    Download a map from the vault with the given name
    LATER: This type of method is so common, it could be put into a nice util method.
    '''
    link = name2link(name)
    url = VAULT_DOWNLOAD_ROOT + link
    logger.debug("Getting map from: " + url)

    progress = QtGui.QProgressDialog()
    if not silent:
        progress.setCancelButtonText("Cancel")
    else:
        progress.setCancelButton(None)

    progress.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
    progress.setAutoClose(False)
    progress.setAutoReset(False)


    try:
        req = urllib.request.Request(url, headers={'User-Agent' : "FAF Client"})
        zipwebfile = urllib.request.urlopen(req)
        meta = zipwebfile.info()
        file_size = int(meta.get_all("Content-Length")[0])


        progress.setMinimum(0)
        progress.setMaximum(file_size)
        progress.setModal(1)
        progress.setWindowTitle("Downloading Map")
        progress.setLabelText(name)
        progress.show()

        #Download the file as a series of 8 KiB chunks, then uncompress it.
        output = io.BytesIO()
        file_size_dl = 0
        block_sz = 8192

        while progress.isVisible():
            read_buffer = zipwebfile.read(block_sz)
            if not read_buffer:
                break
            file_size_dl += len(read_buffer)
            output.write(read_buffer)
            progress.setValue(file_size_dl)

        progress.close()
        if file_size_dl == file_size:
            zfile = zipfile.ZipFile(output)
            zfile.extractall(getUserMapsFolder())
            zfile.close()

            logger.debug("Successfully downloaded and extracted map from: " + url)
        else:
            logger.warn("Map download cancelled for: " + url)
            return False

    except:
        logger.warn("Map download or extraction failed for: " + url)
        if sys.exc_info()[0] is HTTPError:
            logger.warning("Vault download failed with HTTPError,"\
                " map probably not in vault (or broken).")
            QtGui.QMessageBox.information(
                None,
                "Map not downloadable",
                "<b>This map was not found in the vault (or is broken).</b>"\
                "<br/>You need to get it from somewhere else in order to use it.")
        else:
            logger.error("Download Exception", exc_info=sys.exc_info())
            QtGui.QMessageBox.information(
                None,
                "Map installation failed",
                "<b>This map could not be installed (please report this map or bug).</b>")
        return False

    #Count the map downloads
    try:
        url = VAULT_COUNTER_ROOT + "?map=" + urllib.parse.quote(link)
        req = urllib.request.Request(url, headers={'User-Agent' : "FAF Client"})
        urllib.request.urlopen(req)
        logger.debug("Successfully sent download counter request for: " + url)

    except:
        logger.warn("Request to map download counter failed for: " + url)
        logger.error("Download Count Exception", exc_info=sys.exc_info())

    return True

def processMapFolderForUpload(mapDir, positions):
    """
    Zipping the file and creating thumbnails
    """
    # creating thumbnail
    files = __exportPreviewFromMap(mapDir, positions)["tozip"]
    #abort zipping if there is insufficient previews
    if len(files) != 3:
        logger.debug("Insufficient previews for making an archive.")
        return None

    #mapName = os.path.basename(mapDir).split(".v")[0]

    #making sure we pack only necessary files and not random garbage
    for filename in os.listdir(mapDir):
        endings = ['.lua', 'preview.jpg', '.scmap', '.dds']
        # stupid trick: False + False == 0, True + False == 1
        if sum([filename.endswith(x) for x in endings]) > 0:
            files.append(os.path.join(mapDir, filename))

    temp = tempfile.NamedTemporaryFile(mode='w+b', suffix=".zip", delete=False)

    #creating the zip
    zipped = zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED)

    for filename in files:
        zipped.write(filename, os.path.join(os.path.basename(mapDir), os.path.basename(filename)))

    temp.flush()

    return temp
