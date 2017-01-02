import os
import logging
import fafpath

from production import defaults as production_defaults

# These directories are in Appdata (e.g. C:\ProgramData on some Win7 versions)

APPDATA_DIR = fafpath.get_userdir()

defaults = production_defaults.copy()
defaults['host'] = 'test.faforever.com'

# FIXME: Temporary fix for broken https config on test server
# Turns off certificate verification entirely
import ssl
ssl._https_verify_certificates(False)
