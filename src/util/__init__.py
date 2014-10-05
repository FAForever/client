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


import sys
import os
import urllib2
from ctypes import *


# Developer mode flag
def developer():
    return sys.executable.endswith("python.exe")

try:
    with open("RELEASE-VERSION", "r") as version_file:
            VERSION_STRING = version_file.read()
except (BaseException, IOError), e:
    VERSION_STRING = "(unknown version)"

VERSION = 0  # FIXME: causes the updater to always skip.

LOGFILE_MAX_SIZE = 256 * 1024  #256kb should be enough for anyone


UNITS_PREVIEW_ROOT = "http://content.faforever.com/faf/unitsDB/icons/big/"

#These are paths relative to the executable or main.py script
COMMON_DIR = os.path.join(os.getcwd(), "res")

# These directories are in Appdata (e.g. C:\ProgramData on some Win7 versions)
APPDATA_DIR = os.path.join(os.environ['ALLUSERSPROFILE'], "FAForever")

#This contains the themes
THEME_DIR = os.path.join(APPDATA_DIR, "themes")

#This contains cached data downloaded while communicating with the lobby - at the moment, mostly map preview pngs.
CACHE_DIR = os.path.join(APPDATA_DIR, "cache")

#This contains cached data downloaded for FA extras
EXTRA_DIR = os.path.join(APPDATA_DIR, "extra")

#This contains cached data downloaded for FA sounds
SOUND_DIR = os.path.join(APPDATA_DIR, EXTRA_DIR, "sounds")

#This contains cached data downloaded for FA voices
VOICES_DIR = os.path.join(APPDATA_DIR, EXTRA_DIR, SOUND_DIR, "voice", "us")

#This contains the replays recorded by the local replay server
REPLAY_DIR = os.path.join(APPDATA_DIR, "replays")

#This contains all Lobby, Chat and Game logs
LOG_DIR = os.path.join(APPDATA_DIR, "logs")
LOG_FILE_FAF = os.path.join(LOG_DIR, 'forever.log')
LOG_FILE_GAME = os.path.join(LOG_DIR, 'game.log')
LOG_FILE_REPLAY = os.path.join(LOG_DIR, 'replay.log')

#This contains the game binaries (old binFAF folder) and the game mods (.faf files)
BIN_DIR = os.path.join(APPDATA_DIR, "bin")
GAMEDATA_DIR = os.path.join(APPDATA_DIR, "gamedata")
REPO_DIR = os.path.join(APPDATA_DIR, "repo")

if not os.path.exists(REPO_DIR):
    os.makedirs(REPO_DIR)

LOCALFOLDER = os.path.join(os.path.expandvars("%LOCALAPPDATA%"), "Gas Powered Games",
                           "Supreme Commander Forged Alliance")
if not os.path.exists(LOCALFOLDER):
    LOCALFOLDER = os.path.join(os.path.expandvars("%USERPROFILE%"), "Local Settings", "Application Data",
                               "Gas Powered Games", "Supreme Commander Forged Alliance")
PREFSFILENAME = os.path.join(LOCALFOLDER, "game.prefs")

DOWNLOADED_RES_PIX = {}
DOWNLOADING_RES_PIX = {}

# This should be "My Documents" for most users. However, users with accents in their names can't even use these folders in Supcom
# so we are nice and create a new home for them in the APPDATA_DIR
try:
    os.environ['USERNAME'].decode('ascii')  # Try to see if the user has a wacky username

    import ctypes
    from ctypes.wintypes import MAX_PATH

    dll = ctypes.windll.shell32
    buf = ctypes.create_unicode_buffer(MAX_PATH + 1)
    if dll.SHGetSpecialFolderPathW(None, buf, 0x0005, False):
        PERSONAL_DIR = (buf.value)
    else:
        raise StandardError
except:
    PERSONAL_DIR = os.path.join(APPDATA_DIR, "user")

#Ensure Application data directories exist
if not os.path.isdir(APPDATA_DIR):
    os.makedirs(APPDATA_DIR)

if not os.path.isdir(PERSONAL_DIR):
    os.makedirs(PERSONAL_DIR)

if not os.path.isdir(CACHE_DIR):
    os.makedirs(CACHE_DIR)

