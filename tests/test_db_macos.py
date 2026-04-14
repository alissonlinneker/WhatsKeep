"""Tests for the macOS ChatStorage.sqlite reader."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from whatskeep.db.macos import CORE_DATA_EPOCH, MacOSDBReader, _media_type_from_path
from whatskeep.models import DBMediaRecord, MediaType

if TYPE_CHECKING:
    from pathlib import Path

# -----------------------------------------------------------------------
# Helpers — in-memory SQLite with WhatsApp schema
# -----------------------------------------------------------------------

def _create_test_db(path: Path) -> None:
    """Create a minimal ChatStorage.sqlite with the tables used by the reader."""
    conn = sqlite3.connect(str(path))
    conn.executescript(
        """\
        CREATE TABLE ZWACHATSESSION (
            Z_PK     INTEGER PRIMARY KEY,
            ZPARTNERNAME TEXT,
            ZCONTACTJID  TEXT
        );

        CREATE TABLE ZWAMESSAGE (
            Z_PK        INTEGER PRIMARY KEY,
            ZMESSAGEDATE REAL,
            ZCHATSESSION INTEGER REFERENCES ZWACHATSESSION(Z_PK),
            ZPUSHNAME    TEXT,
            ZGROUPMEMBER INTEGER,
            ZMESSAGETYPE INTEGER DEFAULT 1
        );

        CREATE TABLE ZWAMEDIAITEM (
            Z_PK           INTEGER PRIMARY KEY,
            ZMEDIALOCALPATH TEXT,
            ZMESSAGE       INTEGER REFERENCES ZWAMESSAGE(Z_PK)
        );

        CREATE TABLE ZWAGROUPMEMBER (
            Z_PK       INTEGER PRIMARY KEY,
            ZMEMBERJID TEXT
        );

        CREATE TABLE ZWAPROFILEPUSHNAME (
            Z_PK      INTEGER PRIMARY KEY,
            Z_ENT     INTEGER,
            Z_OPT     INTEGER,
            ZJID      TEXT,
            ZPUSHNAME TEXT
        );
        """
    )
    conn.close()


def _insert_record(
    path: Path,
    *,
    session_pk: int,
    partner_name: str,
    contact_jid: str,
    message_pk: int,
    message_date: float,
    media_pk: int,
    media_local_path: str,
    push_name: str | None = None,
) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute(
        "INSERT OR IGNORE INTO ZWACHATSESSION (Z_PK, ZPARTNERNAME, ZCONTACTJID) VALUES (?, ?, ?)",
        (session_pk, partner_name, contact_jid),
    )
    conn.execute(
        "INSERT INTO ZWAMESSAGE (Z_PK, ZMESSAGEDATE, ZCHATSESSION, ZPUSHNAME) VALUES (?, ?, ?, ?)",
        (message_pk, message_date, session_pk, push_name),
    )
    conn.execute(
        "INSERT INTO ZWAMEDIAITEM (Z_PK, ZMEDIALOCALPATH, ZMESSAGE) VALUES (?, ?, ?)",
        (media_pk, media_local_path, message_pk),
    )
    conn.commit()
    conn.close()


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------

@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    """Return path to a test ChatStorage.sqlite with sample rows."""
    p = tmp_path / "ChatStorage.sqlite"
    _create_test_db(p)

    core_date = 700000000.0  # Offset from Core Data epoch

    _insert_record(
        p,
        session_pk=1,
        partner_name="Alice",
        contact_jid="5511999990000@s.whatsapp.net",
        message_pk=1,
        message_date=core_date,
        media_pk=1,
        media_local_path="/Media/image.jpg",
    )

    _insert_record(
        p,
        session_pk=2,
        partner_name="Family Group",
        contact_jid="120363000000000000@g.us",
        message_pk=2,
        message_date=core_date + 100,
        media_pk=2,
        media_local_path="/Media/video.mp4",
    )

    _insert_record(
        p,
        session_pk=1,
        partner_name="Alice",
        contact_jid="5511999990000@s.whatsapp.net",
        message_pk=3,
        message_date=core_date + 200,
        media_pk=3,
        media_local_path="/Media/document.pdf",
    )

    # Record with NULL media path (should be excluded by SQL WHERE)
    conn = sqlite3.connect(str(p))
    conn.execute(
        "INSERT INTO ZWAMESSAGE (Z_PK, ZMESSAGEDATE, ZCHATSESSION, ZPUSHNAME)"
        " VALUES (4, ?, 1, NULL)",
        (core_date + 300,),
    )
    conn.execute(
        "INSERT INTO ZWAMEDIAITEM (Z_PK, ZMEDIALOCALPATH, ZMESSAGE) VALUES (4, NULL, 4)",
    )
    conn.commit()
    conn.close()

    return p


@pytest.fixture()
def reader(db_path: Path) -> MacOSDBReader:
    """Return a MacOSDBReader wired to the test database."""
    r = MacOSDBReader()
    with patch.object(r, "db_path", return_value=db_path):
        yield r  # type: ignore[misc]
    r.close()


# -----------------------------------------------------------------------
# Tests — media type detection
# -----------------------------------------------------------------------

class TestMediaTypeFromPath:
    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("/Media/photo.jpg", MediaType.IMAGE),
            ("/Media/photo.JPEG", MediaType.IMAGE),
            ("/Media/photo.png", MediaType.IMAGE),
            ("/Media/photo.heic", MediaType.IMAGE),
            ("/Media/voice.opus", MediaType.AUDIO),
            ("/Media/voice.m4a", MediaType.AUDIO),
            ("/Media/clip.mp4", MediaType.VIDEO),
            ("/Media/clip.mov", MediaType.VIDEO),
            ("/Media/file.pdf", MediaType.DOCUMENT),
            ("/Media/file.xlsx", MediaType.DOCUMENT),
        ],
    )
    def test_known_extensions(self, path: str, expected: MediaType) -> None:
        assert _media_type_from_path(path) == expected

    def test_unknown_extension_returns_none(self) -> None:
        assert _media_type_from_path("/Media/file.xyz") is None


# -----------------------------------------------------------------------
# Tests — is_available
# -----------------------------------------------------------------------

class TestIsAvailable:
    def test_returns_false_when_db_missing(self) -> None:
        reader = MacOSDBReader()
        with patch.object(reader, "db_path", return_value=None):
            assert reader.is_available() is False

    def test_returns_false_when_path_is_directory(self, tmp_path: Path) -> None:
        d = tmp_path / "ChatStorage.sqlite"
        d.mkdir()
        reader = MacOSDBReader()
        with patch.object(reader, "db_path", return_value=d):
            assert reader.is_available() is False

    def test_returns_true_when_db_exists(self, db_path: Path) -> None:
        reader = MacOSDBReader()
        with patch.object(reader, "db_path", return_value=db_path):
            assert reader.is_available() is True


# -----------------------------------------------------------------------
# Tests — get_media_records
# -----------------------------------------------------------------------

class TestGetMediaRecords:
    def test_returns_correct_count(self, reader: MacOSDBReader) -> None:
        records = reader.get_media_records()
        assert len(records) == 3

    def test_individual_contact_fields(self, reader: MacOSDBReader) -> None:
        records = reader.get_media_records()

        alice_image = [r for r in records if r.media_type == MediaType.IMAGE][0]
        assert alice_image.contact_name == "Alice"
        assert alice_image.phone == "5511999990000"
        assert alice_image.is_group is False
        assert alice_image.jid == "5511999990000@s.whatsapp.net"

    def test_group_contact_fields(self, reader: MacOSDBReader) -> None:
        records = reader.get_media_records()

        group_video = [r for r in records if r.media_type == MediaType.VIDEO][0]
        assert group_video.contact_name == "Family Group"
        assert group_video.phone is None
        assert group_video.is_group is True
        assert group_video.jid == "120363000000000000@g.us"

    def test_timestamp_uses_core_data_epoch(self, reader: MacOSDBReader) -> None:
        records = reader.get_media_records()

        first = records[0]
        expected_unix = 700000000.0 + CORE_DATA_EPOCH
        assert first.timestamp == expected_unix

    def test_returns_dbmediarecord_instances(self, reader: MacOSDBReader) -> None:
        records = reader.get_media_records()
        assert all(isinstance(r, DBMediaRecord) for r in records)

    def test_returns_empty_when_db_not_found(self) -> None:
        reader = MacOSDBReader()
        with patch.object(reader, "db_path", return_value=None):
            assert reader.get_media_records() == []

    def test_returns_empty_on_missing_tables(self, tmp_path: Path) -> None:
        """An empty SQLite file (no WhatsApp tables) should not crash."""
        empty_db = tmp_path / "empty.sqlite"
        conn = sqlite3.connect(str(empty_db))
        conn.close()

        reader = MacOSDBReader()
        with patch.object(reader, "db_path", return_value=empty_db):
            assert reader.get_media_records() == []
        reader.close()


# -----------------------------------------------------------------------
# Tests — locked database retry
# -----------------------------------------------------------------------

class TestLockedDBRetry:
    def test_retries_on_locked_error(self, db_path: Path) -> None:
        """Simulate a locked DB that succeeds on the second attempt."""
        reader = MacOSDBReader()
        call_count = 0

        # Pre-open so _fetch_records works on retry
        real_records: list[DBMediaRecord] = []

        def _mock_fetch(path: Path) -> list[DBMediaRecord]:
            nonlocal call_count, real_records
            call_count += 1
            if call_count == 1:
                raise sqlite3.OperationalError("database is locked")
            # Open the DB and return real records on second attempt
            conn = sqlite3.connect(str(path))
            conn.execute("PRAGMA journal_mode=WAL")
            cursor = conn.execute(
                "SELECT m.ZMESSAGEDATE, mi.ZMEDIALOCALPATH, cs.ZPARTNERNAME, cs.ZCONTACTJID "
                "FROM ZWAMEDIAITEM mi "
                "JOIN ZWAMESSAGE m ON mi.ZMESSAGE = m.Z_PK "
                "JOIN ZWACHATSESSION cs ON m.ZCHATSESSION = cs.Z_PK "
                "WHERE mi.ZMEDIALOCALPATH IS NOT NULL "
                "AND mi.ZMEDIALOCALPATH != '' "
                "AND cs.ZPARTNERNAME IS NOT NULL"
            )
            rows = cursor.fetchall()
            conn.close()
            return [
                DBMediaRecord(
                    timestamp=row[0] + CORE_DATA_EPOCH,
                    media_type=MediaType.IMAGE,
                    contact_name=row[2],
                )
                for row in rows
            ]

        with (
            patch.object(reader, "db_path", return_value=db_path),
            patch.object(reader, "_fetch_records", side_effect=_mock_fetch),
            patch("whatskeep.db.macos.time.sleep"),
        ):
            records = reader.get_media_records()

        assert call_count == 2
        assert len(records) == 3
        reader.close()

    def test_returns_empty_after_max_retries(self, db_path: Path) -> None:
        """All retries fail with locked error — should return empty list."""
        reader = MacOSDBReader()

        def _always_locked(path: Path) -> list[DBMediaRecord]:
            raise sqlite3.OperationalError("database is locked")

        with (
            patch.object(reader, "db_path", return_value=db_path),
            patch.object(reader, "_fetch_records", side_effect=_always_locked),
            patch("whatskeep.db.macos.time.sleep"),
        ):
            records = reader.get_media_records()

        assert records == []

    def test_non_lock_error_returns_empty_immediately(self, db_path: Path) -> None:
        """Non-lock OperationalError should not retry."""
        reader = MacOSDBReader()
        call_count = 0

        def _bad_query(path: Path) -> list[DBMediaRecord]:
            nonlocal call_count
            call_count += 1
            raise sqlite3.OperationalError("no such table: ZWAMEDIAITEM")

        with (
            patch.object(reader, "db_path", return_value=db_path),
            patch.object(reader, "_fetch_records", side_effect=_bad_query),
        ):
            records = reader.get_media_records()

        assert call_count == 1
        assert records == []


# -----------------------------------------------------------------------
# Tests — close
# -----------------------------------------------------------------------

class TestClose:
    def test_close_clears_connection(self, reader: MacOSDBReader) -> None:
        reader.get_media_records()
        assert reader._conn is not None
        reader.close()
        assert reader._conn is None

    def test_close_is_idempotent(self) -> None:
        reader = MacOSDBReader()
        reader.close()  # No connection yet — should not raise
        reader.close()
