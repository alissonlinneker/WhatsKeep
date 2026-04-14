from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path


class MediaType(str, Enum):
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    STICKER = "sticker"
    GIF = "gif"
    VOICE_NOTE = "voice_note"


class BackupMode(str, Enum):
    ALL = "all"
    ALLOWLIST = "allowlist"
    BLOCKLIST = "blocklist"


# Characters that are invalid in file/folder names across OS platforms.
_UNSAFE_FS_RE = re.compile(r'[/\\:<>|?\*\x00]')


def _is_phone_number(name: str) -> bool:
    """Check if a name is just a phone number."""
    from whatskeep.utils.phone import is_phone_number

    return is_phone_number(name)


@dataclass
class Contact:
    name: str
    phone: str | None = None
    is_group: bool = False
    jid: str | None = None  # xxx@s.whatsapp.net or xxx@g.us
    sender_name: str | None = None  # Push name of sender (group messages only)
    sender_phone: str | None = None  # Formatted phone of sender

    def folder_name(
        self,
        show_phone: bool = True,
        group_suffix: str = "(group)",
    ) -> str:
        """Generate a filesystem-safe folder name.

        Sanitises characters that are invalid on common filesystems while
        preserving emojis and other Unicode.  Optionally appends the phone
        number and/or a group indicator.
        """
        # If name is just a phone number, use the formatted phone instead
        # and don't append phone again (avoid duplication)
        name_is_phone = _is_phone_number(self.name)
        if name_is_phone and self.phone:
            parts: list[str] = [self.phone]
        elif name_is_phone:
            parts = [self.name]
        else:
            parts = [self.name]
            if show_phone and self.phone:
                parts.append(f"({self.phone})")

        if self.is_group:
            parts.append(group_suffix)

        raw = " ".join(parts)

        # Replace unsafe characters with underscore and collapse duplicates.
        sanitised = _UNSAFE_FS_RE.sub("_", raw)

        # Block path traversal sequences.
        sanitised = sanitised.replace("..", "_")

        # Strip leading/trailing whitespace and dots (Windows restriction).
        sanitised = sanitised.strip().strip(".")

        return sanitised or "_"


@dataclass
class MediaFile:
    path: Path
    media_type: MediaType
    timestamp: datetime
    extension: str
    contact: Contact | None = None
    duplicate_index: int | None = None
    size_bytes: int = 0
    is_chat_export: bool = False
    chat_contact: str | None = None

    @property
    def is_identified(self) -> bool:
        return self.contact is not None


@dataclass
class OrganizationResult:
    total_files: int = 0
    organized: int = 0
    skipped: int = 0
    duplicates: int = 0
    errors: int = 0
    bytes_organized: int = 0
    bytes_saved: int = 0  # from dedup
    by_contact: dict[str, int] = field(default_factory=dict)
    by_type: dict[str, int] = field(default_factory=dict)
    error_details: list[str] = field(default_factory=list)


@dataclass
class DBMediaRecord:
    """A media record from the WhatsApp database."""

    timestamp: float  # Unix timestamp
    media_type: MediaType
    contact_name: str
    phone: str | None = None
    is_group: bool = False
    jid: str | None = None
    sender_name: str | None = None  # Push name of sender (for group messages)
    sender_jid: str | None = None  # JID of sender (for phone extraction)
