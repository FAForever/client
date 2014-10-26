__author__ = 'Thygrrr'

from fa import mods
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


def test_filter_mod_versions_returns_tuple_of_dicts():
    legacy, repo = mods.filter_mod_versions({}, {})
    assert isinstance(legacy, dict)
    assert isinstance(repo, dict)


def test_filter_mod_removes_found_mods_from_legacy():
    legacy, _ = mods.filter_mod_versions({1: 2}, {1: "test"})
    assert not legacy


def test_filter_mod_strips_unwanted_mods_entirely():
    legacy, repo = mods.filter_mod_versions({2: 3}, {2: None})
    assert 2 not in legacy
    assert 2 not in repo


def test_filter_mod_places_found_mods_with_new_key_in_repo():
    _, repo = mods.filter_mod_versions({1: 2},  {1: "test"})
    assert repo["test"] == 2


def test_filter_mod_versions_passes_through_on_empty_filter_table():
    legacy, repo = mods.filter_mod_versions({1: 2}, {})
    assert legacy[1] == 2
    assert not repo


def test_filter_featured_mods_passesthrough_on_empty_filter_table():
    legacy, repo = mods.filter_featured_mods("unfiltered", {})
    assert legacy == "unfiltered"


def test_filter_featured_mods_no_repo_on_empty_filter_table():
    legacy, repo = mods.filter_featured_mods("unfiltered", {})
    assert repo is None


def test_filter_featured_mods_returns_found_mod_as_repo():
    legacy, repo = mods.filter_featured_mods("filtered", {"filtered":"fi.git"})
    assert repo["filtered"] == "fi.git"


def test_filter_featured_mods_no_legacy_on_found_mod():
    legacy, repo = mods.filter_featured_mods("filtered", {"filtered":"fi.git"})
    assert legacy is None

