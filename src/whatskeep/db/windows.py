"""Windows WhatsApp Desktop database reader."""

from __future__ import annotations

import contextlib
import os
import sqlite3
from pathlib import Path

from loguru import logger

from whatskeep.db.base import BaseDBReader
from whatskeep.models import DBMediaRecord, MediaType

# Maps WhatsApp internal media type strings/integers to our MediaType enum.
_MEDIA_TYPE_MAP: dict[str | int, MediaType] = {
    1: MediaType.IMAGE,
    2: MediaType.AUDIO,
    3: MediaType.VIDEO,
    4: MediaType.DOCUMENT,
    5: MediaType.STICKER,
    6: MediaType.VOICE_NOTE,
    "image": MediaType.IMAGE,
    "audio": MediaType.AUDIO,
    "video": MediaType.VIDEO,
    "document": MediaType.DOCUMENT,
    "sticker": MediaType.STICKER,
    "voice_note": MediaType.VOICE_NOTE,
}


class WindowsDBReader(BaseDBReader):
    """Windows WhatsApp Desktop DB reader.

    Current implementation attempts to locate the database but may not
    support all WhatsApp Desktop versions.  Falls back gracefully.
    """

    _KNOWN_PATHS: list[Path] = [
        # Standalone installer
        Path(os.environ.get("APPDATA", "")) / "WhatsApp" / "databases",
        # UWP / Microsoft Store
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Packages"
        / "5319275A.WhatsAppDesktop_cv1g1gnamhmyr"
        / "LocalCache",
    ]

    def __init__(self) -> None:
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # BaseDBReader interface
    # ------------------------------------------------------------------

    def db_path(self) -> Path | None:
        """Search known paths for any ``.db`` or ``.sqlite`` file."""
        for base in self._KNOWN_PATHS:
            if not base.is_dir():
                continue
            for pattern in ("*.db", "*.sqlite"):
                for candidate in base.rglob(pattern):
                    if candidate.is_file():
                        return candidate
        logger.warning(
            "Windows WhatsApp database not found in any known location"
        )
        return None

    def is_available(self) -> bool:
        """Return ``True`` when the database exists and is readable."""
        return self.db_path() is not None

    def get_media_records(self) -> list[DBMediaRecord]:
        """Return every media record found in the database.

        Best-effort: tries SQLite format similar to macOS.  If the file
        is not SQLite or the expected tables are missing, returns an
        empty list with a warning.
        """
        path = self.db_path()
        if path is None:
            logger.warning(
                "No Windows WhatsApp database available — returning empty list"
            )
            return []

        try:
            self._conn = sqlite3.connect(
                f"file:{path}?mode=ro", uri=True
            )
            self._conn.row_factory = sqlite3.Row
        except sqlite3.OperationalError as exc:
            logger.warning(
                "Cannot open Windows WhatsApp database at {}: {}", path, exc
            )
            return []

        return self._try_read_media()

    def close(self) -> None:
        """Release any resources held by the reader."""
        if self._conn is not None:
            with contextlib.suppress(sqlite3.Error):
                self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _try_read_media(self) -> list[DBMediaRecord]:
        """Attempt to query media records from the open connection."""
        assert self._conn is not None  # noqa: S101

        # Discover available tables to pick the right query strategy.
        try:
            tables: set[str] = {
                row[0]
                for row in self._conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        except sqlite3.Error as exc:
            logger.warning(
                "Failed to list tables in Windows WhatsApp DB: {}", exc
            )
            return []

        # Strategy 1 — Chat Storage schema (similar to macOS)
        if "ZWAMEDIAITEM" in tables and "ZWAMESSAGE" in tables:
            return self._query_zwamedia()

        # Strategy 2 — message_media / messages tables (Android-like export)
        if "message_media" in tables and "messages" in tables:
            return self._query_message_media()

        logger.warning(
            "Windows WhatsApp database does not contain recognised "
            "media tables (found: {}). Format may be unsupported.",
            ", ".join(sorted(tables)[:15]),
        )
        return []

    def _query_zwamedia(self) -> list[DBMediaRecord]:
        """Query the Core Data (``ZWAMEDIAITEM`` / ``ZWAMESSAGE``) schema."""
        assert self._conn is not None  # noqa: S101
        query = """
            SELECT
                m.ZMESSAGEDATE   AS timestamp,
                mi.ZVCARDSTRING  AS media_type,
                COALESCE(cs.ZCONTACTJID, m.ZFROMJID, '')  AS jid,
                COALESCE(cs.ZPARTNERNAME, '')              AS contact_name,
                CASE WHEN cs.ZCONTACTJID LIKE '%@g.us' THEN 1 ELSE 0 END AS is_group
            FROM ZWAMEDIAITEM mi
            JOIN ZWAMESSAGE m  ON mi.ZMESSAGE = m.Z_PK
            LEFT JOIN ZWACHATSESSION cs ON m.ZCHATSESSION = cs.Z_PK
            WHERE mi.ZVCARDSTRING IS NOT NULL
        """
        return self._execute_and_map(query)

    def _query_message_media(self) -> list[DBMediaRecord]:
        """Query the ``message_media`` / ``messages`` schema."""
        assert self._conn is not None  # noqa: S101
        query = """
            SELECT
                msg.timestamp    AS timestamp,
                mm.mime_type     AS media_type,
                COALESCE(msg.key_remote_jid, '')  AS jid,
                COALESCE(msg.key_remote_jid, '')  AS contact_name,
                CASE WHEN msg.key_remote_jid LIKE '%@g.us' THEN 1 ELSE 0 END AS is_group
            FROM message_media mm
            JOIN messages msg ON mm.message_row_id = msg._id
            WHERE mm.mime_type IS NOT NULL
        """
        return self._execute_and_map(query)

    def _execute_and_map(self, query: str) -> list[DBMediaRecord]:
        """Execute *query* and convert rows to :class:`DBMediaRecord`."""
        assert self._conn is not None  # noqa: S101
        records: list[DBMediaRecord] = []

        try:
            cursor = self._conn.execute(query)
        except sqlite3.Error as exc:
            logger.warning(
                "Failed to query Windows WhatsApp database: {}", exc
            )
            return []

        for row in cursor:
            media_type = self._resolve_media_type(row["media_type"])
            if media_type is None:
                continue

            jid: str = row["jid"] or ""
            phone = jid.split("@")[0] if "@" in jid else None

            records.append(
                DBMediaRecord(
                    timestamp=float(row["timestamp"] or 0),
                    media_type=media_type,
                    contact_name=row["contact_name"] or "Unknown",
                    phone=phone,
                    is_group=bool(row["is_group"]),
                    jid=jid or None,
                ),
            )

        logger.info(
            "Windows WhatsApp DB: found {} media records", len(records)
        )
        return records

    @staticmethod
    def _resolve_media_type(raw: str | int | None) -> MediaType | None:
        """Map a raw DB value to :class:`MediaType`, or ``None``."""
        if raw is None:
            return None

        # Direct lookup (int code or exact string).
        mapped = _MEDIA_TYPE_MAP.get(raw)
        if mapped is not None:
            return mapped

        # Fallback: try to match by MIME prefix (e.g. "image/jpeg").
        if isinstance(raw, str):
            prefix = raw.split("/")[0].lower()
            return _MEDIA_TYPE_MAP.get(prefix)

        return None
