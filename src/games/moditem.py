import os

from PyQt5 import QtGui, QtWidgets

import client
import util

# Maps names of featured mods to ModItem objects.
mods = {}

mod_crucial = ["balancetesting", "faf", "fafbeta"]

# These mods are not shown in the game list
mod_invisible = {}

mod_favourites = {}  # LATER: Make these saveable and load them from settings


class ModItem(QtWidgets.QListWidgetItem):
    def __init__(self, message, *args, **kwargs):
        QtWidgets.QListWidgetItem.__init__(self, *args, **kwargs)

        self.mod = message["name"]
        self.order = message.get("order", 0)
        self.name = message["fullname"]
        # Load Icon and Tooltip

        tip = message["desc"]
        self.setToolTip(tip)

        icon = util.THEME.icon(os.path.join("games/mods/", self.mod + ".png"))
        if icon.isNull():
            icon = util.THEME.icon("games/mods/default.png")
        self.setIcon(icon)

        if self.mod in mod_crucial:
            color = client.instance.player_colors.get_color("self")
        else:
            color = client.instance.player_colors.get_color("player")

        self.setForeground(QtGui.QColor(color))
        self.setText(self.name)

    def __eq__(self, other):
        if not isinstance(other, ModItem):
            return False
        return other.mod == self.mod

    def __ge__(self, other):
        """ Comparison operator used for item list sorting """
        return not self.__lt__(other)

    def __lt__(self, other):
        """ Comparison operator used for item list sorting """

        if self.order == other.order:
            # Default: Alphabetical
            return self.name.lower() < other.mod.lower()

        return self.order < other.order
