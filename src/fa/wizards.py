from __future__ import annotations

import os
from typing import TYPE_CHECKING

from PyQt6 import QtCore
from PyQt6 import QtWidgets

from src import util
from src.fa.path import typicalForgedAlliancePaths
from src.fa.path import validate_game_path

if TYPE_CHECKING:
    from src.client._clientwindow import ClientWindow


__author__ = 'Thygrrr'


class UpgradePage(QtWidgets.QWizardPage):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle("Specify Forged Alliance folder")
        self.setPixmap(
            QtWidgets.QWizard.WizardPixmap.WatermarkPixmap,
            util.THEME.pixmap("fa/updater/forged_alliance_watermark.png"),
        )

        layout = QtWidgets.QVBoxLayout()

        self.label = QtWidgets.QLabel(
            "FAF needs a version of Supreme Commander: Forged Alliance to "
            "launch games and replays. <br/><br/><b>Please choose the "
            "installation you wish to use.</b><br/><br/>The following versions"
            " are <u>equally</u> supported:<ul><li>3596(Retail version)</li>"
            "<li>3599 (Retail patch)</li><li>3603beta (GPGnet beta patch)</li>"
            "<li>1.6.6 (Steam Version)</li></ul>FAF doesn't modify your "
            "existing files.<br/><br/>Select folder:",
        )
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

    def comboChanged(self):
        tgt_dir = self.comboBox.currentText()
        if not validate_game_path(tgt_dir):
            # User picked some subdirectory (most likely bin)
            parent = os.path.dirname(tgt_dir)
            if validate_game_path(parent):
                self.comboBox.setCurrentText(parent)
        self.completeChanged.emit()

    @QtCore.pyqtSlot()
    def showChooser(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Forged Alliance folder",
            self.comboBox.currentText(),
            (
                QtWidgets.QFileDialog.Option.DontResolveSymlinks
                | QtWidgets.QFileDialog.Option.ShowDirsOnly
            ),
        )
        if path:
            self.comboBox.insertItem(0, path)
            self.comboBox.setCurrentIndex(0)
            self.completeChanged.emit()

    def isComplete(self, *args, **kwargs):
        return validate_game_path(self.comboBox.currentText())

    def validatePage(self, *args, **kwargs):
        return validate_game_path(self.comboBox.currentText())


class Wizard(QtWidgets.QWizard):
    """
    The actual Wizard which walks the user through the install.
    """

    def __init__(self, client: ClientWindow) -> None:
        super().__init__(client)
        self.upgrade = UpgradePage()
        self.addPage(self.upgrade)

        self.setWizardStyle(QtWidgets.QWizard.WizardStyle.ModernStyle)
        self.setWindowTitle("Forged Alliance Game Path")
        self.setPixmap(
            QtWidgets.QWizard.WizardPixmap.WatermarkPixmap,
            util.THEME.pixmap("fa/updater/forged_alliance_watermark.png"),
        )

        self.setOption(QtWidgets.QWizard.WizardOption.NoBackButtonOnStartPage, True)

    def accept(self):
        util.settings.setValue(
            "ForgedAlliance/app/path", self.upgrade.comboBox.currentText(),
        )
        QtWidgets.QWizard.accept(self)


def constructPathChoices(combobox: QtWidgets.QComboBox, validated_choices: list[str]) -> None:
    """
    Creates a combobox with all potentially valid paths for FA on this system
    """
    combobox.clear()
    for path in validated_choices:
        if combobox.findText(path, QtCore.Qt.MatchFlag.MatchFixedString) == -1:
            combobox.addItem(path)
