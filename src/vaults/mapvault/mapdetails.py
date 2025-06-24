import os
import shutil

from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QWidget

from src import util
from src.api.ApiAccessors import DataApiAccessor
from src.api.ApiBase import ApiResponse
from src.api.models.Map import Map
from src.fa import maps
from src.fa.maps_.preview import create_largest_preview
from src.fa.maps_.previewdialog import MapPreviewDialog
from src.model.player import Player
from src.vaults.detailswidget import DetailsWidget

STYLESHEET = util.THEME.readstylesheet("client/client.css")


class MapDetailsWidget(DetailsWidget):
    def __init__(
            self,
            item_data: Map,
            player: Player,
            parent: QWidget | None = None,
    ) -> None:
        DetailsWidget.__init__(self, item_data, util.MAP_PREVIEW_LARGE_DIR, player, parent)
        self.item_data = item_data
        assert item_data.version is not None
        self.item_version = item_data.version
        self.ui.thumbnailLabel.clicked.connect(self.preview_map_large)

        self.games_api = DataApiAccessor("/data/game")
        self.games_api.data_ready.connect(self.allow_review)

    def _ask_if_played_map(self) -> None:
        self.games_api.requestData({
            "include": "playerStats",
            "filter": (
                f"playerStats.player.id=={self.player.id};"
                f"mapVersion.id=={self.item_version.xd}"
            ),
            "page[size]": 1,
        })

    def ask_review(self) -> None:
        self._ask_if_played_map()

    def allow_review(self, response: ApiResponse) -> None:
        map_played = len(response["data"]) > 0
        self.ui.addReviewButton.setEnabled(map_played)
        self.ui.detailedReviews.addCommentButton.setEnabled(map_played)

    def preview_map_large(self) -> None:
        if not self.is_installed():
            return
        folder = maps.folderForMap(self.item_version.folder_name)
        assert folder is not None
        pixmap = create_largest_preview(self.screen(), folder)
        dialog = MapPreviewDialog(pixmap, self)
        dialog.exec()

    def is_installed(self) -> bool:
        return maps.isMapAvailable(self.item_version.folder_name)

    def set_author(self) -> None:
        if self.item_data.author:
            author_label = QLabel(f"{self.item_data.author.login}")
            self.ui.authorLayout.addRow(QLabel("Author:"), author_label)
        else:
            self.ui.authorLayout.addWidget(QLabel("Unknown Author"))

    def set_type(self) -> None:
        self.ui.typeLabel.setText(f"Type: {self.item_data.map_type}")

    def set_additional_info(self) -> None:
        self.ui.additionalInfoLabel.setText(f"🎮 {self.item_data.games_played} games played")

    def version_info(self) -> list[tuple[str, str]]:
        height = self.item_version.size.height_km
        width = self.item_version.size.width_km
        return [
            ("Version:", str(self.item_version.version)),
            ("Dimensions (km):", f"{width:g} x {height:g}"),
            ("Max Players:", str(self.item_version.max_players)),
            ("Games Played:", str(self.item_version.games_played)),
            ("Ranked:", "Yes" if self.item_version.ranked else "No"),
            ("Hidden:", "Yes" if self.item_version.hidden else "No"),
        ]

    def technical_info(self) -> list[tuple[str, str]]:
        return [
            *super().technical_info(),
            ("Folder Name", self.item_version.folder_name),
            ("Width", str(self.item_version.size.width_km)),
            ("Height", str(self.item_version.size.height_km)),
            ("Max Players", str(self.item_version.max_players)),
            ("Version", str(self.item_version.version)),
            ("Version Games Played", str(self.item_version.games_played)),
            ("Map Games Played", str(self.item_data.games_played)),
            ("Ranked", "Yes" if self.item_version.ranked else "No"),
            ("Hidden", "Yes" if self.item_version.hidden else "No"),
            ("Download URL", self.item_version.download_url),
            ("Small Thumbnail", self.item_version.thumbnail_url_small),
            ("Large Thumbnail", self.item_version.thumbnail_url_large),
        ]

    def download_item(self) -> None:
        ret, msg = maps._doDownloadMap(
            self.item_version.folder_name,
            self.item_version.download_url,
            silent=False,
        )
        if not ret and msg is not None:
            msg()

    def remove_item(self) -> None:
        full_path = os.path.join(maps.getUserMapsFolder(), self.item_version.folder_name)
        shutil.rmtree(full_path)

    def view_folder(self) -> None:
        util.showDirInFileBrowser(maps.folderForMap(self.item_version.folder_name))
