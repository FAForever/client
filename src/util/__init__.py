import datetime
import getpass
import hashlib
import logging
import os
import re
import shutil
import subprocess
import sys

from PyQt5 import QtWidgets
from PyQt5.QtCore import QStandardPaths, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QMessageBox

import fafpath
from config import VERSION as VERSION_STRING
from config import _settings  # Stolen from Config because reasons
from config import Settings
from mapGenerator import mapgenUtils
from util.theme import Theme, ThemeSet

if sys.platform == 'win32':
    import win32service
    import win32serviceutil

logger = logging.getLogger(__name__)

LOGFILE_MAX_SIZE = 256 * 1024  # 256kb should be enough for anyone

UNITS_PREVIEW_ROOT = (
    "{}/faf/unitsDB/icons/big/".format(Settings.get('content/host'))
)

COMMON_DIR = fafpath.get_resdir()

stylesheets = {}  # map [qt obj] ->  filename of stylesheet

APPDATA_DIR = Settings.get('client/data_path')

# This is used to store init_*.lua files
LUA_DIR = os.path.join(APPDATA_DIR, "lua")

# This contains the themes
THEME_DIR = os.path.join(APPDATA_DIR, "themes")

# This contains cached data downloaded while communicating with the lobby
CACHE_DIR = os.path.join(APPDATA_DIR, "cache")

# Use one cache with Java client (maps/small and maps/large)
MAP_PREVIEW_SMALL_DIR = os.path.join(CACHE_DIR, "maps", "small")
MAP_PREVIEW_LARGE_DIR = os.path.join(CACHE_DIR, "maps", "large")

MOD_PREVIEW_DIR = os.path.join(CACHE_DIR, "mod_previews")

# This contains cached data downloaded for FA extras
EXTRA_DIR = os.path.join(APPDATA_DIR, "extra")

# This contains the replays recorded by the local replay server
REPLAY_DIR = os.path.join(APPDATA_DIR, "replays")

# This contains all Lobby, Chat and Game logs
LOG_DIR = os.path.join(APPDATA_DIR, "logs")
LOG_FILE_FAF = os.path.join(LOG_DIR, 'forever.log')
LOG_FILE_MAPGEN = os.path.join(LOG_DIR, 'map_generator.log')
LOG_FILE_GAME_PREFIX = os.path.join(LOG_DIR, 'game')
LOG_FILE_GAME = LOG_FILE_GAME_PREFIX + ".log"
LOG_FILE_GAME_INFIX = ".uid."
LOG_FILE_REPLAY = os.path.join(LOG_DIR, 'replay.log')

# This contains the game binaries (old binFAF folder) and the game mods
# (.faf files)
BIN_DIR = os.path.join(APPDATA_DIR, "bin")
GAMEDATA_DIR = os.path.join(APPDATA_DIR, "gamedata")
REPO_DIR = os.path.join(APPDATA_DIR, "repo")

# This contains java executables of map generators
MAPGEN_DIR = os.path.join(APPDATA_DIR, "map_generator")

if not os.path.exists(REPO_DIR):
    os.makedirs(REPO_DIR)

settings = _settings

# initialize wine settings for non Windows platforms
if sys.platform != 'win32':
    wine_exe = settings.value("wine/exe", "wine", type=str)
    wine_cmd_prefix = settings.value("wine/cmd_prefix", "", type=str)
    if settings.contains("wine/prefix"):
        wine_prefix = str(settings.value("wine/prefix", type=str))
    else:
        wine_prefix = os.path.join(os.path.expanduser("~"), ".wine")

LOCALFOLDER = os.path.join(
    os.path.expandvars("%LOCALAPPDATA%"),
    "Gas Powered Games",
    "Supreme Commander Forged Alliance",
)
if not os.path.exists(LOCALFOLDER):
    LOCALFOLDER = os.path.join(
        os.path.expandvars("%USERPROFILE%"),
        "Local Settings", "Application Data",
        "Gas Powered Games",
        "Supreme Commander Forged Alliance",
    )
