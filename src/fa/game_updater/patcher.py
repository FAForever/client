import logging

from PyQt6.QtCore import QFile

from src.qt.utils import qopen

logger = logging.getLogger(__name__)


class FAPatcher:
    version_addresses = (0xd3d40, 0x47612d, 0x476666)

    @staticmethod
    def read_version(path: str) -> int:
        with qopen(path, QFile.OpenModeFlag.ReadOnly) as file:
            if not file.isOpen():
                return -1
            file.seek(FAPatcher.version_addresses[0])
            return int.from_bytes(file.read(4), "little")

    @staticmethod
    def patch(path: str, version: int) -> bool:
        with qopen(path, QFile.OpenModeFlag.ReadWrite) as file:
            if not file.isOpen():
                return False
            for address in FAPatcher.version_addresses:
                file.seek(address)
                file.write(version.to_bytes(4, "little"))
        logger.info("Patched %s to version %d", path, version)
        return True
