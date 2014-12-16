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

import sys
from PyQt4 import QtGui

# Set up a robust logging system
import util
#util.startLogging()

# Set up crash reporting
excepthook_original = sys.excepthook


def excepthook(exc_type, exc_value, traceback_object):
    """
    This exception hook will stop the app if an uncaught error occurred, regardless where in the QApplication.
    """
    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, traceback_object))
    dialog = util.CrashDialog((exc_type, exc_value, traceback_object))
    answer = dialog.exec_()

    if answer == QtGui.QDialog.Rejected:
        sys.exit(1)


#Override our except hook.
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
    #Set up logging framework
    import logging
    logger = logging.getLogger("faf.main")
    logger.propagate = True

    #init application framework    
    logger.info(">>> --------------------------- Application Launch")    
    app = QtGui.QApplication(sys.argv)
    app.setWindowIcon(util.icon("window_icon.png", True))
    #Set application icon to nicely stack in the system task bar    

    if util.isWindows(): #Windows only
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
            fa.exe.replay(sys.argv[1], True)  # Launch as detached process

    #End of show
    app.closeAllWindows()    
    app.quit()
    
    #End the application, perform some housekeeping
    logger.info("<<< --------------------------- Application Shutdown")    
#   util.stopLogging()

