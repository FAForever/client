import pytest
import os
import pygit2
from . import Repository

__author__ = 'Thygrrr'

TEST_REPO_URL = "https://github.com/thygrrr/test.git"


def test_creates_empty_repository_on_init(tmpdir):
    repo_dir = str(tmpdir.join("test_repo"))
    repo = Repository(repo_dir, TEST_REPO_URL)
    assert os.path.exists(repo_dir)
    assert repo.repo.is_empty


def test_retrieves_contents_on_checkout(tmpdir):
    repo_dir = str(tmpdir.join("test_repo"))
    repo = Repository(repo_dir, TEST_REPO_URL)
    repo.fetch()
    repo.checkout()
    assert os.path.isdir(os.path.join(repo_dir, ".git"))
    assert os.path.isfile(os.path.join(repo_dir, "LICENSE"))


def test_has_remote_faf_after_clone(tmpdir):
    repo_dir = str(tmpdir.join("test_repo"))
    repo = Repository(repo_dir, TEST_REPO_URL)
    assert TEST_REPO_URL in repo.remote_urls
    assert "faf" in repo.remote_names


def test_adds_remote_faf_after_clone(tmpdir):
    repo_dir = str(tmpdir.join("test_repo"))
    repo = Repository(repo_dir, "http://faforever.com")
    repo.repo.remotes[0].rename("faforever")

    repo = Repository(repo_dir, TEST_REPO_URL)
    assert TEST_REPO_URL in repo.remote_urls
    assert "faf" in repo.remote_names


def test_keeps_pre_existing_remote_faf(tmpdir):
    repo_dir = str(tmpdir.join("test_repo"))
    repo = Repository(repo_dir, "http://faforever.com")

    repo = Repository(repo_dir, TEST_REPO_URL)
    assert TEST_REPO_URL not in repo.remote_urls
    assert "faf" in repo.remote_names
    a, b = repo.remote_urls, repo.remote_names
    assert repo.remote_names.index("faf") == repo.remote_urls.index("http://faforever.com")
