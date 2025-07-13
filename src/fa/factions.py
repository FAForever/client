from __future__ import annotations

import random
from enum import Enum
from enum import unique


@unique
class Factions(Enum):
    """
    Enum to represent factions. Numbers match up with faction identification
    ids from the game.
    """
    UEF = 1
    AEON = 2
    CYBRAN = 3
    SERAPHIM = 4

    # Shall remain the last element: not a real faction number.
    RANDOM = 5

    @staticmethod
    def get_random_faction():
        """
        :return: A random faction, but never RANDOM.
        """
        possibilities = list(Factions)
        possibilities.pop()
        return random.choice(possibilities)

    @staticmethod
    def set_faction(sub_factions: list[bool] = []) -> Factions:
        if any(sub_factions):
            possibilities: list[Factions] = []
            for faction, selected in zip(list(Factions)[:-1], sub_factions):
                if selected:
                    possibilities.append(faction)
        else:
            possibilities = list(Factions)[:-1]
        return random.choice(possibilities)

    @staticmethod
    def from_name(name):
        name = name.lower()
        if name == "uef":
            return Factions.UEF
        elif name == "aeon":
            return Factions.AEON
        elif name == "cybran":
            return Factions.CYBRAN
        elif name == "seraphim":
            return Factions.SERAPHIM
        elif name == "random":
            return Factions.RANDOM

        raise ValueError(f"Invalid faction name provided: {name}")

    def to_name(self):
        if self == Factions.UEF:
            return "uef"
        elif self == Factions.AEON:
            return "aeon"
        elif self == Factions.CYBRAN:
            return "cybran"
        elif self == Factions.SERAPHIM:
            return "seraphim"
        elif self == Factions.RANDOM:
            return "random"

        raise ValueError(f"Invalid faction id provided: {self}")
