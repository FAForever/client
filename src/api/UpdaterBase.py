import json
import logging
import time
import urllib

from config import Settings

logger = logging.getLogger(__name__)


class UpdaterBase:
    def __init__(self, route):
        self.route = route

        self.handlers = {}

    def request(self, queryDict, responseHandler):
        url = urllib.parse.urlparse(Settings.get('api') + self.route)
        query = urllib.parse.urlencode(queryDict)
        url = url._replace(query=query)
        url = urllib.parse.urlunparse(url)

        request = urllib.request.Request(url)

        api_token = Settings.get('oauth/token', None)
        if api_token is not None and api_token.get('expires_at') > time.time():
            access_token = api_token.get('access_token')
            bearer = 'Bearer {}'.format(access_token)
            request.add_header('Authorization', bearer)

        request.add_header('User-Agent', 'FAF Client')
        request.add_header('Content-Type', 'application/vnd.api+json')
        logger.debug("Sending API request with URL: {}".format(url))
        reply = urllib.request.urlopen(request)
        self.handlers[reply] = responseHandler
        return self.onRequestFinished(reply)

    def onRequestFinished(self, reply):
        if reply.status != 200:
            logger.error("API request error: {}".format(reply.status))
        else:
            message_bytes = reply.read()
            message = json.loads(message_bytes.decode('utf-8'))
            included = self.parseIncluded(message)
            return self.handlers[reply](self.parseData(message, included))

    def parseIncluded(self, message):
        result = {}
        relationships = []
        if "included" in message:
            for inc_item in message["included"]:
                if not inc_item["type"] in result:
                    result[inc_item["type"]] = {}
                if "attributes" in inc_item:
                    type_ = inc_item["type"]
                    id_ = inc_item["id"]
                    result[type_][id_] = inc_item["attributes"]
                if "relationships" in inc_item:
                    for key, value in inc_item["relationships"].items():
                        relationships.append((
                            inc_item["type"], inc_item["id"], key, value,
                        ))
            message.pop('included')
        # resolve relationships
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
            if (
                data["type"] in included
                and data["id"] in included[data["type"]]
            ):
                result = included[data["type"]][data["id"]]
            result["id"] = data["id"]
            result["type"] = data["type"]
            if "attributes" in data:
                for key, value in data["attributes"].items():
                    result[key] = value
            if "relationships" in data:
                for key, value in data["relationships"].items():
                    result[key] = self.parseData(value, included)
        except BaseException:
            logger.error("error parsing ", data)
        return result
