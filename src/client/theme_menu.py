from PyQt4 import QtGui, QtCore
import util

class ThemeMenu(QtGui.QMenu):
    themeSelected = QtCore.pyqtSignal(object)

    def __init__(self, parent):
        QtGui.QMenu.__init__(self, parent)
        self._themes = {}
        # Hack to not process check signals when we're changing them ourselves
        self._updating = False

    def setup(self, themes):
        for theme in themes:
            action = self.addAction(str(theme))
            action.toggled.connect(self.handle_toggle)
            self._themes[action] = theme
            action.setCheckable(True)
        self.addSeparator()
        self.addAction("Reload Stylesheet", util.reloadStyleSheets)

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
            action.setChecked(True)
        else:
            self.themeSelected.emit(self._themes[action])
            self._updateThemeChecks()
