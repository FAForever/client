from semantic_version import Version

from util import ThemeSet

THEME_FILE_FUNS = [
        "pixmap",
        "loadUi",
        "loadUiType",
        "readlines",
        "readstylesheet",
        "themeurl",
        "readfile",
        "sound",
        ]


def test_basic_init(mocker):
    theme_mock = mocker.Mock()
    theme_mock.configure_mock(version = lambda: Version("1.0.0"), name = "theme", themedir = "")

    setting_mock = mocker.Mock()
    setting_mock.configure_mock(get = lambda x, y = None: None)

    ts = ThemeSet([], theme_mock, setting_mock, "1.0.0")


def test_list_themes(mocker):
    def_mock = mocker.Mock()
    def_mock.configure_mock(version = lambda: Version("1.0.0"), name = "default", themedir = "")
    theme_mock = mocker.Mock()
    theme_mock.configure_mock(version = lambda: Version("1.0.0"), name = "theme", themedir = "")

    setting_mock = mocker.Mock()
    setting_mock.configure_mock(get = lambda x, y = None: None)

    ts = ThemeSet([theme_mock], def_mock, setting_mock, "1.0.0")

    lst = ts.listThemes()
    assert len(lst) == 2
    assert None in lst
    assert "theme" in lst
    assert "default" not in lst


def test_set_theme(mocker):
    def_mock = mocker.Mock()
    def_mock.configure_mock(version = lambda: Version("1.0.0"), name = "default", themedir = "")
    theme_mock = mocker.Mock()
    theme_mock.configure_mock(version = lambda: Version("1.0.0"), name = "theme", themedir = "")
    other_t_mock = mocker.Mock()
    other_t_mock.configure_mock(version = lambda: Version("1.0.0"), name = "other", themedir = "")

    setting_mock = mocker.Mock()
    setting_mock.configure_mock(get = lambda x, y = None: None)

    ts = ThemeSet([theme_mock, other_t_mock], def_mock, setting_mock, "1.0.0")

    ts.setTheme("theme", False)
    theme = ts.theme
    assert theme is theme_mock
    assert theme is not def_mock
    assert theme is not other_t_mock

    ts.setTheme(None, False)
    theme = ts.theme
    assert theme is def_mock
    assert theme is not theme_mock
    assert theme is not other_t_mock


def test_wrong_set_theme(mocker):
    def_mock = mocker.Mock()
    def_mock.configure_mock(version = lambda: Version("1.0.0"), name = "default", themedir = "")
    theme_mock = mocker.Mock()
    theme_mock.configure_mock(version = lambda: Version("1.0.0"), name = "theme", themedir = "")

    setting_mock = mocker.Mock()
    setting_mock.configure_mock(get = lambda x, y = None: None)

    ts = ThemeSet([theme_mock], def_mock, setting_mock, "1.0.0")
    ts.setTheme("wrong", False)
    theme = ts.theme
    assert theme == def_mock


def test_loadTheme(mocker):
    def_mock = mocker.Mock()
    def_mock.configure_mock(version = lambda: Version("1.0.0"), name = "default", themedir = "")
    theme_mock = mocker.Mock()
    theme_mock.configure_mock(version = lambda: Version("1.0.0"), name = "theme", themedir = "")
    other_t_mock = mocker.Mock()
    other_t_mock.configure_mock(version = lambda: Version("1.0.0"), name = "other", themedir = "")

    setting_mock = mocker.Mock()
    # Don't track option name, but make sure something is read
    setting_mock.configure_mock(get = (lambda x, y = None: "theme"))

    ts = ThemeSet([theme_mock], def_mock, setting_mock, "1.0.0")
    theme = ts.theme
    assert theme == def_mock

    ts.loadTheme()
    theme = ts.theme
    assert theme == theme_mock

    setting_mock.configure_mock(get = (lambda x, y = None: None))
    ts.loadTheme()
    theme = ts.theme
    assert theme == def_mock

