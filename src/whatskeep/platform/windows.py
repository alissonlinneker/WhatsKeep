"""Windows daemon installer using Task Scheduler (schtasks)."""

from __future__ import annotations

import shutil
import subprocess
import sys

from loguru import logger

from whatskeep.platform.base import BaseDaemonInstaller

_TASK_NAME = "WhatsKeep"


class WindowsDaemonInstaller(BaseDaemonInstaller):
    """Manage a Windows scheduled task that periodically runs WhatsKeep."""

    def __init__(self) -> None:
        self._task_name: str = _TASK_NAME

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def install(self) -> None:
        """Create a scheduled task that runs on login and repeats every 60 seconds."""
        executable = self._find_executable()

        if executable == sys.executable:
            command = f'"{sys.executable}" -m whatskeep run'
        else:
            command = f'"{executable}" run'

        try:
            subprocess.run(
                [
                    "schtasks",
                    "/create",
                    "/tn", self._task_name,
                    "/tr", command,
                    "/sc", "ONLOGON",
                    "/ri", "1",  # Repeat interval: 1 minute
                    "/du", "9999:59",  # Duration: effectively infinite
                    "/f",  # Force overwrite if exists
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Task '{self._task_name}' created successfully")
        except subprocess.CalledProcessError as exc:
            logger.error(f"Failed to create task: {exc.stderr.strip()}")
            raise

    def uninstall(self) -> None:
        """Delete the scheduled task."""
        try:
            subprocess.run(
                ["schtasks", "/delete", "/tn", self._task_name, "/f"],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Task '{self._task_name}' deleted")
        except subprocess.CalledProcessError as exc:
            logger.warning(f"Could not delete task (may not exist): {exc.stderr.strip()}")

    def start(self) -> None:
        """Manually trigger the scheduled task."""
        try:
            subprocess.run(
                ["schtasks", "/run", "/tn", self._task_name],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Task '{self._task_name}' started")
        except subprocess.CalledProcessError as exc:
            logger.error(f"Failed to start task: {exc.stderr.strip()}")
            raise

    def stop(self) -> None:
        """End the running task."""
        try:
            subprocess.run(
                ["schtasks", "/end", "/tn", self._task_name],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Task '{self._task_name}' stopped")
        except subprocess.CalledProcessError as exc:
            logger.error(f"Failed to stop task: {exc.stderr.strip()}")
            raise

    def is_running(self) -> bool:
        """Check whether the task is currently running."""
        try:
            result = subprocess.run(
                ["schtasks", "/query", "/tn", self._task_name, "/fo", "CSV", "/nh"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                return False
            return "Running" in result.stdout
        except OSError:
            logger.warning("Could not execute schtasks")
            return False

    def status(self) -> dict:
        """Return a dict with status information about the scheduled task."""
        info: dict = {
            "running": False,
            "task_name": self._task_name,
        }

        try:
            result = subprocess.run(
                ["schtasks", "/query", "/tn", self._task_name, "/fo", "LIST", "/v"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                info["exists"] = False
                return info

            info["exists"] = True
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("Status:"):
                    status_value = line.split(":", 1)[1].strip()
                    info["status"] = status_value
                    info["running"] = status_value == "Running"
                elif line.startswith("Last Run Time:"):
                    info["last_run"] = line.split(":", 1)[1].strip()
                elif line.startswith("Last Result:"):
                    info["last_result"] = line.split(":", 1)[1].strip()
                elif line.startswith("Next Run Time:"):
                    info["next_run"] = line.split(":", 1)[1].strip()
        except OSError:
            info["exists"] = False

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
