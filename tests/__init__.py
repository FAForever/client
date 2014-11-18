__author__ = 'Sheeo'

import sys
import os

# Allows you to run tests from either tests or root directory
if os.path.isdir("src"):
    sys.path.insert(0, os.path.abspath("src"))
elif os.path.isdir("../src"):
    sys.path.insert(0, os.path.abspath("../src"))

if os.path.isdir("lib"):
    sys.path.insert(0, os.path.abspath("lib"))
elif os.path.isdir("../lib"):
    sys.path.insert(0, os.path.abspath("../lib"))
