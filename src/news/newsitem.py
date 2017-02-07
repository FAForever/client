import util

FormClass, BaseClass = util.loadUiType("news/newsframe.ui")

class NewsFrame(FormClass, BaseClass):
    def __init__(self, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)
