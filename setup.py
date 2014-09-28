import sys
from cx_Freeze import setup, Executable

company_name = "FAF Community"
product_name = "Forged Alliance Forever"

import version
git_version = version.get_git_version()
msi_version = version.msi_version(git_version)
version_file = version.write_release_version(git_version)

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {
    "include_files": ["res", (version_file.name, "RELEASE-VERSION")],
    "icon": "res/faf.ico",
    "include_msvcr": True
}

bdist_msi_options = {
    'upgrade_code': '{ADE2A55B-834C-4D8D-A071-7A91A3A266B7}',
    'initial_target_dir': r'[ProgramFilesFolder]\%s\%s' % (company_name, product_name),
    'add_to_path': False,
}

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
if sys.platform == "win32":
    base = "Win32GUI"

exe = Executable("src/__main__.py", base=base, targetName="FAForever.exe")

setup(
    name=product_name,
    version=msi_version,
    description="Forged Alliance Forever!",
    options={"build_exe": build_exe_options, 'bdist_msi': bdist_msi_options},
    executables=[exe]
)

# Clean Up Temporary Files
import os
os.remove(version_file.name)