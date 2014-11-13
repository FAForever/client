__author__ = 'Sheeo'

import sys
import os
import sip

sip.setapi('QString', 2)
sip.setapi('QVariant', 2)
sip.setapi('QStringList', 2)
sip.setapi('QList', 2)
sip.setapi('QProcess', 2)

# Allows you to run tests from either tests or root directory
if os.path.isdir("src"):
    sys.path.insert(0, os.path.abspath("src"))
elif os.path.isdir("../src"):
    sys.path.insert(0, os.path.abspath("../src"))
