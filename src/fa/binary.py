from git import Repository

__author__ = 'Thygrrr'

from PyQt4 import QtGui, QtCore
import os
import util
import bsdiff4

import logging
logger = logging.getLogger(__name__)

REPO_NAME = "binary-patch"
REPO_URL = "https://github.com/FAForever/binary-patch.git"


class Updater(QtCore.QObject):
    def __init__(self, parent=None):
        QtCore.QObject.__init__(self, parent)
        self.repo = Repository(self)
        self.progress = QtGui.QProgressDialog("Checking out " + REPO_NAME, "Cancel", 0, 0)
        self.progress.setWindowTitle("Updater")
        self.progress.show()
        self.repo.operation_complete.connect(self.progress.hide)
        self.repo.checkout(REPO_URL, os.path.join(util.REPO_DIR, REPO_NAME))


    def update_fa(self):
        for patch_entry in os.listdir(self.repo.path):
            if patch_entry.startswith("."):
                continue

            patch_path = os.path.join(self.repo.path, patch_entry)

            # The binary-patch repo has a collection of patches for the given file in BIN_DIR
            if os.path.isdir(patch_path):
                fa_filename = os.path.join(util.BIN_DIR, patch_entry)
                fa_md5 = util.md5(fa_filename)
                logger.info("Examining " + fa_filename + ", checksum " + fa_md5)

                patch_filename = os.path.join(patch_path, fa_md5+".bsdiff4")
                if os.path.isfile(patch_filename):
                    logger.info("Applying patch " + patch_filename)

                    # Workaround, 2014-10-02
                    # We cannot use file_patch_inplace here because it has a bug
                    # See: https://github.com/ilanschnell/bsdiff4/pull/5

                    # bsdiff4.file_patch_inplace(fa_filename, patch_filename)

                    with open(fa_filename, "rb") as fa_file:
                        fa_data = fa_file.read()

                    with open(patch_filename, "rb") as patch_file:
                        patch_data = patch_file.read()

                    fa_data = bsdiff4.patch(fa_data, patch_data)
                    with open(fa_filename, "wb+") as fa_file:
                        fa_file.write(fa_data)

                    fa_md5 = util.md5(fa_filename)
                    logger.info("Patched " + fa_filename + ", checksum " + fa_md5)


                goal_filename = os.path.join(patch_path, "goal.md5")
                if os.path.isfile(goal_filename):
                    with open(goal_filename, "r") as goal_file:
                        goal_md5 = goal_file.read()
                        if goal_md5 == fa_md5:
                            logger.info(patch_entry + " is OK")
                        else:
                            logger.error(patch_entry + " checksum mismatch, " + goal_md5 + " != " + fa_md5 )





FA_STEAM_FILES = [
   "BsSndRpt.exe",
   "BugSplat.dll",
   "BugSplatRc.dll",
   "DbgHelp.dll",
   "GDFBinary.dll",
   "LuaPlus_1081.dll",
   "MohoEngine.dll",
   "SHSMP.DLL",
   "SHW32d.DLL",
   "SupremeCommander.exe",
   "d3dx9_31.dll",
   "game.dat",
   "gpgcore.dll",
   "gpggal.dll",
   "msvcm80.dll",
   "msvcp80.dll",
   "msvcr80.dll",
   "splash.png",
   "sx32w.dll",
   "wxmsw24u-vs80.dll",
   "zlibwapi.dll",
   "steam_api.dll",
   "steam_appid.txt",
]

FA_RETAIL_FILES = [
    "BsSndRpt.exe",
    "BugSplat.dll",
    "BugSplatRc.dll",
    "DbgHelp.dll",
    "ForgedAlliance.exe",
    "GDFBinary.dll",
    "Microsoft.VC80.CRT.manifest",
    "SHSMP.DLL",
    "msvcm80.dll",
    "msvcp80.dll",
    "msvcr80.dll",
    "splash.png",
    "sx32w.dll",
    "wxmsw24u-vs80.dll",
    "zlibwapi.dll",
]

FA_RENAMES = {
   "SupremeCommander.exe": "ForgedAllianceForever.exe",
   "ForgedAlliance.exe": "ForgedAllianceForever.exe"
}

