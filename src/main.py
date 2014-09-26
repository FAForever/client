'''
Created on Dec 1, 2011

@author: thygrrr
'''

# CRUCIAL: This must remain on top.
import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)
sip.setapi('QStringList', 2)
sip.setapi('QList', 2)
sip.setapi('QProcess', 2)

#Set up a robust logging system
import util
util.startLogging()


from PyQt4 import QtGui


import sys
excepthook_original = sys.excepthook
def excepthook(excType, excValue, tracebackobj): 
    '''
    This exception hook will stop the app if an uncaught error occurred, regardless where in the QApplication.
    '''
    logger.error("Uncaught exception", exc_info=(excType, excValue, tracebackobj))
    dialog = util.CrashDialog((excType, excValue, tracebackobj))
    answer = dialog.exec_()
        
    if (answer == QtGui.QDialog.Rejected):
        # Shut it down as nicely as possible.
        sys.excepthook = excepthook_original
        QtGui.QApplication.closeAllWindows()
        util.stopLogging()
        QtGui.QApplication.quit()
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
    import ctypes    
    if getattr(ctypes.windll.shell32, "SetCurrentProcessExplicitAppUserModelID", None) is not None: 
        myappid = 'com.faforever.lobby'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    if len(sys.argv) == 1:
        #Do the magic    
        runFAF()
    else:  
        #Try to interpret the argument as a replay.
        if sys.argv[1].lower().endswith(".fafreplay") or sys.argv[1].lower().endswith(".scfareplay"):
            import fa
            fa.exe.replay(sys.argv[1], True) #Launch as detached process

    #End of show
    app.closeAllWindows()    
    app.quit()
    
    #End the application, perform some housekeeping
    logger.info("<<< --------------------------- Application Shutdown")    
    util.stopLogging()


    
    