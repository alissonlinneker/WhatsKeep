"""TOML configuration loading, defaults, and validation for WhatsKeep."""

from __future__ import annotations

import copy
import platform
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

DEFAULT_CONFIG: dict[str, Any] = {
    "general": {
        "language": "en",
        "download_dir": "auto",
        "backup_dir": "~/WhatsKeep",
    },
    "monitoring": {
        "interval": 10,
        "process_existing": True,
    },
    "auto_update": {
        "enabled": True,
        "channel": "stable",
        "check_interval_hours": 24,
    },
    "backup": {
        "mode": "all",
        "allowlist": [],
        "blocklist": [],
    },
    "media_types": {
        "image": True,
        "audio": True,
        "video": True,
        "document": True,
        "sticker": False,
        "gif": False,
        "voice_note": True,
    },
    "organization": {
        "folder_template": "{contact}/{type}",
        "show_phone": True,
        "group_suffix": "(group)",
        "unidentified_folder": "_Unidentified",
        "unidentified_by_date": True,
    },
    "deduplication": {
        "enabled": True,
        "algorithm": "sha256",
    },
    "notifications": {
        "enabled": True,
        "on_organize": False,
        "on_error": True,
        "on_update": True,
    },
    "logging": {
        "level": "INFO",
        "max_size_mb": 10,
        "retention_days": 30,
    },
}

_VALID_BACKUP_MODES = {"all", "allowlist", "blocklist"}
_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_VALID_CHANNELS = {"stable", "beta"}
_VALID_ALGORITHMS = {"sha256", "blake2b"}


def get_config_dir() -> Path:
    """Return ``~/.whatskeep/``, creating the directory if it does not exist."""
    config_dir = Path.home() / ".whatskeep"
    config_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    return config_dir


def get_config_path() -> Path:
    """Return the path to ``~/.whatskeep/config.toml``."""
    return get_config_dir() / "config.toml"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *override* into a copy of *base*.

    Keys present in *override* replace the corresponding keys in *base*.
    Nested dicts are merged recursively rather than replaced wholesale.
    """
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load configuration from a TOML file and deep-merge with defaults.

    If *path* is ``None``, the default config path is used.  When the file
    does not exist the built-in defaults are returned as-is.
    """
    if path is None:
        path = get_config_path()

    if not path.exists():
        return copy.deepcopy(DEFAULT_CONFIG)

    with open(path, "rb") as fh:
        user_config = tomllib.load(fh)

    return _deep_merge(DEFAULT_CONFIG, user_config)


def save_default_config(path: Path | None = None) -> Path:
    """Write the default configuration to a TOML file.

    Intended to be called by ``whatskeep init``.  Returns the path written.
    """
    if path is None:
        path = get_config_path()

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dict_to_toml(DEFAULT_CONFIG), encoding="utf-8")
    return path


def _format_toml_value(value: Any) -> str:
    """Format a single Python value as a TOML literal."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, list):
        items = ", ".join(_format_toml_value(v) for v in value)
        return f"[{items}]"
    msg = f"Unsupported TOML value type: {type(value)}"
    raise TypeError(msg)


def _dict_to_toml(data: dict[str, Any]) -> str:
    """Serialize a dict to a minimal TOML string (one level of tables)."""
    lines: list[str] = []
    for section, values in data.items():
        if not isinstance(values, dict):
            continue
        lines.append(f"[{section}]")
        for key, val in values.items():
            lines.append(f"{key} = {_format_toml_value(val)}")
        lines.append("")
    return "\n".join(lines)


def validate_config(config: dict[str, Any]) -> list[str]:
    """Validate a configuration dict and return a list of error messages.

    An empty list means the configuration is valid.
    """
    errors: list[str] = []

    # --- backup.mode ---
    mode = config.get("backup", {}).get("mode")
    if mode is not None and mode not in _VALID_BACKUP_MODES:
        errors.append(
            f"backup.mode must be one of {sorted(_VALID_BACKUP_MODES)}, got '{mode}'"
        )

    # --- logging.level ---
    level = config.get("logging", {}).get("level")
    if level is not None and level not in _VALID_LOG_LEVELS:
        errors.append(
            f"logging.level must be one of {sorted(_VALID_LOG_LEVELS)}, got '{level}'"
        )

    # --- monitoring.interval ---
    interval = config.get("monitoring", {}).get("interval")
    if interval is not None and (not isinstance(interval, (int, float)) or interval <= 0):
        errors.append(f"monitoring.interval must be a positive number, got {interval!r}")

    # --- auto_update.check_interval_hours ---
    check_hours = config.get("auto_update", {}).get("check_interval_hours")
    if check_hours is not None and (
        not isinstance(check_hours, (int, float)) or check_hours <= 0
    ):
        errors.append(
            f"auto_update.check_interval_hours must be a positive number, got {check_hours!r}"
        )

    # --- auto_update.channel ---
    channel = config.get("auto_update", {}).get("channel")
    if channel is not None and channel not in _VALID_CHANNELS:
        errors.append(
            f"auto_update.channel must be one of {sorted(_VALID_CHANNELS)}, got '{channel}'"
        )

    # --- deduplication.algorithm ---
    algorithm = config.get("deduplication", {}).get("algorithm")
    if algorithm is not None and algorithm not in _VALID_ALGORITHMS:
        errors.append(
            f"deduplication.algorithm must be one of {sorted(_VALID_ALGORITHMS)}, got '{algorithm}'"
        )

    # --- logging.max_size_mb ---
    max_size = config.get("logging", {}).get("max_size_mb")
    if max_size is not None and (not isinstance(max_size, (int, float)) or max_size <= 0):
        errors.append(f"logging.max_size_mb must be a positive number, got {max_size!r}")

    # --- logging.retention_days ---
    retention = config.get("logging", {}).get("retention_days")
    if retention is not None and (not isinstance(retention, (int, float)) or retention <= 0):
        errors.append(
            f"logging.retention_days must be a positive number, got {retention!r}"
        )

    return errors


def resolve_download_dir(config: dict[str, Any]) -> Path:
    """Resolve the download directory from configuration.

    When the value is ``"auto"``, the platform-specific Downloads folder is
    returned.  Otherwise the configured path is expanded and returned.
    """
    raw = config.get("general", {}).get("download_dir", "auto")

    if raw == "auto":
        return _platform_downloads_dir()

    return Path(raw).expanduser().resolve()


def resolve_backup_dir(config: dict[str, Any]) -> Path:
    """Expand ``~`` and resolve the backup directory from configuration."""
    raw = config.get("general", {}).get("backup_dir", "~/WhatsKeep")
    return Path(raw).expanduser().resolve()


def _platform_downloads_dir() -> Path:
    """Return the platform-specific default Downloads directory."""
    import os

    system = platform.system()

    if system == "Linux":
        # Respect XDG_DOWNLOAD_DIR if set.
        xdg = os.environ.get("XDG_DOWNLOAD_DIR")
        if xdg:
            return Path(xdg)

    # macOS, Windows, and Linux fallback all use ~/Downloads.
    return Path.home() / "Downloads"
