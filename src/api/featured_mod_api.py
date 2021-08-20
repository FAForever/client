import logging

from .ApiBase import ApiBase

logger = logging.getLogger(__name__)


class FeaturedModApiConnector(ApiBase):
    def __init__(self, dispatch):
        ApiBase.__init__(self, '/data/featuredMod')
        self.dispatch = dispatch

    def requestData(self):
        self.request({}, self.handleData)

    def handleData(self, message):
        preparedData = {
            "command": "mod_info_api",
            "values": [],
        }
        for mod in message:
            preparedMod = {
                "command": "mod_info_api",
                "name": mod["technicalName"],
                "fullname": mod["displayName"],
                "publish": mod.get("visible", False),
                "order": mod.get("order", 0),
                "desc": mod.get(
                    "description",
                    "<i>No description provided</i>",
                ),
            }
            preparedData["values"].append(preparedMod)
        self.dispatch.dispatch(preparedData)
