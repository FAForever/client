import logging
import os
import re
import shutil
import zipfile

from PyQt5 import QtCore, QtGui, QtWidgets

import util
from config import Settings
from util import PREFSFILENAME
from vault import luaparser
from vault.dialogs import downloadVaultAsset

logger = logging.getLogger(__name__)


def getModFolder():
    return os.path.join(
        util.PERSONAL_DIR, "My Games", "Gas Powered Games",
        "Supreme Commander Forged Alliance", "Mods",
    )


def setModFolder():
    global MODFOLDER
    MODFOLDER = getModFolder()


setModFolder()
MODVAULT_DOWNLOAD_ROOT = "{}/faf/vault/".format(Settings.get('content/host'))

installedMods = []  # This is a global list that should be kept intact.
# So it should be cleared using installedMods[:] = []

# mods selected by user, are not overwritten by temporary mods selected when
# joining game
selectedMods = Settings.get('play/mods', default=[])


class ModInfo(object):
    def __init__(self, **kwargs):
        self.name = "Not filled in"
        self.version = 0
        self.folder = ""
        self.__dict__.update(kwargs)

    def setFolder(self, localfolder):
        self.localfolder = localfolder
        self.absfolder = os.path.join(MODFOLDER, localfolder)
        self.mod_info = os.path.join(self.absfolder, "mod_info.lua")

    def update(self):
        self.setFolder(self.localfolder)
        if isinstance(self.version, int):
            self.totalname = "{} v{}".format(self.name, self.version)
        elif isinstance(self.version, float):
            s = str(self.version).rstrip("0")
            self.totalname = "{} v{}".format(self.name, s)
        else:
            raise TypeError("version is not an int or float")

    def to_dict(self):
        out = {}
        for k, v in list(self.__dict__.items()):
            if isinstance(v, (str, int, float)) and not k[0] == '_':
                out[k] = v
        return out

    def __str__(self):
        return '{} in "{}"'.format(self.totalname, self.localfolder)


def getAllModFolders():  # returns a list of names of installed mods
    mods = []
    if os.path.isdir(MODFOLDER):
        mods = os.listdir(MODFOLDER)
    return mods


def getInstalledMods():
    installedMods[:] = []
    for f in getAllModFolders():
        m = None
        if os.path.isdir(os.path.join(MODFOLDER, f)):
            try:
                m = getModInfoFromFolder(f)
            except BaseException:
                continue
        else:
            try:
                m = getModInfoFromZip(f)
            except BaseException:
                continue
        if m:
            installedMods.append(m)
    logger.debug("Getting installed mods. Count:{}".format(len(installedMods)))
    return installedMods


def modToFilename(mod):
    return mod.absfolder


def isModFolderValid(folder):
    return os.path.exists(os.path.join(folder, "mod_info.lua"))


def iconPathToFull(path):
    """
    Converts a path supplied in the icon field of mod_info with an absolute
    path to that file. So "/mods/modname/data/icons/icon.dds" becomes
    "C:\\Users\\user\\Documents\\My Games\\Gas Powered Games\\Supreme Commander
    ...Forged Alliance\\Mods\\modname\\data\\icons\\icon.dds"
    """
    if not (path.startswith("/mods") or path.startswith("mods")):
        logger.info("Something went wrong parsing the path {}".format(path))
        return ""

    # yay for dirty hacks
    return os.path.join(
        MODFOLDER, os.path.normpath(path[5 + int(path[0] == "/"):]),
    )


def fullPathToIcon(path):
    p = os.path.normpath(os.path.abspath(path))
    return p[len(MODFOLDER) - 5:].replace('\\', '/')


def getIcon(name):
    img = os.path.join(util.MOD_PREVIEW_DIR, name)
    if os.path.isfile(img):
        logger.log(5, "Using cached preview image for: {}".format(name))
        return img
    return None


def getModInfo(modinfofile):
    modinfo = modinfofile.parse(
        {
            "name": "name",
            "uid": "uid",
            "version": "version",
            "author": "author",
            "description": "description",
            "ui_only": "ui_only",
            "icon": "icon",
        },
        {
            "version": "1",
            "ui_only": "false",
            "description": "",
            "icon": "",
            "author": "",
        },
    )
    modinfo["ui_only"] = (modinfo["ui_only"] == 'true')
    if "uid" not in modinfo:
        logger.warning("Couldn't find uid for mod {}".format(modinfo["name"]))
        return None
    # modinfo["uid"] = modinfo["uid"].lower()
    try:
        modinfo["version"] = int(modinfo["version"])
    except BaseException:
        try:
            modinfo["version"] = float(modinfo["version"])
        except BaseException:
            modinfo["version"] = 0
            logger.warning(
                "Couldn't find version for mod {}".format(modinfo["name"]),
            )
    return modinfofile, modinfo


