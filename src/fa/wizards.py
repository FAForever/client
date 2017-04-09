from PyQt5 import QtWidgets, QtCore
from fa.path import validatePath, typicalSupComPaths, typicalForgedAlliancePaths

import util

__author__ = 'Thygrrr'


class UpgradePage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super(UpgradePage, self).__init__(parent)

        self.setTitle("Specify Forged Alliance folder")
        self.setPixmap(QtWidgets.QWizard.WatermarkPixmap, util.pixmap("fa/updater/forged_alliance_watermark.png"))

        layout = QtWidgets.QVBoxLayout()

        self.label = QtWidgets.QLabel(
            "FAF needs a version of Supreme Commander: Forged Alliance to launch games and replays. <br/><br/><b>Please choose the installation you wish to use.</b><br/><br/>The following versions are <u>equally</u> supported:<ul><li>3596(Retail version)</li><li>3599 (Retail patch)</li><li>3603beta (GPGnet beta patch)</li><li>1.6.6 (Steam Version)</li></ul>FAF doesn't modify your existing files.<br/><br/>Select folder:")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        self.comboBox = QtWidgets.QComboBox()
        self.comboBox.setEditable(True)
        constructPathChoices(self.comboBox, typicalForgedAlliancePaths())
        self.comboBox.currentIndexChanged.connect(self.comboChanged)
        self.comboBox.editTextChanged.connect(self.comboChanged)
        layout.addWidget(self.comboBox)
        self.setLayout(layout)

        self.browseButton = QtWidgets.QPushButton()
        self.browseButton.setText("Browse")
        self.browseButton.clicked.connect(self.showChooser)
        layout.addWidget(self.browseButton)

        self.setLayout(layout)

        self.setCommitPage(True)

    @QtCore.pyqtSlot()
    def comboChanged(self):
        self.completeChanged.emit()

    @QtCore.pyqtSlot()
    def showChooser(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Forged Alliance folder",
                                                      self.comboBox.currentText(),
                                                      QtWidgets.QFileDialog.DontResolveSymlinks | QtWidgets.QFileDialog.ShowDirsOnly)
        if (path):
            self.comboBox.insertItem(0, path)
            self.comboBox.setCurrentIndex(0)
            self.completeChanged.emit()

    def isComplete(self, *args, **kwargs):
        if validatePath(self.comboBox.currentText()):
            return True
        else:
            return False

    def validatePage(self, *args, **kwargs):
        if validatePath(self.comboBox.currentText()):
            return True
        else:
            return False


class UpgradePageSC(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super(UpgradePageSC, self).__init__(parent)

        self.setTitle("Specify Supreme Commander folder")
        self.setPixmap(QtWidgets.QWizard.WatermarkPixmap, util.pixmap("fa/updater/supreme_commander_watermark.png"))

        layout = QtWidgets.QVBoxLayout()

        self.label = QtWidgets.QLabel(
            "You can use any version of Supreme Commander.<br/><br/>FAF won't modify your existing files.<br/><br/>Select folder:")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        self.comboBox = QtWidgets.QComboBox()
        self.comboBox.setEditable(True)
        constructPathChoices(self.comboBox, typicalSupComPaths())
        self.comboBox.currentIndexChanged.connect(self.comboChanged)
        self.comboBox.editTextChanged.connect(self.comboChanged)
        layout.addWidget(self.comboBox)
        self.setLayout(layout)

        self.browseButton = QtWidgets.QPushButton()
        self.browseButton.setText("Browse")
        self.browseButton.clicked.connect(self.showChooser)
        layout.addWidget(self.browseButton)

        self.setLayout(layout)

        self.setCommitPage(True)

    @QtCore.pyqtSlot(int)
    def comboChanged(self, index):
        self.completeChanged.emit()

    @QtCore.pyqtSlot()
    def showChooser(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Supreme Commander folder",
                                                      self.comboBox.currentText(),
                                                      QtWidgets.QFileDialog.DontResolveSymlinks | QtWidgets.QFileDialog.ShowDirsOnly)
        if (path):
            self.comboBox.insertItem(0, path)
            self.comboBox.setCurrentIndex(0)
            self.completeChanged.emit()

    def isComplete(self, *args, **kwargs):
        if validatePath(self.comboBox.currentText()):
            return True
        else:
            return False

    def validatePage(self, *args, **kwargs):
        if validatePath(self.comboBox.currentText()):
            return True
        else:
            return False


class WizardSC(QtWidgets.QWizard):
    """
    The actual Wizard which walks the user through the install.
    """

    def __init__(self, client, *args, **kwargs):
        QtWidgets.QWizard.__init__(self, *args, **kwargs)
        self.client = client
        self.upgrade = UpgradePageSC()
        self.addPage(self.upgrade)

        self.setWizardStyle(QtWidgets.QWizard.ModernStyle)
        self.setWindowTitle("Supreme Commander Game Path")
        self.setPixmap(QtWidgets.QWizard.WatermarkPixmap, util.pixmap("fa/updater/forged_alliance_watermark.png"))

        self.setOption(QtWidgets.QWizard.NoBackButtonOnStartPage, True)


    def accept(self):
        util.settings.setValue("SupremeCommander/app/path", self.upgrade.comboBox.currentText())
        QtWidgets.QWizard.accept(self)


class Wizard(QtWidgets.QWizard):
    """
    The actual Wizard which walks the user through the install.
    """

    def __init__(self, client, *args, **kwargs):
        QtWidgets.QWizard.__init__(self, client, *args, **kwargs)
        self.client = client
        self.upgrade = UpgradePage()
        self.addPage(self.upgrade)

        self.setWizardStyle(QtWidgets.QWizard.ModernStyle)
        self.setWindowTitle("Forged Alliance Game Path")
        self.setPixmap(QtWidgets.QWizard.WatermarkPixmap, util.pixmap("fa/updater/forged_alliance_watermark.png"))

        self.setOption(QtWidgets.QWizard.NoBackButtonOnStartPage, True)


    def accept(self):
        util.settings.setValue("ForgedAlliance/app/path", self.upgrade.comboBox.currentText())
        QtWidgets.QWizard.accept(self)


def constructPathChoices(combobox, validated_choices):
    """
    Creates a combobox with all potentially valid paths for FA on this system
    """
    combobox.clear()
    for path in validated_choices:
            if combobox.findText(path, QtCore.Qt.MatchFixedString) == -1:
                combobox.addItem(path)

