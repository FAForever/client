import os
import sys
import site

import sip
from pathlib import Path

sip.setapi('QString', 2)
sip.setapi('QVariant', 2)
sip.setapi('QStringList', 2)
sip.setapi('QList', 2)
sip.setapi('QProcess', 2)

import PyQt5.uic
if sys.platform == 'win32':
    from cx_Freeze import setup, Executable
else:
    from distutils.core import setup

sys.path.insert(0, "src")

company_name = 'FAF Community'
product_name = 'Forged Alliance Forever'

if sys.platform == 'win32':
    import config.version as version

    root_dir = os.path.dirname(os.path.abspath(__file__))
    res_dir = os.path.join(root_dir, "res")
    appveyor_build_version = os.getenv('APPVEYOR_BUILD_VERSION')
    appveyor_build_version = appveyor_build_version.replace(' ','')
    version.write_version_file(appveyor_build_version, res_dir)

    faf_version, git_revision = version.get_git_version()
    msi_version = version.msi_version(faf_version)
    print('Release version:', faf_version,
          'Build version:', appveyor_build_version)
    if git_revision:
        print('Git revision:', git_revision)

# Ugly hack to fix broken PyQt5 (FIXME - necessary?)
for module in ["invoke.py", "load_plugin.py"]:
    try:
        silly_file = Path(PyQt5.__path__[0]) / "uic" / "port_v2" / module
        print("Removing {}".format(silly_file))
        silly_file.unlink()
    except OSError:
        pass

def get_jsonschema_includes():
    schemas = os.path.join(site.getsitepackages()[1], "jsonschema", "schemas")
    onlyfiles = [f for f in os.listdir(schemas) if os.path.isfile(os.path.join(schemas, f))]
    return [(os.path.join(schemas, f), os.path.join("jsonschema", "schemas", f)) for f in onlyfiles]

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

if False:  # Beta build
    product_name += " Beta"
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

if sys.platform == 'win32':
    # Dependencies are automatically detected, but it might need fine tuning.
    build_exe_options = {
        'include_files': ['res',
                          'imageformats',
                          'platforms',
                          'audio',
                          'libeay32.dll',
                          'ssleay32.dll',
                          'libEGL.dll', # For QtWebEngine
                          'libGLESv2.dll', # ditto
                          'icudtl.dat', #ditto
                          'qtwebengine_resources.pak', # ditto
                          'QtWebEngineProcess.exe', # ditto
                          ('lib/faf-uid.exe', 'lib/faf-uid.exe'),
                          ('lib/faf-ice-adapter.exe', 'lib/faf-ice-adapter.exe'),
                          ('lib/qt.conf', 'qt.conf'),
                          ('lib/xdelta3.exe', 'lib/xdelta3.exe')],
        'zip_includes': get_jsonschema_includes(),
        'include_msvcr': True,
        'optimize': 2,
        # cx_freeze >5.0.0 fails to add idna, we'll remove it once they fix it
        # jinja2 dies with 'cannot import compat' without asyncio
        'packages': ['asyncio', 'PyQt5', 'PyQt5.uic', 'idna',
                     'PyQt5.QtWidgets', 'PyQt5.QtNetwork', 'win32com', 'win32com.client'],
        'silent': True,
        'excludes': ['numpy', 'scipy', 'matplotlib', 'tcl', 'tkinter'],

        'zip_include_packages': ["*"],     # Place source files in zip archive, like in cx_freeze 4.3.4
        'zip_exclude_packages': [],
    }

    platform_options = {
        'executables': [Executable(
                          'src/__main__.py',
                          base=base,
                          targetName='FAForever.exe',
                          icon='res/faf.ico'
                      )],
        'requires': ['sip', 'PyQt5', 'cx_Freeze'],
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
    url='http://www.faforever.com',
    license='GNU General Public License, Version 3',
    **platform_options
)
