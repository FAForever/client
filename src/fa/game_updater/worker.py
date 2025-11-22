from __future__ import annotations

import logging
import os
import shutil
import stat
from collections.abc import Callable
from functools import wraps
from typing import Concatenate

from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager

from src import util
from src.api.featured_mod_api import FeaturedModApiConnector
from src.api.featured_mod_api import FeaturedModFilesApiConnector
from src.api.models.FeaturedMod import FeaturedMod
from src.api.models.FeaturedModFile import FeaturedModFile
from src.config import Settings
from src.downloadManager import FileDownload
from src.fa.game_updater.misc import ProgressInfo
from src.fa.game_updater.misc import UpdaterCancellation
from src.fa.game_updater.misc import UpdaterFailure
from src.fa.game_updater.misc import UpdaterResult
from src.fa.game_updater.misc import log
from src.fa.game_updater.patcher import FAPatcher
from src.fa.utils import unpack_movies_and_sounds

logger = logging.getLogger(__name__)


def check_interruption[**P, R](
        fn: Callable[Concatenate[UpdaterWorker, P], R],
) -> Callable[Concatenate[UpdaterWorker, P], R]:
    @wraps(fn)
    def inner(self: UpdaterWorker, *args: P.args, **kwargs: P.kwargs) -> R:
        if self.interruption_requested:
            raise UpdaterCancellation("User aborted the update")
        return fn(self, *args, **kwargs)
    return inner


