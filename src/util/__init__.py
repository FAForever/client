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

from PyQt5 import QtWidgets, uic, QtCore
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
__pixmapcache = {}
__theme = None
__themedir = None

THEME = None

# Public settings object
# Stolen from Config because reasons
from config import _settings
settings = _settings

def clean_slate(path):
    if os.path.exists(path):
        logger.info("Wiping " + path)
        shutil.rmtree(path)
    os.makedirs(path)


class Theme():
    """
    Represents a single FAF client theme.
    """
    def __init__(self, themedir, name):
        """
        A 'None' themedir represents no theming (no dir prepended to filename)
        """
        self._themedir = themedir
        self.name = name
        self._pixmapcache = {}

    def __str__(self):
        return str(self.name)

    def _themepath(self, filename):
        if self._themedir is None:
            return filename
        else:
            return os.path.join(self._themedir, filename)

    @property
    def themedir(self):
        return str(self._themedir)

    def _noneIfNoFile(fun):
        def _fun(self, filename):
            if not os.path.isfile(self._themepath(filename)):
                return None
            return fun(self, filename)
        return _fun

    def version(self):
        if self._themedir == None:
            return None
        try:
            version_file = self._themepath("version")
            with open(version_file) as f:
                return Version(f.read().strip())
        except (IOError, ValueError):
            return None

    def pixmap(self, filename):
        '''
        This function loads a pixmap from a themed directory, or anywhere.
        It also stores them in a cache dictionary (may or may not be necessary depending on how Qt works under the hood)
        '''
        try:
            return self._pixmapcache[filename]
        except KeyError:
            if os.path.isfile(self._themepath(filename)):
                pix = QtGui.QPixmap(self._themepath(filename))
            else:
                pix = None

        self._pixmapcache[filename] = pix
        return pix

    @_noneIfNoFile
    def loadUi(self, filename):
        'Loads and compiles a Qt Ui file via uic.'
        return uic.loadUi(self._themepath(filename))

    @_noneIfNoFile
    def loadUiType(self, filename):
        'Loads and compiles a Qt Ui file via uic, and returns the Type and Basetype as a tuple'
        return uic.loadUiType(self._themepath(filename))

    @_noneIfNoFile
    def readlines(self, filename):
        'Reads and returns the contents of a file in the theme dir.'
        with open(self._themepath(filename)) as f:
            logger.debug(u"Read themed file: " + filename)
            return f.readLines()

    @_noneIfNoFile
    def readstylesheet(self, filename):
        with open(self._themepath(filename)) as f:
            logger.info(u"Read themed stylesheet: " + filename)
            return f.read().replace("%THEMEPATH%", self._themedir.replace("\\", "/"))

    @_noneIfNoFile
    def themeurl(self, filename):
        '''
        This creates an url to use for a local stylesheet. It's a bit of a hack because Qt has a bug identifying proper localfile QUrls
        '''
        return QtCore.QUrl("file://" + self._themepath(filename).replace("\\", "/"))

    @_noneIfNoFile
    def readfile(self, filename):
        'Reads and returns the contents of a file in the theme folder.'
        with open(self._themepath(filename)) as f:
            logger.debug(u"Read themed file: " + filename)
            return f.read()

    @_noneIfNoFile
    def sound(self, filename):
        'Returns a sound file string, from the themed folder.'
        return self._themepath(filename)