if not os.path.exists(LOCALFOLDER) and sys.platform != 'win32':
    LOCALFOLDER = os.path.join(
        wine_prefix, "drive_c", "users",
        getpass.getuser(), "Local Settings",
        "Application Data", "Gas Powered Games",
        "Supreme Commander Forged Alliance",
    )

PREFSFILENAME = os.path.join(LOCALFOLDER, "game.prefs")
if not os.path.exists(PREFSFILENAME):
    PREFSFILENAME = os.path.join(LOCALFOLDER, "Game.prefs")

DOWNLOADED_RES_PIX = {}
DOWNLOADING_RES_PIX = {}


def getPersonalDir():
    fallback = Settings.get('vault/fallback', type=bool, default=False)
    if fallback:
        dir_ = os.path.join(APPDATA_DIR, "user")
    else:
        dir_ = str(
            QStandardPaths.standardLocations(
                QStandardPaths.DocumentsLocation,
            )[0],
        )
        try:
            dir_.encode("ascii")

            if not os.path.isdir(dir_):
                raise Exception(
                    'No documents location. Will use APPDATA instead.',
                )
        except BaseException:
            logger.exception('PERSONAL_DIR not ok, falling back.')
            dir_ = os.path.join(APPDATA_DIR, "user")
    return dir_


def setPersonalDir():
    global PERSONAL_DIR
    PERSONAL_DIR = getPersonalDir()
    logger.info('PERSONAL_DIR set to: ' + PERSONAL_DIR)


PERSONAL_DIR = getPersonalDir()

logger.info('PERSONAL_DIR final: ' + PERSONAL_DIR)

# Ensure Application data directories exist

for data_dir in [
    APPDATA_DIR, PERSONAL_DIR, LUA_DIR, CACHE_DIR,
    MAP_PREVIEW_SMALL_DIR, MAP_PREVIEW_LARGE_DIR, MOD_PREVIEW_DIR,
    THEME_DIR, REPLAY_DIR, LOG_DIR, EXTRA_DIR,
]:
    if not os.path.isdir(data_dir):
        os.makedirs(data_dir)


def get_files_by_mod_date(location):
    files = os.listdir(location)
    files = map(lambda f: os.path.join(location, f), files)
    files = sorted(files, key=os.path.getmtime)
    files = list(map(os.path.basename, files))
    return files


def remove_obsolete_logs(location, pattern, max_number):
    files = get_files_by_mod_date(location)
    replay_files = [e for e in files if pattern in e]
    while len(replay_files) >= max_number:
        os.remove(os.path.join(location, replay_files[0]))
        replay_files.pop(0)


# Dirty log rotation: Get rid of logs if larger than 1 MiB
try:
    # HACK: Clean up obsolete logs directory trees
    if os.path.isfile(os.path.join(LOG_DIR, "faforever.log")):
        shutil.rmtree(LOG_DIR)
        os.makedirs(LOG_DIR)

    if os.path.isfile(LOG_FILE_FAF):
        if os.path.getsize(LOG_FILE_FAF) > LOGFILE_MAX_SIZE:
            os.remove(LOG_FILE_FAF)
    if os.path.isfile(LOG_FILE_GAME):
        if os.path.getsize(LOG_FILE_GAME) > LOGFILE_MAX_SIZE:
            os.remove(LOG_FILE_GAME)
    if os.path.isfile(LOG_FILE_MAPGEN):
        if os.path.getsize(LOG_FILE_MAPGEN) > LOGFILE_MAX_SIZE:
            os.remove(LOG_FILE_MAPGEN)
    remove_obsolete_logs(LOG_DIR, LOG_FILE_GAME_INFIX, 30)
except BaseException:
    pass


# Ensure that access time is modified (needed for cache system)
def setAccessTime(file):
    if os.path.exists(file):
        curr_time = datetime.datetime.timestamp(datetime.datetime.now())
        mtime = os.stat(file).st_mtime
        os.utime(file, times=(curr_time, mtime))


