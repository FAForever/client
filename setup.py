import os
import sys

from cx_Freeze import Executable
from cx_Freeze import setup

from src.config import version

company_name = "FAF Community"
product_name = "Forged Alliance Forever"

root_dir = os.path.dirname(os.path.abspath(__file__))
res_dir = os.path.join(root_dir, "res")
build_version = os.getenv("BUILD_VERSION").replace(" ", "")
version.write_version_file(build_version, res_dir)
msi_version = version.msi_version(build_version)


shortcut_table = [
    (
        "DesktopShortcut",           # Shortcut
        "DesktopFolder",             # Directory_
        "FA Forever",                # Name
        "TARGETDIR",                 # Component_
        "[TARGETDIR]FAForever.exe",  # Target
        None,                        # Arguments
        None,                        # Description
        None,                        # Hotkey
        None,                        # Icon
        None,                        # IconIndex
        None,                        # ShowCmd
        "TARGETDIR",                  # WkDir
    ),
]

target_dir = "[ProgramFilesFolder][ProductName]"
upgrade_code = "{ADE2A55B-834C-4D8D-A071-7A91A3A266B7}"

if os.getenv("BETA"):  # Beta build
    product_name += " Beta"
    upgrade_code = "{2A336240-1D51-4726-B36f-78B998DD3740}"

bdist_msi_options = {
    "upgrade_code": upgrade_code,
    "initial_target_dir": target_dir,
    "add_to_path": False,
    "data": {"Shortcut": shortcut_table},
    "all_users": True,
}


if sys.platform == "win32":
    include_mvcr = True
    exe_base = "Win32Gui"
    exe_name = "FAForever.exe"
else:
    include_mvcr = False
    exe_base = None
    exe_name = "FAForever"


# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {
    "include_files": [
        "res",
        ("build_setup", "natives"),
    ],
    "include_msvcr": include_mvcr,
    "optimize": 2,
    "silent": True,

    # copied from https://github.com/marcelotduarte/cx_Freeze/blob/5e42a97d2da321eae270cdcc65cdc777eb8e8fc4/samples/pyqt6-simplebrowser/setup.py  # noqa: E501
    # and unexcluded overexcluded
    "excludes": ["tkinter", "unittest", "tcl", "scipy"],

    "zip_include_packages": ["*"],
    "zip_exclude_packages": ["pyqtgraph"],

    "build_exe": "build/faf_python_client",
}

platform_options = {
    "executables": [
        Executable(
            "src/__main__.py",
            base=exe_base,
            target_name=exe_name,
            icon="res/faf.ico",
        ),
    ],
    "options": {
        "build_exe": build_exe_options,
        "bdist_msi": bdist_msi_options,
    },
    "version": msi_version,
}

setup(
    name=product_name,
    description="Forged Alliance Forever - Lobby Client",
    long_description=(
        "FA Forever is a community project that allows you to "
        "play Supreme Commander and Supreme Commander: Forged "
        "Alliance online with people across the globe. "
        "Provides new game play modes, including cooperative "
        "play, ranked ladder play, and featured mods."
    ),
    author="FA Forever Community",
    maintainer="Sheeo",
    url="http://www.faforever.com",
    license="GNU General Public License, Version 3",
    **platform_options,
)
