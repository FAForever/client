# -------------------------------------------------------------------------------
# Copyright (c) 2012 Gael Honorez.
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

import os
import sys

import sip

sip.setapi('QString', 2)
sip.setapi('QVariant', 2)
sip.setapi('QStringList', 2)
sip.setapi('QList', 2)
sip.setapi('QProcess', 2)

import PyQt4.uic
from cx_Freeze import setup, Executable

sys.path.insert(0, "src")
sys.path.insert(0, "lib")
sys.path.insert(0, "lib/pygit2")

company_name = 'FAF Community'
product_name = 'Forged Alliance Forever'

import config.version as version
import PyQt4.uic
git_version = version.get_git_version()
msi_version = version.msi_version(git_version)
version_file = version.write_release_version(git_version)

print('Build version:', git_version, 'MSI version:', msi_version)

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {
    'include_files': ['res', 'RELEASE-VERSION', ('lib/uid.dll', 'uid.dll'),
                      ('lib/pygit2/pygit2/decl.h','decl.h')],
    'optimize': 2,
    'icon': 'res/faf.ico',
    'include_msvcr': True,
    'silent': True,
    'packages': ['util', 'sip', 'cffi', 'pycparser', 'PyQt4.uic', 'lupa', 'pygit2', 'pygit2_cffi_18eab927xbf062fb5']
}

shortcut_table = [
    ('DesktopShortcut',           # Shortcut
     'DesktopFolder',             # Directory_
     'FA Forever',                # Name
     'TARGETDIR',                 # Component_
     '[TARGETDIR]FAForever.exe',  # Target
     None,                        # Arguments
     None,                        # Description
     None,                        # Hotkey
     None,                        # Icon
     None,                        # IconIndex
     None,                        # ShowCmd
     'TARGETDIR'                  # WkDir
     )
]

target_dir = '[ProgramFilesFolder][ProductName]'
upgrade_code = '{ADE2A55B-834C-4D8D-A071-7A91A3A266B7}'
if 'pre' in git_version:
    target_dir += "-beta"
    upgrade_code = '{2A336240-1D51-4726-B36f-78B998DD3740}'

bdist_msi_options = {
    'upgrade_code': upgrade_code,
    'initial_target_dir': target_dir,
    'add_to_path': False,
    'data': {'Shortcut': shortcut_table},
}

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
if sys.platform == 'win32':
    base = 'Win32GUI'

exe = Executable(
    'src/__main__.py',
    base=base,
    targetName='FAForever.exe',
    icon='res/faf.ico',
    includes=[os.path.join(os.path.dirname(PyQt4.uic.__file__), "widget-plugins"), "PyQt4.uic.widget-plugins"]
)

setup(
    name=product_name,
    version=msi_version,
    description='Forged Alliance Forever - Lobby Client',
    long_description='FA Forever is a community project that allows you to play \
Supreme Commander and Supreme Commander: Forged Alliance online \
with people across the globe. Provides new game play modes, including cooperative play, \
ranked ladder play, and featured mods.',
    author='FA Forever Community',
    maintainer='Sheeo',
    url='http://www.faforever.com',
    license='GNU General Public License, Version 3',
    options={'build_exe': build_exe_options, 'bdist_msi': bdist_msi_options},
    executables=[exe], requires=['bsdiff4', 'sip', 'pygit2', 'PyQt4', 'cx_Freeze', 'cffi', 'py', 'faftools', 'lupa'],
)
