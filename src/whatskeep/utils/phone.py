"""Phone number formatting utilities for WhatsApp JIDs."""
from __future__ import annotations

import re

_INDIVIDUAL_JID = re.compile(r"^(\d+)@s\.whatsapp\.net$")


def extract_phone_from_jid(jid: str) -> str | None:
    """Extract raw phone digits from a WhatsApp JID.

    Returns ``None`` for group JIDs (``@g.us``) or malformed input.
    """
    if not jid:
        return None

    match = _INDIVIDUAL_JID.match(jid)
    if match:
        return match.group(1)
    return None


def format_phone(jid: str | None) -> str | None:
    """Extract and format a phone number from a WhatsApp JID.

    Brazilian numbers  (55…): ``+55 62 99999-1234``
    US/Canada numbers  (1…):  ``+1 555 123-4567``
    Others:                    ``+{country} {rest}``

    Returns ``None`` for group JIDs or invalid input.
    """
    if jid is None:
        return None

    raw = extract_phone_from_jid(jid)
    if raw is None:
        return None

    return _format_raw(raw)


def _format_raw(number: str) -> str:
    """Apply simple heuristic formatting to a raw phone string."""
    # Brazilian: 55 + 2-digit area + 8-or-9-digit subscriber
    if number.startswith("55") and len(number) in (12, 13):
        cc = number[:2]
        area = number[2:4]
        subscriber = number[4:]
        if len(subscriber) == 9:
            return f"+{cc} {area} {subscriber[:5]}-{subscriber[5:]}"
        # 8-digit landline
        return f"+{cc} {area} {subscriber[:4]}-{subscriber[4:]}"

    # US / Canada: 1 + 3-digit area + 7-digit subscriber
    if number.startswith("1") and len(number) == 11:
        cc = number[0]
        area = number[1:4]
        subscriber = number[4:]
        return f"+{cc} {area} {subscriber[:3]}-{subscriber[3:]}"

    # Generic: assume first 1-3 digits are country code — pick the shortest
    # that leaves at least 6 subscriber digits.
    for cc_len in (1, 2, 3):
        if len(number) > cc_len + 5:
            cc = number[:cc_len]
            rest = number[cc_len:]
            return f"+{cc} {rest}"

    # Fallback — just prefix with +
    return f"+{number}"


def is_phone_number(name: str) -> bool:
    """Check if a string is just a phone number (digits, spaces, +, -, parens)."""
    if not name:
        return False
    stripped = re.sub(r"[+\s\-()]", "", name)
    return stripped.isdigit() and len(stripped) >= 7
