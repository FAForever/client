#-------------------------------------------------------------------------------
# Copyright (c) 2012 Gael Honorez.
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





# Initialize logging system
import logging
logger = logging.getLogger("faf.chat")
logger.setLevel(logging.INFO)

def user2name(user):
    return (user.split('!')[0]).strip('&@~%+')
    
    
#def user2host(user):
#    return user.split('!')[1]
        

#def host2country(host):
#    ip = socket.gethostbyname(host)
#    country = urllib2.urlopen("http://api.hostip.info/country.php?ip=%s" % ip, None, 1000).read()
#    logger.debug("Resolved country for " + host + " as " + country)    
#    return country
            


from _chatwidget import ChatWidget as Lobby

# CAVEAT: DO NOT REMOVE! These are promoted widgets and py2exe wouldn't include them otherwise
from chat.chatlineedit import ChatLineEdit
