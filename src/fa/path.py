import logging
import os
import sys
import textwrap

from src import config
from src import util

logger = logging.getLogger(__name__)


def steamPath():
    try:
        import winreg
        steam_key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            "Software\\Valve\\Steam",
            0,
            (winreg.KEY_WOW64_64KEY + winreg.KEY_ALL_ACCESS),
        )
        query_value = winreg.QueryValueEx(steam_key, "SteamPath")
        return query_value[0].replace("/", "\\")
    except Exception:
        return None


def writeFAPathLua(mod: str, version: int) -> None:
    """
    Writes a small lua file to disk that helps the new
    SupComDataPath.lua find the actual install of the game
    """
    name = os.path.join(util.APPDATA_DIR, "fa_path.lua")
    gamepath_fa = config.Settings.get("ForgedAlliance/app/path", type=str)

    code = f"""\
        fa_path = "{gamepath_fa.replace("\\", "/")}"
        custom_vault_path = "{util.VAULTS_BASE_DIR.replace("\\", "/")}"
        GameType = "{mod}"
        GameVersion = "{version}"
        ClientVersion = "{config.VERSION}"
    """

    with open(name, "w+", encoding='utf-8') as lua:
        lua.write(textwrap.dedent(code))
        lua.flush()
        # Ensuring the file is absolutely, positively on disk.
        os.fsync(lua.fileno())


def typicalForgedAlliancePaths():
    """
    Returns a list of the most probable paths where Supreme Commander:
    Forged Alliance might be installed
    """
    pathlist = [
        config.Settings.get("ForgedAlliance/app/path", "", type=str),

        # Retail path
        os.path.expandvars(
            "%ProgramFiles%\\THQ\\Gas Powered Games\\"
            "Supreme Commander - Forged Alliance",
        ),

        # Direct2Drive Paths
        # ... allegedly identical to impulse paths - need to confirm this

        # Impulse/GameStop Paths - might need confirmation yet
        os.path.expandvars(
            "%ProgramFiles%\\Supreme Commander - Forged Alliance",
        ),

        # Guessed Steam path
        os.path.expandvars(
            "%ProgramFiles%\\Steam\\steamapps\\common\\"
            "supreme commander forged alliance",
        ),
    ]

    # Registry Steam path
    steam_path = steamPath()
    if steam_path:
        pathlist.append(
            os.path.join(
                steam_path, "SteamApps", "common",
                "Supreme Commander Forged Alliance",
            ),
        )

    return list(filter(validate_game_path, pathlist))


def validate_game_path(path: str) -> bool:
    # We check whether the gamedata/lua.scd file exists.
    # This is a mildly naive check, but should suffice
    if not os.path.isfile(os.path.join(path, r"gamedata", r"lua.scd")):
        return False
    return validate_path(path)


def validate_path(path: str) -> bool:
    try:
        # Supcom only supports Ascii Paths
        try:
            path.encode("ascii")
        except UnicodeEncodeError:
            return False

        if not os.path.isdir(path):
            return False

        # Reject or fix paths that end with a slash.
        # LATER: this can have all sorts of intelligent logic added
        # Suggested: Check if the files are actually the right ones, if not,
        # tell the user what's wrong with them.
        if path.endswith("/"):
            return False
        if path.endswith("\\"):
            return False

        return True
    except Exception:
        _, value, _ = sys.exc_info()
        logger.exception("Path validation failed: %s", value)
        return False
