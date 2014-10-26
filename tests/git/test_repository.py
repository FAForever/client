import pytest
import py
import os
import pygit2
from git import Repository

__author__ = 'Thygrrr'

TEST_REPO_URL = "https://github.com/thygrrr/test.git"
TEST_REPO_BRANCHES = ["faf/master", "faf/test"]

@pytest.fixture(scope="module")
def prefetched_repo(request):
    tmpdir = py.test.ensuretemp(__name__ + ".prefetched_repo")
    repo_dir = os.path.join(str(tmpdir), "test_repo_fixture")
    repo = Repository(repo_dir, TEST_REPO_URL)
    repo.fetch()
    return repo


def test_creates_empty_repository_on_init(tmpdir):
    repo_dir = str(tmpdir.join("test_repo"))
    test_repo = Repository(repo_dir, TEST_REPO_URL)
    assert os.path.exists(repo_dir)
    assert test_repo.repo.is_empty


def test_raises_git_error_on_init_if_not_a_git_path(tmpdir):
    with pytest.raises(pygit2.GitError):
        repo_dir = str(tmpdir.mkdir("test_repo"))
        test_repo = Repository(repo_dir, TEST_REPO_URL)
        assert os.path.exists(repo_dir)
        assert test_repo.repo.is_empty


def test_has_remote_faf_after_init(tmpdir):
    repo_dir = str(tmpdir.join("test_repo"))
    test_repo = Repository(repo_dir, TEST_REPO_URL)
    assert TEST_REPO_URL in test_repo.remote_urls
    assert "faf" in test_repo.remote_names


def test_retrieves_contents_on_checkout(prefetched_repo):
    repo_dir = prefetched_repo.path
    prefetched_repo.checkout()
    assert os.path.isdir(os.path.join(repo_dir, ".git"))
    assert os.path.isfile(os.path.join(repo_dir, "LICENSE"))


def test_retrieves_alternate_branch_on_checkout(prefetched_repo):
    repo_dir = prefetched_repo.path
    prefetched_repo.checkout("faf/test")
    assert os.path.isfile(os.path.join(repo_dir, "test"))


def test_wipes_working_directory_on_branch_switch(prefetched_repo):
    repo_dir = prefetched_repo.path

    prefetched_repo.checkout("faf/test")
    assert os.path.isfile(os.path.join(repo_dir, "test"))
    prefetched_repo.checkout("faf/master")
    assert not os.path.isfile(os.path.join(repo_dir, "test"))


def test_has_all_branches_after_fetch(prefetched_repo):
    for branch in TEST_REPO_BRANCHES:
        assert branch in prefetched_repo.remote_branches


def test_adds_remote_faf_after_clone(tmpdir):
    repo_dir = str(tmpdir.join("test_repo"))
    test_repo = Repository(repo_dir, "http://faforever.com")
    test_repo.repo.remotes[0].rename("faforever")

    test_repo = Repository(repo_dir, TEST_REPO_URL)
    assert TEST_REPO_URL in test_repo.remote_urls
    assert "faf" in test_repo.remote_names


def test_adds_faf_even_if_same_remote_url_exists_for_other_remote(tmpdir):
    repo_dir = str(tmpdir.join("test_repo"))
    test_repo = Repository(repo_dir, TEST_REPO_URL)
    test_repo.repo.remotes[0].rename("faforever")

    test_repo = Repository(repo_dir, TEST_REPO_URL)
    assert 2 == len([remote.url for remote in test_repo.repo.remotes if remote.url == TEST_REPO_URL])
    assert "faf" in test_repo.remote_names


def test_keeps_pre_existing_remote_faf(tmpdir):
    repo_dir = str(tmpdir.join("test_repo"))
    _ = Repository(repo_dir, "http://faforever.com")
    repo = Repository(repo_dir, TEST_REPO_URL)
    assert TEST_REPO_URL not in repo.remote_urls
    assert "faf" in repo.remote_names
    assert repo.remote_names.index("faf") == repo.remote_urls.index("http://faforever.com")
