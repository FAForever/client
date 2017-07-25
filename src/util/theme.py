from PyQt5 import QtGui, QtWidgets, QtCore, QtMultimedia, uic
from semantic_version import Version
import os

import logging
logger = logging.getLogger(__name__)


class Theme():
    """
    Represents a single FAF client theme.
    """
    def __init__(self, themedir, name):
        """
        A 'None' themedir represents no theming (no dir prepended to filename)
        """
        self._themedir = themedir
        self.name = name
        self._pixmapcache = {}

    def __str__(self):
        return str(self.name)

    def _themepath(self, filename):
        if self._themedir is None:
            return filename
        else:
            return os.path.join(self._themedir, filename)

    @property
    def themedir(self):
        return str(self._themedir)

    def _noneIfNoFile(fun):
        def _fun(self, filename):
            if not os.path.isfile(self._themepath(filename)):
                return None
            return fun(self, filename)
        return _fun

    def version(self):
        if self._themedir is None:
            return None
        try:
            version_file = self._themepath("version")
            with open(version_file) as f:
                return Version(f.read().strip())
        except (IOError, ValueError):
            return None

    def pixmap(self, filename):
        """
        This function loads a pixmap from a themed directory, or anywhere.
        It also stores them in a cache dictionary (may or may not be necessary depending on how Qt works under the hood)
        """
        try:
            return self._pixmapcache[filename]
        except KeyError:
            if os.path.isfile(self._themepath(filename)):
                pix = QtGui.QPixmap(self._themepath(filename))
            else:
                pix = None

        self._pixmapcache[filename] = pix
        return pix

    @_noneIfNoFile
    def loadUi(self, filename):
        # Loads and compiles a Qt Ui file via uic.
        return uic.loadUi(self._themepath(filename))

    @_noneIfNoFile
    def loadUiType(self, filename):
        # Loads and compiles a Qt Ui file via uic, and returns the Type and Basetype as a tuple
        return uic.loadUiType(self._themepath(filename))

    @_noneIfNoFile
    def readlines(self, filename):
        # Reads and returns the contents of a file in the theme dir.
        with open(self._themepath(filename)) as f:
            logger.debug(u"Read themed file: " + filename)
            return f.readLines()

    @_noneIfNoFile
    def readstylesheet(self, filename):
        with open(self._themepath(filename)) as f:
            logger.info(u"Read themed stylesheet: " + filename)
            return f.read().replace("%THEMEPATH%", self._themedir.replace("\\", "/"))

    @_noneIfNoFile
    def themeurl(self, filename):
        """
        This creates an url to use for a local stylesheet. It's a bit of a hack because Qt has a bug identifying proper localfile QUrls
        """
        return QtCore.QUrl("file://" + self._themepath(filename).replace("\\", "/"))

    @_noneIfNoFile
    def readfile(self, filename):
        # Reads and returns the contents of a file in the theme folder.
        with open(self._themepath(filename)) as f:
            logger.debug(u"Read themed file: " + filename)
            return f.read()

    @_noneIfNoFile
    def sound(self, filename):
        # Returns a sound file string, from the themed folder.
        return self._themepath(filename)


