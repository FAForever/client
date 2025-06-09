import logging
from collections.abc import Callable
from collections.abc import Sequence
from typing import Any
from typing import cast

from PyQt6.QtCore import QByteArray
from PyQt6.QtNetwork import QNetworkReply

from src.api.ApiAccessors import DataApiAccessor
from src.api.ApiBase import PreProcessedApiResponse
from src.api.ApiBase import QueryOptions
from src.api.models.Map import Map
from src.api.models.MapVersion import MapVersion
from src.api.models.MapVersionReview import MapVersionReview
from src.api.models.Mod import Mod
from src.api.models.ModVersion import ModVersion
from src.api.models.ModVersionReview import ModVersionReview
from src.api.parsers.MapParser import MapParser
from src.api.parsers.MapPoolAssignmentParser import MapPoolAssignmentParser
from src.api.parsers.ModParser import ModParser
from src.model.player import Player
from src.util import decapitalize

logger = logging.getLogger(__name__)


class VaultsApiConnector(DataApiAccessor):
    def __init__(self, route: str) -> None:
        super().__init__(route)
        self._includes = ("latestVersion", "reviewsSummary")
        self._filters: tuple[str, ...] = ("latestVersion.hidden=='false'",)

    def _extend_query_options(self, query_options: QueryOptions) -> QueryOptions:
        self._add_default_includes(query_options)
        self._apply_default_filters(query_options)
        return query_options

    def _copy_query_options(self, query_options: QueryOptions | None) -> QueryOptions:
        query_options = query_options or {}  # cast(QueryOptions, {})
        return query_options.copy()

    def request_data(self, query_options: QueryOptions | None = None) -> None:
        query = self._copy_query_options(query_options)
        self._extend_query_options(query)
        self.get_by_query(query, self.handle_response)

    def _add_default_includes(self, query_options: QueryOptions) -> QueryOptions:
        if not self._includes:
            return query_options
        return self._extend_includes(query_options, self._includes)

    def _extend_includes(
            self,
            query_options: QueryOptions,
            to_include: Sequence[str],
    ) -> QueryOptions:
        cur_includes = str(query_options.get("include", ""))
        to_include_str = ",".join((cur_includes, *to_include)).removeprefix(",")
        query_options["include"] = to_include_str
        return query_options

    def _apply_default_filters(self, query_options: QueryOptions) -> QueryOptions:
        if not self._filters:
            return query_options
        cur_filters = str(query_options.get("filter", ""))
        query_options["filter"] = ";".join((cur_filters, *self._filters)).removeprefix(";")
        return query_options


class ModApiConnector(VaultsApiConnector):
    def __init__(self) -> None:
        super().__init__("/data/mod")

    def _extend_query_options(self, query_options: QueryOptions) -> QueryOptions:
        super()._extend_query_options(query_options)
        self._extend_includes(query_options, ["uploader"])
        return query_options

    def prepare_data(self, message: PreProcessedApiResponse) -> dict[str, Any]:
        return {
            "values": ModParser.parse_many(message["data"]),
            "meta": message["meta"],
        }


class MapApiConnector(VaultsApiConnector):
    def __init__(self) -> None:
        super().__init__("/data/map")

    def _extend_query_options(self, query_options: QueryOptions) -> QueryOptions:
        super()._extend_query_options(query_options)
        return self._extend_includes(query_options, ["author"])

    def prepare_data(self, message: PreProcessedApiResponse) -> dict[str, Any]:
        return {
            "values": MapParser.parse_many(message["data"]),
            "meta": message["meta"],
        }


class MapPoolApiConnector(VaultsApiConnector):
    def __init__(self) -> None:
        super().__init__("/data/mapPoolAssignment")
        self._includes = (
            "mapVersion",
            "mapVersion.map",
            "mapVersion.map.author",
            "mapVersion.map.reviewsSummary",
        )

    def _extend_query_options(self, query_options: QueryOptions) -> QueryOptions:
        self._add_default_includes(query_options)
        return query_options

    def prepare_data(self, message: PreProcessedApiResponse) -> dict[str, Any]:
        return {
            "values": MapPoolAssignmentParser.parse_many_to_maps(message["data"]),
            "meta": message["meta"],
        }


class ReviewsApiConnector(VaultsApiConnector):
    def __init__(self) -> None:
        super().__init__("")
        self._includes: tuple[str, ...] = tuple()
        self._filters: tuple[str, ...] = tuple()

    def request_reviews(self, item: Map | Mod) -> None:
        self.route = f"/data/{item.__class__.__name__.lower()}/{item.xd}"
        query_options = {
            "include": ",".join(("versions", "versions.reviews", "versions.reviews.player")),
        }
        self.request_data(cast(QueryOptions, query_options))

    def request_filtered_reviews(
            self,
            item: Map | Mod,
            query_options: QueryOptions | None = None,
    ) -> None:
        self.route = f"/data/{item.__class__.__name__.lower()}"
        self.request_data(query_options)

    def request_review_by_player(
            self,
            item: Map | Mod,
            player: Player,
    ) -> None:
        assert item.version is not None
        json_api_name = decapitalize(item.version.__class__.__name__)
        self.route = f"/data/{json_api_name}Review"
        query = {
            "filter": (
                f"{json_api_name}.id=={item.version.xd}"
                f";player.id=={player.id}"
            ),
            "include": f"player,{json_api_name}",
        }
        self.request_data(cast(QueryOptions, query))

    def submit_review(
            self,
            version: MapVersion | ModVersion,
            payload: QByteArray,
            handler: Callable[[PreProcessedApiResponse], None],
            error_handler: Callable[[QNetworkReply], None],
    ) -> None:
        json_api_name = decapitalize(version.__class__.__name__)
        endpoint = f"/data/{json_api_name}/{version.xd}/reviews"
        self.post(endpoint, payload, handler, error_handler)

    def delete_review(
            self,
            review: MapVersionReview | ModVersionReview,
            handler: Callable[[QNetworkReply], None],
            error_handler: Callable[[QNetworkReply], None],
    ) -> None:
        json_api_name = decapitalize(review.__class__.__name__)
        endpoint = f"/data/{json_api_name}/{review.xd}"
        self.delete(endpoint, handler, error_handler)

    def patch_review(
            self,
            review: MapVersionReview | ModVersionReview,
            payload: QByteArray,
            handler: Callable[[QNetworkReply], None],
            error_handler: Callable[[QNetworkReply], None],
    ) -> None:
        json_api_name = decapitalize(review.__class__.__name__)
        endpoint = f"/data/{json_api_name}/{review.xd}"
        self.patch(endpoint, payload, handler, error_handler, review)
