"""Local tracking database for organized files and deletion detection."""

from __future__ import annotations

import platform
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from whatskeep.config import get_config_dir

_TRACKING_DB = "tracking.db"

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS tracked_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_name TEXT NOT NULL,
    dest_path TEXT NOT NULL,
    media_type TEXT NOT NULL,
    contact_name TEXT,
    sender_name TEXT,
    wa_message_date REAL,
    wa_media_path TEXT,
    file_hash TEXT,
    organized_at TEXT NOT NULL,
    deleted_from_chat INTEGER DEFAULT 0,
    deleted_detected_at TEXT,
    UNIQUE(dest_path)
);
"""

# macOS Finder tag colors
_FINDER_TAG_DELETED = "Red"
_FINDER_TAG_NAME = "Deleted from WhatsApp"


class Tracker:
    """Track organized files and detect when originals are deleted from WhatsApp."""

    def __init__(self) -> None:
        import threading

        self._db_path = get_config_dir() / _TRACKING_DB
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        conn = self._get_conn()
        conn.executescript(_SCHEMA)
        conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
        return self._conn

    def track_file(
        self,
        original_name: str,
        dest_path: Path,
        media_type: str,
        contact_name: str | None = None,
        sender_name: str | None = None,
        wa_message_date: float | None = None,
        wa_media_path: str | None = None,
        file_hash: str | None = None,
    ) -> None:
        """Record an organized file for future deletion tracking."""
        with self._lock:
            self._track_file_locked(
                original_name, dest_path, media_type, contact_name,
                sender_name, wa_message_date, wa_media_path, file_hash,
            )

    def _track_file_locked(
        self,
        original_name: str,
        dest_path: Path,
        media_type: str,
        contact_name: str | None,
        sender_name: str | None,
        wa_message_date: float | None,
        wa_media_path: str | None,
        file_hash: str | None,
    ) -> None:
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO tracked_files
            (original_name, dest_path, media_type, contact_name, sender_name,
             wa_message_date, wa_media_path, file_hash, organized_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                original_name,
                str(dest_path),
                media_type,
                contact_name,
                sender_name,
                wa_message_date,
                wa_media_path,
                file_hash,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()

    def check_deletions(self, wa_db_path: Path) -> list[dict]:
        """Compare tracked files against WhatsApp DB to find deleted messages.

        Returns list of dicts with info about files whose originals were deleted.
        """
        conn = self._get_conn()

        # Get all tracked files that haven't been marked as deleted yet
        rows = conn.execute(
            """SELECT id, dest_path, wa_message_date, wa_media_path, contact_name,
                      original_name
            FROM tracked_files
            WHERE deleted_from_chat = 0
              AND wa_message_date IS NOT NULL""",
        ).fetchall()

        if not rows:
            return []

        # Open WhatsApp DB read-only
        try:
            wa_conn = sqlite3.connect(f"file:{wa_db_path}?mode=ro", uri=True)
        except sqlite3.OperationalError as exc:
            logger.warning(f"Cannot open WhatsApp DB for deletion check: {exc}")
            return []

        deleted: list[dict] = []
        now = datetime.now(timezone.utc).isoformat()

        # First pass: count how many appear deleted
        not_found_count = 0
        for _, _, msg_date, media_path, _, _ in rows:
            if not self._message_exists(wa_conn, msg_date, media_path):
                not_found_count += 1

        # Safety threshold: if >50% appear deleted, something is wrong with DB
        if len(rows) > 10 and not_found_count > len(rows) * 0.5:
            logger.warning(
                f"Aborting deletion check: {not_found_count}/{len(rows)} files appear "
                f"deleted — likely a DB access issue, not actual deletions"
            )
            wa_conn.close()
            return []

        for row_id, dest_path, msg_date, media_path, contact, orig_name in rows:
            # Check if the message still exists in WhatsApp DB
            still_exists = self._message_exists(wa_conn, msg_date, media_path)

            if not still_exists:
                # Mark as deleted
                conn.execute(
                    """UPDATE tracked_files
                    SET deleted_from_chat = 1, deleted_detected_at = ?
                    WHERE id = ?""",
                    (now, row_id),
                )

                dest = Path(dest_path)
                if dest.exists():
                    self._tag_deleted_file(dest)
                    deleted.append({
                        "file": dest_path,
                        "original_name": orig_name,
                        "contact": contact,
                        "detected_at": now,
                    })
                    logger.info(
                        f"Deleted from chat detected: {orig_name} "
                        f"(contact: {contact})"
                    )

        conn.commit()
        wa_conn.close()
        return deleted

    def _message_exists(
        self,
        wa_conn: sqlite3.Connection,
        message_date: float,
        media_path: str | None,
    ) -> bool:
        """Check if a message still exists in the WhatsApp database."""
        # Primary check: match by message date + media path
        if media_path:
            row = wa_conn.execute(
                """SELECT COUNT(*) FROM ZWAMEDIAITEM mi
                JOIN ZWAMESSAGE m ON mi.ZMESSAGE = m.Z_PK
                WHERE m.ZMESSAGEDATE = ?
                  AND mi.ZMEDIALOCALPATH = ?""",
                (message_date, media_path),
            ).fetchone()
            if row and row[0] > 0:
                return True

        # Fallback: match by message date only (media path might change)
        row = wa_conn.execute(
            """SELECT COUNT(*) FROM ZWAMESSAGE
            WHERE ZMESSAGEDATE = ?""",
            (message_date,),
        ).fetchone()
        return bool(row and row[0] > 0)

    def _tag_deleted_file(self, path: Path) -> None:
        """Tag a file as deleted from WhatsApp chat.

        On macOS: adds a red Finder tag.
        On all platforms: renames with [DELETED] prefix.
        """
        system = platform.system()

        if system == "Darwin":
            self._add_macos_finder_tag(path)

        # Rename with prefix for universal visibility
        if not path.name.startswith("[DELETED]"):
            new_name = f"[DELETED] {path.name}"
            new_path = path.parent / new_name
            if not new_path.exists():
                path.rename(new_path)
                logger.info(f"Tagged as deleted: {new_name}")

                # Update tracking DB with new path
                conn = self._get_conn()
                conn.execute(
                    "UPDATE tracked_files SET dest_path = ? WHERE dest_path = ?",
                    (str(new_path), str(path)),
                )
                conn.commit()

    def _add_macos_finder_tag(self, path: Path) -> None:
        """Add a red Finder tag on macOS using xattr."""
        try:
            # Add red color label (6 = red in Finder)
            import plistlib

            # Read existing tags
            try:
                result = subprocess.run(
                    ["xattr", "-px", "com.apple.metadata:_kMDItemUserTags", str(path)],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    hex_data = result.stdout.strip().replace(" ", "").replace("\n", "")
                    existing = plistlib.loads(bytes.fromhex(hex_data))
                else:
                    existing = []
            except Exception:
                existing = []

            # Add our tag
            tag = f"{_FINDER_TAG_NAME}\n6"  # \n6 = red color
            if tag not in existing:
                existing.append(tag)
                tag_data = plistlib.dumps(existing, fmt=plistlib.FMT_BINARY)
                subprocess.run(
                    ["xattr", "-wx", "com.apple.metadata:_kMDItemUserTags",
                     tag_data.hex(), str(path)],
                    capture_output=True,
                )
        except Exception as exc:
            logger.debug(f"Failed to add Finder tag: {exc}")

    def get_stats(self) -> dict:
        """Return tracking statistics."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM tracked_files").fetchone()[0]
        deleted = conn.execute(
            "SELECT COUNT(*) FROM tracked_files WHERE deleted_from_chat = 1"
        ).fetchone()[0]
        return {
            "total_tracked": total,
            "deleted_from_chat": deleted,
            "active": total - deleted,
        }

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
