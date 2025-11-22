from __future__ import annotations

from pydantic import Field

from src.api.models.AbstractEntity import AbstractEntity
from src.api.models.FeaturedMod import FeaturedMod
from src.api.models.Leaderboard import Leaderboard


class MatchmakerQueue(AbstractEntity):
    name:         str                = Field(alias="technicalName")
    team_size:    int                = Field(alias="teamSize")

    leaderboard:  Leaderboard | None = Field(None)
    featured_mod: FeaturedMod | None = Field(None)