def test_returns_when_not_found(mocker):
    mocker.patch("PyQt5.QtMultimedia.QSound")
    mocker.patch("PyQt5.QtGui.QPixmap")

    setting_mock = mocker.Mock()
    setting_mock.configure_mock(get = lambda x, y = None: None)

    def_mock = mocker.Mock()
    def_mock.configure_mock(version = lambda: Version("1.0.0"), name = "default", themedir = "")
    theme_mock = mocker.Mock()
    theme_mock.configure_mock(version = lambda: Version("1.0.0"), name = "theme", themedir = "")
    unthemed = mocker.Mock()
    unthemed.configure_mock(version = lambda: Version("1.0.0"), name = "", themedir = "")

    ts = ThemeSet([theme_mock], def_mock, setting_mock, "1.0.0", unthemed)
    ts.setTheme("theme", restart = False)

    # Make mocks return None
    for theme in [def_mock, theme_mock, unthemed]:
        members = dict((fn, mocker.Mock()) for fn in THEME_FILE_FUNS)
        theme.configure_mock(**members)
        for fn in THEME_FILE_FUNS:
            getattr(theme, fn).return_value = None


    # Don't return none in pixmap even if we don't find one
    assert ts.pixmap("name") is not None
    assert ts.pixmap("name", themed = True) is not None
    assert ts.pixmap("name", themed = False) is not None

    # All others should return None if they don't find the result
    for fn in [f for f in THEME_FILE_FUNS if f not in ["pixmap", "sound"]]:
        assert (getattr(ts, fn)("name")) is None
        assert (getattr(ts, fn)("name", themed = True)) is None
        assert (getattr(ts, fn)("name", themed = False)) is None


def test_theme_call_order(mocker):
    mocker.patch("PyQt5.QtMultimedia.QSound")
    mocker.patch("PyQt5.QtGui.QPixmap")

    setting_mock = mocker.Mock()
    setting_mock.configure_mock(get = lambda x, y = None: None)

    def_mock = mocker.Mock()
    def_mock.configure_mock(version = lambda: Version("1.0.0"), name = "default", themedir = "")
    theme_mock = mocker.Mock()
    theme_mock.configure_mock(version = lambda: Version("1.0.0"), name = "theme", themedir = "")
    unthemed = mocker.Mock()
    unthemed.configure_mock(version = lambda: Version("1.0.0"), name = "", themedir = "")

    all_mocks = [def_mock, theme_mock, unthemed]

    for theme in all_mocks:
        members = dict((fn, mocker.Mock()) for fn in THEME_FILE_FUNS)
        theme.configure_mock(**members)

    ts = ThemeSet([theme_mock], def_mock, setting_mock, "1.0.0", unthemed)

    # Tests if all THEME_FILE_FUNS functions call themes and only
    # themes from should_call in their specified order.
    def test_run(should_call, themed = None):
        for fn in THEME_FILE_FUNS:
            theme_ids = dict((e, "e" + str(i)) for (i, e) in enumerate(all_mocks))
            manager = mocker.Mock()
            for theme in all_mocks:
                manager.attach_mock(theme, theme_ids[theme])

            call_names = [theme_ids[t] + "." + fn for t in should_call]

            if themed is None:
                getattr(ts, fn)("mock")
            else:
                getattr(ts, fn)("mock", themed)
            assert [c[0] for c in manager.mock_calls] == call_names

    test_run([def_mock]) # Default theme returns something
    test_run([def_mock], True) # Same if we explicitly theme
    test_run([unthemed], False) # Unthemed returns something

    ts.setTheme("theme", restart = False)
    test_run([theme_mock]) # Find things in set theme
    test_run([theme_mock], True) # Same if we explicitly theme
    test_run([unthemed], False) # Use unthemed

    for fn in THEME_FILE_FUNS:
        getattr(theme_mock, fn).return_value = None

    test_run([theme_mock, def_mock]) # Try mock first, then fallback to default
    test_run([theme_mock, def_mock], True) # Same if we explicitly theme
    test_run([unthemed], False) # Use unthemed


# TODO - add more setTheme tests once we remove using qt dialogs from themeset
