"""CLI integration tests for WhatsKeep."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from typer.testing import CliRunner

from whatskeep import __version__
from whatskeep.cli import app

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------


class TestVersion:
    """Tests for the ``version`` command."""

    def test_version_shows_version_string(self) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_version_shows_python(self) -> None:
        result = runner.invoke(app, ["version"])
        assert "Python" in result.output


# ---------------------------------------------------------------------------
# config show
# ---------------------------------------------------------------------------


class TestConfigShow:
    """Tests for the ``config show`` command."""

    def test_config_show_returns_valid_output(self) -> None:
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        # Default config always has these sections (Rich panel wraps them)
        output = result.output
        assert "general" in output
        assert "backup" in output
        assert "media_types" in output

    def test_config_show_contains_toml_keys(self) -> None:
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        # Config values should appear in output
        assert "download_dir" in result.output


# ---------------------------------------------------------------------------
# run --dry-run
# ---------------------------------------------------------------------------


def _make_test_config(tmp_path: Path) -> dict:
    """Build a full test config pointing at *tmp_path*."""
    dl_dir = tmp_path / "Downloads"
    dl_dir.mkdir(exist_ok=True)
    return {
        "general": {
            "download_dir": str(dl_dir),
            "backup_dir": str(tmp_path / "Backup"),
        },
        "monitoring": {"interval": 10, "process_existing": True},
        "auto_update": {
            "enabled": False,
            "channel": "stable",
            "check_interval_hours": 24,
        },
        "backup": {"mode": "all", "allowlist": [], "blocklist": []},
        "media_types": {
            "image": True,
            "audio": True,
            "video": True,
            "document": True,
            "sticker": False,
            "voice_note": True,
        },
        "organization": {
            "folder_template": "{contact}/{type}",
            "show_phone": True,
            "group_suffix": "(group)",
            "unidentified_folder": "_Unidentified",
            "unidentified_by_date": True,
        },
        "deduplication": {"enabled": True, "algorithm": "sha256"},
        "notifications": {
            "enabled": False,
            "on_organize": False,
            "on_error": False,
            "on_update": False,
        },
        "logging": {
            "level": "INFO",
            "max_size_mb": 10,
            "retention_days": 30,
        },
    }


class TestRunDryRun:
    """Tests for the ``run --dry-run`` command with empty downloads."""

    def test_dry_run_with_empty_downloads(self, tmp_path: Path) -> None:
        """Dry-run with an empty downloads dir should succeed with 0 files."""
        config = _make_test_config(tmp_path)

        with patch("whatskeep.cli._load_config_safe", return_value=config):
            result = runner.invoke(app, ["run", "--dry-run"])

        assert result.exit_code == 0
        assert "0" in result.output  # 0 total files

    def test_dry_run_shows_dry_run_notice(self, tmp_path: Path) -> None:
        config = _make_test_config(tmp_path)

        with patch("whatskeep.cli._load_config_safe", return_value=config):
            result = runner.invoke(app, ["run", "--dry-run"])

        assert result.exit_code == 0
        assert "Dry-run" in result.output or "dry" in result.output.lower()


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------


class TestDoctor:
    """Tests for the ``doctor`` command."""

    def test_doctor_runs_without_crashing(self) -> None:
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0

    def test_doctor_checks_python_version(self) -> None:
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "Python" in result.output

    def test_doctor_checks_platform(self) -> None:
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "Platform" in result.output


# ---------------------------------------------------------------------------
# stats (empty backup dir)
# ---------------------------------------------------------------------------


class TestStats:
    """Tests for the ``stats`` command."""

    def test_stats_with_nonexistent_backup(self, tmp_path: Path) -> None:
        config = {
            "general": {"backup_dir": str(tmp_path / "nonexistent")},
        }
        with patch(
            "whatskeep.cli._load_config_safe", return_value=config,
        ):
            result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "does not exist" in result.output


# ---------------------------------------------------------------------------
# logs (no log file)
# ---------------------------------------------------------------------------


class TestLogs:
    """Tests for the ``logs`` command."""

    def test_logs_no_file(self, tmp_path: Path) -> None:
        fake_path = tmp_path / "nonexistent.log"
        with patch(
            "whatskeep.cli._get_log_path", return_value=fake_path,
        ):
            result = runner.invoke(app, ["logs"])
        assert result.exit_code == 0
        assert "No log file" in result.output


# ---------------------------------------------------------------------------
# update (module not available)
# ---------------------------------------------------------------------------


class TestUpdate:
    """Tests for the ``update`` command when updater module is absent."""

    def test_update_check(self) -> None:
        result = runner.invoke(app, ["update", "--check"])
        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert (
            "not yet available" in output_lower
            or "latest version" in output_lower
            or "update available" in output_lower
        )


# ---------------------------------------------------------------------------
# no args shows help
# ---------------------------------------------------------------------------


class TestHelp:
    """Tests for help display."""

    def test_no_args_shows_help(self) -> None:
        result = runner.invoke(app, [])
        # Typer with no_args_is_help may return 0 or 2
        assert result.exit_code in (0, 2)
        output_lower = result.output.lower()
        assert "organize" in output_lower or "whatskeep" in output_lower

    def test_explicit_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "whatskeep" in result.output.lower()
