#-------------------------------------------------------------------------------
# Copyright (c) 2013 Gael Honorez.
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


from PyQt4 import QtCore, QtGui, QtNetwork

import functools

import logging
import time
import random
import json

from config import Settings

FAF_PROXY_HOST = Settings.get('HOST', 'PROXY')
FAF_PROXY_PORT = Settings.get('PORT', 'PROXY')

UNIT16 = 8


class proxies(QtCore.QObject):
    __logger = logging.getLogger(__name__)

    def __init__(self, parent = None):
        super(proxies, self).__init__(parent)

        self.client = parent

        self.reconn_escape_prefix = QtCore.QByteArray.fromHex("ffffffffffffffffffffffffffffff");
        self.p2p_game_launched = 0
        self.p2p_bottleneck_ = 0
        self.p2p_state_debug_timestamp = time.time()
        self.P2P_DIRECT_RECONNECT_ATTEMPTS = 30
        self.P2P_RECONNECT_RATELIMIT = 5
        self.P2P_TAG_OFFER_RATELIMIT = 5
        self.P2P_MAX_TAG_OFFERS = 10
        self.P2P_INDIRECT_RECONNECT_AFTER = 5
        self.P2P_INDIRECT_RECONNECT_ATTEMPTS = 20
        # change this back after enabling P2PReconnect server message
        self.p2p_proxy_enable = 1

        self.p2p_want_dump_state = 0

        self.proxy_lastdata = time.time()
        self.proxies = {}
        self.proxiesDestination = {}
        port = 12000
        errored = False
        for i in range(11) :
            port = port + 1
            self.proxies[i] = QtNetwork.QUdpSocket(self)
            if not self.proxies[i].bind(QtNetwork.QHostAddress.LocalHost, port) :
                self.__logger.warn("Can't bind socket %i" % i)
                errored = True
            else :
                self.__logger.info("binding socket %i on port %i" % (i, self.proxies[i].localPort()))
                self.proxies[i].readyRead.connect(functools.partial(self.processPendingDatagrams, i))
                self.proxiesDestination[i] = None
        if errored:
            QtGui.QMessageBox.warning(self.client, "Cannot use proxy server", "FAF is unable to bind the port <b>12000 to 12011 on TCP</b>.<br>Please check your firewall settings.<br><b>You may experience connections problems until it's fixed.</b>")

        self.proxySocket = QtNetwork.QTcpSocket(self)
        self.proxySocket.connected.connect(self.connectedProxy)
        self.proxySocket.readyRead.connect(self.readData)
        self.proxySocket.disconnected.connect(self.disconnectedFromProxy)

        self.blockSize = 0
        self.uid = None
        self.canClose = False
        self.testedPortsAmount = {}
        self.testedPorts = []
        self.testedLoopbackAmount = {}
        self.testedLoopback = []
        self.testing = False

    def testingProxy(self):
        self.testing = True
        self.testedPortsAmount = {}
        self.testedPorts = []
        self.testedLoopbackAmount = {}
        self.testedLoopback = []

    def stopTesting(self):
        self.testing = False
        self.testedPortsAmount = {}
        self.testedPorts = []
        self.testedLoopbackAmount = {}
        self.testedLoopback = []

    def setUid(self, uid):
        self.uid = uid

    def connectedProxy(self):
        ''' Setting the socket option correctly'''
        # we want the low delay for performance.
        self.__logger.debug("Setting low delay on socket.")
        self.proxySocket.setSocketOption(QtNetwork.QAbstractSocket.LowDelayOption, 1)

    def connectToProxy(self):
        self.proxySocket.connectToHost(FAF_PROXY_HOST, FAF_PROXY_PORT)
        if self.proxySocket.waitForConnected(10000):
            self.__logger.info("Connected to proxy server " + self.proxySocket.peerName() + ":" + str(self.proxySocket.peerPort()))

        self.canClose = False
        self.testedPorts = []
        self.testedLoopback = []
        self.sendUid()

    def bindSocket(self, port, uid):
        self.proxiesDestination[port] = uid
        self.__logger.debug("Binding socket " + str(port) + " (local port : " + str(self.proxies[port].localPort()) + ") for uid " + str(uid))
        if not self.proxySocket.state() == QtNetwork.QAbstractSocket.ConnectedState :
            self.connectToProxy()
        return self.proxies[port].localPort()

    def p2p_dump_peer(self, p2p):
        self.__logger.debug("uid={0:6d} pub={1:23s} port={2:5d} last_pub={3:4d} toffer={4:2d} tack={5:1d} ratt={6:2d} iratt={7:2d} conn={8:1d} reconning: {9:1d}".format(p2p['peeruid'], p2p['public_addr'] + ":" + str(p2p['public_port']), p2p['local_port'], int(time.time() - p2p['pub_last_recv']), p2p['num_tag_offers'], p2p['our_reconn_tag_ack'], p2p['reconnect_attempts'], p2p['ind_reconnect_attempts'], p2p['connected'], p2p['currently_reconnecting']));

    def p2p_all_disconnected_time_min(self):
        min_t = 100000
        for k, p2p in self.p2p_by_public.iteritems():
            if self.p2p_is_fully_connected(p2p):
                t = time.time() - p2p['pub_last_recv'];
                if t < min_t: min_t = t
        return min_t

    def p2p_is_fully_connected(self, p2p):
        return p2p['our_reconn_tag_ack'] and not p2p['reconnect_attempts'] and p2p['peeruid'] and p2p['connected'] and time.time() - p2p['pub_last_recv'] < 10

    def p2p_is_eligible_for_reconnect(self, p2p):
        return p2p['our_reconn_tag_ack'] and p2p['peeruid'] and p2p['connected']

    def p2p_bottleneck(self):
        self.p2p_bottleneck_ = 1

    def p2p_bottleneck_cleared(self):
        self.p2p_bottleneck_ = 0

    def p2p_try_reconnect(self, p2p, by_intermediate):
        self.p2p_want_dump_state = 1
        psock = self.p2p_public_sock
        if 'our_reconn_tag' in p2p and p2p['our_reconn_tag_ack']:
            stamp_name = 'try_reconn_timestamp'
            if by_intermediate:
                stamp_name = 'try_ind_reconn_timestamp'

            if p2p[stamp_name] + self.P2P_RECONNECT_RATELIMIT < time.time():
                if by_intermediate:
                    self.__logger.info("attempting reconnect by intermediary to " + p2p['public_addr'] + ":" + str(p2p['public_port']))
                    # we only send one reconnect-by-intermediary message
                    # at a time, because the peer will broadcast to
                    # all his peers
                    count_to = p2p['reconnect_attempts'] - self.P2P_INDIRECT_RECONNECT_AFTER
                    count = 0
                    # we do the antipattern here, and iterate instead
                    # of indexing, because p2p_by_public isnt guaranteed
                    # to only contain active game connections (since
                    # we are currently attempting reconnects)
                    while count <= count_to:
                        for dest_inter, p2p_inter in self.p2p_by_public.iteritems():
                            if self.p2p_is_fully_connected(p2p_inter):
                                if count == count_to:
                                    p = QtCore.QByteArray(self.reconn_escape_prefix)
                                    p.append(chr(17))
                                    p.append(p2p['our_reconn_tag'])
                                    psock.writeDatagram(p, p2p_inter['public_addr_qt'], p2p_inter['public_port'])
                                    p2p['ind_reconnect_attempts'] += 1
                                    count += 1
                                    break
                                count += 1
                        if count == 0:
                            break
                else:
                    self.__logger.info("attempting to reconnect to " + p2p['public_addr'] + ":" + str(p2p['public_port']))
                    p = QtCore.QByteArray(self.reconn_escape_prefix)
                    p.append(chr(23))  # 23 = ask peer to update address
                    p.append(p2p['our_reconn_tag'])
                    psock.writeDatagram(p, p2p['public_addr_qt'], p2p['public_port'])
                    p2p['reconnect_attempts'] += 1

                p2p[stamp_name] = time.time()


    # forward all datagrams to the remote address:port associated with this local port
    def p2p_read_local(self, p2p):
        psock = self.p2p_public_sock
        lsock = p2p['local_sock']
        while lsock.hasPendingDatagrams():
            size = lsock.pendingDatagramSize()
            dgram, _, _ = lsock.readDatagram(size)
            psock.writeDatagram(dgram, p2p['public_addr_qt'], p2p['public_port'])

        # no incoming traffic (from public_sock) for 10 seconds (for all p2p peers) is trouble
        # this condition is true on the peer that got a new IP address...it will still be sending
        # messages to former peers, but will not receive any
        # in a 1v1 situation, both will want to reconnect (only traffic that is forwarded
        # to FA.exe counts and that will not happen in a 1v1 on either side)
        # if we are the healthy peer in a 1v1, the remote never ack'd our tag on the
        # new connection, and thus our reconn request will go to the old IP and will not
        # matter
        #
        # we also only act if FA.exe reports bottleneck

        if time.time() - p2p['pub_last_recv'] > 10 and self.p2p_bottleneck_:
            if p2p['currently_reconnecting']:
                if p2p['reconnect_attempts'] >= self.P2P_INDIRECT_RECONNECT_AFTER:
                    self.p2p_try_reconnect(p2p, 1)
                if p2p['reconnect_attempts'] < self.P2P_DIRECT_RECONNECT_ATTEMPTS:
                    self.p2p_try_reconnect(p2p, 0)
            elif self.p2p_game_launched and self.p2p_all_disconnected_time_min() > 10:
                for k, p2p in self.p2p_by_public.iteritems():
                    if self.p2p_is_eligible_for_reconnect(p2p):
                        p2p['reconnect_attempts'] = 0
                        p2p['ind_reconnect_attempts'] = 0
                        p2p['currently_reconnecting'] = 1
                        self.p2p_try_reconnect(p2p, 0)
                self.p2p_successful_reconnects = 0
        if self.p2p_want_dump_state and time.time() - self.p2p_state_debug_timestamp > 20 or time.time() - self.p2p_state_debug_timestamp > 180:
            self.p2p_state_debug_timestamp = time.time()
            for dbg_dest, dbg_p2p in self.p2p_by_public.iteritems():
                self.p2p_dump_peer(dbg_p2p);
            self.p2p_want_dump_state = 0

    def p2p_handle_public(self, dgram, host, port, p2p):
        psock = self.p2p_public_sock
        if dgram.startsWith(self.reconn_escape_prefix):
            hexdump = ''.join([hex(ord(dgram[i])).replace('0x', ' ') for i in range(0, len(dgram))])
            self.__logger.debug("recv prefixed dgram " + hexdump)
            # one of our prefixed messages
            if dgram.at(15) == chr(1) or dgram.at(15) == chr(11):
                # if chr(1) their tag offer, we send ack if we dont have tag or tag matches
                # if chr(11) their tag confirm request, we only send ack if tag matches

                # in case we got a new IP and FA.exe keeps sending to the peer,
                # remote thinks we are a new connection
                # and will try to send us his tag. we must refuse, since their temp connection
                # will cease to exist after our reconn message and we want to retain the
                # original tag. only accepting the very first tag should do the trick
                theirtag = dgram.mid(16, 8)
                if 'their_reconn_tag' in p2p and p2p['their_reconn_tag'] != theirtag or dgram.at(15) == chr(11) and not 'their_reconn_tag' in p2p:
                    self.__logger.info("peer wants to send a different tag now. we ignore")
                    p = QtCore.QByteArray(self.reconn_escape_prefix)
                    p.append(chr(3))  # decline
                    p.append(theirtag)
                    psock.writeDatagram(p, host, port)
                else:
                    self.__logger.info("peer " + host.toString() + ":" + str(port) + " offers tag")
                    # but in case they send the same tag twice, we assume our ack got lost
                    p2p['their_reconn_tag'] = theirtag
                    p = QtCore.QByteArray(self.reconn_escape_prefix)
                    p.append(chr(2))  # 2 = ack tag
                    p.append(theirtag)
                    psock.writeDatagram(p, host, port)
            elif dgram.at(15) == chr(2):
                # their ack of our tag, we send nothing
                tag = dgram.mid(16, 8)

                if p2p['our_reconn_tag'] == tag:
                    self.__logger.info("peer " + host.toString() + ":" + str(port) + " acks our tag")
                    p2p['our_reconn_tag_ack'] = 1
                    p2p['num_tag_offers'] = 0
                    if p2p['reconnect_attempts']:
                        self.p2p_successful_reconnects += 1
                    p2p['reconnect_attempts'] = 0
                    p2p['currently_reconnecting'] = 0
                    self.p2p_want_dump_state = 1
                else:
                    self.__logger.error("peer " + host.toString() + ":" + str(port) + " acks a tag which we didnt send")
            elif dgram.at(15) == chr(3):
                # they decline our tag
                tag = dgram.mid(16, 8)

                if p2p['our_reconn_tag'] == tag:
                    self.__logger.info("peer " + host.toString() + ":" + str(port) + " declines our tag")
                    p2p['our_reconn_tag_declined'] = 1
                else:
                    self.__logger.info("peer " + host.toString() + ":" + str(port) + " declines a tag we did not send")
            elif dgram.at(15) == chr(17):
                # reconnect-by-intermediary message
                # we need this for udp hole punching
                # in a situation where the disconnected peer attempts to
                # reconnect to a peer whose NAT requires udp hole punching
                # the reconnect would fail, because no hole has been punched
                # for the new IP address. But in this case the disconnected peer
                # does not require hole punching, because otherwise the
                # p2p udp channel would not have been possible without a proxy
                # anyway. The disconnected peer announces his (promiscuous)
                # new IP:port to a third peer to which it already has reestablished
                # a connection, which in turn forwards it to all peers to which
                # he still has the old and good connections. the peer that
                # needs to initiate the udp hole punch gets the new IP:port via
                # this third peer. this does not work in a 1v1 where the
                # peer that does not require hole punching gets disconnected though
                # (that special case requires another third party: the server
                # and an additional mechanism). the same failure happens in a XvX where
                # the disconnected peer is the only one that did not require
                # hole punching
                #
                # the format of this message is the same as for the reconnect
                # message and the tag is the same as it would be in the reconnect
                # message. on the second leg, when the third party forwards this
                # reconnect-by-intermediary message it includes the originator IP:port
                # of this message in its reconnect-by-intermediary-2 message
                for k, p2p in self.p2p_by_public.iteritems():
                    if p2p['public_addr_qt'] != host or p2p['public_port'] != port:
                        self.__logger.info("passing on reconn-by-intermediary to " + p2p['public_addr'] + ":" + str(p2p['public_port']))
                        p = QtCore.QByteArray(self.reconn_escape_prefix)
                        p.append(chr(18))  # 18 = reconn-by-intermediary-2
                        p.append(dgram.mid(16, 8))
                        h32 = host.toIPv4Address()
                        for ii in range(4, 0, -1):
                            p.append(chr(h32 >> ii * 8 - 8 & 0xff))
                        p.append(chr(port >> 8 & 0xff))
                        p.append(chr(port & 0xff))
                        psock.writeDatagram(p, p2p['public_addr_qt'], p2p['public_port'])

            elif dgram.at(15) == chr(18):
                # reconnect-by-intermediary-2 message (see above)
                # we use the IP:port from the payload instead of the UDP header
                tag = dgram.mid(16, 8)
                sender_host32 = 0
                for i in range(0, 4):
                    sender_host32 |= ord(dgram.at(24 + i)) << (3 - i) * 8
                sender_host = QtNetwork.QHostAddress(sender_host32)
                sender_port = 0
                sender_port |= ord(dgram.at(28)) << 8
                sender_port |= ord(dgram.at(29))
                self.__logger.info("reconn-by-intermediary-2 from " + host.toString() + ":" + str(port) + " for " + sender_host.toString() + ":" + str(sender_port))
                found = 0
                update_dest_old = None
                update_dest_new = None
                for dest, p2p in self.p2p_by_public.iteritems():
                    if 'their_reconn_tag' in p2p and p2p['their_reconn_tag'] == tag:
                        found = 1
                        if p2p['public_addr_qt'] != sender_host or p2p['public_port'] != sender_port:
                            self.__logger.info("update peer from " + p2p['public_addr'] + ":" + str(p2p['public_port']) + " to " + sender_host.toString() + ":" + str(sender_port))
                            p2p['public_addr_qt'] = sender_host
                            p2p['public_addr'] = sender_host.toString()
                            p2p['public_port'] = sender_port
                            update_dest_old = dest
                            update_dest_new = sender_host.toString() + ":" + str(sender_port)
                        else:
                            self.__logger.info("ignore duplicate update")
                if not found:
                    self.__logger.error("cannot match tag to any connection...update not for us")
                if update_dest_old:
                    self.p2p_by_public[update_dest_new] = self.p2p_by_public[update_dest_old]
                    del self.p2p_by_public[update_dest_old]
                    self.p2p_want_dump_state = 1
            elif dgram.at(15) == chr(23):
                # if the tag matches our current conn we do nothing
                # this can happen if peer sends too many update messages due to network lag
                # or his IP address didnt change in the first place
                # also in a 1v1 situation, both peers experience no network traffic
                # on their public socket and both try to reconnect
                # but the reconnect message
                self.__logger.info("reconnect request from peer " + host.toString() + ":" + str(port))
                if 'their_reconn_tag' in p2p:
                    if p2p['their_reconn_tag'] == dgram.mid(16, 8):
                        self.__logger.info("but tag matches the current connection")
                        return

                # at this point we should be able to find the tag in another forwarder
                # and update this other forwarder with a new address

                update_dest_old = None
                update_dest_new = None
                for dest, p2p_other in self.p2p_by_public.iteritems():
                    if 'their_reconn_tag' in p2p_other:
                        if p2p_other['their_reconn_tag'] == dgram.mid(16, 8):
                            p2p_other['public_addr'] = host.toString()
                            p2p_other['public_addr_qt'] = host
                            p2p_other['public_port'] = port
                            update_dest_old = dest
                            update_dest_new = host.toString() + ":" + str(port)
                            break
                if update_dest_old:
                    tmp = self.p2p_by_public[update_dest_old]
                    del self.p2p_by_public[update_dest_old]

                    # now we can close the current forwarder, which was intended to be temporary anyway
                    # (implement me, for now we trust in the garbage collector)

                    self.p2p_by_public[update_dest_new] = tmp
                    self.__logger.info("p2p peer address updated sucessfully (at least we hope)")
                    self.p2p_want_dump_state = 1
                else:
                    self.__logger.error("cannot find peer address update tag among existing connections")
            else:
                self.__logger.error("unknown p2p_reconn message")
        else:
            p2p['pub_last_recv'] = time.time()
            p2p['local_sock'].writeDatagram(dgram, QtNetwork.QHostAddress.LocalHost, self.client.gamePort + 1)

            # offer tag if we are connected to peer
            #
            # during reconnect:
            # if we currently are attempting to reconnect to
            # this peer we try to get our tag acked again so as to
            # confirm that our reconnect attempt was successful
            # (we dont continue our reconnect attempts as long as
            # we continue to receive data after a successful reconnect
            # but we will reset reconnect counters after we receive
            # the new ack)
            # we leave our_reconn_tag_ack alone, because the reconnect
            # logic must have that ack for the previous connection

            if p2p['connected'] and (p2p['currently_reconnecting'] or not p2p['our_reconn_tag_ack'] and not 'our_reconn_tag_declined' in p2p):
                if 'tag_offer_timestamp' in p2p and p2p['tag_offer_timestamp'] + self.P2P_TAG_OFFER_RATELIMIT >= time.time():
                    return
                if p2p['num_tag_offers'] == self.P2P_MAX_TAG_OFFERS:
                    self.__logger.info("giving up on tag offers for " + host.toString() + ":" + str(port))
                    p2p['num_tag_offers'] += 1
                    return
                elif p2p['num_tag_offers'] > self.P2P_MAX_TAG_OFFERS:
                    return

                p2p['tag_offer_timestamp'] = time.time()
                if not 'our_reconn_tag' in p2p:
                    tag = ''.join([chr(random.randint(0, 255)) for i in range(0, 8)])
                    p2p['our_reconn_tag'] = tag
                else:
                    tag = p2p['our_reconn_tag']

                p = QtCore.QByteArray(self.reconn_escape_prefix)
                if p2p['our_reconn_tag_ack']:
                    # we only want to get an ack from a peer that acked
                    # us before
                    p.append(chr(11))  # 11 = confirm tag
                else:
                    p.append(chr(1))  # 1 = offer tag
                p.append(tag)
                self.__logger.info("sending tag to peer " + host.toString() + ":" + str(port))
                psock.writeDatagram(p, host, port)
                p2p['num_tag_offers'] += 1

    # find local socket by sender address:port and forward datagram
    def p2p_read_public(self):
        psock = self.p2p_public_sock
        while psock.hasPendingDatagrams():
            size = psock.pendingDatagramSize()
            dgram, host, port = psock.readDatagram(size)
            remote_str = host.toString() + ':' + str(port)
            if remote_str in self.p2p_by_public:
                # self.__logger.info("UDP forward " + remote_str + "->127.0.0.1:" + str(self.client.gamePort + 1))
                p2p = self.p2p_by_public[remote_str]
                self.p2p_handle_public(QtCore.QByteArray(dgram), host, port, p2p)
            else:
                # (for all scenarios)
                # hm, unexpected packet from different port now, we just create more forwarders
                # traffic from 2 different ports on 1 IP often happens during normal game launch, so we
                # just blindly forward

                # (when we have a healthy conn, but one of our peers got a new IP address)
                # if its due to legitimate reconn attempt we will see an escaped reconn message
                # on this new conn soon and then hand over the peer to the existing connection
                # with a matching tag
                # this gets mildly confusing, as we will create a new connection for udp traffic
                # from the now effectively half-open UDP connection (the disconnected peer can
                # still send traffic from his new IP address to us). our FA.exe will ignore this
                # traffic (like without any proxying). We may or may not negotiate new tags on this
                # connection with the peer, but these new tags will be forgotten after the
                # reconnect message has been processed. while our conn is temporary the remote
                # peer has to make sure he is not learning any new tags from us
                self.p2p_translate_to_local(remote_str, None)
                if remote_str in self.p2p_by_public:
                    # self.__logger.info("UDP forward " + remote_str + "->127.0.0.1:" + str(self.client.gamePort + 1))
                    p2p = self.p2p_by_public[remote_str]
                    self.p2p_handle_public(QtCore.QByteArray(dgram), host, port, p2p);
                else:
                    self.__logger.error("STILL no local forward for " + remote_str)

    def p2p_set_uid_for_peer(self, pubaddr, uid):
        if pubaddr in self.p2p_by_public:
            self.p2p_by_public[pubaddr]['peeruid'] = uid
            self.p2p_want_dump_state = 1
        else:
            self.__logger.error("request to memorize UID " + str(uid) + " for peer " + pubaddr + " but we dont know the peer")

    def p2p_set_connected_state(self, uid, connected):
        num_found = 0
        remove_pub = [ ]
        remove_loc = [ ]

        for pub, p2p in self.p2p_by_public.iteritems():
            if p2p['peeruid'] == uid:
                if not connected and p2p['connected']:
                    remove_pub.append(pub)
                    remove_loc.append(p2p['local_port'])
                p2p['connected'] = connected
                self.p2p_want_dump_state = 1
                num_found += 1
        if num_found != 1:
            self.__logger.error("request to set connected state " + str(connected) + " for UID " + str(uid) + " but we have " + str(num_found) + " connections to peer")
        for p in remove_pub:
            # rely on the garbage collector, maybe fixme
            self.__logger.info("remove p2p peer " + p);
            del self.p2p_by_public[p]
        for l in remove_loc:
            del self.p2p_by_local["127.0.0.1:" + str(l)]

    def p2p_set_game_launched(self, launching):
        self.p2p_game_launched = 1

    # address translation during lobby phase
    def p2p_translate_to_local(self, dest, relay):
        if dest in self.p2p_by_public:
            return '127.0.0.1:' + str(self.p2p_by_public[dest]['local_port'])
        else:
            p2p = { }
            p2p['relay'] = 0
            p2p['public_addr'] = dest.split(':', 1)[0]
            p2p['public_addr_qt'] = QtNetwork.QHostAddress(p2p['public_addr'])
            p2p['public_port'] = int(dest.split(':', 1)[1])
            p2p['pub_last_recv'] = time.time()
            p2p['num_tag_offers'] = 0
            lsock = p2p['local_sock'] = QtNetwork.QUdpSocket(self)
            if not lsock.bind(QtNetwork.QHostAddress.LocalHost, 0):
                self.__logger.error("cannot bind local udp socket (any port)")
                return None
            lsock.readyRead.connect(functools.partial(self.p2p_read_local, p2p))
            localport = lsock.localPort()
            p2p['local_port'] = localport
            p2p['try_reconn_timestamp'] = time.time()
            p2p['try_ind_reconn_timestamp'] = time.time()
            p2p['reconnect_attempts'] = 0
            p2p['ind_reconnect_attempts'] = 0
            p2p['our_reconn_tag_ack'] = 0
            p2p['connected'] = 0
            p2p['peeruid'] = 0
            p2p['currently_reconnecting'] = 0
            self.p2p_by_public[dest] = p2p;
            self.p2p_by_local["127.0.0.1:" + str(localport)] = p2p;
            self.__logger.info("created new p2p proxy port for " + dest + " on 127.0.0.1:" + str(localport))
            self.p2p_want_dump_state = 1
            return '127.0.0.1:' + str(localport)

    # address translation during lobby phase
    def p2p_translate_to_public(self, local):
        if local in self.p2p_by_local:
            return str(self.p2p_by_local[local]['public_addr']) + ':' + str(self.p2p_by_local[local]['public_port'])
        else:
            self.__logger.error("no public address found for " + local)
            return None

    def p2p_state_finish(self, relay):
        self.p2p_public_sock.close()
        self.p2p_by_local = { }
        self.p2p_by_public = { }
        # change back when P2PReconnect
        self.p2p_proxy_enable = 0

    def p2p_state_initialize(self, relay):
        # public p2p forward port
        self.p2p_public_sock = QtNetwork.QUdpSocket(self)
        if not self.p2p_public_sock.bind(QtNetwork.QHostAddress.Any, self.client.gamePort):
            self.__logger.error("cannot bind to port %i" % self.client.gamePort)
            errored = True
        self.p2p_public_sock.readyRead.connect(self.p2p_read_public)
        self.p2p_by_public = {}
        self.p2p_by_local = {}
        self.p2p_game_launched = 0
        self.p2p_bottleneck_ = 0
        self.p2p_proxy_enable = 1
        self.p2p_want_dump_state = 0

    def releaseSocket(self, port):
        self.proxiesDestination[port] = None

    def tranfertToUdp(self, port, packet):
        if self.testing:
            if not port in self.testedLoopbackAmount:
                self.testedLoopbackAmount[port] = 0
            if self.testedLoopbackAmount[port] < 10:
                self.testedLoopbackAmount[port] = self.testedLoopbackAmount[port] + 1
            else:
                if not port in self.testedLoopback:
                    self.__logger.info("Testing proxy : Received data from proxy on port %i" % self.proxies[port].localPort())
                    self.testedLoopback.append(port)

            if len(self.testedLoopback) == len(self.proxies):
                self.__logger.info("Testing proxy : All ports received data correctly")
                self.client.stopTesting(success = True)
                self.testing = False
        else:
            if not port in self.testedPorts:
                self.testedPorts.append(port)
                self.__logger.debug("Received data from proxy on port %i, forwarding to FA" % self.proxies[port].localPort())

            teh_port = self.client.gamePort
            if self.p2p_proxy_enable:
                teh_port += 1
            self.proxies[port].writeDatagram(packet, QtNetwork.QHostAddress.LocalHost, teh_port)

    def readData(self):
        self.proxy_lastdata = time.time()
        if self.proxySocket.isValid() :
            if self.proxySocket.bytesAvailable() == 0 :
                return
            ins = QtCore.QDataStream(self.proxySocket)
            ins.setVersion(QtCore.QDataStream.Qt_4_2)
            while ins.atEnd() == False :
                if self.proxySocket.isValid() :
                    if self.blockSize == 0:
                        if self.proxySocket.isValid() :
                            if self.proxySocket.bytesAvailable() < 4:
                                return

                            self.blockSize = ins.readUInt32()
                        else :
                            return

                    if self.proxySocket.isValid() :
                        if self.proxySocket.bytesAvailable() < self.blockSize:
                            return

                    else :
                        return
                    port = ins.readUInt16()
                    packet = ins.readQVariant()

                    self.tranfertToUdp(port, packet)

                    self.blockSize = 0

                else :
                    return
            return

    def sendUid(self, *args, **kwargs) :
        if self.uid:
            self.__logger.warn("sending our uid (%i) to the server" % self.uid)
            reply = QtCore.QByteArray()
            stream = QtCore.QDataStream(reply, QtCore.QIODevice.WriteOnly)
            stream.setVersion(QtCore.QDataStream.Qt_4_2)
            stream.writeUInt32(0)

            stream.writeUInt16(self.uid)
            stream.device().seek(0)

            stream.writeUInt32(reply.size() - 4)

            if self.proxySocket.write(reply) == -1 :
                # we may be reconnecting and dont wanna flood the logs
                pass
                # self.__logger.warn("error writing to proxy server !")

    def sendReply(self, port, uid, packet, *args, **kwargs) :
        reply = QtCore.QByteArray()
        stream = QtCore.QDataStream(reply, QtCore.QIODevice.WriteOnly)
        stream.setVersion(QtCore.QDataStream.Qt_4_2)
        stream.writeUInt32(0)

        stream.writeUInt16(port)
        stream.writeUInt16(uid)
        stream.writeQVariant(packet)
        stream.device().seek(0)

        stream.writeUInt32(reply.size() - 4)

        if self.proxySocket.write(reply) == -1 :
            # we may be reconnecting and dont wanna flood the logs
            pass
            # self.__logger.warn("error writing to proxy server !")

    def closeSocket(self):
        if self.proxySocket.state() == QtNetwork.QAbstractSocket.ConnectedState :
            self.canClose = True
            self.__logger.info("disconnecting from proxy server")
            self.proxySocket.disconnectFromHost()
            for port in self.proxies:
                self.releaseSocket(port)

    def processPendingDatagrams(self, i):
        if self.p2p_proxy_enable and self.proxy_lastdata + 10 < time.time():
            # reconnect to the proxy
            self.__logger.info("reconnecting to proxy due to no data")
            self.proxySocket.close()
            self.proxySocket = QtNetwork.QTcpSocket(self)
            self.proxySocket.connected.connect(self.connectedProxy)
            self.proxySocket.readyRead.connect(self.readData)
            self.proxySocket.disconnected.connect(self.disconnectedFromProxy)
            self.connectToProxy()
            # give it 10 seconds to get incoming data again
            self.proxy_lastdata = time.time()

        udpSocket = self.proxies[i]
        while udpSocket.hasPendingDatagrams():
            datagram, _, _ = udpSocket.readDatagram(udpSocket.pendingDatagramSize())
            if self.testing:
                if not i in self.testedPortsAmount:
                    self.testedPortsAmount[i] = 0

                if self.testedPortsAmount[i] < 10:
                    self.testedPortsAmount[i] = self.testedPortsAmount[i] + 1
                else:
                    if not i in self.testedPorts:
                        self.__logger.info("Testing proxy : Received data from FA on port %i" % self.proxies[i].localPort())
                        self.testedPorts.append(i)

                if len(self.testedPorts) == len(self.proxies):
                    self.__logger.info("Testing proxy : All ports triggered correctly")
                self.sendReply(i, 1, QtCore.QByteArray(datagram))

            else:
                if not i in self.testedLoopback:
                    self.__logger.debug("Received data from FA on port %i" % self.proxies[i].localPort())
                if self.proxiesDestination[i] != None:
                    if not i in self.testedLoopback:
                        self.testedLoopback.append(i)
                        self.__logger.debug("Forwarding packet to proxy.")
                    self.sendReply(i, self.proxiesDestination[i], QtCore.QByteArray(datagram))
                else:
                    self.__logger.warn("Unknown destination for forwarding.")

    def disconnectedFromProxy(self):
        '''Disconnection'''
        self.testedPorts = []
        self.testedLoopback = []
        self.__logger.info("disconnected from proxy server")
        if self.canClose == False:
            self.__logger.info("reconnecting to proxy server")
            self.connectToProxy()

