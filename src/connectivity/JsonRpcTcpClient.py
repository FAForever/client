from PyQt4.QtNetwork import QTcpSocket, QAbstractSocket
from PyQt4 import QtCore

import json

from decorators import with_logger


# This class is just a stub that works for now:
# TODO: a lot of error checking and JSON stream parsing would be nice instead of parsing individual lines only
@with_logger
class JsonRpcTcpClient(object):
    def __init__(self, host, port, request_handler_instance):
        self.socket = QTcpSocket()
        self.socket.connectToHost(host, port)
        self.socket.readyRead.connect(self.onData)
        self.socket.error.connect(self.onSocketError)
        self.request_handler_instance = request_handler_instance
        self.nextid = 1
        self.callbacks_result = {}
        self.callbacks_error = {}
        self.socket.waitForConnected(300)

    @QtCore.pyqtSlot(QAbstractSocket.SocketError)
    def onSocketError(self, error):
        raise RuntimeError("Connection error to JSON RPC server: {} ({})".format(self.socket.errorString(), error))

    def close(self):
        self.socket.close()

    def parseRequest(self, request):
        try:
            m = getattr(self.request_handler_instance, request["method"])
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
                self.socket.write(json.dumps(responseObject))
        except AttributeError:
            if "id" in request:
                responseObject = {
                    "id": request["id"],
                    "error": "no such method",
                    "jsonrpc": "2.0"
                }
                self.socket.write(json.dumps(responseObject))

    def parseResponse(self, response):
        if "error" in response:
            self._logger.error("response error {}".format(response))
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
    def onData(self):
        while self.socket.canReadLine():
            data = str(self.socket.readLine())
            try:
                request = json.loads(data)
                # is this a request?
                if "method" in request:
                    self.parseRequest(request)
                # this is only a response
                else:
                    self.parseResponse(request)
            except ValueError:
                self._logger.error("parse failed {}".format(data))

    def call(self, method, args=[], callback_result=None, callback_error=None):
        if self.socket.state() != QAbstractSocket.ConnectedState:
            raise RuntimeError("Not connected to the JSONRPC server.")
        rpcObject = {
            "method": method,
            "params": args,
            "jsonrpc": "2.0"
        }
        if callback_result:
            rpcObject["id"] = self.nextid
            self.callbacks_result[self.nextid] = callback_result
            if callback_error:
                self.callbacks_error[self.nextid] = callback_error
            self.nextid += 1
        self._logger.debug("sending JSONRPC object {}".format(rpcObject))
        self.socket.write(json.dumps(rpcObject) + '\n')
