"""Tests for the main organization engine."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from whatskeep.models import Contact, MediaFile, MediaType
from whatskeep.organizer import EXT_TO_GROUP, Organizer

if TYPE_CHECKING:
    from pathlib import Path

# ── Helpers ────────────────────────────────────────────────────────────────


def _make_config(
    tmp_downloads: Path,
    tmp_backup: Path,
    *,
    media_types: dict | None = None,
    backup: dict | None = None,
    organization: dict | None = None,
    deduplication: dict | None = None,
) -> dict:
    """Build a minimal config dict pointing at temp directories."""
    cfg: dict = {
        "general": {
            "download_dir": str(tmp_downloads),
            "backup_dir": str(tmp_backup),
        },
        "media_types": media_types
        or {
            "image": True,
            "audio": True,
            "video": True,
            "document": True,
            "sticker": False,
            "voice_note": True,
        },
        "backup": backup or {"mode": "all", "allowlist": [], "blocklist": []},
        "organization": organization
        or {
            "show_phone": True,
            "group_suffix": "(group)",
            "unidentified_folder": "_Unidentified",
            "unidentified_by_date": True,
            "chat_exports_folder": "_Chat Exports",
        },
        "deduplication": deduplication or {"enabled": True, "algorithm": "sha256"},
    }
    return cfg


def _write_fake(path: Path, content: bytes = b"fake content") -> Path:
    """Write a fake file and backdate its mtime so the organizer doesn't skip it."""
    import os

    path.write_bytes(content)
    # Set mtime to 10 seconds ago so file_is_stable / mtime check passes
    old_time = os.path.getmtime(path) - 10
    os.utime(path, (old_time, old_time))
    return path


# ── Scanning ───────────────────────────────────────────────────────────────


