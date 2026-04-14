"""Abstract base class for WhatsApp database readers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from whatskeep.models import DBMediaRecord


class BaseDBReader(ABC):
    """Read-only interface to a WhatsApp Desktop local database."""

    @abstractmethod
    def db_path(self) -> Path | None:
        """Return the database file path, or ``None`` if it cannot be located."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return ``True`` when the database exists and is readable."""

    @abstractmethod
    def get_media_records(self) -> list[DBMediaRecord]:
        """Return every media record found in the database.

        The implementation must open the database **read-only** and tolerate
        the file being locked by the running WhatsApp process (WAL mode /
        retry with back-off).
        """

    def build_lookup(
        self,
        tolerance: int = 3,
    ) -> dict[
        tuple[int, str],
        tuple[str, str | None, bool, str | None, str | None, str | None],
    ]:
        """Build a fast-lookup dict from DB records.

        Key:   ``(unix_timestamp, media_type_group)``
        Value: ``(contact_name, phone, is_group, jid, sender_name, sender_jid)``

        *tolerance* expands each record into ``±tolerance`` second keys so
        that file-timestamp → DB-timestamp matching is forgiving of small
        clock skew.
        """
        lookup: dict[
            tuple[int, str],
            tuple[str, str | None, bool, str | None, str | None, str | None],
        ] = {}
        for rec in self.get_media_records():
            ts = int(rec.timestamp)
            info = (
                rec.contact_name,
                rec.phone,
                rec.is_group,
                rec.jid,
                rec.sender_name,
                rec.sender_jid,
            )
            media_group = _media_type_to_group(rec.media_type.value)
            for offset in range(-tolerance, tolerance + 1):
                key = (ts + offset, media_group)
                if key not in lookup:
                    lookup[key] = info
        return lookup

    def close(self) -> None:  # noqa: B027
        """Release any resources held by the reader."""


# Maps fine-grained MediaType values to the broader groups used in lookup keys.
_EXT_GROUP_MAP: dict[str, str] = {
    "image": "image",
    "audio": "audio",
    "video": "video",
    "document": "document",
    "sticker": "image",
    "gif": "image",
    "voice_note": "audio",
}


def _media_type_to_group(media_type: str) -> str:
    return _EXT_GROUP_MAP.get(media_type, "unknown")
