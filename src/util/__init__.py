import sys
import os
import subprocess
import getpass
import codecs
from ctypes import *

from PyQt4.QtGui import QDesktopServices, QMessageBox, QInputDialog
from PyQt4.QtCore import QUrl
import subprocess

from semantic_version import Version

from config import Settings
if sys.platform == 'win32':
    import win32serviceutil
    import win32service

# Developer mode flag
def developer():
    return sys.executable.endswith("python.exe")

from config import VERSION as VERSION_STRING

import logging
logger = logging.getLogger(__name__)

LOGFILE_MAX_SIZE = 256 * 1024  #256kb should be enough for anyone

UNITS_PREVIEW_ROOT = "{}/faf/unitsDB/icons/big/".format(Settings.get('content/host'))

import fafpath
COMMON_DIR = fafpath.get_resdir()

stylesheets = {} # map [qt obj] ->  filename of stylesheet

APPDATA_DIR = Settings.get('client/data_path')

#This is used to store init_*.lua files
LUA_DIR = os.path.join(APPDATA_DIR, "lua")

#This contains the themes
THEME_DIR = os.path.join(APPDATA_DIR, "themes")

#This contains cached data downloaded while communicating with the lobby - at the moment, mostly map preview pngs.
CACHE_DIR = os.path.join(APPDATA_DIR, "cache")

#This contains cached data downloaded for FA extras
EXTRA_DIR = os.path.join(APPDATA_DIR, "extra")

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

# Public settings object
# Stolen from Config because reasons
from config import _settings
settings = _settings

# initialize wine settings for non Windows platforms
if sys.platform != 'win32':
    wine_exe = settings.value("wine/exe", "wine", type=str)
    wine_cmd_prefix = settings.value("wine/cmd_prefix", "", type=str)
    if settings.contains("wine/prefix"):
        wine_prefix = str(settings.value("wine/prefix", type=str))
    else:
        wine_prefix = os.path.join(os.path.expanduser("~"), ".wine")

LOCALFOLDER = os.path.join(os.path.expandvars("%LOCALAPPDATA%"), "Gas Powered Games",
                           "Supreme Commander Forged Alliance")
if not os.path.exists(LOCALFOLDER):
    LOCALFOLDER = os.path.join(os.path.expandvars("%USERPROFILE%"), "Local Settings", "Application Data",
                               "Gas Powered Games", "Supreme Commander Forged Alliance")
if not os.path.exists(LOCALFOLDER) and sys.platform != 'win32':
    LOCALFOLDER = os.path.join(wine_prefix, "drive_c", "users", getpass.getuser(), "Local Settings", "Application Data",
                               "Gas Powered Games", "Supreme Commander Forged Alliance")

PREFSFILENAME = os.path.join(LOCALFOLDER, "game.prefs")
if not os.path.exists(PREFSFILENAME):
    PREFSFILENAME = os.path.join(LOCALFOLDER, "Game.prefs")

DOWNLOADED_RES_PIX = {}
DOWNLOADING_RES_PIX = {}

PERSONAL_DIR = str(QDesktopServices.storageLocation(QDesktopServices.DocumentsLocation))
logger.info('PERSONAL_DIR initial: ' + PERSONAL_DIR)
try:
    PERSONAL_DIR.encode("ascii")

    if not os.path.isdir(PERSONAL_DIR):
        raise Exception('No documents location. Will use APPDATA instead.')
except:
    logger.exception('PERSONAL_DIR not ok, falling back.')
    PERSONAL_DIR = os.path.join(APPDATA_DIR, "user")

logger.info('PERSONAL_DIR final: ' + PERSONAL_DIR)

#Ensure Application data directories exist
if not os.path.isdir(APPDATA_DIR):
    os.makedirs(APPDATA_DIR)

if not os.path.isdir(PERSONAL_DIR):
    os.makedirs(PERSONAL_DIR)

if not os.path.isdir(LUA_DIR):
    os.makedirs(LUA_DIR)

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

from PyQt4 import QtGui, uic, QtCore
from PyQt4.uic import *
import shutil
import hashlib
import re


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
# Stolen from Config because reasons
from config import _settings
settings = _settings

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

