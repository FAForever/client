from enum import Enum, unique

@unique
class Faction(Enum):
    """
    Enum to represent factions. Numbers match up with faction identification ids from the game.
    """
    UEF = 1
    AEON = 2
    CYBRAN = 3
    SERAPHIM = 4

    @staticmethod
    def from_name(name):
        name = name.lower()
        if name == "uef":
            return Faction.UEF
        elif name == "aeon":
            return Faction.AEON
        elif name == "cybran":
            return Faction.CYBRAN
        elif name == "seraphim":
            return Faction.SERAPHIM

        raise ValueError("Invalid faction name provided: %s" % name)
