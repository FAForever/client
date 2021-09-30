import json
from enum import Enum

from PyQt5.QtCore import QObject, QUrl, pyqtSignal
from PyQt5.QtNetwork import QNetworkReply, QNetworkRequest
from semantic_version import Version

from config import Settings
from decorators import with_logger


class UpdateChannel(Enum):
    Stable = 0
    Prerelease = 1
    Unstable = 2

    def to_reltype(self):
        d = {
            UpdateChannel.Stable: ReleaseType.STABLE,
            UpdateChannel.Prerelease: ReleaseType.PRERELEASE,
            UpdateChannel.Unstable: ReleaseType.UNSTABLE,
        }
        return d[self]


class ReleaseType(Enum):
    STABLE = "stable"
    PRERELEASE = "pre"
    UNSTABLE = "beta"
    MINIMUM = "server"

    @classmethod
    def get(cls, version):
        if version < Version("0.18.0"):
            return cls.legacy_versioning(version)
        else:
            return cls.new_versioning(version)

    @classmethod
    def legacy_versioning(cls, version):
        if version.minor % 2 == 1:
            return cls.UNSTABLE
        else:
            if version.prerelease == ():
                return cls.STABLE
            else:
                return cls.PRERELEASE

    @classmethod
    def new_versioning(cls, version):
        for tuple_value in version.prerelease:
            if any(p in tuple_value for p in ['alpha', 'beta']):
                return cls.UNSTABLE
            if any(p in tuple_value for p in ['pre', 'rc']):
                return cls.PRERELEASE
        return cls.STABLE

    def included_channels(self):
        order = [
            ReleaseType.MINIMUM,
            ReleaseType.STABLE,
            ReleaseType.PRERELEASE,
            ReleaseType.UNSTABLE,
        ]
        for item in order:
            yield item
            if item == self:
                break


class Release:
    def __init__(self, version, installer, branch=None):
        self.version = version
        self.installer = installer
        self._branch = branch

    @property
    def branch(self):
        if self._branch is not None:
            return self._branch
        return ReleaseType.get(self.version)

    def __lt__(self, other):
        return self.version < other.version


class Releases:
    def __init__(self, release_list, current_version):
        self._current_version = current_version
        self.branches = {}
        for branch in ReleaseType:
            b_releases = [r for r in release_list if r.branch == branch]
            b_releases.sort(reverse=True)
            self.branches[branch] = b_releases

    def newest(self, channel):
        try:
            return max(self.versions(channel))
        except ValueError:
            return None

    def versions(self, channel, show_older=False):
        current = self._current_version
        eligible_channels = channel.included_channels()
        versions = [v for c in eligible_channels for v in self.branches[c]]
        if not show_older:
            versions = filter(lambda r: r.version > current, versions)
        else:
            versions = filter(
                lambda r: r.version > current or r.version < current,
                versions,
            )
        versions = list(versions)
        versions.sort(reverse=True)
        return versions

    def mandatory_update(self):
        return self.optional_update(ReleaseType.MINIMUM)

    def optional_update(self, channel):
        newest = self.newest(channel)
        return newest is not None and newest.version > self._current_version


class UpdateSettings:
    _updater_branch = Settings.persisted_property(
        'updater/branch',
        type=str,
        default_value=UpdateChannel.Prerelease.name,
    )
    updater_downgrade = Settings.persisted_property(
        'updater/downgrade', type=bool, default_value=False,
    )
    gh_releases_url = Settings.persisted_property(
        'updater/gh_release_url',
        type=str,
        default_value=(
            'https://api.github.com/repos/FAForever/'
            'client/releases?per_page=20'
        ),
    )
    changelog_url = Settings.persisted_property(
        'updater/changelog_url',
        type=str,
        default_value='https://github.com/FAForever/client/releases/tag',
    )

    def __init__(self):
        pass

    @property
    def updater_branch(self):
        try:
            return UpdateChannel[self._updater_branch]
        except ValueError:
            return UpdateChannel.Prerelease

    @updater_branch.setter
    def updater_branch(self, value):
        self._updater_branch = value.name


class GithubUpdateChecker(QObject):
    finished = pyqtSignal()

    def __init__(self, settings, network_manager):
        QObject.__init__(self)
        self._settings = settings
        self._network_manager = network_manager
        self._rep = None
        self.releases = None
        self.done = False

    @classmethod
    def builder(cls, settings, network_manager, **kwargs):
        def build():
            return cls(settings, network_manager)
        return build

    def start(self):
        gh_url = QUrl(self._settings.gh_releases_url)
        self._rep = self._network_manager.get(QNetworkRequest(gh_url))
        self._rep.finished.connect(self._req_done)

    def _req_done(self):
        self.done = True
        self.releases = self._process_response(self._rep)
        self.finished.emit()

    def _process_response(self, rep):
        if rep.error() != QNetworkReply.NoError:
            return None
        release_data = bytes(self._rep.readAll())
        try:
            releases = json.loads(release_data.decode('utf-8'))
        except (UnicodeError, json.JSONDecodeError):
            self._logger.exception(
                "Error parsing network reply: {}".format(repr(release_data)),
            )
            return None
        return list(self._parse_releases(releases))

    def _parse_releases(self, releases):
        if not isinstance(releases, list):
            releases = [releases]
        for release_dict in releases:
            for asset in release_dict['assets']:
                if '.msi' in asset['browser_download_url']:
                    download_url = asset['browser_download_url']
                    version = Version(release_dict['tag_name'])
                    yield Release(version, download_url)


@with_logger
class UpdateChecker(QObject):
    finished = pyqtSignal(object, bool)

    def __init__(self, current_version, github_check_builder):
        QObject.__init__(self)
        self._current_version = current_version
        self._github_check_builder = github_check_builder
        self._github_checker = None
        self.releases = None
        self._always_notify = False

    @classmethod
    def build(cls, current_version, **kwargs):
        github_check_builder = GithubUpdateChecker.builder(**kwargs)
        return cls(current_version, github_check_builder)

    def check(self, always_notify=False):
        self._always_notify = always_notify
        self._start_github_check()

    def _start_github_check(self):
        self._github_checker = self._github_check_builder()
        self._github_checker.finished.connect(self._check_all_checks_finished)
        self._github_checker.start()

    def _check_all_checks_finished(self):
        if self._github_checker is None:
            return
        if not self._github_checker.done:
            return
        self._set_releases()
        self.finished.emit(self.releases, self._always_notify)

    def _set_releases(self):
        releases = []
        if self._github_checker.releases is not None:
            releases.extend(self._github_checker.releases)
        self.releases = Releases(releases, self._current_version)


class UpdateNotifier(QObject):
    update = pyqtSignal(object, bool)

    def __init__(self, settings, update_checker):
        QObject.__init__(self)
        self._settings = settings
        self._update_checker = update_checker
        self._update_checker.finished.connect(self._notify_if_needed)

    def _notify_if_needed(self, releases, force=False):
        if force:
            self.update.emit(releases, False)
        elif releases.mandatory_update():
            self.update.emit(releases, True)
        elif releases.optional_update(
                self._settings.updater_branch.to_reltype(),
        ):
            self.update.emit(releases, False)
