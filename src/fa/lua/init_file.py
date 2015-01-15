__author__ = 'Sheeo'

from faftools.lua import emit


class InitFile(object):
    """
    Represents and emits lua code for configuring FA
    """
    def __init__(self):
        self._init_keys = {
            'path': [],
            'hook': ['/schook'],
            'protocols': ['http', 'https', 'mailto', 'ventrilo', 'teamspeak', 'daap', 'im']
        }

    def mount(self, path, mountpoint):
        self.path.append({"mountpoint": mountpoint, "dir": path.replace('\\', '\\\\')})

    def add_hook(self, path):
        self.hook.append(path)

    @property
    def path(self):
        return self._init_keys['path']

    @property
    def hook(self):
        return self._init_keys['hook']

    @property
    def protocols(self):
        return self._init_keys['protocols']

    def to_lua(self):
        lua = []
        for k, v in self._init_keys.items():
            lua.append(''.join([k, '=', emit.to_lua(v), '\n']))
        return ''.join(lua)

