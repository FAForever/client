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

# The targets to build
BUILD = int(open("build.dat").read())+1
open("build.dat", "w").write(str(BUILD))

print "py2exe version: " + py2exe.__version__
print "BUILD: " + str(BUILD)
# create a target that says nothing about UAC - On Python 2.6+, this
# should be identical to "asInvoker" below.  However, for 2.5 and
# earlier it will force the app into compatibility mode (as no
# manifest will exist at all in the target.)

t1 = {
      "script":"__main__.py",
      "dest_base":"FAForever",
      "icon_resources" : [(0, "_lib/faf.ico")]
      }



print "BUILD BEGINS."

if (os.path.isdir("\\\\LIBERATOR\\faf\\current-build")):
    shutil.rmtree("\\\\LIBERATOR\\faf\\current-build")
    
if (os.path.isdir("dist")):
    shutil.rmtree("dist")

shutil.copytree("lib", "dist")             #Lib directory needs to contain MSVCRT90.dll and FreeImage.dll, plus Qt Image format plugins etc.
shutil.copytree("res", "dist/res")

VERSION_STRING = "0.7." + str(BUILD)

versionfile = open("dist/version", "w")
versionfile.write(VERSION_STRING)
versionfile.flush()
os.fsync(versionfile.fileno())
versionfile.close()

setup(      
      windows = [t1], # targets to build
      version = VERSION_STRING,
      description = "Forged Alliance Forever",
      name = "Forged Alliance Forever",
      options = {
                 "py2exe": {
                            "includes":["sip"], "dll_excludes": ["MSVCP90.dll", "POWRPROF.dll", "API-MS-Win-Core-LocalRegistry-L1-1-0.dll", "MPR.dll"],
			    'excludes': ['_gtkagg', '_tkagg'],                          
                           }
                }, 
      data_files=matplotlib.get_py2exe_datafiles(),
      zipfile = "FAForever.lib"
    )

print "Clearing and copying..."
if (os.path.isdir("build")):
    shutil.rmtree("build")


print "BUILD FINISHED!"
print "Build no. " + str(BUILD)
