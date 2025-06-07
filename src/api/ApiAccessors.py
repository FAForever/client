import logging
from collections.abc import Callable
from typing import Any
from typing import cast

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtNetwork import QNetworkReply

from src.api.ApiBase import ApiBase
from src.api.ApiBase import ApiResourceObject
from src.api.ApiBase import ApiResponse
from src.api.ApiBase import PreParsedApiResponse
from src.api.ApiBase import PreProcessedApiResponse
from src.api.ApiBase import QueryOptions

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

    def parse_message(self, message: ApiResponse) -> PreParsedApiResponse:
        included = self.parseIncluded(message)
        result: PreParsedApiResponse = {"data": {}}
        result["data"] = self.parseData(message, included)
        result["meta"] = self.parseMeta(message)
        return result

    def parseIncluded(self, message: ApiResponse) -> dict[str, Any]:
        result: dict[str, Any] = {}
        relationships: list[tuple[str, str, str, ApiResponse]] = []
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

    def parseData(
            self,
            message: ApiResponse,
            included: dict[str, Any],
    ) -> dict[str, Any] | list[dict[str, Any]]:
        if "data" in message:
            if isinstance(message["data"], (list)):
                result: list[dict[str, Any]] = []
                for data in message["data"]:
                    result.append(self.parseSingleData(data, included))
                return result
            elif isinstance(message["data"], (dict)):  # pyright: ignore[reportUnnecessaryIsInstance]  # noqa: E501
                return self.parseSingleData(message["data"], included)
        else:
            logger.error("error in response", message)
        if "included" in message:
            logger.error("unexpected 'included' in message", message)
        return {}

    def parseSingleData(self, data: ApiResourceObject, included: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
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

    def parseMeta(self, message: ApiResponse) -> dict[str, float]:
        if "meta" in message:
            return message["meta"]
        return {}

    def requestData(
            self,
            query_dict: QueryOptions | None = None,
            error_handler: Callable[[QNetworkReply], None] | None = None,
    ) -> None:
        query_dict = query_dict or {}
        if error_handler is None:
            self.get_by_query(query_dict, self.handle_response)
        else:
            self.get_by_query(query_dict, self.handle_response, error_handler)

    def prepare_data(self, message: PreProcessedApiResponse) -> dict[str, Any]:
        return cast(dict[str, Any], message)

    def handle_response(self, message: PreProcessedApiResponse) -> None:
        self.data_ready.emit(self.prepare_data(message))
