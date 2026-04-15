"""Storage statistics for WhatsKeep backups."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class StorageStats:
    """Aggregated storage metrics for a backup directory."""

    total_files: int = 0
    total_bytes: int = 0
    by_contact: dict[str, int] = field(default_factory=dict)
    by_type: dict[str, int] = field(default_factory=dict)
    duplicates_skipped: int = 0
    bytes_saved: int = 0


def calculate_stats(backup_dir: Path) -> StorageStats:
    """Walk *backup_dir* and calculate storage statistics.

    Directory structure assumed::

        backup_dir/
            <contact_name>/
                <media_type>/
                    file1.jpg
                    ...

    Files directly inside *backup_dir* are counted under contact ``_root``
    and type ``_unknown``.
    """
    stats = StorageStats()

    if not backup_dir.is_dir():
        return stats

    for item in backup_dir.rglob("*"):
        if not item.is_file():
            continue

        try:
            size = item.stat().st_size
        except OSError:
            continue

        stats.total_files += 1
        stats.total_bytes += size

        # Determine contact and media type from path hierarchy
        try:
            relative = item.relative_to(backup_dir)
            parts = relative.parts
        except ValueError:
            parts = ()

        # Path hierarchy varies:
        # Account structure: <account>/Contacts/<name>/<type>/file
        # Flat structure:    Contacts/<name>/<type>/file
        # Legacy:            <name>/<type>/file
        categories = {"Contacts", "Groups"}
        p = list(parts)
        # Skip account folder if present (first level not in categories and not _)
        if p and p[0] not in categories and not p[0].startswith("_"):
            p = p[1:]
        # Skip Contacts/Groups category
        if p and p[0] in categories:
            p = p[1:]

        contact = p[0] if len(p) >= 2 else "_root"
        ext_fallback = item.suffix.lstrip(".").lower() or "_unknown"
        media_type = p[1] if len(p) >= 3 else ext_fallback

        stats.by_contact[contact] = stats.by_contact.get(contact, 0) + size
        stats.by_type[media_type] = stats.by_type.get(media_type, 0) + size

    return stats
