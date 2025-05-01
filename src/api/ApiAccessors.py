import logging
from collections.abc import Callable

from PyQt6.QtCore import pyqtSignal

from src.api.ApiBase import ApiBase

logger = logging.getLogger(__name__)


class ApiAccessor(ApiBase):
    def __init__(self, route: str = "") -> None:
        super().__init__(route)
        self.host_config_key = "api"


class UserApiAccessor(ApiBase):
    def __init__(self, route: str = "") -> None:
        super().__init__(route)
        self.host_config_key = "user_api"


class DataApiAccessor(ApiAccessor):
    data_ready = pyqtSignal(dict)

    def parse_message(self, message: dict) -> dict:
        included = self.parseIncluded(message)
        result = {}
        result["data"] = self.parseData(message, included)
        result["meta"] = self.parseMeta(message)
        return result

    def parseIncluded(self, message: dict) -> dict:
        result: dict = {}
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

    def parseData(self, message: dict, included: dict) -> dict | list:
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

    def parseSingleData(self, data: dict, included: dict) -> dict:
        result = {}
        try:
            if (
                data["type"] in included
                and data["id"] in included[data["type"]]
            ):
                result = included[data["type"]][data["id"]]
            result["id"] = data["id"]
            if "type" not in result:
                result["type"] = data["type"]
            if "attributes" in data:
                for key, value in data["attributes"].items():
                    result[key] = value
            if "relationships" in data:
                for key, value in data["relationships"].items():
                    result[key] = self.parseData(value, included)
        except Exception as e:
            logger.error("Erorr parsing %s: %s", data, e)
        return result

    def parseMeta(self, message: dict) -> dict:
        if "meta" in message:
            return message["meta"]
        return {}

    def requestData(
            self,
            query_dict: dict | None = None,
            error_handler: Callable | None = None,
    ) -> None:
        query_dict = query_dict or {}
        if error_handler is None:
            self.get_by_query(query_dict, self.handle_response)
        else:
            self.get_by_query(query_dict, self.handle_response, error_handler)

    def prepare_data(self, message: dict) -> dict:
        return message

    def handle_response(self, message: dict) -> None:
        self.data_ready.emit(self.prepare_data(message))
