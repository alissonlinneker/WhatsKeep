"""macOS ChatStorage.sqlite reader for WhatsApp Desktop."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from loguru import logger

from whatskeep.db.base import BaseDBReader
from whatskeep.models import DBMediaRecord, MediaType
from whatskeep.utils.phone import extract_phone_from_jid

# Core Data epoch: 2001-01-01 00:00:00 UTC expressed as Unix timestamp.
CORE_DATA_EPOCH = 978307200

_DB_RELATIVE = (
    "Library"
    "/Group Containers"
    "/group.net.whatsapp.WhatsApp.shared"
    "/ChatStorage.sqlite"
)

# All known WhatsApp container names on macOS
_CONTAINERS = [
    "group.net.whatsapp.WhatsApp.shared",      # Personal
    "group.net.whatsapp.WhatsAppSMB.shared",    # Business
]

_SQL_MEDIA = """\
SELECT
    m.ZMESSAGEDATE,
    mi.ZMEDIALOCALPATH,
    cs.ZPARTNERNAME,
    cs.ZCONTACTJID,
    sender_ppn.ZPUSHNAME,
    gm.ZMEMBERJID,
    contact_ppn.ZPUSHNAME,
    m.ZMESSAGETYPE
FROM ZWAMEDIAITEM mi
JOIN ZWAMESSAGE m ON mi.ZMESSAGE = m.Z_PK
JOIN ZWACHATSESSION cs ON m.ZCHATSESSION = cs.Z_PK
LEFT JOIN ZWAGROUPMEMBER gm ON m.ZGROUPMEMBER = gm.Z_PK
LEFT JOIN ZWAPROFILEPUSHNAME sender_ppn ON gm.ZMEMBERJID = sender_ppn.ZJID
LEFT JOIN ZWAPROFILEPUSHNAME contact_ppn ON cs.ZCONTACTJID = contact_ppn.ZJID
WHERE mi.ZMEDIALOCALPATH IS NOT NULL
  AND mi.ZMEDIALOCALPATH != ''
  AND cs.ZPARTNERNAME IS NOT NULL
