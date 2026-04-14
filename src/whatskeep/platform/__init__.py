"""Platform-specific daemon installers — auto-detect OS and return correct installer."""

from __future__ import annotations

import platform as _platform
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from whatskeep.platform.base import BaseDaemonInstaller


def get_daemon_installer() -> BaseDaemonInstaller | None:
    """Return the appropriate daemon installer for the current platform."""
    system = _platform.system()
    if system == "Darwin":
        from whatskeep.platform.macos import MacOSDaemonInstaller

        return MacOSDaemonInstaller()
    if system == "Windows":
        from whatskeep.platform.windows import WindowsDaemonInstaller

        return WindowsDaemonInstaller()
    if system == "Linux":
        from whatskeep.platform.linux import LinuxDaemonInstaller

        return LinuxDaemonInstaller()
    return None
