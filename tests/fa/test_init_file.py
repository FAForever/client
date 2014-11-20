__author__ = 'Sheeo'

from fa.init_file import InitFile


def test_default_init_file():
    f = InitFile()
    print f.to_lua()
    assert f.to_lua() == \
"""path={}
hook={"/schook"}
protocols={"http","https","mailto","ventrilo","teamspeak","daap","im"}
"""
