import sys
import os
import getpass
import codecs

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QIcon, QPixmap, QDesktopServices
from PyQt5.QtCore import QUrl
from PyQt5.QtMultimedia import QSound
import subprocess

from semantic_version import Version
from util.theme import Theme, ThemeSet

from config import Settings
from PyQt5.QtCore import QStandardPaths
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

PERSONAL_DIR = str(QStandardPaths.standardLocations(QStandardPaths.DocumentsLocation)[0])
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

from PyQt5 import QtWidgets
from PyQt5.uic import *
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
            result = QtWidgets.QMessageBox.question(None, "Clear Directory",
                                                "Are you sure you wish to clear the following directory:<br/><b>&nbsp;&nbsp;" + directory + "</b>",
                                                QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
        else:
            result = QtWidgets.QMessageBox.Yes

        if (result == QtWidgets.QMessageBox.Yes):
            shutil.rmtree(directory)
            return True
        else:
            return False


# Theme and settings

THEME = None


def _setup_theme():
    global THEME
    global VERSION_STRING

    default = Theme(COMMON_DIR, None)
    themes = []
    if (os.path.isdir(THEME_DIR)):
        for infile in os.listdir(THEME_DIR):
            theme_path = os.path.join(THEME_DIR, infile)
            if os.path.isdir(os.path.join(THEME_DIR, infile)):
                themes.append(Theme(theme_path, infile))
    THEME = ThemeSet(themes, default, Settings, VERSION_STRING)

_setup_theme()

# Public settings object
# Stolen from Config because reasons
from config import _settings
settings = _settings


def clean_slate(path):
    if os.path.exists(path):
        logger.info("Wiping " + path)
        shutil.rmtree(path)
    os.makedirs(path)


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
        return THEME.icon(img, False)

def wait(until):
    '''
    Super-simple wait function that takes a callable and waits until the callable returns true or the user aborts.
    '''
    progress = QtWidgets.QProgressDialog()
    progress.show()

    while not until() and progress.isVisible():
        QtWidgets.QApplication.processEvents()

    progress.close()

    return not progress.wasCanceled()

def showDirInFileBrowser(location):
    QDesktopServices.openUrl(QUrl.fromLocalFile(location))

def showFileInFileBrowser(location):
    if sys.platform == 'win32':
        # Open the directory and highlight the picked file
        subprocess.Popen('explorer /select,"{}"'.format(location))
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
    # the UID check needs the WMI service running on Windows
    if sys.platform == 'win32':
        try:
            _, wmi_state, _, _, _, _, _ = win32serviceutil.QueryServiceStatus('Winmgmt')
            if wmi_state != win32service.SERVICE_RUNNING:
                QMessageBox.critical(None, "WMI service not running", "FAF requires the 'Windows Management Instrumentation' service for smurf protection to be running. "
                                     "Please run 'service.msc', open the 'Windows Management Instrumentation' service, set the startup type to automatic and restart FAF.")
        except Exception as e:
            QMessageBox.critical(None, "WMI service missing", "FAF requires the 'Windows Management Instrumentation' service for smurf protection. This service could not be found.")

    if sys.platform == 'win32':
        exe_path = os.path.join(fafpath.get_libdir(), "faf-uid.exe")
    else:   # Expect it to be in PATH already
        exe_path = "faf-uid"
    try:
        uid_p = subprocess.Popen([exe_path, session], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
    username, success = QtWidgets.QInputDialog.getText(parent, 'Input Username', caption)
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
