__author__ = 'Sheeo'

from faftools.lua import emit


class InitFile(object):
    """
    Represents and emits lua code for configuring FA
    """
    def __init__(self):
        self._init_keys = [
            ('path', []),
            ('hook', ['/schook']),
            ('protocols', ['http', 'https', 'mailto', 'ventrilo', 'teamspeak', 'daap', 'im'])
        ]

    def mount(self, path, mountpoint):
        self._init_keys[0][1].append({"mountpoint": mountpoint, "dir": path})

    def hook(self, path):
        self._init_keys[1][1].append(path)

    def to_lua(self):
        lua = []
        for k, v in self._init_keys:
            lua.append(''.join([k, '=', emit.to_lua(v), '\n']))
        return ''.join(lua)

