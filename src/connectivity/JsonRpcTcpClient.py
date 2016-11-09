from PyQt4.QtNetwork import QTcpSocket, QAbstractSocket
from PyQt4 import QtCore
from PyQt4.QtCore import QObject

import json

from decorators import with_logger

@with_logger
class JsonRpcTcpClient(QObject):
    def __init__(self, request_handler_instance):
        QObject.__init__(self)
        self.socket = QTcpSocket()
        self.connectionAttempts = 1
        self.socket.readyRead.connect(self.onData)
        self.socket.error.connect(self.onSocketError)
        self.request_handler_instance = request_handler_instance
        self.nextid = 1
        self.callbacks_result = {}
        self.callbacks_error = {}
        self.socket.waitForConnected(3000)
        self.buffer = ''

    def connect(self, host, port):
        self.host = host
        self.port = port
        self.socket.connectToHost(host, port)

    @QtCore.pyqtSlot(QAbstractSocket.SocketError)
    def onSocketError(self, error):
        if (error == QAbstractSocket.ConnectionRefusedError):
            self.socket.connectToHost(self.host, self.port)
            self.connectionAttempts += 1
            #self._logger.info("reconnecting to JSONRPC server {}".format(self.connectionAttempts))
        else:
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
        newData = ''
        while self.socket.bytesAvailable():
            newData += str(self.socket.readAll())

        # this seems to be a new notification, which invalidates out buffer. This may happen on malformed JSON data
        if newData.startswith("{\"jsonrpc\":\"2.0\""):
            if len(self.buffer) > 0:
                self._logger.error("parse error: discarding old possibly malformed buffer data {}".format(self.buffer))
            self.buffer = newData
        else:
            self.buffer += newData
        self.buffer = self.processBuffer(self.buffer.strip())

    #from https://github.com/joncol/jcon-cpp/blob/master/src/jcon/json_rpc_endpoint.cpp#L107
    def processBuffer(self, buf):
        if len(buf) == 0:
            return ''
        if not buf.startswith('{'):
            self._logger.error("parse error: buffer expected to start {{: {}".format(buf))
            return ''
        in_string = False
        brace_nesting_level = 0
        for i, c in enumerate(buf):
            if c == '"':
                in_string = not in_string

            if not in_string:
                if c == '{':
                    brace_nesting_level += 1
                if c == '}':
                    brace_nesting_level -= 1
                    if brace_nesting_level < 0:
                        self._logger.error("parse error: brace_nesting_level < 0: {}".format(buf))
                        return ''
                    if brace_nesting_level == 0:
                        complete_json_buf = buf[:i+1]
                        remaining_buf = buf[i+1:]
                        try:
                            request = json.loads(complete_json_buf)
                        except ValueError:
                            self._logger.error("json.loads failed for {}".format(complete_json_buf))
                            return ''
                        # is this a request?
                        if "method" in request:
                            self.parseRequest(request)
                        # this is only a response
                        else:
                            self.parseResponse(request)
                        return self.processBuffer(remaining_buf.strip())
        return buf

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
