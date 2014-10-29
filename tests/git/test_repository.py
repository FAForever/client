import pytest
import py
import os
import pygit2
from git import Repository, Version

__author__ = 'Thygrrr'

TEST_REPO_URL = "https://github.com/thygrrr/test.git"
TEST_REPO_BRANCHES = ["faf/master", "faf/test"]
TEST_REPO_TAGS = ["v0.0.1", "v0.0.2"]

TEST_ARBITRARY_COMMIT = "34856db7a9effddbfcfb56a25d6ef17ef7d51290"

TEST_TAG = "v0.0.2"
TEST_TAG_COMMIT = "af24b324862df335c2664d2d68dca2a4e4011043"

TEST_MASTER = "faf/master"
TEST_BRANCH = "faf/test"
TEST_BRANCH_COMMIT = "b20f559f4e1857ea78783a84ffec4ddfaa60f557"

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


def test_emits_transfer_signals_on_fetch(tmpdir, signal_receiver):
    repo_dir = str(tmpdir.join("test_repo"))
    test_repo = Repository(repo_dir, TEST_REPO_URL)
    test_repo.transfer_complete.connect(signal_receiver.generic_slot)
    test_repo.transfer_progress_value.connect(signal_receiver.int_slot)
    test_repo.transfer_progress_maximum.connect(signal_receiver.int_slot)
    test_repo.fetch()

    assert signal_receiver.generic_values
    assert signal_receiver.int_values
    assert signal_receiver.int_values[-2:][0] == signal_receiver.int_values[-2:][1]


def test_retrieves_contents_on_checkout(prefetched_repo):
    repo_dir = prefetched_repo.path
    prefetched_repo.checkout()
    assert os.path.isdir(os.path.join(repo_dir, ".git"))
    assert os.path.isfile(os.path.join(repo_dir, "LICENSE"))


def test_retrieves_alternate_branch_on_checkout(prefetched_repo):
    repo_dir = prefetched_repo.path
    prefetched_repo.checkout(TEST_BRANCH)
    assert os.path.isfile(os.path.join(repo_dir, "test"))


def test_wipes_working_directory_on_branch_switch(prefetched_repo):
    repo_dir = prefetched_repo.path

    prefetched_repo.checkout(TEST_BRANCH)
    assert os.path.isfile(os.path.join(repo_dir, "test"))
    prefetched_repo.checkout(TEST_MASTER)
    assert not os.path.isfile(os.path.join(repo_dir, "test"))


def test_has_all_remote_branches_after_fetch(prefetched_repo):
    for branch in TEST_REPO_BRANCHES:
        assert branch in prefetched_repo.remote_branches


def test_has_no_local_branches_after_fetch(prefetched_repo):
    assert not prefetched_repo.local_branches


def test_has_all_tags_after_fetch(prefetched_repo):
    for branch in TEST_REPO_TAGS:
        assert branch in prefetched_repo.tags


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


def test_retrieves_arbitrary_commit_on_checkout(prefetched_repo):
    repo_dir = prefetched_repo.path
    assert prefetched_repo.has_hex(TEST_ARBITRARY_COMMIT)
    prefetched_repo.checkout(TEST_ARBITRARY_COMMIT)
    assert os.path.isfile(os.path.join(repo_dir, "arbitrary"))


def test_retrieves_correct_tag_on_checkout(prefetched_repo):
    repo_dir = prefetched_repo.path
    prefetched_repo.checkout(TEST_TAG)
    assert os.path.isfile(os.path.join(repo_dir, "tagged"))


def test_returns_correct_commit_hex_after_checkout(prefetched_repo):
    prefetched_repo.checkout(TEST_ARBITRARY_COMMIT)
    assert prefetched_repo.current_head.hex == TEST_ARBITRARY_COMMIT


def test_retrieves_correct_hex_on_tag_checkout(prefetched_repo):
    prefetched_repo.checkout(TEST_TAG)
    assert prefetched_repo.current_head.hex == TEST_TAG_COMMIT


def test_retrieves_correct_hex_on_branch_checkout(prefetched_repo):
    prefetched_repo.checkout(TEST_BRANCH)
    assert prefetched_repo.current_head.hex == TEST_BRANCH_COMMIT


def test_repo_has_version(prefetched_repo):
    prefetched_repo.checkout(TEST_TAG)
    assert prefetched_repo.has_version(Version("thygrrr/test", TEST_TAG, None, TEST_TAG_COMMIT))
