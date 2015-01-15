__author__ = 'Sheeo'

from fa.lua import InitFile
from lupa import LuaRuntime

lua = LuaRuntime(unpack_returned_tuples=True)


def test_default_init_values():
    f = InitFile()
    print f.to_lua()
    lua.execute(f.to_lua())
    path = list(lua.eval('path').items())
    assert path == f.path
    hook = list(lua.eval('hook').values())
    assert hook == f.hook
    protocols = list(lua.eval('protocols').values())
    assert protocols == f.protocols


def test_path_gets_amended():
    f = InitFile()
    f.mount('c:\\some-directory\\', '/')
    print f.to_lua()
    lua.execute(f.to_lua())
    path = []
    for k in list(lua.eval('path').values()):
        path.append(dict(k))
    assert path == [{u'mountpoint': u'/', u'dir': u'c:\\some-directory\\'}]


def test_mount_order_matters():
    f = InitFile()
    f.mount('first-dir', '/')
    f.mount('second-dir', '/')
    lua.execute(f.to_lua())
    path = []
    for k in list(lua.eval('path').values()):
        path.append(dict(k))
    assert path == [{'mountpoint': '/', 'dir': "first-dir"},
                    {'mountpoint': '/', 'dir': "second-dir"}]


def test_can_add_hook_directoies():
    f = InitFile()
    f.add_hook('/nomads')
    lua.execute(f.to_lua())
    hook = list(lua.eval('hook').values())
    assert hook == ['/schook', '/nomads']

