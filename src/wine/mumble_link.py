#-------------------------------------------------------------------------------
# Copyright (c) 2015 Igor Kotrasinski.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#-------------------------------------------------------------------------------

# This code is a stub mumble_link interface that forwards calls through a socket
# to a python script outside wine that passes it to the linux Mumble.
#
# Only calls used in the main code are implemented here, but all of them should
# be implementable in the same fashion, since they only pass simple types.

import socket
import wine

mumble_socket = None
prefix = ""
helper_running = False
dead = False

def launch_helper():
    """
    Launches a helper script outside wine to pass calls to.

    Since (I believe) we have no way to monitor its status, we assume that
    the script either fails to launch immediately and can't be fixed or works
    fine until FAF exits. For this reason we will only ever try to launch it once.
    """

    global helper_running
    if !helper_running:
        subprocess.call(["cmd", "/c", "start", "/unix", wine.FAFpath + "/FAF_wine_mumble_helper"])
        helper_running = True
    return _link()

def _link():
    global mumble_socket
    local = "127.0.0.1"
    port = 6113
    timeout = 3

    mumble_socket = socket.socket()
    try:
        mumble_socket.bind((local, port))
    except socket.error:
        return False
    mumble_socket.settimeout(3) # TODO - tweak, this may freeze ui for a moment

    try:
        mumble_socket.connect()
    except socket.timeout:
        return False

    mumble_socket.settimeout(1) # TODO - tweak
    return True

def _sendstr(socket, string):
    # We can't use sendall with a non-blocking socket
    sent = 0
    data = string + '\x00'
    while (sent < data.len())
        sent += socket.send(data[sent:])

def _recvstr(socket):
    global prefix
    while not '\x00' in prefix:
        data = socket.recv(1 < 16)
        if not data:
            raise socket.error
        prefix += data
        res = (prefix[:prefix.find('\x00')], prefix[prefix.find('\x00') + 1:])
    prefix = res[1]
    return res[0]

def die_gracefully(fn):

    def new_fn(*args, **kwargs):
        global dead
        if dead:
            return -1 # better feed garbage than kill entire FAF
        try:
            return fn(*args, **kwargs)
        except socket.error, socket.timeout:
            dead = True
            return -1

    return new_fn

@die_gracefully
def get_version():
    global mumble_socket
    _sendstr(mumble_socket, "get_version")
    return _recvstr(mumble_socket)

@die_gracefully
def setup(plugin, desc):
    global mumble_socket
    _sendstr(mumble_socket, "setup")
    _sendstr(mumble_socket, plugin)
    _sendstr(mumble_socket, desc)
    return int(_recvstr(mumble_socket))

@die_gracefully
def set_identity(identity):
    global mumble_socket
    _sendstr(mumble_socket, "set_identity")
    _sendstr(mumble_socket, identity)
    return int(_recvstr(mumble_socket, identity))
