"""
Script to install PyQt or PySide in CI (Travis and AppVeyor).

Adapted from pytest-qt
"""
from __future__ import print_function
import os
import subprocess
import urllib


def fix_registry(python_ver):
    """Update install path on windows registry so PyQt installation installs at the correct
    location.
    python_ver must be "34", "27", etc.
    """
    import _winreg as winreg
    python_dir = r'C:\Python%s' % python_ver
    print("Fixing registry %s..." % python_ver)
    assert os.path.isdir(python_dir)
    registry_key = r'Software\Python\PythonCore\%s.%s' % (python_ver[0], python_ver[1])
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            registry_key, 0,
                            winreg.KEY_WRITE) as key:
            winreg.SetValue(key, 'InstallPath', winreg.REG_SZ, python_dir)
    except:
        pass

base_url = 'http://downloads.sourceforge.net/project/pyqt/'
downloads = {
    'py34-pyqt5': 'PyQt5/PyQt-5.5/PyQt5-5.5-gpl-Py3.4-Qt5.5.0-x32.exe',
    'py34-pyqt4': 'PyQt4/PyQt-4.11.4/PyQt4-4.11.4-gpl-Py3.4-Qt4.8.7-x32.exe',
    'py27-pyqt4': 'PyQt4/PyQt-4.11.4/PyQt4-4.11.4-gpl-Py2.7-Qt4.8.7-x32.exe',
}
if 'INSTALL_QT' in os.environ:
    fix_registry('34')
    fix_registry('27')
    caption = os.environ['INSTALL_QT']
    url = downloads[caption]
    print("Downloading %s..." % caption)
    installer = r'C:\install-%s.exe' % caption
    urllib.urlretrieve(base_url + url, installer)
    print('Installing %s...' % caption)
    subprocess.check_call([installer, '/S'])
    python = caption.split('-')[0]
    assert python[:2] == 'py'
    executable = r'C:\Python%s\python.exe' % python[2:]
    module = url.split('/')[0]
    cmdline = [executable, '-c', 'import %s;print(%s)' % (module, module)]
    print('Checking: %r' % cmdline)
    subprocess.check_call(cmdline)
    print('OK')
else:
    print('Skip install for this build')
