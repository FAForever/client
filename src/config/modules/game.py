from Setting import Setting, PrefixedPathSetting
import fafpath

_userdir = fafpath.get_userdir()

logs = Setting("game/logs", bool)
upnp = Setting('game/upnp', bool)
port = Setting('game/port', int)
bin_path = PrefixedPathSetting('game/bin/path', _userdir)
engine_path = PrefixedPathSetting('game/engine/path', _userdir)
logs_path = PrefixedPathSetting('game/logs/path', _userdir)
mods_path = PrefixedPathSetting('game/mods/path', _userdir)
maps_path = PrefixedPathSetting('game/maps/path', _userdir)