if not os.path.isdir(THEME_DIR):
    os.makedirs(THEME_DIR)

if not os.path.isdir(REPLAY_DIR):
    os.makedirs(REPLAY_DIR)

if not os.path.isdir(LOG_DIR):
    os.makedirs(LOG_DIR)

if not os.path.isdir(EXTRA_DIR):
    os.makedirs(EXTRA_DIR)

if not os.path.isdir(SOUND_DIR):
    os.makedirs(SOUND_DIR)

if not os.path.isdir(VOICES_DIR):
    os.makedirs(VOICES_DIR)

from PyQt4 import QtGui, uic, QtCore
import shutil
import hashlib, sha
import re
import urllib
import _winreg


# Dirty log rotation: Get rid of logs if larger than 1 MiB
try:
    #HACK: Clean up obsolete logs directory trees
    if os.path.isfile(os.path.join(LOG_DIR, "faforever.log")):
        shutil.rmtree(LOG_DIR)
        os.makedirs(LOG_DIR)

    if os.path.isfile(LOG_FILE_FAF):
        if os.path.getsize(LOG_FILE_FAF) > LOGFILE_MAX_SIZE:
            os.remove(LOG_FILE_FAF)
except:
    pass

# Initialize logging system
import logging
import traceback

if not developer():
    logging.basicConfig(filename=LOG_FILE_FAF, level=logging.INFO,
                        format='%(asctime)s %(levelname)-8s %(name)-40s %(message)s')
else:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(name)-40s %(message)s')

logger = logging.getLogger(__name__)


def startLogging():
    logger.debug("Logging started.")


def stopLogging():
    logger.debug("Logging ended.")
    logging.shutdown()


