from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any
from typing import Literal
from typing import NotRequired
from typing import TypedDict

from PyQt6 import QtCore
from PyQt6.QtCore import QObject
from PyQt6.QtNetwork import QAbstractSocket
from PyQt6.QtNetwork import QTcpSocket

type RpcParams = list[str | int | bool]


class RpcObject(TypedDict):
    method: str
    params: RpcParams
    jsonrpc: Literal["2.0"]
    id: NotRequired[int]


class JsonRpcTcpClient(QObject):
    def __init__(self, logger: logging.Logger) -> None:
        QObject.__init__(self)
        self._logger = logger
        self.socket = QTcpSocket(self)
        self.connectionAttempts = 1
        self.socket.readyRead.connect(self.onData)
        self.socket.errorOccurred.connect(self.onSocketError)
        self.nextid = 1
        self.callbacks_result: dict[int, Callable[..., None]] = {}
        self.callbacks_error: dict[int, Callable[..., None]] = {}
        self.buffer = b''

    def connect_(self, host: str, port: int, *, blocking: bool = False) -> None:
        self.host = host
        self.port = port
        self.socket.connectToHost(host, port)
        if blocking:
            self.socket.waitForConnected(5000)

    def isConnected(self):
        return self.socket.state() == QAbstractSocket.SocketState.ConnectedState

    @QtCore.pyqtSlot(QAbstractSocket.SocketError)
    def onSocketError(self, error: QAbstractSocket.SocketError) -> None:
        if (error == QAbstractSocket.SocketError.ConnectionRefusedError):
            self.socket.connectToHost(self.host, self.port)
            self.connectionAttempts += 1
            # self._logger.info("Reconnecting to JSONRPC server {}"
            #                   .format(self.connectionAttempts))
        else:
            raise RuntimeError(
                "Connection error to JSON RPC server: {} ({})"
                .format(self.socket.errorString(), error),
            )

    def close(self):
        self.socket.close()

    def parseRequest(self, request: dict[str, Any]) -> None:
        try:
            m = getattr(self, request["method"])
            if "params" in request and len(request["params"]) > 0:
                result = m(*request["params"])
            else:
                result = m()

            # we do not only have a notification,
            # but a request which awaits a response
            if "id" in request:
                responseObject = {
                    "id": request["id"],
                    "result": result,
                    "jsonrpc": "2.0",
                }
                self.socket.write(
                    json.dumps(responseObject).encode('utf8') + b'\n',
                )
        except AttributeError:
            if "id" in request:
                responseObject = {
                    "id": request["id"],
                    "error": "no such method",
                    "jsonrpc": "2.0",
                }
                self.socket.write(
                    json.dumps(responseObject).encode('utf8') + b'\n',
                )

    def parseResponse(self, response: dict[str, Any]) -> None:
        if "error" in response:
            self._logger.error("Response error %s", response)
            if "id" in response:
                if response["id"] in self.callbacks_error:
                    self.callbacks_error[response["id"]](response["error"])
        elif "result" in response:
            if "id" in response:
                if response["id"] in self.callbacks_result:
                    self.callbacks_result[response["id"]](response["result"])
        if "id" in response:
            self.callbacks_error.pop(response["id"], None)
            self.callbacks_result.pop(response["id"], None)

    @QtCore.pyqtSlot()
    def onData(self) -> None:
        newData = b''
        while self.socket.bytesAvailable():
            newData += bytes(self.socket.readAll())

        # this seems to be a new notification, which invalidates out buffer.
        # This may happen on malformed JSON data
        if newData.startswith(b"{\"jsonrpc\":\"2.0\""):
            if len(self.buffer) > 0:
                self._logger.error(
                    "Parse error: discarding old possibly malformed buffer data: %s",
                    self.buffer,
                )
            self.buffer = newData
        else:
            self.buffer += newData
        self.buffer = self.processBuffer(self.buffer.strip())

    # from https://github.com/joncol/jcon-cpp/blob/master/src/jcon/
    # json_rpc_endpoint.cpp#L107
    def processBuffer(self, buf: bytes) -> bytes:
        if len(buf) == 0:
            return b''
        if not buf.startswith(b'{'):
            self._logger.error("parse error: buffer expected to start: %s", buf)
            return b''
        in_string = False
        brace_nesting_level = 0
        for i, c in enumerate(buf):
            if c == ord('"'):
                in_string = not in_string

            if not in_string:
                if c == ord('{'):
                    brace_nesting_level += 1
                if c == ord('}'):
                    brace_nesting_level -= 1
                    if brace_nesting_level < 0:
                        self._logger.error("parse error: brace_nesting_level < 0: %s", buf)
                        return b''
                    if brace_nesting_level == 0:
                        complete_json_buf = buf[:i + 1]
                        remaining_buf = buf[i + 1:]
                        try:
                            request = json.loads(
                                complete_json_buf.decode('utf-8'),
                            )
                        except ValueError:
                            self._logger.error("json.loads failed for %s", complete_json_buf)
                            return b''
                        # is this a request?
                        if "method" in request:
                            self.parseRequest(request)
                        # this is only a response
                        else:
                            self.parseResponse(request)
                        return self.processBuffer(remaining_buf.strip())
        return buf

    def call(
        self,
        method: str,
        args: list[str | int | bool] = [],
        callback_result: Callable[..., None] | None = None,
        callback_error: Callable[..., None] | None = None,
        *,
        blocking: bool = False,
    ) -> None:
        if self.socket.state() != QAbstractSocket.SocketState.ConnectedState:
            raise RuntimeError("Not connected to the JSONRPC server.")
        rpcObject: RpcObject = {
            "method": method,
            "params": args,
            "jsonrpc": "2.0",
        }
        if callback_result:
            rpcObject["id"] = self.nextid
            self.callbacks_result[self.nextid] = callback_result
            if callback_error:
                self.callbacks_error[self.nextid] = callback_error
            self.nextid += 1
        self._logger.debug("Sending JSONRPC object %s", rpcObject)
        self.socket.write(json.dumps(rpcObject).encode('utf8') + b'\n')
        if blocking:
            self.socket.waitForBytesWritten()
