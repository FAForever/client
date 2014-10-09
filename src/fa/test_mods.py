__author__ = 'Thygrrr'

import mods
import os

def test_fix_init_luas_changes_affected_files(tmpdir):
    tmpdir.join("test.lua").write("dofile('init_local.lua')")
    mods.fix_init_luas(str(tmpdir))
    assert tmpdir.join("test.lua").read() == "dofile(InitFileDir .. '\\\\init_local.lua')"


def test_fix_init_luas_ignores_unaffected_files(tmpdir):
    tmpdir.join("test.lua").write("print 'You know nothing!'")
    mods.fix_init_luas(str(tmpdir))
    assert tmpdir.join("test.lua").read() == "print 'You know nothing!'"


def test_init_lua_for_featured_mod_returns_correct_legacy_lua(tmpdir):
    repo_dir = tmpdir.mkdir("repo")
    lua_dir = tmpdir.mkdir("lua")
    legacy_lua = mods.init_lua_for_featured_mod("test", str(repo_dir), str(lua_dir))
    assert legacy_lua == os.path.join(str(lua_dir),"init_test.lua")


def test_init_lua_for_featured_mod_returns_correct_repo_lua(tmpdir):
    repo_dir = tmpdir.mkdir("repo")
    lua_dir = tmpdir.mkdir("lua")
    repo_dir.mkdir("test").ensure("init.lua")
    repo_lua = mods.init_lua_for_featured_mod("test", str(repo_dir), str(lua_dir))
    assert repo_lua == os.path.join(str(repo_dir), "test", "init.lua")
