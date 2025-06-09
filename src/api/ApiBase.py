from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any
from typing import NotRequired
from typing import TypedDict

from PyQt6 import QtWidgets
from PyQt6.QtCore import QByteArray
from PyQt6.QtCore import QEventLoop
from PyQt6.QtCore import QObject
from PyQt6.QtCore import QUrl
from PyQt6.QtCore import QUrlQuery
from PyQt6.QtNetwork import QNetworkAccessManager
from PyQt6.QtNetwork import QNetworkReply
from PyQt6.QtNetwork import QNetworkRequest

from src.config import Settings
from src.oauth.oauth_flow import OAuth2Flow
from src.oauth.oauth_flow import OAuth2FlowInstance

logger = logging.getLogger(__name__)


class ApiResourceObject(TypedDict):
    id: str
    type: str
    attributes: NotRequired[dict[str, Any]]
    relationships: NotRequired[dict[str, ApiResponse]]


class ApiResponse(TypedDict):
    data: ApiResourceObject | list[ApiResourceObject]
    included: NotRequired[list[ApiResourceObject]]
    meta: NotRequired[dict[str, float]]


class PreParsedApiResponse(TypedDict):
    data: dict[str, Any] | list[dict[str, Any]]
    meta: NotRequired[dict[str, float]]


type PreProcessedApiResponse = ApiResponse | PreParsedApiResponse
type QueryOptions = dict[str, str | float]

DO_NOT_ENCODE = QByteArray(b":/?&=.,")


