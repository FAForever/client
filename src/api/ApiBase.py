from PyQt5 import QtCore, QtNetwork
import logging
import json

from config import Settings

logger = logging.getLogger(__name__)

class ApiBase(QtCore.QObject):
    def __init__(self, route):
        QtCore.QObject.__init__(self)

        self.url = QtCore.QUrl(Settings.get('api') + route)
        self.manager = QtNetwork.QNetworkAccessManager()
        self.manager.finished.connect(self.onRequestFinished)

        self.handlers = {}

    # query arguments like filter=login==Rhyza
    def request(self, queryDict, responseHandler):
        query = QtCore.QUrlQuery()
        for key, value in queryDict.items():
          query.addQueryItem(key, str(value))
        url = QtCore.QUrl(self.url)
        url.setQuery(query)
        request = QtNetwork.QNetworkRequest(url)
        request.setRawHeader(b'User-Agent', b"FAF Client")
        request.setRawHeader(b'Content-Type', b'application/vnd.api+json')
        reply = self.manager.get(request)
        self.handlers[reply] = responseHandler

    def onRequestFinished(self, reply):
        if reply.error() != QtNetwork.QNetworkReply.NoError:
            logger.error("API request error:", reply.error())
        else:
            message_bytes = reply.readAll().data()
            message = json.loads(message_bytes.decode('utf-8'))
            included = self.parseIncluded(message)
            self.handlers[reply](self.parseData(message, included))
        self.handlers.pop(reply)
        reply.deleteLater()

    def parseIncluded(self, message):
        result = {}
        relationships = []
        if "included" in message:
            for inc_item in message["included"]:
                if not inc_item["type"] in result:
                    result[inc_item["type"]] = {}
                if "attributes" in inc_item:
                    result[inc_item["type"]][inc_item["id"]] = inc_item["attributes"]
                if "relationships" in inc_item:
                    for key, value in inc_item["relationships"].items():
                        relationships.append((inc_item["type"], inc_item["id"], key, value))
            message.pop('included')
        #resolve relationships
        for r in relationships:
            result[r[0]][r[1]][r[2]] = self.parseData(r[3], result)
        return result

    def parseData(self, message, included):
        if "data" in message:
            if isinstance(message["data"], (list)):
                result = []
                for data in message["data"]:
                    result.append(self.parseSingleData(data, included))
                return result
            elif isinstance(message["data"], (dict)):
                return self.parseSingleData(message["data"], included)
        else:
            logger.error("error in response", message)
        if "included" in message:
            logger.error("unexpected 'included' in message", message)
        return {}

    def parseSingleData(self, data, included):
        result = {}
        try:
            if data["type"] in included and data["id"] in included[data["type"]]:
                result = included[data["type"]][data["id"]]
            result["id"] = data["id"]
            result["type"] = data["type"]
            if "attributes" in data:
                for key, value in data["attributes"].items():
                    result[key] = value
            if "relationships" in data:
                for key, value in data["relationships"].items():
                    result[key] = self.parseData(value, included)
        except:
            logger.error("error parsing ", data)
        return result