"""

_EXT_TO_MEDIA_TYPE: dict[str, MediaType] = {
    ".jpg": MediaType.IMAGE,
    ".jpeg": MediaType.IMAGE,
    ".png": MediaType.IMAGE,
    ".webp": MediaType.IMAGE,
    ".gif": MediaType.IMAGE,
    ".heic": MediaType.IMAGE,
    ".opus": MediaType.AUDIO,
    ".ogg": MediaType.AUDIO,
    ".m4a": MediaType.AUDIO,
    ".mp3": MediaType.AUDIO,
    ".aac": MediaType.AUDIO,
    ".wav": MediaType.AUDIO,
    ".mp4": MediaType.VIDEO,
    ".mov": MediaType.VIDEO,
    ".avi": MediaType.VIDEO,
    ".3gp": MediaType.VIDEO,
    ".pdf": MediaType.DOCUMENT,
    ".docx": MediaType.DOCUMENT,
    ".xlsx": MediaType.DOCUMENT,
    ".pptx": MediaType.DOCUMENT,
    ".txt": MediaType.DOCUMENT,
    ".zip": MediaType.DOCUMENT,
}

_MAX_RETRIES = 3
_RETRY_BACKOFF_SECS = 1.0


def _media_type_from_path(local_path: str) -> MediaType | None:
    """Infer :class:`MediaType` from a file extension."""
    ext = Path(local_path).suffix.lower()
    return _EXT_TO_MEDIA_TYPE.get(ext)


class MacOSDBReader(BaseDBReader):
    """Read-only access to the macOS WhatsApp ChatStorage.sqlite database."""

    def __init__(self, container: str | None = None) -> None:
        self._conn: sqlite3.Connection | None = None
        self._container = container  # e.g. "group.net.whatsapp.WhatsApp.shared"
        self._account_name: str | None = None
        self._account_phone: str | None = None

    @classmethod
    def discover_all(cls) -> list[MacOSDBReader]:
        """Return a reader for each WhatsApp account found on this Mac."""
        readers: list[MacOSDBReader] = []
        for container in _CONTAINERS:
            db = Path.home() / "Library/Group Containers" / container / "ChatStorage.sqlite"
            if db.exists() and db.is_file():
                readers.append(cls(container=container))
        return readers

    # ------------------------------------------------------------------
    # BaseDBReader interface
    # ------------------------------------------------------------------

    def db_path(self) -> Path | None:
        if self._container:
            path = Path.home() / "Library/Group Containers" / self._container / "ChatStorage.sqlite"
        else:
            path = Path.home() / _DB_RELATIVE
        return path if path.exists() else None

    def is_available(self) -> bool:
        p = self.db_path()
        return p is not None and p.is_file()

    def account_info(self) -> tuple[str, str]:
        """Return (account_name, formatted_phone) for this WhatsApp account.

        Reads the owner phone from the container preferences and resolves
        the display name from the push name table.
        """
        if self._account_name and self._account_phone:
            return self._account_name, self._account_phone

        import re

        container = self._container or "group.net.whatsapp.WhatsApp.shared"
        plist = (
            Path.home()
            / "Library/Group Containers"
            / container
            / "Library/Preferences"
            / f"{container}.plist"
        )

        phone_raw = None
        if plist.exists():
            raw = plist.read_bytes()
            idx = raw.find(b"OwnPhoneNumber")
            if idx >= 0:
                nearby = raw[idx : idx + 200]
                # Extract phone from "XXXXX@s.whatsapp.net" pattern (most reliable)
                jid_match = re.search(rb"(\d{10,15})@s\.whatsapp\.net", nearby)
                if jid_match:
                    phone_raw = jid_match.group(1).decode()

        if phone_raw:
            from whatskeep.utils.phone import format_phone

            self._account_phone = format_phone(f"{phone_raw}@s.whatsapp.net") or f"+{phone_raw}"

            # Try to get display name from push name table
            db_path = self.db_path()
            if db_path:
                try:
                    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                    row = conn.execute(
                        "SELECT ZPUSHNAME FROM ZWAPROFILEPUSHNAME WHERE ZJID = ?",
                        (f"{phone_raw}@s.whatsapp.net",),
                    ).fetchone()
                    conn.close()
                    if row and row[0]:
                        self._account_name = row[0]
                except sqlite3.Error:
                    pass

        if not self._account_name:
            self._account_name = "WhatsApp Business" if "SMB" in container else "WhatsApp"

        if not self._account_phone:
            self._account_phone = "Unknown"

        return self._account_name, self._account_phone

    def get_media_records(self) -> list[DBMediaRecord]:
        path = self.db_path()
        if path is None:
            logger.warning("WhatsApp database not found on this system")
            return []

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return self._fetch_records(path)
            except sqlite3.OperationalError as exc:
                msg = str(exc).lower()
                if "locked" in msg or "busy" in msg:
                    if attempt < _MAX_RETRIES:
                        logger.warning(
                            "Database locked, retrying ({}/{})",
                            attempt,
                            _MAX_RETRIES,
                        )
                        time.sleep(_RETRY_BACKOFF_SECS * attempt)
                        continue
                    logger.warning(
                        "Database still locked after {} attempts", _MAX_RETRIES
                    )
                else:
                    logger.warning("Failed to read WhatsApp database: {}", exc)
                return []

        return []  # pragma: no cover — unreachable, satisfies type checker

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _open(self, path: Path) -> sqlite3.Connection:
        """Open (or reuse) a read-only connection with WAL mode."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                f"file:{path}?mode=ro",
                uri=True,
            )
            import contextlib

            with contextlib.suppress(sqlite3.OperationalError):
                # Read-only connections cannot set journal mode; the DB is
                # expected to already be in WAL mode when WhatsApp is running.
                self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _fetch_records(self, path: Path) -> list[DBMediaRecord]:
        conn = self._open(path)
        cursor = conn.execute(_SQL_MEDIA)

        records: list[DBMediaRecord] = []
        # Message type 15 = sticker in WhatsApp
        sticker_msg_type = 15

        for (
            message_date, local_path, partner_name, contact_jid,
            push_name, member_jid, contact_push_name, msg_type,
        ) in cursor:
            # Override media type for stickers (type 15)
            if msg_type == sticker_msg_type:
                media_type: MediaType = MediaType.STICKER
            else:
                resolved = _media_type_from_path(local_path)
                if resolved is None:
                    continue
                media_type = resolved

            unix_ts = (message_date or 0) + CORE_DATA_EPOCH
            is_group = "@g.us" in (contact_jid or "")
            phone = extract_phone_from_jid(contact_jid) if not is_group else None

            # Use WhatsApp push name when contact not saved in address book
            from whatskeep.utils.phone import is_phone_number

            display_name = partner_name
            if not is_group and contact_push_name and is_phone_number(partner_name):
                display_name = contact_push_name

            records.append(
                DBMediaRecord(
                    timestamp=unix_ts,
                    media_type=media_type,
                    contact_name=display_name,
                    phone=phone,
                    is_group=is_group,
                    jid=contact_jid,
                    sender_name=push_name if is_group else None,
                    sender_jid=member_jid if is_group else None,
                )
            )

        logger.debug("Loaded {} media records from ChatStorage.sqlite", len(records))
        return records