# Throws an exception if it fails to read and parse theme version string.
def _checkThemeVersion(theme):
    version_file = os.path.join(THEME_DIR, theme, "version")
    version_str = open(version_file).read().strip()
    version = Version(version_str)

    override_config = "theme_version_override/" + theme
    override_version_str = Settings.get(override_config, None)
    if override_version_str is None:
        return version

    try:
        override_version = Version(override_version_str)
    except ValueError:
        # Did someone manually mess with the override config?
        logger.warn("Malformed theme version override setting: " + override_version_str)
        Settings.remove(override_config)
        return version

    if version >= override_version:
        logger.info("New version " + version_str + " of theme " + theme +
                    ", removing override " + override_version_str)
        Settings.remove(override_config)
        return version
    else:
        return override_version

def _checkThemeOutdated(theme):
    theme_version = _checkThemeVersion(theme)
    faf_version = Version(VERSION_STRING)
    return faf_version > theme_version

def _do_setTheme(new_theme):
    global __theme
    global __themedir

    old_theme = __theme
    theme_changed = lambda: old_theme != __theme

    if new_theme == __theme:
        return theme_changed()

    # Is the theme default?
    if new_theme is None:
        __theme = None
        __themedir = None
        return theme_changed()

    test_dir = os.path.join(THEME_DIR, new_theme)
    if not os.path.isdir(test_dir):
        logger.error("Theme not found: " + new_theme + " in directory " + test_dir)
        return theme_changed()

    try:
        outdated = _checkThemeOutdated(new_theme)
    except:
        QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
                "Invalid Theme",
                "Failed to read the version of the following theme:<br/><b>" +
                new_theme +
                "</b><br/><i>Contact the maker of the theme for a fix!</i>")
        logger.error("Error reading theme version: " + new_theme + " in directory " + test_dir)
        return theme_changed()

    if not outdated:
        logger.info("Using theme: " + new_theme + " in directory " + test_dir)
        __themedir = test_dir
        __theme = new_theme
    else:
        box = QtGui.QMessageBox(QtGui.QApplication.activeWindow())
        box.setWindowTitle("Incompatible Theme")
        box.setText(
                "The selected theme reports compatibility with a lower version of the FA client:<br/><b>" +
                new_theme +
                "</b><br/><i>Contact the maker of the theme for an update!</i><br/>" +
                "<b>Do you want to try to apply the theme anyway?</b>")
        b_yes = box.addButton("Apply this once", QtGui.QMessageBox.YesRole)
        b_always = box.addButton("Always apply for this FA version", QtGui.QMessageBox.YesRole)
        b_default = box.addButton("Use default theme", QtGui.QMessageBox.NoRole)
        b_no = box.addButton("Abort", QtGui.QMessageBox.NoRole)
        box.exec_()
        result = box.clickedButton()

        if result == b_always:
            QMessageBox.information(
                    QtGui.QApplication.activeWindow(),
                    "Notice",
                    "If the applied theme causes crashes, clear the '[theme_version_override]'<br/>" +
                    "section of your FA client config file.")
            logger.info("Overriding version of theme " + new_theme + "with " + VERSION_STRING)
            override_config = "theme_version_override/" + new_theme
            Settings.set(override_config, VERSION_STRING)

        if result == b_always or result == b_yes:
            logger.info("Using theme: " + new_theme + " in directory " + test_dir)
            __themedir = test_dir
            __theme = new_theme
        elif result == b_default:
            __themedir = None
            __theme = None
        else:
            pass
    return theme_changed()

def setTheme(theme, restart=True):
    global __theme

    set_theme = _do_setTheme(theme)

    #Starting value of __theme needn't be the value in settings
    settings.beginGroup("theme")
    settings.setValue("theme/name", __theme)
    settings.endGroup()
    settings.sync()

    if set_theme and restart:
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
            logger.debug("Read themed file: " + filename)
        else:
            result = open(os.path.join(COMMON_DIR, filename))
            logger.debug("Read common file: " + filename)
    else:
        result = open(filename)
        logger.debug("Read unthemed file: " + filename)

    lines = result.readlines()
    result.close()
    return lines


def setStyleSheet(obj, filename):
    stylesheets[obj] = filename
    obj.setStyleSheet(readstylesheet(filename))


def reloadStyleSheets():
    for obj, filename in stylesheets.items():
        obj.setStyleSheet(readstylesheet(filename))

