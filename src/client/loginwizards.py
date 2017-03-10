from PyQt4 import QtCore, QtGui
import util


class gameSettingsWizard(QtGui.QWizard):
    def __init__(self, client, *args, **kwargs):
        QtGui.QWizard.__init__(self, *args, **kwargs)
        
        self.client = client

        self.settings = GameSettings()
        self.settings.gamePortSpin.setValue(self.client.gamePort)
        self.settings.checkUPnP.setChecked(self.client.useUPnP)
        self.addPage(self.settings)

        self.setWizardStyle(1)

        self.setPixmap(QtGui.QWizard.BannerPixmap,
                QtGui.QPixmap('client/banner.png'))
        self.setPixmap(QtGui.QWizard.BackgroundPixmap,
                QtGui.QPixmap('client/background.png'))

        self.setWindowTitle("Set Game Port")

    def accept(self):
        self.client.gamePort = self.settings.gamePortSpin.value()
        self.client.useUPnP = self.settings.checkUPnP.isChecked()
        QtGui.QWizard.accept(self)


class GameSettings(QtGui.QWizardPage):
    def __init__(self, parent=None):
        super(GameSettings, self).__init__(parent)

        self.parent = parent
        self.setTitle("Network Settings")
        self.setPixmap(QtGui.QWizard.WatermarkPixmap, util.pixmap("client/settings_watermark.png"))
        
        self.label = QtGui.QLabel()
        self.label.setText('Forged Alliance needs an open UDP port to play. If you have trouble connecting to other players, try the UPnP option first. If that fails, you should try to open or forward the port on your router and firewall.<br/><br/>Visit the <a href="http://forums.faforever.com/forums/viewforum.php?f=3">Tech Support Forum</a> if you need help.<br/><br/>')
        self.label.setOpenExternalLinks(True)
        self.label.setWordWrap(True)

        self.labelport = QtGui.QLabel()
        self.labelport.setText("<b>UDP Port</b> (default 6112)")
        self.labelport.setWordWrap(True)
        
        self.gamePortSpin = QtGui.QSpinBox() 
        self.gamePortSpin.setMinimum(1024)
        self.gamePortSpin.setMaximum(65535) 
        self.gamePortSpin.setValue(6112)

        self.checkUPnP = QtGui.QCheckBox("use UPnP")
        self.checkUPnP.setToolTip("FAF can try to open and forward your game port automatically using UPnP.<br/><b>Caution: This doesn't work for all connections, but may help with some routers.</b>")

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.labelport)
        layout.addWidget(self.gamePortSpin)
        layout.addWidget(self.checkUPnP)
        self.setLayout(layout)


    def validatePage(self):        
        return 1
