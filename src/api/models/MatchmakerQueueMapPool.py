from __future__ import annotations

from pydantic import Field

from src.api.models.AbstractEntity import AbstractEntity
from src.api.models.MapPool import MapPool
from src.api.models.MatchmakerQueue import MatchmakerQueue


class MatchmakerQueueMapPool(AbstractEntity):
    min_rating:     float | None           = Field(alias="minRating")
    max_rating:     float | None           = Field(alias="maxRating")
    tokens:         int                    = Field(alias="vetoTokensPerPlayer")
    max_map_tokens: int                    = Field(alias="maxTokensPerMap")
    min_size:       int                    = Field(alias="minimumMapsAfterVeto")

    map_pool:       MapPool | None         = Field(None, alias="mapPool")
    queue:          MatchmakerQueue | None = Field(None, alias="matchmakerQueue")
