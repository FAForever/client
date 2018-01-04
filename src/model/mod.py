from PyQt5.QtCore import QObject, pyqtSignal

from decorators import with_logger


@with_logger
class Mod(QObject):

    modUpdated = pyqtSignal(object, object)

    SENTINEL = object()

    def __init__(self, uid, description, version, thumbnail, date, ui, link, played,
                 author, bugreports, name, downloads, likes, comments):

        QObject.__init__(self)

        self.uid = uid
        self.description = ""
        self.version = 0
        self.thumbnail = None
        self.date = None
        self.is_uimod = False
        self.link = ""
        self.played = 0
        self.author = ""
        self.comments = []  # every element is a dictionary with a
        self.bugreports = []  # text, author and date key
        self.name = ""
        self.downloads = 0
        self.likes = 0

        self.installed = False
        self.uploaded_byuser = False

        self._update(uid, description, version, thumbnail, date, ui, link, played,
                     author, bugreports, name, downloads, likes, comments)

    def copy(self):
        s = self
        return Mod(s.uid, s.description, s.version, s.thumbnail, s.date, s.is_uimod, s.link, s.played,
                   s.author, s.bugreports, s.name, s.downloads, s.likes, s.comments)

    def update(self, *args, **kwargs):
        old = self.copy()
        self._update(*args, **kwargs)
        self.modUpdated.emit(self, old)

    def _update(self,
                uid=SENTINEL,
                description=SENTINEL,
                version=SENTINEL,
                thumbnail=SENTINEL,
                date=SENTINEL,
                ui=SENTINEL,
                link=SENTINEL,
                played=SENTINEL,
                author=SENTINEL,
                bugreports=SENTINEL,
                name=SENTINEL,
                downloads=SENTINEL,
                likes=SENTINEL,
                comments=SENTINEL):

        def changed(item):
            return item is not self.SENTINEL

        if changed(uid):
            self.uid = uid
        if changed(name):
            self.name = name
        if changed(description):
            self.description = description
        if changed(author):
            self.author = author
        if changed(version):
            self.version = version
        if changed(downloads):
            self.downloads = downloads
        if changed(likes):
            self.likes = likes
        if changed(played):
            self.played = played
        if changed(comments):
            self.comments = comments
        if changed(bugreports):
            self.bugreports = bugreports
        if changed(date):
            self.date = date
        if changed(ui):
            self.is_uimod = ui
        if changed(thumbnail):
            self.thumbnail = thumbnail
        if changed(link):
            self.link = link

    def to_dict(self):
        return {
            "name": self.name,
            "played": self.played,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "downloads": self.downloads,
            "likes": self.likes,
            "comments": self.comments,
            "bugreports": self.bugreports,
            "date": self.date,  # = QtCore.QDateTime.fromSecsSinceEpoch(dic['date': ).toString("yyyy-MM-dd")
            "ui": self.is_uimod,
            "link": self.link,  # Direct link to the zip file.
            "thumbnail": self.thumbstr  # direct url to the thumbnail file.
        }
