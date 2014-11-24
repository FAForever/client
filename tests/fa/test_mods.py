__author__ = 'Thygrrr'

from fa import mods
import os


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

