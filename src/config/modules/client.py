from Setting import Setting, PrefixedPathSetting
import fafpath

_userdir = fafpath.get_userdir()

ignore_admin = Setting("client/ignore_admin", bool)
auto_bugreport = Setting("client/auto_bugreport", bool)

data_path = PrefixedPathSetting("client/data_path", _userdir)

logs_path = PrefixedPathSetting('client/logs/path', _userdir)
logs_level = Setting("client/logs/level", int)
logs_max_size = Setting("client/logs/max_size", int)
logs_buffer_size = Setting("client/logs/buffer_size", int)

host = Setting("host")
