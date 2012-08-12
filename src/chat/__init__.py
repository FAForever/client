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