def parseModInfo(folder):
    if not isModFolderValid(folder):
        return None
    modinfofile = luaparser.luaParser(os.path.join(folder, "mod_info.lua"))
    return getModInfo(modinfofile)


modCache = {}


def getModInfoFromZip(zfile):
    """get the mod info from a zip file"""
    if zfile in modCache:
        return modCache[zfile]

    r = None
    if zipfile.is_zipfile(os.path.join(MODFOLDER, zfile)):
        zip_ = zipfile.ZipFile(
            os.path.join(MODFOLDER, zfile), "r", zipfile.ZIP_DEFLATED,
        )
        if zip_.testzip() is None:
            for member in zip_.namelist():
                filename = os.path.basename(member)
                if not filename:
                    continue
                if filename == "mod_info.lua":
                    modinfofile = luaparser.luaParser("mod_info.lua")
                    modinfofile.iszip = True
                    modinfofile.zip = zip_
                    r = getModInfo(modinfofile)
    if r is None:
        logger.debug("mod_info.lua not found in zip file {}".format(zfile))
        return None
    f, info = r
    if f.error:
        logger.debug("Error in parsing mod_info.lua in {}".format(zfile))
        return None
    m = ModInfo(**info)
    m.setFolder(zfile)
    m.update()
    modCache[zfile] = m
    return m


def getModInfoFromFolder(modfolder):  # modfolder must be local to MODFOLDER
    if modfolder in modCache:
        return modCache[modfolder]

    r = parseModInfo(os.path.join(MODFOLDER, modfolder))
    if r is None:
        logger.debug("mod_info.lua not found in {} folder".format(modfolder))
        return None
    f, info = r
    if f.error:
        logger.debug("Error in parsing {}/mod_info.lua".format(modfolder))
        return None
    m = ModInfo(**info)
    m.setFolder(modfolder)
    m.update()
    modCache[modfolder] = m
    return m


# returns a list of ModInfo's containing information of the mods
def getActiveMods(uimods=None, temporary=True):
    """uimods:
        None - return all active mods
        True - only return active UI Mods
        False - only return active non-UI Mods
       temporary:
        read from game.prefs and not from settings
    """
    active_mods = []
    try:
        if not os.path.exists(PREFSFILENAME):
            logger.info("No game.prefs file found")
            return []
        if temporary:
            parser = luaparser.luaParser(PREFSFILENAME)
            parser.loweringKeys = False
            parsedlist = parser.parse(
                {"active_mods": "active_mods"},
                {"active_mods": {}},
            )
            modlist = parsedlist["active_mods"]
            if parser.error:
                logger.info("Error in reading the game.prefs file")
                return []
            uids = [uid for uid, b in list(modlist.items()) if b == 'true']
            # logger.debug("Active mods detected: {}".format(str(uids)))
        else:
            uids = selectedMods[:]

        allmods = []
        for m in installedMods:
            if (
                (uimods and m.ui_only)
                or (not uimods and not m.ui_only)
                or uimods is None
            ):
                allmods.append(m)
        active_mods = [m for m in allmods if m.uid in uids]
        # logger.debug(
        #     "All mods uids: {}\n\nActive mods uids: {}\n"
        #     .format(", ".join([mod.uid for mod in allmods]),
        #             ", ".join([mod.uid for mod in allmods]))
        # )
        return active_mods
    except BaseException:
        return []


