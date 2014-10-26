__author__ = 'Sheeo'

import sys,os

# Allows you to run tests from either tests or root directory
if os.path.isdir("src"):
    sys.path.insert(0, os.path.abspath("src"))
elif os.path.isdir("../src"):
    sys.path.insert(0, os.path.abspath("../src"))
