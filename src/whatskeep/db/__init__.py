"""WhatsApp database readers — auto-detect platform and return correct reader."""

from __future__ import annotations

import platform
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from whatskeep.db.base import BaseDBReader


def get_db_reader() -> BaseDBReader | None:
    """Return the appropriate DB reader for the current platform, or None if unsupported."""
    system = platform.system()
    if system == "Darwin":
        from whatskeep.db.macos import MacOSDBReader

        return MacOSDBReader()
    if system == "Windows":
        from whatskeep.db.windows import WindowsDBReader

        return WindowsDBReader()
    if system == "Linux":
        from whatskeep.db.linux import LinuxDBReader

        return LinuxDBReader()
    return None