class ThemeSet:
    """
    Represent a collection of themes to choose from, with a default theme and
    an unthemed directory.
    """
    def __init__(self, themeset, default_theme, settings,
                 client_version, unthemed = None):
        self._default_theme = default_theme
        self._themeset = themeset
        self._theme = default_theme
        self._unthemed = Theme(None, '') if unthemed is None else unthemed
        self._settings = settings
        self._client_version = client_version

        # For refreshing stylesheets
        self._stylesheets = {}

    @property
    def theme(self):
        return self._theme

    def _getThemeByName(self, name):
        if name is None:
            return self._default_theme
        matching_themes = [theme for theme in self._themeset if theme.name == name]
        if not matching_themes:
            return None
        return matching_themes[0]

    def loadTheme(self):
        name = self._settings.get("theme/theme/name", None)
        logger.debug("Loaded Theme: " + str(name))
        self.setTheme(name, False)

    def listThemes(self):
        return [None] + [theme.name for theme in self._themeset]

    def setTheme(self, name, restart = True):
        theme = self._getThemeByName(name)
        if theme is None:
            return

        set_theme = self._do_setTheme(theme)

        self._settings.set("theme/theme/name", self._theme.name)
        self._settings.sync()

        if set_theme and restart:
            QtWidgets.QMessageBox.information(None, "Restart Needed", "FAF will quit now.")
            QtWidgets.QApplication.quit()

    def _checkThemeVersion(self, theme):
        # Returns a (potentially overridden) theme version.
        version = theme.version()
        if version is None:
            # Malformed theme, we should not override it!
            return None

        override_config = "theme_version_override/" + str(theme)
        override_version_str = self._settings.get(override_config, None)

        if override_version_str is None:
            return version

        try:
            override_version = Version(override_version_str)
        except ValueError:
            # Did someone manually mess with the override config?
            logger.warn("Malformed theme version override setting: " + override_version_str)
            self._settings.remove(override_config)
            return version

        if version >= override_version:
            logger.info("New version " + str(version) + " of theme " + theme +
                        ", removing override " + override_version_str)
            self._settings.remove(override_config)
            return version
        else:
            return override_version

    def _checkThemeOutdated(self, theme_version):
        faf_version = Version(self._client_version)
        return faf_version > theme_version

    def _do_setTheme(self, new_theme):
        old_theme = self._theme
        theme_changed = lambda: old_theme != self._theme

        if new_theme == self._theme:
            return theme_changed()

        if new_theme == self._default_theme:
            # No need for checks
            self._theme = new_theme
            return theme_changed()

        theme_version = self._checkThemeVersion(new_theme)
        if theme_version is None:
            QtWidgets.QMessageBox.information(
                    QtWidgets.QApplication.activeWindow(),
                    "Invalid Theme",
                    "Failed to read the version of the following theme:<br/><b>" +
                    str(new_theme) +
                    "</b><br/><i>Contact the maker of the theme for a fix!</i>")
            logger.error("Error reading theme version: " + str(new_theme) +
                         " in directory " + new_theme.themedir)
            return theme_changed()

        outdated = self._checkThemeOutdated(theme_version)

        if not outdated:
            logger.info("Using theme: " + str(new_theme) +
                        " in directory " + new_theme.themedir)
            self._theme = new_theme
        else:
            box = QtWidgets.QMessageBox(QtWidgets.QApplication.activeWindow())
            box.setWindowTitle("Incompatible Theme")
            box.setText(
                    "The selected theme reports compatibility with a lower version of the FA client:<br/><b>" +
                    str(new_theme) +
                    "</b><br/><i>Contact the maker of the theme for an update!</i><br/>" +
                    "<b>Do you want to try to apply the theme anyway?</b>")
            b_yes = box.addButton("Apply this once", QtWidgets.QMessageBox.YesRole)
            b_always = box.addButton("Always apply for this FA version", QtWidgets.QMessageBox.YesRole)
            b_default = box.addButton("Use default theme", QtWidgets.QMessageBox.NoRole)
            b_no = box.addButton("Abort", QtWidgets.QMessageBox.NoRole)
            box.exec_()
            result = box.clickedButton()

            if result == b_always:
                QtWidgets.QMessageBox.information(
                        QtWidgets.QApplication.activeWindow(),
                        "Notice",
                        "If the applied theme causes crashes, clear the '[theme_version_override]'<br/>" +
                        "section of your FA client config file.")
                logger.info("Overriding version of theme " + str(new_theme) + "with " + self._client_version)
                override_config = "theme_version_override/" + str(new_theme)
                self._settings.set(override_config, self._client_version)

            if result == b_always or result == b_yes:
                logger.info("Using theme: " + str(new_theme) +
                            " in directory " + new_theme.themedir)
                self._theme = new_theme
            elif result == b_default:
                self._theme = self._default_theme
            else:
                pass
        return theme_changed()

    def _theme_callchain(self, fn_name, filename, themed):
        """
        Calls fn_name chaining through theme / default theme / unthemed.
        """
        if themed:
            item = getattr(self._theme, fn_name)(filename)
            if item is None:
                item = getattr(self._default_theme, fn_name)(filename)
        else:
            item = getattr(self._unthemed, fn_name)(filename)
        return item

    def _warn_resource_null(fn):
        def _nullcheck(self, filename, themed=True):
            ret = fn(self, filename, themed)
            if ret is None:
                logger.warn("Failed to load resource '" + filename + "' in theme." + fn.__name__)
            return ret
        return _nullcheck

    def _pixmap(self, filename, themed=True):
        return self._theme_callchain("pixmap", filename, themed)

    @_warn_resource_null
    def loadUi(self, filename, themed=True):
        return self._theme_callchain("loadUi", filename, themed)

    @_warn_resource_null
    def loadUiType(self, filename, themed=True):
        return self._theme_callchain("loadUiType", filename, themed)

    @_warn_resource_null
    def readlines(self, filename, themed=True):
        return self._theme_callchain("readlines", filename, themed)

    @_warn_resource_null
    def readstylesheet(self, filename, themed=True):
        return self._theme_callchain("readstylesheet", filename, themed)

    @_warn_resource_null
    def themeurl(self, filename, themed=True):
        return self._theme_callchain("themeurl", filename, themed)

    @_warn_resource_null
    def readfile(self, filename, themed=True):
        return self._theme_callchain("readfile", filename, themed)

    @_warn_resource_null
    def _sound(self, filename, themed=True):
        return self._theme_callchain("sound", filename, themed)

    def pixmap(self, filename, themed=True):
        # If we receive None, return the default pixmap
        ret = self._pixmap(filename, themed)
        if ret is None:
            return QtGui.QPixmap()
        return ret

    def sound(self, filename, themed=True):
        QtMultimedia.QSound.play(self._sound(filename, themed))

    def setStyleSheet(self, obj, filename):
        self._stylesheets[obj] = filename
        obj.setStyleSheet(self.readstylesheet(filename))

    def reloadStyleSheets(self):
        for obj, filename in self._stylesheets.items():
            obj.setStyleSheet(self.readstylesheet(filename))

    def icon(self, filename, themed=True, pix=False):
        """
        Convenience method returning an icon from a cached,
        optionally themed pixmap as returned by the pixmap(...) function
        """
        if pix:
            return self.pixmap(filename, themed)
        else:
            icon = QtGui.QIcon()
            icon.addPixmap(self.pixmap(filename, themed), QtGui.QIcon.Normal)
            splitExt = os.path.splitext(filename)
            if len(splitExt) == 2:
                pixDisabled = self.pixmap(splitExt[0] + "_disabled" + splitExt[1], themed)
                if pixDisabled is not None:
                    icon.addPixmap(pixDisabled, QtGui.QIcon.Disabled, QtGui.QIcon.On)

                pixActive = self.pixmap(splitExt[0] + "_active" + splitExt[1], themed)
                if pixActive is not None:
                    icon.addPixmap(pixActive, QtGui.QIcon.Active, QtGui.QIcon.On)

                pixSelected = self.pixmap(splitExt[0] + "_selected" + splitExt[1], themed)
                if pixSelected is not None:
                    icon.addPixmap(pixSelected, QtGui.QIcon.Selected, QtGui.QIcon.On)
            return icon