# Get rid of cached files that are stored for too long
def clearGameCache():
    fmod_dir = os.path.join(CACHE_DIR, 'featured_mod')
    if os.path.exists(fmod_dir):
        curr_time = datetime.datetime.now()
        max_storage_time = Settings.get(
            'cache/number_of_days', type=int, default=0,
        )
        if max_storage_time > -1:  # -1 stands for keeping files forever
            for _dir in ['bin', 'gamedata']:
                dir_to_check = os.path.join(fmod_dir, _dir)
                if os.path.exists(dir_to_check):
                    files_to_check = []
                    for dir, _, files in os.walk(dir_to_check):
                        files_to_check = files
                    for _file in files_to_check:
                        access_time = os.path.getatime(
                            os.path.join(dir_to_check, _file),
                        )
                        access_time = datetime.datetime.fromtimestamp(
                            access_time,
                        )
                        if (curr_time - access_time).days >= max_storage_time:
                            os.remove(os.path.join(dir_to_check, _file))


# Get rid of generated maps
def clearGeneratedMaps():
    map_dir = os.path.join(
        PERSONAL_DIR, "My Games", "Gas Powered Games",
        "Supreme Commander Forged Alliance", "Maps",
    )
    if os.path.exists(map_dir):
        for entry in os.scandir(map_dir):
            if re.match(mapgenUtils.generatedMapPattern, entry.name):
                if entry.is_dir():
                    shutil.rmtree(os.path.join(map_dir, entry.name))


def clearDirectory(directory, confirm=True):
    if os.path.isdir(directory):
        if (confirm):
            result = QtWidgets.QMessageBox.question(
                None,
                "Clear Directory",
                (
                    "Are you sure you wish to clear the following directory:"
                    "<br/><b>&nbsp;&nbsp;{}</b>".format(directory)
                ),
                QtWidgets.QMessageBox.Yes,
                QtWidgets.QMessageBox.No,
            )
        else:
            result = QtWidgets.QMessageBox.Yes

        if result == QtWidgets.QMessageBox.Yes:
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
    if os.path.isdir(THEME_DIR):
        for infile in os.listdir(THEME_DIR):
            theme_path = os.path.join(THEME_DIR, infile)
            if os.path.isdir(os.path.join(THEME_DIR, infile)):
                themes.append(Theme(theme_path, infile))
    THEME = ThemeSet(themes, default, Settings, VERSION_STRING)


_setup_theme()


def __downloadPreviewFromWeb(unitname):
    """
    Downloads a preview image from the web for the given unit name
    """
    # This is done so generated previews always have a lower case name.
    # This doesn't solve the underlying problem
    # (case folding Windows vs. Unix vs. FAF)
    import urllib.error
    import urllib.parse
    import urllib.request
    unitname = unitname.lower()

    logger.debug("Searching web preview for: " + unitname)

    url = UNITS_PREVIEW_ROOT + urllib.parse.quote(unitname)
    header = urllib.request.Request(url, headers={'User-Agent': "FAF Client"})
    req = urllib.request.urlopen(header)
    img = os.path.join(CACHE_DIR, unitname)
    with open(img, 'wb') as fp:
        shutil.copyfileobj(req, fp)
        fp.flush()
        os.fsync(fp.fileno())  # probably works without the flush and fsync
        fp.close()
    return img


def wrongPathNotice():
    msgBox = QtWidgets.QMessageBox()
    msgBox.setWindowTitle("Location not found")
    msgBox.setIcon(QtWidgets.QMessageBox.Information)
    msgBox.setText("Folder or file does not exist")
    msgBox.exec()


def showDirInFileBrowser(location):
    if not QDesktopServices.openUrl(QUrl.fromLocalFile(location)):
        wrongPathNotice()


def showFileInFileBrowser(location):
    if sys.platform == 'win32':
        # Ensure that the path is in Windows format
        location = os.path.normpath(location)

        if os.path.exists(location):
            # Open the directory and highlight the picked file
            subprocess.Popen('explorer /select,"{}"'.format(location))
        else:
            wrongPathNotice()
    else:
        # No highlighting on cross-platform, sorry!
        showDirInFileBrowser(os.path.dirname(location))


def showConfigFile():
    showFileInFileBrowser(Settings.fileName())


html_escape_table = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
    ">": "&gt;",
    "<": "&lt;",
}


def html_escape(text):
    """Produce entities within text."""
    return "".join(html_escape_table.get(c, c) for c in text)


