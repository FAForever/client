#-------------------------------------------------------------------------------
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


"""
Created on Dec 1, 2011

@author: thygrrr
"""

# CRUCIAL: This must remain on top.
import sip

sip.setapi('QString', 2)
sip.setapi('QVariant', 2)
sip.setapi('QStringList', 2)
sip.setapi('QList', 2)
sip.setapi('QProcess', 2)

import os
import sys
from config.production import ON_WINDOWS

if os.path.isdir("lib"):
    sys.path.insert(0, os.path.abspath("lib"))
elif os.path.isdir("../lib"):
    sys.path.insert(0, os.path.abspath("../lib"))
if os.path.isdir("lib/pygit2"):
    sys.path.insert(0, os.path.abspath("lib/pygit2"))
if os.path.isdir("lib/mumbleconnector"):
    sys.path.insert(0, os.path.abspath("lib/mumbleconnector"))

from PyQt4 import QtGui
import util



# Set up crash reporting
excepthook_original = sys.excepthook


def excepthook(exc_type, exc_value, traceback_object):
    """
    This exception hook will stop the app if an uncaught error occurred, regardless where in the QApplication.
    """
    sys.excepthook = excepthook_original

    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, traceback_object))
    dialog = util.CrashDialog((exc_type, exc_value, traceback_object))
    answer = dialog.exec_()

    if answer == QtGui.QDialog.Rejected:
        QtGui.QApplication.exit(1)


#Override our except hook for better crash reporting for the end user.
if not util.developer():
    sys.excepthook = excepthook


def runFAF():
    #Load theme from settings (one of the first things to be done)
    util.loadTheme()
    
    #create client singleton and connect
    import client
        
    faf_client = client.instance
    faf_client.setup()

    #Connect and login, then load and show the UI if everything worked
    if faf_client.doConnect():
        if faf_client.waitSession() :
            if faf_client.doLogin():    
                #Done setting things up, show the window to the user.
                faf_client.show()                    

                #Main update loop
                QtGui.QApplication.exec_()


#Actual "main" method
if __name__ == '__main__':
    import logging
    logger = logging.getLogger(__name__)

    #init application framework
    logger.info(">>> --------------------------- Application Launch")
    app = QtGui.QApplication(sys.argv)
    app.setWindowIcon(util.icon("window_icon.png", True))
    #Set application icon to nicely stack in the system task bar    
    
    if ON_WINDOWS: #Windows only
        import ctypes
        if getattr(ctypes.windll.shell32, "SetCurrentProcessExplicitAppUserModelID", None) is not None: 
            myappid = 'com.faforever.lobby'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    if len(sys.argv) == 1:
        #Do the magic   
        sys.path += ['.'] 
        runFAF()
    else:  
        # Try to interpret the argument as a replay.
        if sys.argv[1].lower().endswith(".fafreplay") or sys.argv[1].lower().endswith(".scfareplay"):
            import fa
            fa.replay(sys.argv[1], True)  # Launch as detached process

    #End of show
    app.closeAllWindows()    
    app.quit()
    
    #End the application, perform some housekeeping
    logger.info("<<< --------------------------- Application Shutdown")    

