"""Auto-update mechanism via GitHub Releases API."""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx
from loguru import logger

from whatskeep import __version__
from whatskeep.config import get_config_dir

GITHUB_REPO = "alissonlinneker/whatskeep"
RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CHECK_FILE = "last_update_check.json"


@dataclass
class UpdateInfo:
    """Metadata about an available update."""

    current_version: str
    latest_version: str
    download_url: str | None
    changelog: str
    published_at: str
    is_newer: bool


def check_for_update() -> UpdateInfo:
    """Query GitHub Releases API for the latest version.

    Returns an :class:`UpdateInfo` describing what is available, regardless
    of whether an update is actually needed.
    """
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                RELEASES_URL,
                headers={"Accept": "application/vnd.github+json"},
            )
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning(f"Failed to check for updates: {exc}")
        return UpdateInfo(
            current_version=__version__,
            latest_version=__version__,
            download_url=None,
            changelog="",
            published_at="",
            is_newer=False,
        )

    data = resp.json()
    latest_tag: str = data.get("tag_name", "").lstrip("v")
    changelog: str = data.get("body", "")
    published: str = data.get("published_at", "")
    download_url = _pick_asset_url(data.get("assets", []))

    return UpdateInfo(
        current_version=__version__,
        latest_version=latest_tag,
        download_url=download_url,
        changelog=changelog,
        published_at=published,
        is_newer=_version_is_newer(latest_tag, __version__),
    )


def perform_update(info: UpdateInfo) -> bool:
    """Apply the update described by *info*.

    If installed via pip, runs ``pip install --upgrade whatskeep``.
    For standalone binaries, downloads the platform asset and replaces the
    current executable.

    Returns ``True`` on success.
    """
    if not info.is_newer:
        logger.info("Already up to date.")
        return False

    if _installed_via_pip():
        return _update_via_pip()

    if info.download_url:
        return _update_binary(info.download_url)

    logger.warning("No suitable update method found.")
    return False


def should_check(interval_hours: int = 24) -> bool:
    """Return ``True`` if enough time has passed since the last check."""
    state = _load_check_state()
    if not state:
        return True
    last = state.get("last_check")
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
        elapsed = datetime.now(timezone.utc) - last_dt
        return elapsed.total_seconds() > interval_hours * 3600
    except (ValueError, TypeError):
        return True


def record_check() -> None:
    """Persist the current time as the last update check."""
    path = get_config_dir() / CHECK_FILE
    data = {"last_check": datetime.now(timezone.utc).isoformat()}
    path.write_text(json.dumps(data), encoding="utf-8")


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _version_is_newer(latest: str, current: str) -> bool:
    """Simple semver comparison (major.minor.patch)."""
    try:
        lat = tuple(int(x) for x in latest.split("."))
        cur = tuple(int(x) for x in current.split("."))
        return lat > cur
    except (ValueError, AttributeError):
        return False


def _installed_via_pip() -> bool:
    """Check if whatskeep was installed via pip by inspecting its own package path."""
    try:
        import whatskeep as _pkg

        pkg_path = str(Path(_pkg.__file__).resolve())
        return "site-packages" in pkg_path or "dist-packages" in pkg_path
    except (AttributeError, TypeError):
        return False


def _update_via_pip() -> bool:
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "whatskeep"],
            check=True,
            capture_output=True,
        )
        logger.info("Updated via pip successfully.")
        return True
    except subprocess.CalledProcessError as exc:
        logger.error(f"pip upgrade failed: {exc.stderr.decode()}")
        return False


def _update_binary(url: str) -> bool:
    try:
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()

        import os

        # Verify we're not overwriting a system binary
        exe = Path(sys.executable).resolve()
        system_paths = [
            "/usr/bin", "/usr/local/bin", "/bin",  # Unix
            "C:\\Windows", "C:\\Program Files",     # Windows
        ]
        if any(str(exe).startswith(sp) for sp in system_paths):
            logger.error(
                f"Refusing to overwrite system binary: {exe}. "
                "Install whatskeep in a virtual environment or use pip."
            )
            return False

        # Download to temporary file first, then swap
        import tempfile

        tmp = Path(tempfile.mktemp(suffix=".new", dir=exe.parent))
        tmp.write_bytes(resp.content)

        # Basic integrity: reject empty or tiny downloads
        if tmp.stat().st_size < 1024:
            tmp.unlink()
            logger.error("Downloaded binary is suspiciously small — aborting.")
            return False

        if platform.system() != "Windows":
            tmp.chmod(0o755)

        # Swap: os.replace works cross-platform (atomic on same filesystem)
        backup = exe.with_suffix(".bak")
        if exe.exists():
            os.replace(str(exe), str(backup))

        os.replace(str(tmp), str(exe))

        if backup.exists():
            backup.unlink()

        logger.info("Binary updated successfully.")
        return True
    except Exception as exc:
        logger.error(f"Binary update failed: {exc}")
        backup = Path(sys.executable).resolve().with_suffix(".bak")
        if backup.exists():
            backup.rename(sys.executable)
        return False


def _pick_asset_url(assets: list[dict]) -> str | None:
    """Select the correct binary asset for the current platform."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    platform_hints: dict[tuple[str, str], list[str]] = {
        ("darwin", "arm64"): ["macos-arm64", "macos-aarch64", "darwin-arm64"],
        ("darwin", "x86_64"): ["macos-x86_64", "macos-intel", "darwin-x86_64"],
        ("windows", "amd64"): ["windows-x86_64", "win64", "windows"],
        ("windows", "x86_64"): ["windows-x86_64", "win64", "windows"],
        ("linux", "x86_64"): ["linux-x86_64", "linux-amd64", "linux"],
        ("linux", "aarch64"): ["linux-arm64", "linux-aarch64"],
    }

    hints = platform_hints.get((system, machine), [system])

    for asset in assets:
        name = asset.get("name", "").lower()
        for hint in hints:
            if hint in name:
                return asset.get("browser_download_url")

    return None


def _load_check_state() -> dict | None:
    path = get_config_dir() / CHECK_FILE
    if not path.exists():
        return None
    try:
        result: dict = json.loads(path.read_text(encoding="utf-8"))
        return result
    except (json.JSONDecodeError, OSError):
        return None
