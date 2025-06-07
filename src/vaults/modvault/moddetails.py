import os

from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QWidget

from src import util
from src.api.models.Mod import Mod
from src.model.player import Player
from src.vaults.detailswidget import DetailsWidget
from src.vaults.modvault import utils


class ModDetailsWidget(DetailsWidget):
    def __init__(
            self,
            item_data: Mod,
            player: Player,
            parent: QWidget | None = None,
    ) -> None:
        DetailsWidget.__init__(self, item_data, util.MOD_PREVIEW_DIR, player, parent)
        self.item_data = item_data
        assert item_data.version is not None
        self.item_version = item_data.version

    def can_review(self) -> bool:
        return (
            self.is_installed()
            and self.item_data.author != self.player.login
            and (
                self.item_data.uploader is None
                or self.item_data.uploader.login != self.player.login
            )
        )

    def is_installed(self) -> bool:
        return self.item_version.uid in [mod.uid for mod in utils.installedMods]

    def set_author(self) -> None:
        if self.item_data.author:
            author_label = QLabel(f"{self.item_data.author}")
            self.ui.authorLayout.addRow(QLabel("Author:"), author_label)
        else:
            self.ui.authorLayout.addWidget(QLabel("Unknown Author"))
        if self.item_data.uploader:
            uploader_label = QLabel(f"{self.item_data.uploader.login}")
            self.ui.authorLayout.addRow(QLabel("Uploader:"), uploader_label)

    def set_type(self) -> None:
        self.ui.typeLabel.setText(f"Type: {self.item_version.typ}")

    def set_additional_info(self) -> None:
        self.ui.additionalInfoLabel.setText(f"UID: {self.item_version.uid}")

    def version_info(self) -> list[tuple[str, str]]:
        return [
            ("Version:", str(self.item_version.version)),
            ("Filename:", self.item_version.filename),
            ("Type:", self.item_version.typ),
            ("Ranked:", "Yes" if self.item_version.ranked else "No"),
            ("Hidden:", "Yes" if self.item_version.hidden else "No"),
        ]

    def technical_info(self) -> list[tuple[str, str]]:
        return [
            *super().technical_info(),
            ("UID", self.item_version.uid),
            ("Filename", self.item_version.filename),
            ("Version", str(self.item_version.version)),
            ("Type", self.item_version.typ),
            ("Ranked", "Yes" if self.item_version.ranked else "No"),
            ("Hidden", "Yes" if self.item_version.hidden else "No"),
            ("Download URL", self.item_version.download_url),
            ("Thumbnail URL", self.item_version.thumbnail_url),
        ]

    def download_item(self) -> None:
        utils.downloadMod(self.item_version.download_url, self.item_data.display_name)

    def remove_item(self) -> None:
        mod = utils.getModInfoFromFolder(self.item_data.display_name)
        utils.removeMod(mod)

    def view_folder(self) -> None:
        full_path = os.path.join(utils.MODFOLDER, self.item_data.display_name)
        util.showDirInFileBrowser(full_path)
