from Setting import Setting

enabled = Setting("chat/enabled", bool)
port = Setting("chat/port", int)
host = Setting("chat/host", str)
tls = Setting("chat/tls", bool)

soundeffects = Setting("chat/soundeffects", bool)
livereplays = Setting("chat/livereplays", bool)
opengames = Setting("chat/opengames", bool)
joinsparts = Setting("chat/joinsparts", bool)
coloredNicknames = Setting("chat/coloredNicknames", bool)
friendsontop = Setting("chat/friendsontop", bool)
