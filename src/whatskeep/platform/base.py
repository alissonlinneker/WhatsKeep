"""Abstract base class for platform-specific daemon installers."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseDaemonInstaller(ABC):
    """Interface that every platform daemon installer must implement."""

    @abstractmethod
    def install(self) -> None:
        """Install the daemon/service for the current platform."""

    @abstractmethod
    def uninstall(self) -> None:
        """Remove the daemon/service."""

    @abstractmethod
    def start(self) -> None:
        """Start the daemon."""

    @abstractmethod
    def stop(self) -> None:
        """Stop the daemon."""

    @abstractmethod
    def is_running(self) -> bool:
        """Check if the daemon is currently running."""

    @abstractmethod
    def status(self) -> dict:
        """Return status info dict: running, pid, uptime, last_run, etc."""