def clearDirectory(directory, confirm=True):
    if (os.path.isdir(directory)):
        if (confirm):
            result = QtGui.QMessageBox.question(None, "Clear Directory",
                                                "Are you sure you wish to clear the following directory:<br/><b>&nbsp;&nbsp;" + directory + "</b>",
                                                QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        else:
            result = QtGui.QMessageBox.Yes

        if (result == QtGui.QMessageBox.Yes):
            shutil.rmtree(directory)
            return True
        else:
            return False


# Theme and settings
__pixmapcache = {}
__theme = None
__themedir = None


# Public settings object
settings = QtCore.QSettings("ForgedAllianceForever", "FA Lobby")

def clean_slate(path):
    if os.path.exists(path):
        logger.info("Wiping " + path)
        shutil.rmtree(path)
    os.makedirs(path)


def loadTheme():
    global __theme
    global __themedir

    settings.beginGroup("theme")
    loaded = settings.value("theme/name")
    settings.endGroup()
    logger.debug("Loaded Theme: " + str(loaded))

    setTheme(loaded, False)


def getTheme():
    return __theme


def setTheme(theme, restart=True):
    global __theme
    global __themedir

    __theme = None
    __themedir = None

    if theme:
        test_dir = os.path.join(THEME_DIR, theme)
        if os.path.isdir(test_dir):
            version_file = os.path.join(THEME_DIR, theme, "version")
            if developer() or os.path.isfile(version_file) and (VERSION_STRING == open(version_file).read()):
                logger.info("Using theme: " + theme + " in directory " + test_dir)
                __themedir = test_dir
                __theme = theme
            else:
                result = QtGui.QMessageBox.question(QtGui.QApplication.activeWindow(), "Incompatible Theme",
                                                    "The following theme is not the right version:<br/><b>" + theme + "</b><br/><i>Contact the maker of the theme for an update!</i><br/><br/><b>Reset to default, or apply theme anyway?</b>",
                                                    QtGui.QMessageBox.Apply, QtGui.QMessageBox.Reset)
                if result == QtGui.QMessageBox.Apply:
                    logger.info("Using theme: " + theme + " in directory " + test_dir)
                    __themedir = test_dir
                    __theme = theme
                else:
                    logger.warn(
                        "Theme '" + theme + "' does not have the appropriate version string.<br/><b> FAF is reverting to unthemed mode for safety.</b><br/>Check the source where you got the theme for an update.")
        else:
            logger.error("Theme not found: " + theme + " in directory " + test_dir)

            #Save theme setting
    settings.beginGroup("theme")
    settings.setValue("theme/name", __theme)
    settings.endGroup()
    settings.sync()

    if restart:
        QtGui.QMessageBox.information(None, "Restart Needed", "FAF will quit now.")
        QtGui.QApplication.quit()


def listThemes():
    '''
    Searches the THEME_DIR for all available themes, returning them as Callable Theme objects.
    '''
    themes = [None]
    if (os.path.isdir(THEME_DIR)):
        for infile in os.listdir(THEME_DIR):
            if os.path.isdir(os.path.join(THEME_DIR, infile)):
                themes.append(infile)
    else:
        logger.error("No Theme Directory")
    return themes


def curDownloadAvatar(url):
    if url in DOWNLOADING_RES_PIX:
        return DOWNLOADING_RES_PIX[url]
    return None


def removeCurrentDownloadAvatar(url, player, item):
    if url in DOWNLOADING_RES_PIX:
        DOWNLOADING_RES_PIX[url].remove(player)


def addcurDownloadAvatar(url, player):
    if url in DOWNLOADING_RES_PIX:
        if not player in DOWNLOADING_RES_PIX[url]:
            DOWNLOADING_RES_PIX[url].append(player)
        return False
    else:
        DOWNLOADING_RES_PIX[url] = []
        DOWNLOADING_RES_PIX[url].append(player)
        return True


def addrespix(url, pixmap):
    DOWNLOADED_RES_PIX[url] = pixmap


def respix(url):
    if url in DOWNLOADED_RES_PIX:
        return DOWNLOADED_RES_PIX[url]
    return None


def pixmap(filename, themed=True):
    '''
    This function loads a pixmap from a themed directory, or anywhere.
    It also stores them in a cache dictionary (may or may not be necessary depending on how Qt works under the hood)
    '''
    try:
        return __pixmapcache[filename]
    except:
        if themed:
            if __themedir and os.path.isfile(os.path.join(__themedir, filename)):
                pix = QtGui.QPixmap(os.path.join(__themedir, filename))
            else:
                pix = QtGui.QPixmap(os.path.join(COMMON_DIR, filename))
        else:
            pix = QtGui.QPixmap(filename)  #Unthemed means this can come from any location

        __pixmapcache[filename] = pix
        return pix
    return None


def loadUi(filename, themed=True):
    '''
    Loads and compiles a Qt Ui file via uic.
    Looks in theme directories first. Nonthemed means the file can come from anywhere.
    '''
    if themed:
        if __themedir and os.path.isfile(os.path.join(__themedir, filename)):
            ui = uic.loadUi(os.path.join(__themedir, filename))
        else:
            ui = uic.loadUi(os.path.join(COMMON_DIR, filename))
    else:
        ui = uic.loadUi(filename)  #Unthemed means this can come from any location

    return ui


def loadUiType(filename, themed=True):
    '''
    Loads and compiles a Qt Ui file via uic, and returns the Type and Basetype as a tuple
    Looks in theme directories first. Nonthemed means the file can come from anywhere.
    '''
    if themed:
        if __themedir and os.path.isfile(os.path.join(__themedir, filename)):
            return uic.loadUiType(os.path.join(__themedir, filename))
        else:
            return uic.loadUiType(os.path.join(COMMON_DIR, filename))
    else:
        return uic.loadUiType(filename)  #Unthemed means this can come from any location


def readlines(filename, themed=True):
    '''
    Reads and returns the contents of a file. It looks in theme folders first.
    If non-themed, the file can come from anywhere.
    '''
    if themed:
        if __themedir and os.path.isfile(os.path.join(__themedir, filename)):
            result = open(os.path.join(__themedir, filename))
            logger.debug(u"Read themed file: " + filename)
        else:
            result = open(os.path.join(COMMON_DIR, filename))
            logger.debug(u"Read common file: " + filename)
    else:
        result = open(filename)
        logger.debug(u"Read unthemed file: " + filename)

    lines = result.readlines()
    result.close()
    return lines


def readstylesheet(filename):
    if __themedir and os.path.isfile(os.path.join(__themedir, filename)):
        result = open(os.path.join(__themedir, filename)).read().replace("%THEMEPATH%", __themedir.replace("\\", "/"))
        logger.info(u"Read themed stylesheet: " + filename)
    else:
        baseDir = os.path.join(COMMON_DIR, os.path.dirname(filename))
        result = open(os.path.join(COMMON_DIR, filename)).read().replace("%THEMEPATH%", baseDir.replace("\\", "/"))
        logger.info(u"Read common stylesheet: " + filename)

    return result


def themeurl(filename):
    '''
    This creates an url to use for a local stylesheet. It's a bit of a hack because Qt has a bug identifying proper localfile QUrls
    '''
    if __themedir and os.path.isfile(os.path.join(__themedir, filename)):
        return QtCore.QUrl("file://" + os.path.join(__themedir, filename).replace("\\", "/"))
    elif os.path.isfile(os.path.join(COMMON_DIR, filename)):
        return QtCore.QUrl("file://" + os.path.join(os.getcwd(), COMMON_DIR, filename).replace("\\", "/"))
    else:
        return None


def readfile(filename, themed=True):
    '''
    Reads and returns the contents of a file. It looks in theme folders first.
    If non-themed, the file can come from anywhere.
    '''
    if themed:
        if __themedir and os.path.isfile(os.path.join(__themedir, filename)):
            result = open(os.path.join(__themedir, filename))
            logger.debug(u"Read themed file: " + filename)
        else:
            result = open(os.path.join(COMMON_DIR, filename))
            logger.debug(u"Read common file: " + filename)
    else:
        result = open(filename)
        logger.debug(u"Read unthemed file: " + filename)

    data = result.read()
    result.close()
    return data


def __downloadPreviewFromWeb(unitname):
    '''
    Downloads a preview image from the web for the given unit name
    '''
    #This is done so generated previews always have a lower case name. This doesn't solve the underlying problem (case folding Windows vs. Unix vs. FAF)
    unitname = unitname.lower()

    logger.debug("Searching web preview for: " + unitname)

    url = UNITS_PREVIEW_ROOT + urllib2.quote(unitname)
    header = urllib2.Request(url, headers={'User-Agent': "FAF Client"})
    req = urllib2.urlopen(header)
    img = os.path.join(CACHE_DIR, unitname)
    with open(img, 'wb') as fp:
        shutil.copyfileobj(req, fp)
        fp.flush()
        os.fsync(fp.fileno())  #probably works fine without the flush and fsync
        fp.close()


def iconUnit(unitname):
    # Try to load directly from cache

    img = os.path.join(CACHE_DIR, unitname)
    if os.path.isfile(img):
        logger.debug("Using cached preview image for: " + unitname)
        return icon(img, False)
    # Try to download from web
    img = __downloadPreviewFromWeb(unitname)
    if img and os.path.isfile(img):
        logger.debug("Using web preview image for: " + unitname)
        return icon(img, False)


def icon(filename, themed=True, pix=False):
    '''
    Convenience method returning an icon from a cached, optionally themed pixmap as returned by the util.pixmap(...) function
    '''
    if pix:
        return pixmap(filename, themed)
    else:
        icon = QtGui.QIcon()
        icon.addPixmap(pixmap(filename, themed), QtGui.QIcon.Normal)
        splitExt = os.path.splitext(filename)
        if len(splitExt) == 2:
            pixDisabled = pixmap(splitExt[0] + "_disabled" + splitExt[1], themed)
            if pixDisabled != None:
                icon.addPixmap(pixDisabled, QtGui.QIcon.Disabled, QtGui.QIcon.On)

            pixActive = pixmap(splitExt[0] + "_active" + splitExt[1], themed)
            if pixActive != None:
                icon.addPixmap(pixActive, QtGui.QIcon.Active, QtGui.QIcon.On)

            pixSelected = pixmap(splitExt[0] + "_selected" + splitExt[1], themed)
            if pixSelected != None:
                icon.addPixmap(pixSelected, QtGui.QIcon.Selected, QtGui.QIcon.On)

        return icon


def sound(filename, themed=True):
    '''
    Plays a sound, from one of the themed or fallback folders, or optionally from anywhere if unthemed.
    '''
    if themed:
        if __themedir and os.path.isfile(os.path.join(__themedir, filename)):
            QtGui.QSound.play(os.path.join(__themedir, filename))
        else:
            QtGui.QSound.play(os.path.join(COMMON_DIR, filename))
    else:
        QtGui.QSound.play(filename)


def wait(until):
    '''
    Super-simple wait function that takes a callable and waits until the callable returns true or the user aborts.
    '''
    progress = QtGui.QProgressDialog()
    progress.show()

    while not until() and progress.isVisible():
        QtGui.QApplication.processEvents()

    progress.close()

    return not progress.wasCanceled()


def openInExplorer(location):
    '''
    Opens a given location in Windows Explorer
    '''
    import subprocess

    _command = (u'explorer  "%s"' % location).encode(sys.getfilesystemencoding())
    subprocess.Popen(_command)


def showInExplorer(location):
    """
    Opens a given location's parent in Windows Explorer and focuses the location in it.
    """
    import subprocess

    _command = (u'explorer  /select, "%s"' % location).encode(sys.getfilesystemencoding())
    subprocess.Popen(_command)


html_escape_table = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
    ">": "&gt;",
    "<": "&lt;"
}


