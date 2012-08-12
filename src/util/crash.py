# Bug Reporting
import fa

CRASHREPORT_USER = "pre-login"

from util import APPDATA_DIR, PERSONAL_DIR, VERSION_STRING, LOG_FILE_FAF,\
    readlines
from PyQt4 import QtGui, QtCore
import traceback
import hashlib



HELP_URL = "http://www.faforever.com/forums/viewforum.php?f=3"
TICKET_URL = "http://bitbucket.org/thepilot/falobby/issues"

class CrashDialog(QtGui.QDialog):
    def __init__(self, exc_info, *args, **kwargs):
        QtGui.QDialog.__init__(self, *args, **kwargs)
        
        excType, excValue, tracebackobj = exc_info
        
        dialog = self
        
        
        dialog.setLayout(QtGui.QVBoxLayout())
        label = QtGui.QLabel()
        label.setText("An Error has occurred in FAF.<br><br>You can report it by clicking the ticket button. <b>Please check if that error is new first !</b>")
        label.setWordWrap(True)
        dialog.layout().addWidget(label)

        label = QtGui.QLabel()
        label.setText("<b>This is what happened (but please add your own explanation !)</b>")
        label.setWordWrap(False)
        dialog.layout().addWidget(label)

        self.trace = u"".join(traceback.format_exception(excType, excValue, tracebackobj, 10))
        self.hash = hashlib.md5(self.trace).hexdigest()

        self.title = u"[auto] Crash from " + CRASHREPORT_USER + u": " + str(excValue)
        
        dialog.setWindowTitle(self.title)
        
        self.box = QtGui.QTextEdit()
        box = self.box
        try:
            box.setFont(QtGui.QFont("Lucida Console", 8))
            box.append(u"\n**FAF Username:** " + CRASHREPORT_USER)
            box.append(u"\n**FAF Version:** " + VERSION_STRING)
            box.append(u"\n**FAF Directory:** " + APPDATA_DIR)
            box.append(u"\n**FA Path:** " + str(fa.gamepath))
            box.append(u"\n**Home Directory:** " + PERSONAL_DIR)            
        except:
            box.append(u"\n**(Exception raised while writing debug vars)**")
            pass
        
            box.append(u"")
            box.append(u"\n**FA Forever Log (last 128 lines):**")
            box.append(u"{{{")
            try:
                box.append("\n".join(readlines(LOG_FILE_FAF, False)[-128:]))
            except:
                box.append(unicode(LOG_FILE_FAF))
                box.append(u"empty or not readable")
        
        box.append(u"\n**Stacktrace:**")
        box.append(u"{{{")
        box.append(self.trace)
        box.append(u"}}}")
        box.append(u"")

        dialog.layout().addWidget(box)
        self.sendButton = QtGui.QPushButton("\nOpen ticket system.\n")
        self.sendButton.pressed.connect(self.postReport) 
        dialog.layout().addWidget(self.sendButton)
        
        label = QtGui.QLabel()
        label.setText("<b></b><br/><i>(please note that the error may be fatal and continue won't work in that case)</i>")
        label.setWordWrap(False)
        dialog.layout().addWidget(label)
        
        self.buttons = QtGui.QDialogButtonBox()
        buttons = self.buttons        
        buttons.addButton("Continue", QtGui.QDialogButtonBox.AcceptRole)
        buttons.addButton("Close FAF", QtGui.QDialogButtonBox.RejectRole)
        buttons.addButton("Help", QtGui.QDialogButtonBox.HelpRole)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        buttons.helpRequested.connect(dialog.techSupport)
        dialog.layout().addWidget(buttons)        
    
    
    @QtCore.pyqtSlot()
    def techSupport(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(HELP_URL))


    @QtCore.pyqtSlot()
    def postReport(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(TICKET_URL))
        
#        try:
#            self.sendButton.setEnabled(False)
#            self.sendButton.setText("\nSending...\n")
#            QtGui.QApplication.processEvents()
#            
#            import urllib
#            import urllib2
#
#            #A simple POST forwarder sends these to the REST Api of Bitbucket
#            url = CRASHREPORT_URL
#            data = urllib.urlencode({
#                                        'title': self.title,
#                                        'content': self.box.toPlainText().encode("utf-8"),
#                                        'hash' : self.hash
#                                     })
#            request = urllib2.Request(url=url, data=data)
#            urllib2.urlopen(request)
#            self.sendButton.setText("\nThanks!\n")
#        except:
#            self.sendButton.setText("\nFailed. :( Click Help and tell us about it!\n")
#            pass

        
    