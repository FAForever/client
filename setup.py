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





# A simple setup script to create various executables with 
# different User Access Control flags in the manifest.

# Run the build process by entering 'setup.py py2exe' or
# 'python setup.py py2exe' in a console prompt.
#
# If everything works well, you should find a subdirectory named 'dist'
# containing lots of executables

from distutils.core import setup
import py2exe
import shutil
import os
import matplotlib
import sys


# The targets to build
if os.path.isfile("build.dat"):
    with open("build.dat") as f:
        BUILD = int(f.read()) + 1
else:
    BUILD = 1

print "py2exe version: " + py2exe.__version__
print "BUILD: " + str(BUILD)
# create a target that says nothing about UAC - On Python 2.6+, this
# should be identical to "asInvoker" below.  However, for 2.5 and
# earlier it will force the app into compatibility mode (as no
# manifest will exist at all in the target.)

t1 = {
    "script": "src/__main__.py",
    "dest_base": "FAForever",
    "icon_resources": [(0, "res/faf.ico")]
}

print "BUILD BEGINS."

if (os.path.isdir("dist")):
    shutil.rmtree("dist")

shutil.copytree("lib", "dist")  #Lib directory needs to contain MSVCRT90.dll, plus Qt Image format plugins etc.
shutil.copytree("res", "dist/res")

VERSION_STRING = "0.10." + str(BUILD)

versionfile = open("dist/version", "w")
versionfile.write(VERSION_STRING)
versionfile.flush()
os.fsync(versionfile.fileno())
versionfile.close()

setup(
    windows=[t1],  # targets to build
    version=VERSION_STRING,
    description="Forged Alliance Forever",
    name="Forged Alliance Forever",
    options={
        "py2exe": {
            "includes": ["ctypes.util", "sip", "PyQt4"],
            "dll_excludes": ["MSVCP90.dll", "POWRPROF.dll", "API-MS-Win-Core-LocalRegistry-L1-1-0.dll", "MPR.dll"],
            'excludes': ['_gtkagg', '_tkagg', "OpenGL"],
        }
    },
    data_files=matplotlib.get_py2exe_datafiles(),
    zipfile="FAForever.lib", requires=['sip']
)

open("build.dat", "w").write(str(BUILD))

print "BUILD FINISHED!"
print "Build no. " + str(BUILD)