# uimods works the same as in getActiveMods
def setActiveMods(mods, keepuimods=True, temporary=True):
    """
    keepuimods:
        None: Replace all active mods with 'mods'
        True: Keep the UI mods already activated activated
        False: Keep only the non-UI mods that were activated activated
        So set it True if you want to set gameplay mods, and False if you want
        to set UI mods.
    temporary:
        Set this when mods are activated due to joining a game.
    """
    if keepuimods is not None:
        # returns the active UI mods if True, the active non-ui mods if False
        keepTheseMods = getActiveMods(keepuimods)
    else:
        keepTheseMods = []
    allmods = keepTheseMods + mods
    logger.debug(
        'Setting active Mods: {}'.format([
            mod.uid
            for mod in allmods
        ]),
    )
    s = "active_mods = {\n"
    for mod in allmods:
        s += "['{}'] = true,\n".format(str(mod.uid))
    s += "}"

    if not temporary:
        global selectedMods
        logger.debug('selectedMods was: {}'.format(Settings.get('play/mods')))
        selectedMods = [str(mod.uid) for mod in allmods]
        logger.debug('Writing selectedMods: {}'.format(selectedMods))
        Settings.set('play/mods', selectedMods)
        logger.debug(
            'selectedMods written: {}'.format(Settings.get('play/mods')),
        )

    try:
        with open(PREFSFILENAME, 'r') as f:
            data = f.read()
    except BaseException:
        logger.info("Couldn't read the game.prefs file")
        return False

    if re.search(r"active_mods\s*=\s*{.*?}", data, re.S):
        data = re.sub(r"active_mods\s*=\s*{.*?}", s, data, 1, re.S)
    else:
        data += "\n" + s

    try:
        with open(PREFSFILENAME, 'w') as f:
            f.write(data)
    except BaseException:
        logger.info("Cound't write to the game.prefs file")
        return False

    return True


def updateModInfo(mod, info):  # should probably not be used.
    """
    Updates a mod_info.lua file with new data.
    Because those files can be random lua this function can fail if the file is
    complicated enough. If every value however is on a seperate line, this
    should work.
    """
    logger.warning("updateModInfo called. Probably not a good idea")
    fname = mod.mod_info
    try:
        with open(fname, 'r') as f:
            data = f.read()
    except BaseException:
        logger.info("Something went wrong reading {}".format(fname))
        return False

    for k, v in list(info.items()):
        if type(v) in (bool, int):
            val = str(v).lower()
        if type(v) in (str, str):
            val = '"' + v.replace('"', '\\"') + '"'
        if re.search(r'^\s*' + k, data, re.M):
            data = re.sub(
                r'^\s*' + k + r'\s*=.*$', "{} = {}".format(k, val),
                data, 1, re.M,
            )
        else:
            if data[-1] != '\n':
                data += '\n'
            data += "{} = {}".format(k, val)
    try:
        with open(fname, 'w') as f:
            f.write(data)
    except BaseException:
        logger.info("Something went wrong writing to {}".format(fname))
        return False

    return True


def generateThumbnail(sourcename, destname):
    """
    Given a dds file, generates a png file (or whatever the extension
    of dest is
    """
    logger.debug(
        "Creating png thumnail for {} to {}".format(sourcename, destname),
    )

    try:
        img = bytearray()
        buf = bytearray(16)
        with open(sourcename, "rb") as f:
            f.seek(128)  # skip header
            while f.readinto(buf):
                img += buf[:3] + buf[4:7] + buf[8:11] + buf[12:15]

        size = int((len(img) / 3) ** (1.0 / 2))
        image = QtGui.QImage(img, size, size, QtGui.QImage.Format_RGB888)
        imageFile = image.rgbSwapped().scaled(
            100, 100, transformMode=QtCore.Qt.SmoothTransformation,
        )
        imageFile.save(destname)
    except IOError:
        return False

    if os.path.isfile(destname):
        return True
    else:
        return False


def downloadMod(item):
    if isinstance(item, str):
        link = item
    else:
        link = item.link
    logger.debug("Getting mod from: {}".format(link))

    def handle_exist(path, modname):
        modpath = os.path.join(path, modname)
        oldmod = getModInfoFromFolder(modpath)
        result = QtWidgets.QMessageBox.question(
            None,
            "Modfolder already exists",
            (
                "The mod is to be downloaded to the folder '{}'. This folder "
                "already exists and contains <b>{}</b>. Do you want to "
                "overwrite this mod?"
            ).format(modpath, oldmod.totalname),
            QtWidgets.QMessageBox.Yes,
            QtWidgets.QMessageBox.No,
        )
        if result == QtWidgets.QMessageBox.No:
            return False
        removeMod(oldmod)
        return True

    return downloadVaultAsset(
        link, MODFOLDER, handle_exist, link, "mod", False,
    )


def removeMod(mod):
    logger.debug("removing mod {}".format(mod.name))
    real = None
    for m in getInstalledMods():
        if m.uid == mod.uid:
            real = m
            break
    else:
        logger.debug("Can't remove mod. Mod not found.")
        return False
    shutil.rmtree(real.absfolder)
    if real.localfolder in modCache:
        del modCache[real.localfolder]
    installedMods.remove(real)
    return True
    # we don't update the installed mods, because the operating system takes
    # some time registering the deleted folder.
