"""Tests for whatskeep.config — TOML loading, defaults, validation."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import patch

from whatskeep.config import (
    DEFAULT_CONFIG,
    load_config,
    resolve_backup_dir,
    resolve_download_dir,
    save_default_config,
    validate_config,
)

# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


class TestLoadConfig:
    """Tests for ``load_config``."""

    def test_returns_defaults_when_no_file(self, tmp_path: Path) -> None:
        """When the config file does not exist, defaults are returned."""
        missing = tmp_path / "nonexistent.toml"
        config = load_config(missing)
        assert config == DEFAULT_CONFIG

    def test_returns_deep_copy_of_defaults(self, tmp_path: Path) -> None:
        """Mutating the returned dict must not affect ``DEFAULT_CONFIG``."""
        missing = tmp_path / "nonexistent.toml"
        config = load_config(missing)
        config["general"]["language"] = "pt"
        assert DEFAULT_CONFIG["general"]["language"] == "en"

    def test_load_from_toml_file(self, tmp_path: Path) -> None:
        """Values present in the TOML file override defaults."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text(
            textwrap.dedent("""\
                [general]
                language = "pt"

                [monitoring]
                interval = 30
            """),
            encoding="utf-8",
        )
        config = load_config(cfg_file)
        assert config["general"]["language"] == "pt"
        assert config["monitoring"]["interval"] == 30

    def test_deep_merge_preserves_unset_keys(self, tmp_path: Path) -> None:
        """Keys not present in the user file fall back to defaults."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text(
            textwrap.dedent("""\
                [general]
                language = "es"
            """),
            encoding="utf-8",
        )
        config = load_config(cfg_file)
        # Overridden value
        assert config["general"]["language"] == "es"
        # Untouched values in same section
        assert config["general"]["download_dir"] == "auto"
        assert config["general"]["backup_dir"] == "~/WhatsKeep"
        # Untouched sections
        assert config["monitoring"]["interval"] == 10
        assert config["deduplication"]["algorithm"] == "sha256"

    def test_deep_merge_does_not_drop_sections(self, tmp_path: Path) -> None:
        """All default sections must be present even when the user file is minimal."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text("[logging]\nlevel = \"DEBUG\"\n", encoding="utf-8")
        config = load_config(cfg_file)
        for section in DEFAULT_CONFIG:
            assert section in config, f"Missing section: {section}"

    def test_user_can_add_unknown_keys(self, tmp_path: Path) -> None:
        """Unknown keys should pass through without error."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text(
            textwrap.dedent("""\
                [general]
                custom_flag = true
            """),
            encoding="utf-8",
        )
        config = load_config(cfg_file)
        assert config["general"]["custom_flag"] is True


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------


class TestValidateConfig:
    """Tests for ``validate_config``."""

    def test_defaults_are_valid(self) -> None:
        errors = validate_config(DEFAULT_CONFIG)
        assert errors == []

    def test_invalid_backup_mode(self) -> None:
        config = {"backup": {"mode": "invalid"}}
        errors = validate_config(config)
        assert any("backup.mode" in e for e in errors)

    def test_invalid_log_level(self) -> None:
        config = {"logging": {"level": "VERBOSE"}}
        errors = validate_config(config)
        assert any("logging.level" in e for e in errors)

    def test_negative_monitoring_interval(self) -> None:
        config = {"monitoring": {"interval": -5}}
        errors = validate_config(config)
        assert any("monitoring.interval" in e for e in errors)

    def test_zero_monitoring_interval(self) -> None:
        config = {"monitoring": {"interval": 0}}
        errors = validate_config(config)
        assert any("monitoring.interval" in e for e in errors)

    def test_invalid_channel(self) -> None:
        config = {"auto_update": {"channel": "nightly"}}
        errors = validate_config(config)
        assert any("auto_update.channel" in e for e in errors)

    def test_invalid_algorithm(self) -> None:
        config = {"deduplication": {"algorithm": "crc32"}}
        errors = validate_config(config)
        assert any("deduplication.algorithm" in e for e in errors)

    def test_negative_max_size_mb(self) -> None:
        config = {"logging": {"max_size_mb": -1}}
        errors = validate_config(config)
        assert any("logging.max_size_mb" in e for e in errors)

    def test_negative_retention_days(self) -> None:
        config = {"logging": {"retention_days": 0}}
        errors = validate_config(config)
        assert any("logging.retention_days" in e for e in errors)

    def test_multiple_errors_collected(self) -> None:
        config = {
            "backup": {"mode": "bad"},
            "logging": {"level": "NOPE"},
            "monitoring": {"interval": -1},
        }
        errors = validate_config(config)
        assert len(errors) == 3


# ---------------------------------------------------------------------------
# resolve_download_dir
# ---------------------------------------------------------------------------


class TestResolveDownloadDir:
    """Tests for ``resolve_download_dir``."""

    def test_auto_returns_downloads_on_darwin(self) -> None:
        config = {"general": {"download_dir": "auto"}}
        with patch("whatskeep.config.platform.system", return_value="Darwin"):
            result = resolve_download_dir(config)
        assert result == Path.home() / "Downloads"

    def test_auto_returns_downloads_on_windows(self) -> None:
        config = {"general": {"download_dir": "auto"}}
        with patch("whatskeep.config.platform.system", return_value="Windows"):
            # Windows path resolution falls back to ~/Downloads when ctypes unavailable.
            result = resolve_download_dir(config)
            assert result == Path.home() / "Downloads"

    def test_auto_returns_downloads_on_linux_no_xdg(self) -> None:
        import os

        config = {"general": {"download_dir": "auto"}}
        # Keep HOME/USERPROFILE so Path.home() works on all platforms
        clean_env = {k: v for k, v in os.environ.items() if k != "XDG_DOWNLOAD_DIR"}
        with (
            patch("whatskeep.config.platform.system", return_value="Linux"),
            patch.dict("os.environ", clean_env, clear=True),
        ):
            result = resolve_download_dir(config)
        assert result == Path.home() / "Downloads"

    def test_auto_respects_xdg_on_linux(self) -> None:
        config = {"general": {"download_dir": "auto"}}
        with (
            patch("whatskeep.config.platform.system", return_value="Linux"),
            patch.dict("os.environ", {"XDG_DOWNLOAD_DIR": "/custom/dl"}),
        ):
            result = resolve_download_dir(config)
        assert result == Path("/custom/dl")

    def test_explicit_path_expanded(self, tmp_path: Path) -> None:
        config = {"general": {"download_dir": str(tmp_path / "MyDL")}}
        result = resolve_download_dir(config)
        assert result == (tmp_path / "MyDL").resolve()

    def test_tilde_expanded(self) -> None:
        config = {"general": {"download_dir": "~/CustomDownloads"}}
        result = resolve_download_dir(config)
        assert result == Path.home() / "CustomDownloads"


# ---------------------------------------------------------------------------
# resolve_backup_dir
# ---------------------------------------------------------------------------


class TestResolveBackupDir:
    """Tests for ``resolve_backup_dir``."""

    def test_expands_tilde(self) -> None:
        config = {"general": {"backup_dir": "~/WhatsKeep"}}
        result = resolve_backup_dir(config)
        assert result == (Path.home() / "WhatsKeep").resolve()

    def test_absolute_path_unchanged(self, tmp_path: Path) -> None:
        config = {"general": {"backup_dir": str(tmp_path / "Backup")}}
        result = resolve_backup_dir(config)
        assert result == (tmp_path / "Backup").resolve()

    def test_defaults_when_missing(self) -> None:
        config: dict = {}
        result = resolve_backup_dir(config)
        assert result == (Path.home() / "WhatsKeep").resolve()


# ---------------------------------------------------------------------------
# save_default_config
# ---------------------------------------------------------------------------


class TestSaveDefaultConfig:
    """Tests for ``save_default_config``."""

    def test_creates_file(self, tmp_path: Path) -> None:
        path = tmp_path / ".whatskeep" / "config.toml"
        result = save_default_config(path)
        assert result == path
        assert path.exists()

    def test_file_is_valid_toml(self, tmp_path: Path) -> None:
        path = tmp_path / "config.toml"
        save_default_config(path)
        # Re-load to verify round-trip
        config = load_config(path)
        assert config == DEFAULT_CONFIG

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "nested" / "config.toml"
        save_default_config(path)
        assert path.exists()

    def test_content_contains_all_sections(self, tmp_path: Path) -> None:
        path = tmp_path / "config.toml"
        save_default_config(path)
        content = path.read_text(encoding="utf-8")
        for section in DEFAULT_CONFIG:
            assert f"[{section}]" in content
