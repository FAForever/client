import logging

# Do not remove - promoted widget, py2exe does not include it otherwise
from client.theme_menu import ThemeMenu

from ._clientwindow import ClientWindow

__all__ = (
    "ThemeMenu",
)

logger = logging.getLogger(__name__)

instance = ClientWindow()
