import sys
from cx_Freeze import setup, Executable

import version
git_version = version.get_git_version()
sanitized_version = version.sanitize_version(git_version)
version_file = version.write_release_version(git_version)

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {"include_files": ["res", (version_file.name, "RELEASE-VERSION")], "icon": "res/faf.ico", "include_msvcr": True}

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
if sys.platform == "win32":
    base = "Win32GUI"


setup(
    name="faforever",
    version=sanitized_version,
    description="Forged Alliance Forever!",
    options={"build_exe": build_exe_options},
    executables=[Executable("src/__main__.py", base=base, targetName="FAForever.exe")]
)

# Clean Up Temporary Files
import os
os.remove(version_file.name)