class TestScanDownloads:
    """_scan_downloads should find WhatsApp files and ignore others."""

    def test_finds_whatsapp_files(self, tmp_downloads: Path, tmp_backup: Path) -> None:
        _write_fake(tmp_downloads / "WhatsApp Image 2026-04-08 at 14.20.43.jpeg")
        _write_fake(tmp_downloads / "WhatsApp Audio 2026-04-01 at 07.41.04.opus")
        _write_fake(tmp_downloads / "random_photo.jpg")

        org = Organizer(config=_make_config(tmp_downloads, tmp_backup))
        files = org._scan_downloads()

        assert len(files) == 2
        names = {f.path.name for f in files}
        assert "WhatsApp Image 2026-04-08 at 14.20.43.jpeg" in names
        assert "WhatsApp Audio 2026-04-01 at 07.41.04.opus" in names

    def test_ignores_directories(self, tmp_downloads: Path, tmp_backup: Path) -> None:
        (tmp_downloads / "WhatsApp Image 2026-04-08 at 14.20.43.jpeg").mkdir()
        _write_fake(tmp_downloads / "WhatsApp Audio 2026-04-01 at 07.41.04.opus")

        org = Organizer(config=_make_config(tmp_downloads, tmp_backup))
        files = org._scan_downloads()

        assert len(files) == 1

    def test_empty_downloads(self, tmp_downloads: Path, tmp_backup: Path) -> None:
        org = Organizer(config=_make_config(tmp_downloads, tmp_backup))
        files = org._scan_downloads()

        assert files == []

    def test_missing_downloads_dir(self, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist"
        backup = tmp_path / "backup"
        backup.mkdir()

        org = Organizer(config=_make_config(missing, backup))
        files = org._scan_downloads()

        assert files == []

    def test_includes_legacy_pattern(self, tmp_downloads: Path, tmp_backup: Path) -> None:
        _write_fake(tmp_downloads / "IMG-20220331-WA0076.jpg")

        org = Organizer(config=_make_config(tmp_downloads, tmp_backup))
        files = org._scan_downloads()

        assert len(files) == 1
        assert files[0].media_type == MediaType.IMAGE

    def test_includes_chat_exports(self, tmp_downloads: Path, tmp_backup: Path) -> None:
        _write_fake(tmp_downloads / "WhatsApp Chat - Family Group.zip")

        org = Organizer(config=_make_config(tmp_downloads, tmp_backup))
        files = org._scan_downloads()

        assert len(files) == 1
        assert files[0].is_chat_export is True
        assert files[0].chat_contact == "Family Group"


# ── Media type filtering ──────────────────────────────────────────────────


class TestMediaTypeFiltering:
    """Disabled media types should be excluded from scanning."""

    def test_stickers_disabled_by_default(
        self, tmp_downloads: Path, tmp_backup: Path
    ) -> None:
        _write_fake(tmp_downloads / "WhatsApp Sticker 2026-01-01 at 12.00.00.webp")
        _write_fake(tmp_downloads / "WhatsApp Image 2026-04-08 at 14.20.43.jpeg")

        org = Organizer(config=_make_config(tmp_downloads, tmp_backup))
        files = org._scan_downloads()

        assert len(files) == 1
        assert files[0].media_type == MediaType.IMAGE

    def test_disabling_images(self, tmp_downloads: Path, tmp_backup: Path) -> None:
        _write_fake(tmp_downloads / "WhatsApp Image 2026-04-08 at 14.20.43.jpeg")
        _write_fake(tmp_downloads / "WhatsApp Audio 2026-04-01 at 07.41.04.opus")

        cfg = _make_config(
            tmp_downloads,
            tmp_backup,
            media_types={"image": False, "audio": True, "video": True},
        )
        org = Organizer(config=cfg)
        files = org._scan_downloads()

        assert len(files) == 1
        assert files[0].media_type == MediaType.AUDIO

    def test_chat_exports_bypass_media_type_filter(
        self, tmp_downloads: Path, tmp_backup: Path
    ) -> None:
        """Chat exports should be included even if documents are disabled."""
        _write_fake(tmp_downloads / "WhatsApp Chat - Someone.zip")

        cfg = _make_config(
            tmp_downloads,
            tmp_backup,
            media_types={"document": False, "image": True},
        )
        org = Organizer(config=cfg)
        files = org._scan_downloads()

        assert len(files) == 1


# ── Destination path building ─────────────────────────────────────────────


class TestBuildDestPath:
    """Verify destination path construction for identified and unidentified files."""

    def test_identified_file(self, tmp_downloads: Path, tmp_backup: Path) -> None:
        org = Organizer(config=_make_config(tmp_downloads, tmp_backup))
        contact = Contact(
            name="Alice", phone="+55 62 99999-1234", jid="5562999991234@s.whatsapp.net"
        )
        mf = MediaFile(
            path=tmp_downloads / "WhatsApp Image 2026-04-08 at 14.20.43.jpeg",
            media_type=MediaType.IMAGE,
            timestamp=datetime(2026, 4, 8, 14, 20, 43),
            extension="jpeg",
            contact=contact,
        )

        dest = org._build_dest_path(mf, org.config["organization"])

        expected = tmp_backup / "Contacts" / "Alice (+55 62 99999-1234)" / "Image"
        assert dest == expected / mf.path.name

    def test_identified_group(self, tmp_downloads: Path, tmp_backup: Path) -> None:
        org = Organizer(config=_make_config(tmp_downloads, tmp_backup))
        contact = Contact(
            name="Work Team",
            phone=None,
            is_group=True,
            jid="12345@g.us",
        )
        mf = MediaFile(
            path=tmp_downloads / "WhatsApp Video 2025-02-21 at 12.41.20.mp4",
            media_type=MediaType.VIDEO,
            timestamp=datetime(2025, 2, 21, 12, 41, 20),
            extension="mp4",
            contact=contact,
        )

        dest = org._build_dest_path(mf, org.config["organization"])

        assert "Work Team" in str(dest)
        assert "Groups" in str(dest)
        assert dest.parent.name == "Video"

    def test_unidentified_with_date(self, tmp_downloads: Path, tmp_backup: Path) -> None:
        org = Organizer(config=_make_config(tmp_downloads, tmp_backup))
        mf = MediaFile(
            path=tmp_downloads / "WhatsApp Image 2026-04-08 at 14.20.43.jpeg",
            media_type=MediaType.IMAGE,
            timestamp=datetime(2026, 4, 8, 14, 20, 43),
            extension="jpeg",
        )

        dest = org._build_dest_path(mf, org.config["organization"])

        assert dest == (
            tmp_backup / "_Unidentified" / "Image" / "2026-04" / mf.path.name
        )

    def test_unidentified_without_date(self, tmp_downloads: Path, tmp_backup: Path) -> None:
        cfg = _make_config(
            tmp_downloads,
            tmp_backup,
            organization={
                "show_phone": True,
                "group_suffix": "(group)",
                "unidentified_folder": "_Unidentified",
                "unidentified_by_date": False,
            },
        )
        org = Organizer(config=cfg)
        mf = MediaFile(
            path=tmp_downloads / "WhatsApp Audio 2026-04-01 at 07.41.04.opus",
            media_type=MediaType.AUDIO,
            timestamp=datetime(2026, 4, 1, 7, 41, 4),
            extension="opus",
        )

        dest = org._build_dest_path(mf, org.config["organization"])

        assert dest == tmp_backup / "_Unidentified" / "Audio" / mf.path.name


# ── Chat export path ──────────────────────────────────────────────────────


class TestChatExportPath:
    """Chat exports go to _Chat Exports/{contact}/."""

    def test_chat_export_with_contact(self, tmp_downloads: Path, tmp_backup: Path) -> None:
        org = Organizer(config=_make_config(tmp_downloads, tmp_backup))
        mf = MediaFile(
            path=tmp_downloads / "WhatsApp Chat - Family Group.zip",
            media_type=MediaType.DOCUMENT,
            timestamp=datetime.min,
            extension="zip",
        )

        dest = org._build_chat_export_path(mf, "Family Group", org.config["organization"])

        assert dest == (
            tmp_backup / "_Chat Exports" / "Family Group" / "WhatsApp Chat - Family Group.zip"
        )

    def test_chat_export_without_contact(self, tmp_downloads: Path, tmp_backup: Path) -> None:
        org = Organizer(config=_make_config(tmp_downloads, tmp_backup))
        mf = MediaFile(
            path=tmp_downloads / "WhatsApp Chat - Someone.zip",
            media_type=MediaType.DOCUMENT,
            timestamp=datetime.min,
            extension="zip",
        )

        dest = org._build_chat_export_path(mf, None, org.config["organization"])

        assert dest.parent.name == "_Unknown"


# ── Allowlist / blocklist ─────────────────────────────────────────────────


class TestShouldProcess:
    """Allowlist and blocklist filtering logic."""

    def _org(self, tmp_path: Path, backup_config: dict) -> Organizer:
        dl = tmp_path / "dl"
        dl.mkdir(exist_ok=True)
        bk = tmp_path / "bk"
        bk.mkdir(exist_ok=True)
        return Organizer(config=_make_config(dl, bk, backup=backup_config))

    def test_mode_all_passes_everything(self, tmp_path: Path) -> None:
        org = self._org(tmp_path, {"mode": "all"})
        contact = Contact(name="Alice")
        assert org._should_process(contact, org.config["backup"]) is True
        assert org._should_process(None, org.config["backup"]) is True

    def test_allowlist_passes_listed_contact(self, tmp_path: Path) -> None:
        org = self._org(tmp_path, {"mode": "allowlist", "allowlist": ["Alice", "Bob"]})
        assert org._should_process(Contact(name="Alice"), org.config["backup"]) is True
        assert org._should_process(Contact(name="Eve"), org.config["backup"]) is False

    def test_allowlist_passes_unidentified(self, tmp_path: Path) -> None:
        org = self._org(tmp_path, {"mode": "allowlist", "allowlist": ["Alice"]})
        assert org._should_process(None, org.config["backup"]) is True

    def test_blocklist_rejects_listed_contact(self, tmp_path: Path) -> None:
        org = self._org(tmp_path, {"mode": "blocklist", "blocklist": ["Spammer"]})
        assert org._should_process(Contact(name="Spammer"), org.config["backup"]) is False
        assert org._should_process(Contact(name="Alice"), org.config["backup"]) is True

    def test_blocklist_passes_unidentified(self, tmp_path: Path) -> None:
        org = self._org(tmp_path, {"mode": "blocklist", "blocklist": ["Spammer"]})
        assert org._should_process(None, org.config["backup"]) is True


# ── Duplicate handling ────────────────────────────────────────────────────


class TestDuplicateHandling:
    """When destination already exists with identical content, source is removed."""

    @patch("whatskeep.organizer.get_db_reader", return_value=None)
    def test_duplicate_removed(
        self, _mock_db: MagicMock, tmp_downloads: Path, tmp_backup: Path
    ) -> None:
        content = b"identical content here"
        src = _write_fake(
            tmp_downloads / "WhatsApp Image 2026-04-08 at 14.20.43.jpeg", content
        )

        # Pre-create the destination so it collides
        dest_dir = tmp_backup / "_Unidentified" / "Image" / "2026-04"
        dest_dir.mkdir(parents=True)
        _write_fake(dest_dir / src.name, content)

        cfg = _make_config(tmp_downloads, tmp_backup)
        org = Organizer(config=cfg)
        result = org.run(dry_run=False)

        assert result.duplicates == 1
        assert result.organized == 0
        assert not src.exists(), "Source should be deleted after dedup"

    @patch("whatskeep.organizer.get_db_reader", return_value=None)
    def test_non_duplicate_gets_counter_suffix(
        self, _mock_db: MagicMock, tmp_downloads: Path, tmp_backup: Path
    ) -> None:
        src = _write_fake(
            tmp_downloads / "WhatsApp Image 2026-04-08 at 14.20.43.jpeg",
            b"source content",
        )

        dest_dir = tmp_backup / "_Unidentified" / "Image" / "2026-04"
        dest_dir.mkdir(parents=True)
        _write_fake(dest_dir / src.name, b"different content")

        cfg = _make_config(tmp_downloads, tmp_backup)
        org = Organizer(config=cfg)
        result = org.run(dry_run=False)

        assert result.organized == 1
        assert result.duplicates == 0
        # The file should have been moved with a counter suffix
        moved = dest_dir / "WhatsApp Image 2026-04-08 at 14.20.43 (1).jpeg"
        assert moved.exists()

    @patch("whatskeep.organizer.get_db_reader", return_value=None)
    def test_dedup_disabled(
        self, _mock_db: MagicMock, tmp_downloads: Path, tmp_backup: Path
    ) -> None:
        content = b"same content"
        src = _write_fake(
            tmp_downloads / "WhatsApp Image 2026-04-08 at 14.20.43.jpeg", content
        )

        dest_dir = tmp_backup / "_Unidentified" / "Image" / "2026-04"
        dest_dir.mkdir(parents=True)
        _write_fake(dest_dir / src.name, content)

        cfg = _make_config(
            tmp_downloads, tmp_backup, deduplication={"enabled": False}
        )
        org = Organizer(config=cfg)
        result = org.run(dry_run=False)

        # Should not dedup — instead resolve_duplicate adds a counter
        assert result.duplicates == 0
        assert result.organized == 1


# ── Dry-run mode ──────────────────────────────────────────────────────────


class TestDryRun:
    """Dry-run should not move or delete any files."""

    @patch("whatskeep.organizer.get_db_reader", return_value=None)
    def test_dry_run_does_not_move(
        self, _mock_db: MagicMock, tmp_downloads: Path, tmp_backup: Path
    ) -> None:
        src = _write_fake(
            tmp_downloads / "WhatsApp Image 2026-04-08 at 14.20.43.jpeg"
        )

        cfg = _make_config(tmp_downloads, tmp_backup)
        org = Organizer(config=cfg)
        result = org.run(dry_run=True)

        assert result.organized == 1
        assert src.exists(), "Source file must remain after dry-run"

        dest = (
            tmp_backup
            / "_Unidentified"
            / "Image"
            / "2026-04"
            / src.name
        )
        assert not dest.exists(), "Destination must not be created in dry-run"

    @patch("whatskeep.organizer.get_db_reader", return_value=None)
    def test_dry_run_does_not_delete_duplicates(
        self, _mock_db: MagicMock, tmp_downloads: Path, tmp_backup: Path
    ) -> None:
        content = b"duplicate content"
        src = _write_fake(
            tmp_downloads / "WhatsApp Image 2026-04-08 at 14.20.43.jpeg", content
        )

        dest_dir = tmp_backup / "_Unidentified" / "Image" / "2026-04"
        dest_dir.mkdir(parents=True)
        _write_fake(dest_dir / src.name, content)

        cfg = _make_config(tmp_downloads, tmp_backup)
        org = Organizer(config=cfg)
        result = org.run(dry_run=True)

        assert result.duplicates == 1
        assert src.exists(), "Source must remain after dry-run even for duplicates"


# ── Full run integration ──────────────────────────────────────────────────


class TestFullRun:
    """End-to-end pass through run()."""

    @patch("whatskeep.organizer.get_db_reader", return_value=None)
    def test_organizes_multiple_files(
        self, _mock_db: MagicMock, tmp_downloads: Path, tmp_backup: Path
    ) -> None:
        _write_fake(tmp_downloads / "WhatsApp Image 2026-04-08 at 14.20.43.jpeg")
        _write_fake(tmp_downloads / "WhatsApp Audio 2026-04-01 at 07.41.04.opus")
        _write_fake(tmp_downloads / "WhatsApp Video 2025-02-21 at 12.41.20.mp4")

        cfg = _make_config(tmp_downloads, tmp_backup)
        org = Organizer(config=cfg)
        result = org.run(dry_run=False)

        assert result.total_files == 3
        assert result.organized == 3
        assert result.errors == 0
        assert result.by_type["image"] == 1
        assert result.by_type["audio"] == 1
        assert result.by_type["video"] == 1

    @patch("whatskeep.organizer.get_db_reader", return_value=None)
    def test_chat_export_goes_to_exports_folder(
        self, _mock_db: MagicMock, tmp_downloads: Path, tmp_backup: Path
    ) -> None:
        _write_fake(tmp_downloads / "WhatsApp Chat - Family Group.zip")

        cfg = _make_config(tmp_downloads, tmp_backup)
        org = Organizer(config=cfg)
        result = org.run(dry_run=False)

        assert result.organized == 1
        expected = (
            tmp_backup / "_Chat Exports" / "Family Group" / "WhatsApp Chat - Family Group.zip"
        )
        assert expected.exists()

    @patch("whatskeep.organizer.get_db_reader", return_value=None)
    def test_skipped_by_blocklist(
        self, _mock_db: MagicMock, tmp_downloads: Path, tmp_backup: Path
    ) -> None:
        """Files from a blocklisted contact are skipped (no DB = unidentified = passes)."""
        _write_fake(tmp_downloads / "WhatsApp Image 2026-04-08 at 14.20.43.jpeg")

        cfg = _make_config(
            tmp_downloads,
            tmp_backup,
            backup={"mode": "blocklist", "blocklist": ["Spammer"]},
        )
        org = Organizer(config=cfg)
        result = org.run(dry_run=False)

        # Without DB, file is unidentified → passes blocklist
        assert result.organized == 1
        assert result.skipped == 0

    @patch("whatskeep.organizer.get_db_reader", return_value=None)
    def test_result_bytes_tracked(
        self, _mock_db: MagicMock, tmp_downloads: Path, tmp_backup: Path
    ) -> None:
        content = b"x" * 1024
        _write_fake(
            tmp_downloads / "WhatsApp Image 2026-04-08 at 14.20.43.jpeg", content
        )

        cfg = _make_config(tmp_downloads, tmp_backup)
        org = Organizer(config=cfg)
        result = org.run(dry_run=False)

        assert result.bytes_organized == 1024


# ── Contact lookup ────────────────────────────────────────────────────────


class TestLookupContact:
    """DB-backed contact lookup."""

    def test_returns_contact_on_hit(self, tmp_downloads: Path, tmp_backup: Path) -> None:
        org = Organizer(config=_make_config(tmp_downloads, tmp_backup))

        ts = datetime(2026, 4, 8, 14, 20, 43)
        ts_unix = int(ts.timestamp())
        org._lookup = {
            (ts_unix, "image"): (
                "Alice", "+5562999991234", False, "5562999991234@s.whatsapp.net",
                None, None,
            ),
        }

        mf = MediaFile(
            path=tmp_downloads / "test.jpeg",
            media_type=MediaType.IMAGE,
            timestamp=ts,
            extension="jpeg",
        )
        contact = org._lookup_contact(mf)

        assert contact is not None
        assert contact.name == "Alice"
        assert contact.is_group is False

    def test_returns_none_on_miss(self, tmp_downloads: Path, tmp_backup: Path) -> None:
        org = Organizer(config=_make_config(tmp_downloads, tmp_backup))
        org._lookup = {}

        mf = MediaFile(
            path=tmp_downloads / "test.jpeg",
            media_type=MediaType.IMAGE,
            timestamp=datetime(2026, 4, 8, 14, 20, 43),
            extension="jpeg",
        )
        assert org._lookup_contact(mf) is None

    def test_returns_none_when_no_lookup(
        self, tmp_downloads: Path, tmp_backup: Path
    ) -> None:
        org = Organizer(config=_make_config(tmp_downloads, tmp_backup))
        org._lookup = {}

        mf = MediaFile(
            path=tmp_downloads / "test.jpeg",
            media_type=MediaType.IMAGE,
            timestamp=datetime(2026, 4, 8, 14, 20, 43),
            extension="jpeg",
        )
        assert org._lookup_contact(mf) is None


# ── EXT_TO_GROUP mapping ──────────────────────────────────────────────────


class TestExtToGroup:
    """Smoke-test the extension mapping."""

    @pytest.mark.parametrize(
        ("ext", "expected"),
        [
            (".jpg", "image"),
            (".mp4", "video"),
            (".opus", "audio"),
            (".pdf", "document"),
            (".zip", "document"),
        ],
    )
    def test_known_extensions(self, ext: str, expected: str) -> None:
        assert EXT_TO_GROUP[ext] == expected
