__author__ = 'Sheeo'

from git.fetcher import Fetcher
from git.repository import Repository
from git.version import Version
from flexmock import flexmock

import pygit2


def test_fetches_given_repo_versions(qtbot):
    version_1 = Version("FAForever/test", "master", "http://example.com")
    version_2 = Version("FAForever/test", "test", "http://example.com")

    test_repo = flexmock(path='', progress=flexmock(connect=flexmock()))
    flexmock(Repository).new_instances(test_repo)
    test_repo.should_receive('fetch_version').with_args(version_1).once()
    test_repo.should_receive('fetch_version').with_args(version_2).once()

    fetcher = Fetcher([(test_repo, version_1),
                       (test_repo, version_2)])
    fetcher.run()

    qtbot.waitSignal(fetcher.done)


def test_fetcher_emits_done_signal(qtbot):
    version = Version("FAForever/test", "master", "http://example.com")
    test_repo = flexmock(path='',
                         fetch_version=lambda v: True,
                         progress=flexmock(connect=flexmock()))
    fetcher = Fetcher([(test_repo, version)])
    with qtbot.waitSignal(fetcher.done, 200) as blocker:
        fetcher.start()

    assert blocker.signal_triggered


def test_fetcher_emits_error_on_error(qtbot):
    version = Version("FAForever/test", "master", "http://example.com")

    def raise_pygit(v):
        raise pygit2.GitError("Test")
    test_repo = flexmock(path='',
                         fetch_version=raise_pygit,
                         progress=flexmock(connect=flexmock()))

    fetcher = Fetcher([(test_repo, version)])
    with qtbot.waitSignal(fetcher.error, 200) as blocker:
        blocker.connect(fetcher.error)
        fetcher.start()

    assert blocker.signal_triggered
