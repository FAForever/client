__author__ = 'Thygrrr'

import mods


def test_fix_init_luas_changes_affected_files(tmpdir):
    tmpdir.join("test.lua").write("dofile('init_local.lua')")
    mods.fix_init_luas(str(tmpdir))
    assert tmpdir.join("test.lua").read() == "dofile(InitFileDir .. '\\\\init_local.lua')"


def test_fix_init_luas_ignores_unaffected_files(tmpdir):
    tmpdir.join("test.lua").write("print 'You know nothing!'")
    mods.fix_init_luas(str(tmpdir))
    assert tmpdir.join("test.lua").read() == "print 'You know nothing!'"

