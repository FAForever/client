from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field

from src.api.models.AbstractEntity import AbstractEntity


@dataclass
class MapSize:
    height_px: int
    width_px: int

    @property
    def width_km(self) -> float:
        return self.width_px / 51.2

    @property
    def height_km(self) -> float:
        return self.height_px / 51.2

    def __lt__(self, other: MapSize) -> bool:
        return self.height_px * self.width_px < other.height_px * other.width_px

    def __ge__(self, other: MapSize) -> bool:
        return not self.__lt__(other)

    def __str__(self) -> str:
        return f"{self.width_km} x {self.height_km} km"


class MapVersion(AbstractEntity):
    folder_name:         str       = Field(alias="folderName")
    games_played:        int       = Field(alias="gamesPlayed")
    description:         str
    max_players:         int       = Field(alias="maxPlayers")
    height:              int
    width:               int
    version:             int | str
    hidden:              bool
    ranked:              bool
    download_url:        str       = Field(alias="downloadUrl")
    thumbnail_url_small: str       = Field(alias="thumbnailUrlSmall")
    thumbnail_url_large: str       = Field(alias="thumbnailUrlLarge")

    @property
    def size(self) -> MapSize:
        return MapSize(self.height, self.width)

    @property
    def thumbnail_url(self) -> str:
        return self.thumbnail_url_small
