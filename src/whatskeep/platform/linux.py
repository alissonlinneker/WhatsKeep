"""Linux daemon installer using systemd user units."""

from __future__ import annotations

import contextlib
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from loguru import logger

from whatskeep.platform.base import BaseDaemonInstaller

_SERVICE_NAME = "whatskeep"
_UNIT_DIR = Path.home() / ".config" / "systemd" / "user"
_UNIT_PATH = _UNIT_DIR / f"{_SERVICE_NAME}.service"


class LinuxDaemonInstaller(BaseDaemonInstaller):
    """Manage a systemd user service for WhatsKeep."""

    def __init__(self) -> None:
        self._service_name: str = _SERVICE_NAME
        self._unit_path: Path = _UNIT_PATH

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def install(self) -> None:
        """Write the systemd unit file, reload the daemon, and enable the service."""
        unit_content = self._build_unit_file()

        self._unit_path.parent.mkdir(parents=True, exist_ok=True)
        self._unit_path.write_text(unit_content, encoding="utf-8")
        logger.info(f"Unit file written to {self._unit_path}")

        try:
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info("systemd user daemon reloaded")
        except subprocess.CalledProcessError as exc:
            logger.error(f"Failed to reload daemon: {exc.stderr.strip()}")
            raise

        try:
            subprocess.run(
                ["systemctl", "--user", "enable", self._service_name],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Service '{self._service_name}' enabled")
        except subprocess.CalledProcessError as exc:
            logger.error(f"Failed to enable service: {exc.stderr.strip()}")
            raise

    def uninstall(self) -> None:
        """Disable the service and remove the unit file."""
        try:
            subprocess.run(
                ["systemctl", "--user", "disable", self._service_name],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Service '{self._service_name}' disabled")
        except subprocess.CalledProcessError as exc:
            logger.warning(
                f"Could not disable service (may not be enabled): {exc.stderr.strip()}"
            )

        if self._unit_path.exists():
            self._unit_path.unlink()
            logger.info(f"Unit file removed: {self._unit_path}")

        with contextlib.suppress(subprocess.CalledProcessError):
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=True,
                capture_output=True,
                text=True,
            )

    def start(self) -> None:
        """Start the systemd user service."""
        try:
            subprocess.run(
                ["systemctl", "--user", "start", self._service_name],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Service '{self._service_name}' started")
        except subprocess.CalledProcessError as exc:
            logger.error(f"Failed to start service: {exc.stderr.strip()}")
            raise

    def stop(self) -> None:
        """Stop the systemd user service."""
        try:
            subprocess.run(
                ["systemctl", "--user", "stop", self._service_name],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Service '{self._service_name}' stopped")
        except subprocess.CalledProcessError as exc:
            logger.error(f"Failed to stop service: {exc.stderr.strip()}")
            raise

    def is_running(self) -> bool:
        """Check whether the service is currently active."""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", self._service_name],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.stdout.strip() == "active"
        except OSError:
            logger.warning("Could not execute systemctl")
            return False

    def status(self) -> dict:
        """Return a dict with status information about the service."""
        info: dict = {
            "running": self.is_running(),
            "service_name": self._service_name,
            "unit_path": str(self._unit_path),
            "unit_exists": self._unit_path.exists(),
        }

        try:
            result = subprocess.run(
                ["systemctl", "--user", "show", self._service_name,
                 "--property=ActiveState,SubState,MainPID,ExecMainStartTimestamp"],
                capture_output=True,
                text=True,
                check=False,
            )
            for line in result.stdout.splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if key == "MainPID" and value != "0":
                        info["pid"] = value
                    elif key == "ActiveState":
                        info["active_state"] = value
                    elif key == "SubState":
                        info["sub_state"] = value
                    elif key == "ExecMainStartTimestamp" and value:
                        info["started_at"] = value
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

    def _build_unit_file(self) -> str:
        """Build the systemd unit file content."""
        executable = self._find_executable()

        if executable == sys.executable:
            exec_start = f"{sys.executable} -m whatskeep run --watch"
        else:
            exec_start = f"{executable} run --watch"

        return textwrap.dedent(f"""\
            [Unit]
            Description=WhatsKeep — WhatsApp media organizer
            After=default.target

            [Service]
            Type=simple
            ExecStart={exec_start}
            Restart=on-failure
            RestartSec=10
            Environment=PYTHONUNBUFFERED=1

            [Install]
            WantedBy=default.target
        """)
