from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field

from src.api.models.AbstractEntity import AbstractEntity
from src.api.models.MapType import MapType
from src.api.models.Player import Player
from src.api.models.ReviewsSummary import ReviewsSummary


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


# FIXME/HACK: duplicate of the Map model, which can't be imported due to circular imports
class Map(AbstractEntity):
    display_name:    str                   = Field(alias="displayName")
    recommended:     int
    author:          Player | None         = Field(None)
    reviews_summary: ReviewsSummary | None = Field(None, alias="reviewsSummary")
    games_played:    int                   = Field(alias="gamesPlayed")
    map_type:        str                   = Field(alias="mapType")
    version:         MapVersion | None     = Field(None)

    @property
    def maptype(self) -> MapType:
        return MapType.from_string(self.map_type)


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

    map:                 Map | None = Field(None)

    @property
    def size(self) -> MapSize:
        return MapSize(self.height, self.width)

    @property
    def thumbnail_url(self) -> str:
        return self.thumbnail_url_small