class ThemeSet:
    '''
    Represent a collection of themes to choose from, with a default theme and
    an unthemed directory.
    '''
    def __init__(self, themeset, default_theme, settings,
                 client_version, unthemed = None):
        self._default_theme = default_theme
        self._themeset = themeset
        self._theme = default_theme
        self._unthemed = Theme(None, '') if unthemed is None else unthemed
        self._settings = settings
        self._client_version = client_version

        # For refreshing stylesheets
        self._stylesheets = {}

    @property
    def theme(self):
        return self._theme

    def _getThemeByName(self, name):
        if name is None:
            return self._default_theme
        matching_themes = [theme for theme in self._themeset if theme.name == name]
        if not matching_themes:
            return None
        return matching_themes[0]

    def loadTheme(self):
        name = self._settings.get("theme/theme/name", None)
        logger.debug("Loaded Theme: " + str(name))
        self.setTheme(name, False)

    def listThemes(self):
        return [None] + [theme.name for theme in self._themeset]

    def setTheme(self, name, restart = True):
        theme = self._getThemeByName(name)
        if theme is None:
            return

        set_theme = self._do_setTheme(theme)

        self._settings.set("theme/theme/name", self._theme.name)
        self._settings.sync()

        if set_theme and restart:
            QtGui.QMessageBox.information(None, "Restart Needed", "FAF will quit now.")
            QtGui.QApplication.quit()


    def _checkThemeVersion(self, theme):
        "Returns a (potentially overridden) theme version."
        version = theme.version()
        if version is None:
            # Malformed theme, we should not override it!
            return None

        override_config = "theme_version_override/" + str(theme)
        override_version_str = self._settings.get(override_config, None)

        if override_version_str is None:
            return version

        try:
            override_version = Version(override_version_str)
        except ValueError:
            # Did someone manually mess with the override config?
            logger.warn("Malformed theme version override setting: " + override_version_str)
            self._settings.remove(override_config)
            return version

        if version >= override_version:
            logger.info("New version " + str(version) + " of theme " + theme +
                        ", removing override " + override_version_str)
            self._settings.remove(override_config)
            return version
        else:
            return override_version

    def _checkThemeOutdated(self, theme_version):
        faf_version = Version(self._client_version)
        return faf_version > theme_version


    def _do_setTheme(self, new_theme):
        old_theme = self._theme
        theme_changed = lambda: old_theme != self._theme

        if new_theme == self._theme:
            return theme_changed()

        if new_theme == self._default_theme:
            # No need for checks
            self._theme = new_theme
            return theme_changed()

        theme_version = self._checkThemeVersion(new_theme)
        if theme_version is None:
            QtGui.QMessageBox.information(
                    QtGui.QApplication.activeWindow(),
                    "Invalid Theme",
                    "Failed to read the version of the following theme:<br/><b>" +
                    str(new_theme) +
                    "</b><br/><i>Contact the maker of the theme for a fix!</i>")
            logger.error("Error reading theme version: " + str(new_theme) +
                         " in directory " + new_theme.themedir)
            return theme_changed()

        outdated = self._checkThemeOutdated(theme_version)

        if not outdated:
            logger.info("Using theme: " + str(new_theme) +
                        " in directory " + new_theme.themedir)
            self._theme = new_theme
        else:
            box = QtGui.QMessageBox(QtGui.QApplication.activeWindow())
            box.setWindowTitle("Incompatible Theme")
            box.setText(
                    "The selected theme reports compatibility with a lower version of the FA client:<br/><b>" +
                    str(new_theme) +
                    "</b><br/><i>Contact the maker of the theme for an update!</i><br/>" +
                    "<b>Do you want to try to apply the theme anyway?</b>")
            b_yes = box.addButton("Apply this once", QtGui.QMessageBox.YesRole)
            b_always = box.addButton("Always apply for this FA version", QtGui.QMessageBox.YesRole)
            b_default = box.addButton("Use default theme", QtGui.QMessageBox.NoRole)
            b_no = box.addButton("Abort", QtGui.QMessageBox.NoRole)
            box.exec_()
            result = box.clickedButton()

            if result == b_always:
                QtGui.QMessageBox.information(
                        QtGui.QApplication.activeWindow(),
                        "Notice",
                        "If the applied theme causes crashes, clear the '[theme_version_override]'<br/>" +
                        "section of your FA client config file.")
                logger.info("Overriding version of theme " + str(new_theme) + "with " + self._client_version)
                override_config = "theme_version_override/" + str(new_theme)
                self._settings.set(override_config, self._client_version)

            if result == b_always or result == b_yes:
                logger.info("Using theme: " + str(new_theme) +
                            " in directory " + new_theme.themedir)
                self._theme = new_theme
            elif result == b_default:
                self._theme = self._default_theme
            else:
                pass
        return theme_changed()


    def _theme_callchain(self, fn_name, filename, themed):
        """
        Calls fn_name chaining through theme / default theme / unthemed.
        """
        if themed:
            item = getattr(self._theme, fn_name)(filename)
            if item is None:
                item = getattr(self._default_theme, fn_name)(filename)
        else:
            item = getattr(self._unthemed, fn_name)(filename)
        return item

    def _warn_resource_null(fn):
        def _nullcheck(self, filename, themed = True):
            ret = fn(self, filename, themed)
            if ret is None:
                logger.warn("Failed to load resource '" + filename + "' in theme." + fn.__name__)
            return ret
        return _nullcheck


    def _pixmap(self, filename, themed = True):
        return self._theme_callchain("pixmap", filename, themed)

    @_warn_resource_null
    def loadUi(self, filename, themed = True):
        return self._theme_callchain("loadUi", filename, themed)

    @_warn_resource_null
    def loadUiType(self, filename, themed = True):
        return self._theme_callchain("loadUiType", filename, themed)

    @_warn_resource_null
    def readlines(self, filename, themed = True):
        return self._theme_callchain("readlines", filename, themed)

    @_warn_resource_null
    def readstylesheet(self, filename, themed = True):
        return self._theme_callchain("readstylesheet", filename, themed)

    @_warn_resource_null
    def themeurl(self, filename, themed = True):
        return self._theme_callchain("themeurl", filename, themed)

    @_warn_resource_null
    def readfile(self, filename, themed = True):
        return self._theme_callchain("readfile", filename, themed)

    @_warn_resource_null
    def _sound(self, filename, themed = True):
        return self._theme_callchain("sound", filename, themed)

    def pixmap(self, filename, themed = True):
        # If we receive None, return the default pixmap
        ret = self._pixmap(filename, themed)
        if ret is None:
            return QtGui.QPixmap()
        return ret

    def sound(self, filename, themed = True):
        QSound.play(self._sound(filename, themed))


    def setStyleSheet(self, obj, filename):
        self._stylesheets[obj] = filename
        obj.setStyleSheet(self.readstylesheet(filename))

    def reloadStyleSheets(self):
        for obj, filename in self._stylesheets.items():
            obj.setStyleSheet(self.readstylesheet(filename))

    def icon(self, filename, themed=True, pix=False):
        '''
        Convenience method returning an icon from a cached, optionally themed pixmap as returned by the pixmap(...) function
        '''
        if pix:
            return self.pixmap(filename, themed)
        else:
            icon = QtGui.QIcon()
            icon.addPixmap(self.pixmap(filename, themed), QtGui.QIcon.Normal)
            splitExt = os.path.splitext(filename)
            if len(splitExt) == 2:
                pixDisabled = self.pixmap(splitExt[0] + "_disabled" + splitExt[1], themed)
                if pixDisabled != None:
                    icon.addPixmap(pixDisabled, QtGui.QIcon.Disabled, QtGui.QIcon.On)

                pixActive = self.pixmap(splitExt[0] + "_active" + splitExt[1], themed)
                if pixActive != None:
                    icon.addPixmap(pixActive, QtGui.QIcon.Active, QtGui.QIcon.On)

                pixSelected = self.pixmap(splitExt[0] + "_selected" + splitExt[1], themed)
                if pixSelected != None:
                    icon.addPixmap(pixSelected, QtGui.QIcon.Selected, QtGui.QIcon.On)
            return icon


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
