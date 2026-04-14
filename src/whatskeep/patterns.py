"""Regex patterns for detecting and parsing WhatsApp media filenames."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Final

# ---------------------------------------------------------------------------
# Media-type mappings
# ---------------------------------------------------------------------------

_MODERN_TYPE_MAP: Final[dict[str, str]] = {
    "image": "image",
    "audio": "audio",
    "video": "video",
    "ptt": "voice_note",
    "document": "document",
    "sticker": "sticker",
}

_LEGACY_TYPE_MAP: Final[dict[str, str]] = {
    "IMG": "image",
    "VID": "video",
    "DOC": "document",
    "AUD": "audio",
    "PTT": "voice_note",
    "STK": "sticker",
}

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

# Modern pattern (Desktop macOS/Windows) — spaces, hyphens or underscores as separators.
# Examples:
#   WhatsApp Image 2026-04-08 at 14.20.43.jpeg
#   WhatsApp-Image-2024-01-15-at-21.34.04.jpg
#   WhatsApp_Image_2024-06-24_at_18.54.07.png
#   WhatsApp Image 2026-04-08 at 14.20.43 (1).jpeg
_MODERN_RE: Final[re.Pattern[str]] = re.compile(
    r"^WhatsApp"
    r"(?P<sep>[\s_-])"                          # separator character
    r"(?P<type>Image|Audio|Video|Ptt|Document|Sticker)"
    r"(?P=sep)"                                  # same separator
    r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"
    r"(?P=sep)at(?P=sep)"
    r"(?P<hour>\d{2})\.(?P<minute>\d{2})\.(?P<second>\d{2})"
    r"(?:\s\((?P<dup>\d+)\))?"                   # optional duplicate index
    r"\.(?P<ext>[a-zA-Z0-9]+)$",
)

# Legacy Android pattern: IMG-20220331-WA0076.jpg
_LEGACY_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<type>IMG|VID|DOC|AUD|PTT|STK)"
    r"-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})"
    r"-WA(?P<seq>\d+)"
    r"\.(?P<ext>[a-zA-Z0-9]+)$",
)

# Chat export pattern: WhatsApp Chat - Contact Name.zip
_CHAT_RE: Final[re.Pattern[str]] = re.compile(
    r"^WhatsApp Chat - (?P<contact>.+)\.zip$",
)

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ParsedWhatsAppFile:
    """Structured result of parsing a WhatsApp filename."""

    media_type: str
    timestamp: datetime
    extension: str
    duplicate_index: int | None
    is_chat_export: bool
    contact_name: str | None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_whatsapp_filename(filename: str) -> ParsedWhatsAppFile | None:
    """Parse a WhatsApp media filename and return structured data.

    Returns ``None`` when *filename* does not match any known WhatsApp
    naming convention.
    """

    # --- Modern pattern ---------------------------------------------------
    m = _MODERN_RE.match(filename)
    if m:
        raw_type = m.group("type").lower()
        media_type = _MODERN_TYPE_MAP[raw_type]
        ts = datetime(
            int(m.group("year")),
            int(m.group("month")),
            int(m.group("day")),
            int(m.group("hour")),
            int(m.group("minute")),
            int(m.group("second")),
        )
        dup = int(m.group("dup")) if m.group("dup") else None
        return ParsedWhatsAppFile(
            media_type=media_type,
            timestamp=ts,
            extension=m.group("ext").lower(),
            duplicate_index=dup,
            is_chat_export=False,
            contact_name=None,
        )

    # --- Legacy pattern ---------------------------------------------------
    m = _LEGACY_RE.match(filename)
    if m:
        media_type = _LEGACY_TYPE_MAP[m.group("type")]
        ts = datetime(
            int(m.group("year")),
            int(m.group("month")),
            int(m.group("day")),
        )
        return ParsedWhatsAppFile(
            media_type=media_type,
            timestamp=ts,
            extension=m.group("ext").lower(),
            duplicate_index=None,
            is_chat_export=False,
            contact_name=None,
        )

    # --- Chat export pattern ----------------------------------------------
    m = _CHAT_RE.match(filename)
    if m:
        return ParsedWhatsAppFile(
            media_type="document",
            timestamp=datetime(1970, 1, 1),
            extension="zip",
            duplicate_index=None,
            is_chat_export=True,
            contact_name=m.group("contact"),
        )

    return None


def is_whatsapp_file(filename: str) -> bool:
    """Return ``True`` if *filename* looks like a WhatsApp media file."""
    return parse_whatsapp_filename(filename) is not None
