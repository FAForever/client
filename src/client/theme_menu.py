from PyQt5 import QtWidgets, QtCore
import util

class ThemeMenu(QtCore.QObject):
    themeSelected = QtCore.pyqtSignal(object)

    def __init__(self, menu):
        QtCore.QObject.__init__(self)
        self._menu = menu
        self._themes = {}
        # Hack to not process check signals when we're changing them ourselves
        self._updating = False

    def setup(self, themes):
        for theme in themes:
            action = self._menu.addAction(str(theme))
            action.toggled.connect(self.handle_toggle)
            self._themes[action] = theme
            action.setCheckable(True)
        self._menu.addSeparator()
        self._menu.addAction("Reload Stylesheet", util.reloadStyleSheets)

        self._updateThemeChecks()

    def _updateThemeChecks(self):
        self._updating = True
        new_theme = util.getTheme()
        for action in self._themes:
            action.setChecked(new_theme == self._themes[action])
        self._updating = False

    def handle_toggle(self, toggled):
        if self._updating:
            return

        action = self.sender()
        if not toggled:
            self._updating = True
            action.setChecked(True)
            self._updating = False
        else:
            self.themeSelected.emit(self._themes[action])
            self._updateThemeChecks()
