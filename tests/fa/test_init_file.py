__author__ = 'Sheeo'

from fa.init_file import InitFile

"""
These tests suck quite hard, since they
depend on the order that the dict happens to be iterated in.

We should parse the lua back and compare values instead.
"""

def test_default_init_file():
    f = InitFile()
    assert f.to_lua() == \
"""path={}
hook={"/schook"}
protocols={"http","https","mailto","ventrilo","teamspeak","daap","im"}
"""


def test_path_gets_amended():
    f = InitFile()
    f.mount('c:\\some-directory\\', '/')
    assert f.to_lua() == \
"""path={{"mountpoint"="/","dir"="c:\\some-directory\\"}}
hook={"/schook"}
protocols={"http","https","mailto","ventrilo","teamspeak","daap","im"}
"""
