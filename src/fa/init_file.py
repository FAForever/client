from faf.tools.lua import to_lua


class InitFile(object):
    """
    Represents and emits lua code for configuring FA
    """
    def __init__(self):
        self._init_keys = [
            ('path', {}),
            ('hook', ['/schook']),
            ('protocols', ['http', 'https', 'mailto', 'ventrilo', 'teamspeak', 'daap', 'im'])
        ]

    def to_lua(self):
        lua = []
        for k, v in self._init_keys:
            lua.append(''.join([k, '=', to_lua(v), '\n']))
        return ''.join(lua)

