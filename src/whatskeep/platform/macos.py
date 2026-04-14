"""macOS daemon installer using launchd / launchctl."""

from __future__ import annotations

import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

from loguru import logger

from whatskeep.platform.base import BaseDaemonInstaller

_LABEL = "com.whatskeep.agent"
_PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{_LABEL}.plist"


class MacOSDaemonInstaller(BaseDaemonInstaller):
    """Manage a launchd agent that watches the Downloads folder for WhatsApp files."""

    def __init__(self) -> None:
        self._label: str = _LABEL
        self._plist_path: Path = _PLIST_PATH

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def install(self) -> None:
        """Generate a launchd plist and load it via launchctl."""
        plist = self._build_plist()

        self._plist_path.parent.mkdir(parents=True, exist_ok=True)
        with self._plist_path.open("wb") as fh:
            plistlib.dump(plist, fh)
        logger.info(f"Plist written to {self._plist_path}")

        try:
            subprocess.run(
                ["launchctl", "load", str(self._plist_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Agent '{self._label}' loaded successfully")
        except subprocess.CalledProcessError as exc:
            logger.error(f"Failed to load agent: {exc.stderr.strip()}")
            raise

    def uninstall(self) -> None:
        """Unload the launchd agent and remove the plist file."""
        try:
            subprocess.run(
                ["launchctl", "unload", str(self._plist_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Agent '{self._label}' unloaded")
        except subprocess.CalledProcessError as exc:
            logger.warning(f"Could not unload agent (may not be loaded): {exc.stderr.strip()}")

        if self._plist_path.exists():
            self._plist_path.unlink()
            logger.info(f"Plist removed: {self._plist_path}")

    def start(self) -> None:
        """Start the launchd agent."""
        try:
            subprocess.run(
                ["launchctl", "start", self._label],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Agent '{self._label}' started")
        except subprocess.CalledProcessError as exc:
            logger.error(f"Failed to start agent: {exc.stderr.strip()}")
            raise

    def stop(self) -> None:
        """Stop the launchd agent."""
        try:
            subprocess.run(
                ["launchctl", "stop", self._label],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Agent '{self._label}' stopped")
        except subprocess.CalledProcessError as exc:
            logger.error(f"Failed to stop agent: {exc.stderr.strip()}")
            raise

    def is_running(self) -> bool:
        """Check whether the agent is currently loaded and running."""
        try:
            result = subprocess.run(
                ["launchctl", "list"],
                capture_output=True,
                text=True,
                check=False,
            )
            return _LABEL in result.stdout
        except OSError:
            logger.warning("Could not execute launchctl")
            return False

    def status(self) -> dict:
        """Return a dict with status information about the agent."""
        running = self.is_running()
        info: dict = {
            "running": running,
            "label": self._label,
            "plist_path": str(self._plist_path),
            "plist_exists": self._plist_path.exists(),
        }

        if running:
            try:
                result = subprocess.run(
                    ["launchctl", "list", self._label],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                for line in result.stdout.splitlines():
                    if "PID" in line:
                        parts = line.split("=")
                        if len(parts) == 2:
                            info["pid"] = parts[1].strip()
                    if "LastExitStatus" in line:
                        parts = line.split("=")
                        if len(parts) == 2:
                            info["last_exit_status"] = parts[1].strip()
            except OSError:
                pass

        return info

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_executable(self) -> str:
        """Resolve the path to the ``whatskeep`` executable."""
        path = shutil.which("whatskeep")
        if path:
            return path
        return sys.executable

    def _build_plist(self) -> dict:
        """Build the launchd plist dictionary."""
        executable = self._find_executable()

        program_args: list[str]
        if executable == sys.executable:
            program_args = [sys.executable, "-m", "whatskeep", "run", "--watch"]
        else:
            program_args = [executable, "run", "--watch"]

        return {
            "Label": self._label,
            "ProgramArguments": program_args,
            "RunAtLoad": True,
            "KeepAlive": True,
            "StandardOutPath": str(Path.home() / ".whatskeep" / "whatskeep.log"),
            "StandardErrorPath": str(Path.home() / ".whatskeep" / "whatskeep.err"),
        }
