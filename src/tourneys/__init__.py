from PyQt4 import QtCore
from PyQt4 import QtWebKit
import logging

logger = logging.getLogger("faf.tourneys")
logger.setLevel(logging.DEBUG)

from _tournamentswidget import TournamentsWidget as Tourneys