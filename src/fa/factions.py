import random
from enum import Enum, unique


@unique
class Factions(Enum):
    """
    Enum to represent factions. Numbers match up with faction identification ids from the game.
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

        raise ValueError("Invalid faction name provided: %s" % name)

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

        raise ValueError("Invalid faction id provided: %i" % self)
