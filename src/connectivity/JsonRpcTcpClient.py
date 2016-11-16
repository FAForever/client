from PyQt4.QtNetwork import QTcpSocket, QAbstractSocket
from PyQt4 import QtCore

import json

from decorators import with_logger


# This class is just a stub that works for now:
# TODO: a lot of error checking and JSON stream parsing would be nice instead of parsing individual lines only
@with_logger
class JsonRpcTcpClient(object):
    def __init__(self, host, port, requestHandlerInstance):
        self._socket = QTcpSocket()
        self._socket.connectToHost(host, port)
        self._socket.readyRead.connect(self._onData)
        self._requestHandlerInstance = requestHandlerInstance
        self._nextid = 1
        if not self._socket.waitForConnected(100):
            raise RuntimeError("Error connecting to the JSON RPC server on {}:{}".format(host, port))

    def close(self):
        self._socket.close()

    def _parseRequest(self, request):
        try:
            m = getattr(self._requestHandlerInstance, request["method"])
            if "params" in request and len(request["params"]) > 0:
                result = m(*request["params"])
            else:
                result = m()

            # we do not only have a notification, but a request which awaits a response
            if "id" in request:
                responseObject = {
                    "id": request["id"],
                    "result": result,
                    "jsonrpc": "2.0"
                }
                self._socket.write(json.dumps(responseObject))
        except AttributeError:
            if "id" in request:
                responseObject = {
                    "id": request["id"],
                    "error": "no such method",
                    "jsonrpc": "2.0"
                }
                self._socket.write(json.dumps(responseObject))

    def _parseResponse(self, response):
        if "error" in response:
            self._lastError = response["error"]
            try:
                del self._lastResponse
            except AttributeError:
                pass
        elif "result" in response:
            self._lastResponse = response["result"]
            try:
                del self._lastError
            except AttributeError:
                pass

    @QtCore.pyqtSlot()
    def _onData(self):
        while self._socket.canReadLine():
            data = str(self._socket.readLine())
            try:
                request = json.loads(data)
                # is this a request?
                if "method" in request:
                    self._parseRequest(request)
                # this is only a response
                else:
                    self._parseResponse(request)
            except ValueError:
                self._logger.error("parse failed {}".format(data))

    def call(self, method, args=[]):
        if self._socket.state() != QAbstractSocket.ConnectedState:
            raise RuntimeError("Not connected to the JSONRPC server.")
        rpcObject = {
            "id": self._nextid,
            "method": method,
            "params": args,
            "jsonrpc": "2.0"
        }
        self._nextid += 1
        self._logger.debug("sending JSONRPC object {}".format(rpcObject))
        self._socket.write(json.dumps(rpcObject))
        self._socket.waitForBytesWritten(100)
        self._socket.waitForReadyRead(100)
        if hasattr(self, "_lastError"):
            raise RuntimeError("The call to {0} returned an error: {1!s}".format(method, self._lastError))
        return self._lastResponse