class ApiBase(QObject):
    oauth: OAuth2Flow = OAuth2FlowInstance

    def __do_nothing(*args: Any, **kwargs: Any) -> None:
        pass

    def __init__(self, route: str = "") -> None:
        QObject.__init__(self)
        self.route = route
        self.host_config_key = ""
        self.manager = QNetworkAccessManager()
        self.manager.finished.connect(self.onRequestFinished)
        self._running = False
        self.handlers: dict[QNetworkReply, Callable[[PreProcessedApiResponse], Any]] = {}
        self.non_get_handlers: dict[QNetworkReply, Callable[[QNetworkReply], Any]] = {}
        self.error_handlers: dict[QNetworkReply, Callable[[QNetworkReply], Any]] = {}

    def set_route(self, route: str) -> None:
        self.route = route

    def set_host_config_key(self, host_config_key: str) -> None:
        self.host_config_key = host_config_key

    @classmethod
    def set_oauth(cls, oauth: OAuth2Flow) -> None:
        cls.oauth = oauth

    def build_query_url(self, query_dict: QueryOptions) -> QUrl:
        query = QUrlQuery()
        for key, value in query_dict.items():
            query.addQueryItem(key, str(value))
        stringQuery = query.toString(QUrl.ComponentFormattingOption.FullyDecoded)
        percentEncodedByteArrayQuery = QUrl.toPercentEncoding(
            stringQuery,
            exclude=DO_NOT_ENCODE,
        )
        percentEncodedStrQuery = percentEncodedByteArrayQuery.data().decode()
        url = self._get_host_url().resolved(QUrl(self.route))
        url.setQuery(percentEncodedStrQuery)
        return url

    def _get_host_url(self) -> QUrl:
        return QUrl(Settings.get(self.host_config_key))

    def _url_from_endpoint(self, endpoint: str) -> QUrl:
        return self._get_host_url().resolved(QUrl(endpoint))

    # query arguments like filter=login==Rhyza
    def get_by_query(
            self,
            query_dict: QueryOptions,
            response_handler: Callable[[PreProcessedApiResponse], None],
            error_handler: Callable[[QNetworkReply], None] = __do_nothing,
    ) -> None:
        url = self.build_query_url(query_dict)
        self.get(url, response_handler, error_handler)

    def get_by_endpoint(
            self,
            endpoint: str,
            response_handler: Callable[[PreProcessedApiResponse], None],
            error_handler: Callable[[QNetworkReply], None] = __do_nothing,
    ) -> None:
        url = self._url_from_endpoint(endpoint)
        self.get(url, response_handler, error_handler)

    @staticmethod
    def prepare_request(url: QUrl | None) -> QNetworkRequest:
        request = QNetworkRequest(url) if url else QNetworkRequest()
        # last 2 args are unused, but for some reason they are required
        ApiBase.oauth.prepareRequest(request, QByteArray(), QByteArray())
        return request

    def get(
            self,
            url: QUrl,
            response_handler: Callable[[PreProcessedApiResponse], None],
            error_handler: Callable[[QNetworkReply], None] = __do_nothing,
    ) -> None:
        self._running = True
        logger.debug("Sending GET API request with URL: %s", url.toString())
        reply = self.manager.get(self.prepare_request(url))
        if reply is None:
            # in C++ this case is not even possible
            # but PyQt decided, that `get` returns an optional (maybe it still never happens)
            logger.error("Error sending GET request to: '%s'", url.toString())
            self._running = False
            return
        self.handlers[reply] = response_handler
        self.error_handlers[reply] = error_handler

    def post(
            self,
            endpoint: str,
            data: QByteArray,
            response_handler: Callable[[PreProcessedApiResponse], None] = __do_nothing,
            error_handler: Callable[[QNetworkReply], None] = __do_nothing,
    ) -> None:
        self._running = True
        url = self._url_from_endpoint(endpoint)
        logger.debug("Sending POST API request with URL: %s", url.toString())
        request = self.prepare_request(url)
        request.setRawHeader(b"Content-Type", b"application/vnd.api+json;charset=utf-8")
        reply = self.manager.post(request, data)
        if reply is None:
            logger.error("Error sending POST request to: '%s' with %s", url.toString(), data.data())
            self._running = False
            return
        self.handlers[reply] = response_handler
        self.error_handlers[reply] = error_handler

    def delete(
            self,
            endpoint: str,
            response_handler: Callable[[QNetworkReply], None] = __do_nothing,
            error_handler: Callable[[QNetworkReply], None] = __do_nothing,
    ) -> None:
        self._running = True
        url = self._url_from_endpoint(endpoint)
        logger.debug("Sending DELETE API request with URL: %s", url.toString())
        request = self.prepare_request(url)
        reply = self.manager.deleteResource(request)
        if reply is None:
            self._running = False
            logger.error("Error sending DELETE request to: %s", url.toString())
            return
        self.non_get_handlers[reply] = response_handler
        self.error_handlers[reply] = error_handler

    def patch(
            self,
            endpoint: str,
            data: QByteArray,
            response_handler: Callable[[QNetworkReply], None] = __do_nothing,
            error_handler: Callable[[QNetworkReply], None] = __do_nothing,
            patch_property: Any | None = None,
    ) -> None:
        self._running = True
        url = self._url_from_endpoint(endpoint)
        logger.debug("Sending PATCH API request with URL: %s", url.toString())
        request = self.prepare_request(url)
        request.setRawHeader(b"Content-Type", b"application/vnd.api+json;charset=utf-8")
        reply = self.manager.sendCustomRequest(request, b"PATCH", data)

        if reply is None:
            logger.error("Error sending PATCH request to: %s", url.toString())
            self._running = False
            return

        reply.setProperty("patch_property", patch_property)
        self.non_get_handlers[reply] = response_handler
        self.error_handlers[reply] = error_handler

    def parse_message(self, message: ApiResponse) -> ApiResponse | PreParsedApiResponse:
        return message

    def onRequestFinished(self, reply: QNetworkReply) -> None:
        self._running = False
        if reply.error() != QNetworkReply.NetworkError.NoError:
            logger.error("API request error: %s", reply.error())
            self.error_handlers[reply](reply)
        elif (
                reply.operation() in (
                    self.manager.Operation.DeleteOperation,
                    self.manager.Operation.CustomOperation,
                )
        ):
            url = reply.request().url().toString()
            logger.debug("%s operation succeeded: %s", reply.operation(), url)
            self.non_get_handlers[reply](reply)
            self.non_get_handlers.pop(reply)
        else:
            message_bytes = reply.readAll().data()
            message = json.loads(message_bytes.decode('utf-8'))
            result = self.parse_message(message)
            self.handlers[reply](result)
            self.handlers.pop(reply)

        self.error_handlers.pop(reply)
        reply.deleteLater()

    def waitForCompletion(self):
        waitFlag = QEventLoop.ProcessEventsFlag.WaitForMoreEvents
        while self._running:
            QtWidgets.QApplication.processEvents(waitFlag)

    def abort(self) -> None:
        for reply in self.handlers.copy():
            reply.abort()