def html_escape(text):
    """Produce entities within text."""
    return "".join(html_escape_table.get(c, c) for c in text)


def irc_escape(text, a_style=""):
    #first, strip any and all html
    text = html_escape(text)

    #taken from django and adapted
    url_re = re.compile(
        r'^((https?|faflive|fafgame|fafmap|ftp|ts3server)://)?'  # protocols    
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'  # domain name, then TLDs
        r'(?:ac|ad|ae|aero|af|ag|ai|al|am|an|ao|aq|ar|arpa|as|asia|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|biz|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cat|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|com|coop|cr|cu|cv|cw|cx|cy|cz|de|dj|dk|dm|do|dz|ec|edu|ee|eg|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gov|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|info|int|io|iq|ir|is|it|je|jm|jo|jobs|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mil|mk|ml|mm|mn|mo|mobi|mp|mq|mr|ms|mt|mu|museum|mv|mw|mx|my|mz|na|name|nc|ne|net|nf|ng|ni|nl|no|np|nr|nu|nz|om|org|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|pro|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|sk|sl|sm|sn|so|sr|st|su|sv|sx|sy|sz|tc|td|tel|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|travel|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|xxx|ye|yt|za|zm|zw)'
        r'|localhost'  # localhost...
        r'|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    # Tired of bothering with end-of-word cases in this regex
    # I'm splitting the whole string and matching each fragment start-to-end as a whole
    strings = text.split()
    result = []
    for fragment in strings:
        match = url_re.match(fragment)
        if match:
            if "://" in fragment:  #slight hack to get those protocol-less URLs on board. Better: With groups!
                rpl = '<a href="{0}" style="{1}">{0}</a>'.format(fragment, a_style)
            else:
                rpl = '<a href="http://{0}" style="{1}">{0}</a>'.format(fragment, a_style)

            fragment = fragment.replace(match.group(0), rpl)

        result.append(fragment)
    return " ".join(result)


def md5text(text):
    m = hashlib.md5()
    m.update(text)
    return m.hexdigest()


def md5(file_name):
    """
    Compute md5 hash of the specified file.
    IOErrors raised here are handled in doUpdate.
    """
    m = hashlib.md5()
    if not os.path.isfile(file_name): return None

    with open(file_name, "rb") as fd:
        while True:
            content = fd.read(1024 * 1024)
            if not content: break
            m.update(content)

    return m.hexdigest()


def uniqueID(user, session):
    ''' This is used to uniquely identify a user's machine to prevent smurfing. '''
    try:
        if os.path.isfile("uid.dll"):
            mydll = cdll.LoadLibrary("uid.dll")
        else:
            mydll = cdll.LoadLibrary(os.path.join("lib", "uid.dll"))

        mydll.uid.restype = c_char_p
        baseString = (mydll.uid(session, os.path.join(LOG_DIR, "uid.log")) )
        DllCanUnloadNow()

        return baseString

    except:
        logger.error("UniqueID Failure", exc_info=sys.exc_info())
        return None


import datetime

_dateDummy = datetime.datetime(2013, 5, 27)


def strtodate(s):
    return _dateDummy.strptime(s, "%Y-%m-%d %H:%M:%S")


def datetostr(d):
    return str(d)[:-7]


def now():
    return _dateDummy.now()

from crash import CrashDialog