def irc_escape(text):
    # first, strip any and all html
    text = html_escape(text)

    # taken from django and adapted
    url_re = re.compile(
        r'^((https?|faflive|fafgame|fafmap|ftp|ts3server)://)?'  # protocols
        # domain name, then TLDs
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'
        r'(?:ac|ad|ae|aero|af|ag|ai|al|am|an|ao|aq|ar|arpa|as|asia|at|au|aw|'
        r'ax|az|ba|bb|bd|be|bf|bg|bh|bi|biz|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|'
        r'ca|cat|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|com|coop|cr|cu|cv|cw|cx|cy|'
        r'cz|de|dj|dk|dm|do|dz|ec|edu|ee|eg|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|'
        r'gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gov|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|'
        r'hr|ht|hu|id|ie|il|im|in|info|int|io|iq|ir|is|it|je|jm|jo|jobs|jp|'
        r'ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|'
        r'ma|mc|md|me|mg|mh|mil|mk|ml|mm|mn|mo|mobi|mp|mq|mr|ms|mt|mu|museum|'
        r'mv|mw|mx|my|mz|na|name|nc|ne|net|nf|ng|ni|nl|no|np|nr|nu|nz|om|org|'
        r'pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|pro|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|'
        r'sb|sc|sd|se|sg|sh|si|sj|sk|sl|sm|sn|so|sr|st|su|sv|sx|sy|sz|tc|td|'
        r'tel|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|travel|tt|tv|tw|tz|ua|ug|uk|'
        r'us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|xxx|ye|yt|za|zm|zw)'
        r'|localhost'  # localhost...
        r'|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE,
    )

    # Tired of bothering with end-of-word cases in this regex
    # I'm splitting the whole string and matching each fragment start-to-end
    # as a whole
    strings = text.split(" ")
    result = []
    for fragment in strings:
        match = url_re.match(fragment)
        if match:
            # slight hack to get those protocol-less URLs on board.
            # Better: With groups!
            if "://" in fragment:
                rpl = '<a href="{0}">{0}</a>'.format(fragment)
            else:
                rpl = '<a href="http://{0}">{0}</a>'.format(fragment)

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
    if not os.path.isfile(file_name):
        return None

    with open(file_name, "rb") as fd:
        while True:
            content = fd.read(1024 * 1024)
            if not content:
                break
            m.update(content)

    return m.hexdigest()


def uniqueID(session):
    """
    This is used to uniquely identify a user's machine to prevent smurfing.
    """
    # the UID check needs the WMI service running on Windows
    if sys.platform == 'win32':
        try:
            wmi_state = win32serviceutil.QueryServiceStatus('Winmgmt')[1]
            if wmi_state != win32service.SERVICE_RUNNING:
                QMessageBox.critical(
                    None,
                    "WMI service not running",
                    "FAF requires the 'Windows Management Instrumentation' "
                    "service for smurf protection to be running. Please run "
                    "'service.msc', open the 'Windows Management "
                    "Instrumentation' service, set the startup type to "
                    "automatic and restart FAF.",
                )
        except BaseException:
            QMessageBox.critical(
                None,
                "WMI service missing",
                "FAF requires the 'Windows Management Instrumentation' service"
                " for smurf protection. This service could not be found.",
            )

    if sys.platform == 'win32':
        exe_path = os.path.join(fafpath.get_libdir(), "faf-uid.exe")
    else:   # Expect it to be in PATH already
        exe_path = "faf-uid"
    try:
        uid_p = subprocess.Popen(
            [exe_path, session],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = uid_p.communicate()
        if uid_p.returncode != 0:
            logger.error("UniqueID executable error:")
            for line in err.decode('utf-8').split('\n'):
                logger.error(line)
            return None
        else:
            return out.decode('utf-8')
    except OSError as err:
        logger.error("UniqueID error finding the executable: {}".format(err))
        return None


def strtodate(s):
    return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def datetostr(d):
    return d.strftime("%Y-%m-%d %H:%M:%S")


def getJavaPath():
    return os.path.join(
        fafpath.get_libdir(), "ice-adapter", "jre", "bin", "java.exe",
    )