def readstylesheet(filename):
    if __themedir and os.path.isfile(os.path.join(__themedir, filename)):
        result = open(os.path.join(__themedir, filename)).read().replace("%THEMEPATH%", __themedir.replace("\\", "/"))
        logger.info("Read themed stylesheet: " + filename)
    else:
        baseDir = os.path.join(COMMON_DIR, os.path.dirname(filename))
        result = open(os.path.join(COMMON_DIR, filename)).read().replace("%THEMEPATH%", baseDir.replace("\\", "/"))
        logger.info("Read common stylesheet: " + filename)

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
            result = codecs.open(os.path.join(__themedir, filename), encoding='utf-8')
            logger.debug("Read themed file: " + filename)
        else:
            result = codecs.open(os.path.join(COMMON_DIR, filename), encoding='utf-8')
            logger.debug("Read common file: " + filename)
    else:
        result = codecs.open(filename, encoding='utf-8')
        logger.debug("Read unthemed file: " + filename)

    data = result.read()
    result.close()
    return data


def __downloadPreviewFromWeb(unitname):
    '''
    Downloads a preview image from the web for the given unit name
    '''
    #This is done so generated previews always have a lower case name. This doesn't solve the underlying problem (case folding Windows vs. Unix vs. FAF)
    import urllib.request, urllib.error, urllib.parse
    unitname = unitname.lower()

    logger.debug("Searching web preview for: " + unitname)

    url = UNITS_PREVIEW_ROOT + urllib.parse.quote(unitname)
    header = urllib.request.Request(url, headers={'User-Agent': "FAF Client"})
    req = urllib.request.urlopen(header)
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
        logger.log(5, "Using cached preview image for: " + unitname)
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

def showDirInFileBrowser(location):
    QDesktopServices.openUrl(QUrl.fromLocalFile(location))

def showFileInFileBrowser(location):
    if sys.platform == 'win32':
        # Open the directory and highlight the picked file
        _command = (u'explorer  /select, "%s"' % location).encode(sys.getfilesystemencoding())
        subprocess.Popen(_command)
    else:
        # No highlighting on cross-platform, sorry!
        showDirInFileBrowser(os.path.dirname(location))

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

def password_hash(password):
    return hashlib.sha256(password.strip().encode("utf-8")).hexdigest()

def md5text(text):
    m = hashlib.md5()
    m.update(text.encode('utf-8'))
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
    env = os.environ
    env['PATH'] += os.pathsep + os.getcwd() # the Windows setup places executables in the root/CWD
    env['PATH'] += os.pathsep + os.path.join(os.getcwd(), "lib") # the default download location for travis/Appveyor
    # the UID check needs the WMI service running on Windows
    if sys.platform == 'win32':
        try:
            _, wmi_state, _, _, _, _, _ = win32serviceutil.QueryServiceStatus('Winmgmt')
            if wmi_state != win32service.SERVICE_RUNNING:
                QMessageBox.critical(None, "WMI service not running", "FAF requires the 'Windows Management Instrumentation' service for smurf protection to be running. "
                                     "Please run 'service.msc', open the 'Windows Management Instrumentation' service, set the startup type to automatic and restart FAF.")
        except Exception as e:
            QMessageBox.critical(None, "WMI service missing", "FAF requires the 'Windows Management Instrumentation' service for smurf protection. This service could not be found.")
    try:
        uid_p = subprocess.Popen(["faf-uid", session], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = uid_p.communicate()
        if uid_p.returncode != 0:
            logger.error("UniqueID executable error:")
            for line in err.split('\n'):
                logger.error(line)
            return None
        else:
            return out.decode('utf-8')
    except OSError as err:
        logger.error("UniqueID error finding the executable: {}".format(err))
        return None


def userNameAction(parent, caption, action):
    """ Get a username and execute action with it"""
    username, success = QInputDialog.getText(parent, 'Input Username', caption)
    if success and username != '':
        action(username)

import datetime

_dateDummy = datetime.datetime(2013, 5, 27)


def strtodate(s):
    return _dateDummy.strptime(s, "%Y-%m-%d %H:%M:%S")


def datetostr(d):
    return str(d)[:-7]


def now():
    return _dateDummy.now()

from .crash import CrashDialog
