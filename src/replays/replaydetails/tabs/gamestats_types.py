from typing import TypedDict


class GeneralStatsMetric(TypedDict):
    mass: float
    count: int
    energy: float


class UnitStat(TypedDict):
    built: int
    lost: int
    kills: int


class GeneralStats(TypedDict):
    lastupdatetick: int
    score: int
    currentcap: float
    currentunits: float
    lost: GeneralStatsMetric
    kills: GeneralStatsMetric
    built: GeneralStatsMetric


class PlayerGameStats(TypedDict):
    defeated: int | None
    type: str
    name: str
    faction: int
    general: GeneralStats
    units: dict[str, UnitStat]
    resources: dict[str, dict[str, float]]


type GameStats = list[PlayerGameStats]
