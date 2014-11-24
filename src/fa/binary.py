# -------------------------------------------------------------------------------
# Copyright (c) 2014 Forged Alliance Forever Community Project.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#-------------------------------------------------------------------------------

from git import Repository

__author__ = 'Thygrrr'


from PyQt4 import QtGui, QtCore
import os
import util
import bsdiff4
import shutil
import sys
import json
import logging
import hashlib

logger = logging.getLogger(__name__)

REPO_NAME = "binary-patch"
REPO_URL = "https://github.com/FAForever/binary-patch.git"

from util import settings

class PatchFailedError(StandardError):
    pass

def make_counter(start=0):
    _closure={"count":start}
    def f(jump=1):
        _closure['count'] += jump
        return _closure['count']
    return f


class Updater(QtCore.QObject):
    progress_reset = QtCore.pyqtSignal()
    progress_value = QtCore.pyqtSignal(int)
    progress_maximum = QtCore.pyqtSignal(int)
    progress_log = QtCore.pyqtSignal(str)
    failed = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, repo, parent=None):
        QtCore.QObject.__init__(self, parent)
        self.repo = repo


    @staticmethod
    def guess_install_type(game_path):
        return 'steam' if os.path.isfile(os.path.join(game_path, "steam_api.dll")) else 'retail'


    def copy_rename(self, copy_rename, source_path, destination_path=util.BIN_DIR):
        count = make_counter()
        self.prepare_progress("Copying Files", len(copy_rename))

        if not os.path.exists(destination_path):
            shutil.mkdirs(destination_path)

        for source_name, destination_name in copy_rename.iteritems():
            logger.info("Copying " + os.path.join(source_path, source_name))
            shutil.copyfile(os.path.join(source_path, source_name), os.path.join(destination_path, destination_name or source_name))
            self.progress_value.emit(count())
            QtGui.QApplication.processEvents()

    def log(self, text):
        self.progress_log.emit("Game: " + text)
        logger.info(text)


    def prepare_progress(self, operation, maximum=0):
        self.log(operation)
        self.progress_maximum.emit(maximum)
        self.progress_reset.emit()
        QtGui.QApplication.processEvents()


    def patch_directory_contents(self, post_patch_verify, patch_data_directory=os.path.join(util.REPO_DIR, REPO_NAME, "bsdiff4"), bin_dir=util.BIN_DIR):
        count = make_counter()
        self.prepare_progress("Patching Install", len(post_patch_verify))

        for file_name, expected_md5 in post_patch_verify.iteritems():
            with open(os.path.join(bin_dir, file_name), "rb+") as source_file:
                file_data = source_file.read()
                file_md5 = hashlib.md5(file_data).hexdigest()

                patch_name = os.path.join(patch_data_directory, file_md5)
                if os.path.isfile(os.path.join(patch_data_directory, file_md5)):
                    logger.info("Patching " + file_name)

                    # Workaround, 2014-10-02
                    # We cannot use file_patch_inplace here because it has a bug
                    # See: https://github.com/ilanschnell/bsdiff4/pull/5

                    # bsdiff4.file_patch_inplace(file_name, patch_name)

                    with open(patch_name, "rb") as patch_file:
                        patched_data = bsdiff4.patch(file_data, patch_file.read())
                        file_md5 = hashlib.md5(patched_data).hexdigest()

                    source_file.seek(0)
                    source_file.write(patched_data)

                    source_file.truncate()

            if file_md5 == expected_md5:
                logger.info("Verified: " + file_name + " OK")
            else:
                logger.error(file_name + " checksum mismatch after patching, " + file_md5 + " != " + expected_md5 + " (expected)")
                raise PatchFailedError("MD5 mismatch for " + file_name)

            self.progress_value.emit(count())
            QtGui.QApplication.processEvents()


    def verify_directory_contents(self, post_patch_verify, bin_dir=util.BIN_DIR):
        count = make_counter()
        self.prepare_progress("Verifying Install", len(post_patch_verify))

        okay = True
        logger.info("Verifying bin directory " + bin_dir)
        try:
            for file_name, expected_md5 in post_patch_verify.iteritems():
                with open(os.path.join(bin_dir, file_name), "rb+") as source_file:
                    file_data = source_file.read()
                    file_md5 = hashlib.md5(file_data).hexdigest()

                if file_md5 == expected_md5:
                    logger.debug(file_name + " OK")
                else:
                    logger.warn(file_name + " checksum mismatch, " + file_md5 + " != " + expected_md5 + " (expected)")
                    okay  = False

                self.progress_value.emit(count())
                QtGui.QApplication.processEvents()

            for existing_file in os.listdir(bin_dir):
                if not existing_file in post_patch_verify:
                    logger.warn(existing_file + " is not in verify list.")

        except StandardError, err:
            logger.error("Error verifying files: " + str(err))
            okay = False

        return okay


    def patch_forged_alliance(self, game_path):
        with open(os.path.join(util.REPO_DIR, "binary-patch", Updater.guess_install_type(game_path) + ".json")) as json_file:
            migration_data = json.loads(json_file.read())

        self.copy_rename(migration_data['pre_patch_copy_rename'], game_path)
        self.patch_directory_contents(migration_data['post_patch_verify'])


    def check_up_to_date(self, game_path, bin_dir=util.BIN_DIR):
        if not os.path.exists(bin_dir):
            return False

        with open(os.path.join(util.REPO_DIR, "binary-patch", Updater.guess_install_type(game_path) + ".json")) as json_file:
            migration_data = json.loads(json_file.read())

        return self.verify_directory_contents(migration_data['post_patch_verify'])


    @QtCore.pyqtSlot()
    def run(self):
        self.prepare_progress("Checking out Git Repository")

        self.repo.fetch()
        self.repo.checkout()

        gamepath = os.path.join(str(settings.value("ForgedAlliance/app/path", type=str)), "bin")

        if not self.check_up_to_date(gamepath):
            logger.info("Updated bin directory required.")
            self.prepare_progress("Creating fresh install.")
            try:
                self.patch_forged_alliance(gamepath)
            except PatchFailedError, pfe:
                self.failed.emit(str(pfe))

        self.finished.emit()
