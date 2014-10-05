from git import Repository
import pytest
import os
__author__ = 'Thygrrr'


def test_creates_directory_on_init(tmpdir):
    origin_dir = tmpdir.join("origin")
    Repository(tmpdir.join("origin").dirname, origin_dir.dirname).init()
    assert origin_dir.exists


def test_creates_directory_on_checkout(tmpdir):
    origin_dir = tmpdir.join("origin")
    Repository(origin_dir.dirname, origin_dir.dirname).init()

    repo_dir = tmpdir.join("repo")
    Repository(repo_dir.dirname, origin_dir.dirname).checkout()
    assert repo_dir.exists


def test_has_remote_after_clone(tmpdir):
    origin_dir = tmpdir.join("origin")
    Repository(origin_dir.dirname).init()

    repo_dir = tmpdir.join("repo")
    repo = Repository(repo_dir.dirname)
    repo.checkout(origin_dir.dirname)
    assert repo.remote


def test_checkout_raises_error_on_bogus_location(tmpdir):
    Repository(tmpdir.dirname, None).checkout()