class UpdaterWorker(QObject):
    done = pyqtSignal(UpdaterResult)

    current_mod = pyqtSignal(ProgressInfo)
    hash_progress = pyqtSignal(ProgressInfo)
    extras_progress = pyqtSignal(ProgressInfo)
    game_progress = pyqtSignal(ProgressInfo)
    mod_progress = pyqtSignal(ProgressInfo)

    download_started = pyqtSignal(FileDownload)
    download_progress = pyqtSignal(FileDownload)
    download_finished = pyqtSignal(FileDownload)

    def __init__(
        self,
        target_base_dir: str,
        featured_mod: str,
        version: int | None,
        modversions: dict[str, int] | None,
    ) -> None:
        super().__init__()
        self.featured_mod = featured_mod
        self.version = version
        self.modversions = modversions

        self.nam = QNetworkAccessManager(self)
        self.result = UpdaterResult.NONE

        self.cache_enabled = Settings.get("cache/store_duration", default=30, type=int) > -1

        self.dlers: list[FileDownload] = []
        self.interruption_requested = False
        self.fa_patcher = FAPatcher()

        self.base_dir = target_base_dir
        self.bin_dir = os.path.join(self.base_dir, "bin")
        self.gamedata_dir = os.path.join(self.base_dir, "gamedata")

    def get_files_to_update(self, mod_id: str, version: str) -> list[FeaturedModFile]:
        return FeaturedModFilesApiConnector(mod_id, version).get_files()

    def get_featured_mod_by_name(self, technical_name: str) -> FeaturedMod:
        return FeaturedModApiConnector().request_and_get_fmod_by_name(technical_name)

    @staticmethod
    def _filter_files_to_update(
        files: list[FeaturedModFile],
        precalculated_md5s: dict[str, str],
    ) -> list[FeaturedModFile]:
        return [file for file in files if precalculated_md5s[file.md5] != file.md5]

    @check_interruption
    def _calculate_md5s(self, files: list[FeaturedModFile]) -> dict[str, str]:
        total = len(files)
        result: dict[str, str] = {}
        for index, file in enumerate(files, start=1):
            filepath = os.path.join(self.base_dir, file.group, file.name)
            result[file.md5] = util.md5(filepath)
            self.hash_progress.emit(ProgressInfo(index, total, file.name))
        return result

    def fetch_fmod_file(self, file: FeaturedModFile) -> None:
        target_path = os.path.join(self.base_dir, file.group, file.name)
        url = file.cacheable_url
        self._download(target_path, url, {file.hmac_parameter: file.hmac_token})

    def move_from_cache(self, file: FeaturedModFile) -> None:
        src_dir = os.path.join(self.base_dir, file.group)
        cache_dir = os.path.join(util.GAME_CACHE_DIR, file.group)
        if os.path.exists(os.path.join(cache_dir, file.md5)):
            shutil.move(
                os.path.join(cache_dir, file.md5),
                os.path.join(src_dir, file.name),
            )

    def move_to_cache(
            self,
            file: FeaturedModFile,
            precalculated_md5s: dict[str, str] | None = None,
    ) -> None:
        precalculated_md5s = precalculated_md5s or {}
        src_dir = os.path.join(self.base_dir, file.group)
        cache_dir = os.path.join(util.GAME_CACHE_DIR, file.group)
        if os.path.exists(os.path.join(src_dir, file.name)):
            md5 = precalculated_md5s.get(file.md5, util.md5(os.path.join(src_dir, file.name)))
            shutil.move(
                os.path.join(src_dir, file.name),
                os.path.join(cache_dir, md5),
            )
            util.setAccessTime(os.path.join(cache_dir, md5))

    @staticmethod
    def _is_cached(file: FeaturedModFile) -> bool:
        cached_file = os.path.join(util.GAME_CACHE_DIR, file.group, file.md5)
        return os.path.isfile(cached_file)

    def ensure_subdirs(self, files: list[FeaturedModFile]) -> None:
        for group in {file.group for file in files}:
            cache = os.path.join(util.GAME_CACHE_DIR, group)
            os.makedirs(cache, exist_ok=True)
            os.makedirs(os.path.join(self.base_dir, group), exist_ok=True)

    @check_interruption
    def update_file(
            self,
            file: FeaturedModFile,
            precalculated_md5s: dict[str, str] | None = None,
    ) -> None:
        if self.cache_enabled:
            self.move_to_cache(file, precalculated_md5s)
        if self._is_cached(file):
            self.move_from_cache(file)
        else:
            self.fetch_fmod_file(file)

    @check_interruption
    def update_files(self, files: list[FeaturedModFile]) -> None:
        """
        Updates the files in the destination
        subdirectory of the Forged Alliance path.
        """
        self.ensure_subdirs(files)
        md5s = self._calculate_md5s(files)

        to_update = self._filter_files_to_update(files, md5s)
        total = len(to_update)

        if total == 0:
            self.mod_progress.emit(ProgressInfo(0, 0, ""))

        for index, file in enumerate(to_update, start=1):
            self.update_file(file, md5s)
            self.mod_progress.emit(ProgressInfo(index, total, file.name))

        self.unpack_movies_and_sounds(files)
        self.patch_fa_exe_if_needed(files)

    @check_interruption
    def unpack_movies_and_sounds(self, files: list[FeaturedModFile]) -> None:
        logger.info("Checking files for movies and sounds")

        total = len(files)
        for index, file in enumerate(files, start=1):
            unpack_movies_and_sounds(file)
            self.extras_progress.emit(ProgressInfo(index, total, file.name))

    def prepare_bin_FAF(self) -> None:
        """
        Creates all necessary files in the binFAF folder, which contains
        a modified copy of all that is in the standard bin folder of
        Forged Alliance
        """
        # now we check if we've got a binFAF folder
        faf_path = Settings.get("ForgedAlliance/app/path")
        assert faf_path is not None
        FABindir = os.path.join(faf_path, "bin")
        FAFdir = self.bin_dir

        # Try to copy without overwriting, but fill in any missing files,
        # otherwise it might miss some files to update
        root_src_dir = FABindir
        root_dst_dir = FAFdir

        for src_dir, _, files in os.walk(root_src_dir):
            dst_dir = src_dir.replace(root_src_dir, root_dst_dir)
            os.makedirs(dst_dir, exist_ok=True)
            total_files = len(files)
            for index, file in enumerate(files, start=1):
                src_file = os.path.join(src_dir, file)
                dst_file = os.path.join(dst_dir, file)
                if not os.path.exists(dst_file):
                    shutil.copy(src_file, dst_dir)
                st = os.stat(dst_file)
                # make all files we were considering writable, because we may
                # need to patch them
                os.chmod(dst_file, st.st_mode | stat.S_IWRITE)
                self.game_progress.emit(ProgressInfo(index, total_files, file))

    def _download(self, target_path: str, url: str, params: dict[str, str]) -> None:
        logger.info("Updater: Downloading %s", url)
        dler = FileDownload(target_path, self.nam, url, params)
        dler.blocksize = None
        dler.progress.connect(self.download_progress.emit)
        dler.start.connect(self.download_started.emit)
        dler.finished.connect(self.download_finished.emit)
        self.dlers.append(dler)
        dler.run()
        dler.waitForCompletion()
        if dler.canceled:
            raise UpdaterCancellation(dler.error_string())
        elif dler.failed():
            raise UpdaterFailure(f"Update failed: {dler.error_string()}")

    def patch_fa_executable(self, exe_info: FeaturedModFile) -> None:
        exe_path = os.path.join(self.bin_dir, exe_info.name)
        self.version = int(self._resolve_base_version(exe_info))

        if self.version == self.fa_patcher.read_version(exe_path):
            return

        for attempt in range(10):  # after download antimalware can interfere in our update process
            if self.fa_patcher.patch(exe_path, self.version):
                return
            logger.warning("Could not open fa exe for patching. Attempt #%d", attempt + 1)
            thread = self.thread()
            assert thread is not None
            thread.msleep(500)
        else:
            raise UpdaterFailure(f"Could not update FA exe to version '{self.version}'")

    def patch_fa_exe_if_needed(self, files: list[FeaturedModFile]) -> None:
        for file in files:
            if file.name == Settings.get("game/exe-name"):
                self.patch_fa_executable(file)
                return

    @check_interruption
    def update_featured_mod(self, modname: str, modversion: str) -> list[FeaturedModFile]:
        fmod = self.get_featured_mod_by_name(modname)
        files = self.get_files_to_update(fmod.xd, modversion)
        self.update_files(files)
        return files

    def _resolve_modversion(self) -> str:
        if self.modversions:
            return str(max(self.modversions.values()))
        return "latest"

    def _resolve_base_version(self, exe_info: FeaturedModFile | None = None) -> str:
        if self.version:
            return str(self.version)
        if exe_info:
            return str(exe_info.version)
        return "latest"

    def do_update(self) -> None:
        """ The core function that does most of the actual update work."""
        try:
            # Prepare FAF directory & all necessary files
            self.prepare_bin_FAF()
            # Update the mod if it's requested
            if self.featured_mod in ("faf", "fafbeta", "fafdevelop", "ladder1v1"):
                self.current_mod.emit(ProgressInfo(1, 1, self.featured_mod))
                self.update_featured_mod(self.featured_mod, self._resolve_base_version())
            else:
                # update faf first
                self.current_mod.emit(ProgressInfo(1, 2, "FAF"))
                self.update_featured_mod("faf", self._resolve_base_version())
                # update featured mod then
                self.current_mod.emit(ProgressInfo(2, 2, self.featured_mod))
                self.update_featured_mod(self.featured_mod, self._resolve_modversion())
        except UpdaterCancellation as e:
            log(f"CANCELLED: {e}", logger)
            self.result = UpdaterResult.CANCEL
        except Exception as e:
            log(f"EXCEPTION: {e}", logger)
            logger.exception("EXCEPTION: %s", e)
            self.result = UpdaterResult.FAILURE
        else:
            self.result = UpdaterResult.SUCCESS
        self.done.emit(self.result)

    def abort(self) -> None:
        for dler in self.dlers:
            dler.cancel()
        self.interruption_requested = True
