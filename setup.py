import os
import sys

import sip
from pathlib import Path

sip.setapi('QString', 2)
sip.setapi('QVariant', 2)
sip.setapi('QStringList', 2)
sip.setapi('QList', 2)
sip.setapi('QProcess', 2)

import PyQt4.uic
if sys.platform == 'win32':
    from cx_Freeze import setup, Executable
else:
    from distutils.core import setup

sys.path.insert(0, "src")
sys.path.insert(0, "lib")

company_name = 'FAF Community'
product_name = 'Forged Alliance Forever'
product_name_short = 'FA Forever'

if sys.platform == 'win32':
    import config.version as version
    import PyQt4.uic

    root_dir = os.path.dirname(os.path.abspath(__file__))
    res_dir = os.path.join(root_dir, "res")
    git_version = version.get_git_version()
    msi_version = version.msi_version(git_version)
    appveyor_build_version = os.getenv('APPVEYOR_BUILD_VERSION')
    appveyor_build_version = appveyor_build_version.replace(' ','')
    version.write_version_file(appveyor_build_version, res_dir)

    print('Git version:', git_version,
          'Release version:', appveyor_build_version,
          'Build version:', msi_version)

# Ugly hack to fix broken PyQt4
try:
    silly_file = Path(PyQt4.__path__[0]) / "uic" / "port_v3" / "proxy_base.py"
    print("Removing {}".format(silly_file))
    silly_file.unlink()
except OSError:
    pass


# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {
    'include_files': ['res',
                      'faf-ice-adapter',
                      'imageformats',
                      'libeay32.dll',
                      'ssleay32.dll',
                      ('lib/faf-uid.exe', 'faf-uid.exe'),
                      ('lib/qt.conf', 'qt.conf'),
                      ('lib/xdelta3.exe', 'xdelta3.exe')],
    'icon': 'res/faf.ico',
    'include_msvcr': True,
    'optimize': 2,
    'packages': ['cffi', 'pycparser', 'PyQt4', 'PyQt4.uic',
                 'PyQt4.QtGui', 'PyQt4.QtNetwork', 'win32com', 'win32com.client'],
    'silent': True,
    'excludes': ['numpy', 'scipy', 'matplotlib', 'tcl', 'Tkinter']
}

target_dir = '[ProgramFilesFolder][ProductName]'
upgrade_code = '{ADE2A55B-834C-4D8D-A071-7A91A3A266B7}'

if True:  # Beta build
    product_name += " Beta"
    product_name_short += " Beta"
    upgrade_code = '{2A336240-1D51-4726-B36f-78B998DD3740}'

shortcut_table = [
    ('DesktopShortcut',           # Shortcut
     'DesktopFolder',             # Directory_
     product_name_short,          # Name
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

if sys.platform == 'win32':
    platform_options = {
        'executables': [Executable(
                          'src/__main__.py',
                          base=base,
                          targetName='FAForever.exe',
                          icon='res/faf.ico',
                          includes=[os.path.join(os.path.dirname(PyQt4.uic.__file__), "widget-plugins"),
                                  "PyQt4.uic.widget-plugins"]
                      )],
        'requires': ['bsdiff4', 'sip', 'PyQt4', 'cx_Freeze', 'cffi', 'py', 'faftools'],
        'options': {'build_exe': build_exe_options,
                 'bdist_msi': bdist_msi_options},
        'version': msi_version,
                 }
        
else:
    from setuptools import find_packages
    platform_options = {
        'packages': find_packages(),
        'version': os.getenv('FAFCLIENT_VERSION'),
        }

setup(
    name=product_name,
    description='Forged Alliance Forever - Lobby Client',
    long_description='FA Forever is a community project that allows you to play \
Supreme Commander and Supreme Commander: Forged Alliance online \
with people across the globe. Provides new game play modes, including cooperative play, \
ranked ladder play, and featured mods.',
    author='FA Forever Community',
    maintainer='Sheeo',
    url='https://www.faforever.com',
    license='GNU General Public License, Version 3',
    **platform_options
)
