from PyQt4 import QtGui, QtCore
from fa.patchspec import RETAIL, STEAM
from util import BIN_DIR
import os
import bsdiff4
import shutil
import logging
import hashlib

logger = logging.getLogger(__name__)

from util import settings

class Updater(QtCore.QObject):
    progress_reset = QtCore.pyqtSignal()
    progress_value = QtCore.pyqtSignal(int)
    progress_maximum = QtCore.pyqtSignal(int)
    progress_log = QtCore.pyqtSignal(str)
    failed = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        QtCore.QObject.__init__(self, parent)
        self.needed_renames = None
        self.expected_patched_checksums = None

    @staticmethod
    def is_steam_version(game_path):
        """
        Returns true if we believe the installed game is the steam version. False if it's probably
        the retail version.
        """
        return os.path.isfile(os.path.join(game_path, "steam_api.dll"))

    def prepare_progress(self, operation, maximum=0):
        self.progress_log.emit("Game: %s" % operation)
        logger.info(operation)
        self.progress_maximum.emit(maximum)
        self.progress_reset.emit()
        QtGui.QApplication.processEvents()

    def patch_file(self, file_name, checksum):
        """
        Apply the patch identified by the given checksum to the given file in FAF's bin directory.
        The input file's md5sum must be equal to the given checksum for this to end nonterribly.
        """
        with open(os.path.join(BIN_DIR, file_name), "rb+") as source_file:
            file_data = source_file.read()

            # Workaround, 2014-10-02
            # We cannot use file_patch_inplace here because it has a bug
            # See: https://github.com/ilanschnell/bsdiff4/pull/5

            # bsdiff4.file_patch_inplace(file_name, patch_name)

            with open("/res/patches/%s" % checksum, "rb") as patch_file:
                patched_data = bsdiff4.patch(file_data, patch_file.read())
                new_md5 = hashlib.md5(patched_data).hexdigest()

            source_file.seek(0)
            source_file.write(patched_data)

            source_file.truncate()

        return new_md5

    def md5sum(self, file_path):
        with open(file_path, "rb+") as source_file:
            file_data = source_file.read()
            return hashlib.md5(file_data).hexdigest()

    def verify_checksum(self, file_name):
        file_md5 = self.md5sum(os.path.join(BIN_DIR, file_name))
        return file_md5 == self.expected_patched_checksums[file_name]

    def refresh_bin_dir(self, game_path):
        """

        """
        if not os.path.exists(BIN_DIR):
            os.makedirs(BIN_DIR)

        # Files that fail the checksum test, or do not exist, are added here. These are re-copied
        # from the install directory, patched, and the test repeated.
        broken_files = []

        # For each file we care about, check it exists and has the right checksum.
        self.prepare_progress("Validating installation...", len(self.expected_patched_checksums))
        progress_counter = 0
        for file in self.expected_patched_checksums:
            file_path = os.path.join(file, BIN_DIR)
            if not os.path.isfile(file_path) \
                or not self.verify_checksum(file):
                broken_files.append(file)

            # Show a nice progress bar.
            progress_counter += 1
            self.progress_value.emit(progress_counter)
            QtGui.QApplication.processEvents()

        logger.info("Broken files: %s", ", ".join(broken_files))

        for broken in broken_files:
            # Copy the original from the game directory, renaming if configured to do so.
            dest_path = os.path.join(BIN_DIR, self.needed_renames[broken] or broken)
            shutil.copyfile(os.path.join(game_path, broken), dest_path)

            # If the configuration has a patch for this file, apply it.
            checksum = self.md5sum(dest_path)
            if self.expected_patched_checksums[checksum]:
                checksum = self.patch_file(broken, checksum)

            if checksum != self.expected_patched_checksums[broken]:
                # Halt and catch fire.
                self.failed.emit("Patching failed for: %s" % broken)

    @QtCore.pyqtSlot()
    def run(self):
        game_path = os.path.join(str(settings.value("ForgedAlliance/app/path", type=str)), "bin")

        # Determine if we want steam or retail patching and select the right config.
        if self.is_steam_version(game_path):
            required_configuration = STEAM
        else:
            required_configuration = RETAIL

        self.needed_renames = required_configuration["RENAMES"]
        self.expected_patched_checksums = required_configuration["PATCHED_CHECKSUMS"]

        self.refresh_bin_dir(game_path)

        logger.info("Updated bin directory required.")

        self.finished.emit()
