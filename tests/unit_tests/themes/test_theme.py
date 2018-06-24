from semantic_version import Version

from util import Theme

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


def test_theme_with_empty_dir_keeps_filename(tmpdir):
    vfile = tmpdir.join("file")
    vfile.write("content")
    theme = Theme(None, "")
    assert theme.readfile(str(tmpdir.join("file"))) == "content"


def test_theme_with_dir_prepends_dir(tmpdir):
    themedir = tmpdir.mkdir("theme")
    vfile = themedir.join("file")
    vfile.write("content")
    theme = Theme(str(themedir), "")
    assert theme.readfile("file") == "content"


def test_missing_files_return_none(tmpdir):
    themedir = tmpdir.mkdir("theme")

    theme = Theme(str(themedir), "")
    for fun in THEME_FILE_FUNS:
        assert getattr(theme, fun)("file") == None

    theme = Theme(None, "")
    for fun in THEME_FILE_FUNS:
        assert getattr(theme, fun)(str(themedir.join("file"))) == None


def test_missing_version_returns_none(tmpdir):
    themedir = tmpdir.mkdir("theme")
    theme = Theme(str(themedir), "")
    assert theme.version() == None


def test_empty_dir_theme_version_returns_none(tmpdir):
    themedir = tmpdir.mkdir("theme")
    theme = Theme(None, "")
    assert theme.version() == None


def test_malformed_version_returns_none(tmpdir):
    themedir = tmpdir.mkdir("theme")
    themedir.join("version").write("1.0blergh")
    theme = Theme(str(themedir), "")
    assert theme.version() == None


def test_version_correctly_read(tmpdir):
    themedir = tmpdir.mkdir("theme")
    themedir.join("version").write("0.12.4")
    theme = Theme(str(themedir), "")
    version = theme.version()
    assert isinstance(version, Version)
    assert str(theme.version()) == "0.12.4"


def test_pixmap_cache_caches(tmpdir, mocker):
    with mocker.patch('PyQt5.QtGui.QPixmap', side_effect = [1, 2]) as pixmock:
        themedir = tmpdir.mkdir("theme")
        themedir.join("file").write("content")
        themedir.join("second_file").write("content")
        theme = Theme(str(themedir), "")

        first = theme.pixmap("file")
        still_first = theme.pixmap("file")
        second = theme.pixmap("second_file")

        assert first is not None and second is not None
        assert first is still_first
        assert first is not second

# TODO - tests for specific results of functions
