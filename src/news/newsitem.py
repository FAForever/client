import util

FormClass, BaseClass = util.loadUiType("news/newsframe.ui")

class NewsFrame(FormClass, BaseClass):
    def __init__(self, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)
        self.setupUi(self)

        self.expandButton.clicked.connect(self.toggle)

        self.collapse()

    def set_content(self, title, content):
        self.titleLabel.setText(title)
        self.newsTextBrowser.setHtml(content)

    def collapse(self):
        self.newsTextBrowser.hide()
        self.expandButton.setText('>>')

    def expand(self):
        self.newsTextBrowser.show()
        self.expandButton.setText('<<')

    def toggle(self):
        if self.newsTextBrowser.isHidden():
            self.expand()
        else:
            self.collapse()
