"""Main organization engine — scans, correlates, and moves WhatsApp media."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from whatskeep.config import load_config, resolve_backup_dir, resolve_download_dir
from whatskeep.db import get_db_reader
from whatskeep.models import (
    BackupMode,
    Contact,
    MediaFile,
    MediaType,
    OrganizationResult,
)
from whatskeep.patterns import parse_whatsapp_filename
from whatskeep.tracker import Tracker
from whatskeep.utils.dedup import file_is_stable, files_are_duplicates
from whatskeep.utils.fs import resolve_duplicate, safe_move, validate_dest_within_root
from whatskeep.utils.phone import format_phone

if TYPE_CHECKING:
    from pathlib import Path

    from whatskeep.db.base import BaseDBReader

# ---------------------------------------------------------------------------
# Extension → media-type group for DB lookup matching
# ---------------------------------------------------------------------------

EXT_TO_GROUP: dict[str, str] = {
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".webp": "image",
    ".gif": "image",
    ".heic": "image",
    ".opus": "audio",
    ".ogg": "audio",
    ".m4a": "audio",
    ".mp3": "audio",
    ".aac": "audio",
    ".wav": "audio",
    ".mp4": "video",
    ".mov": "video",
    ".avi": "video",
    ".3gp": "video",
    ".pdf": "document",
    ".docx": "document",
    ".xlsx": "document",
    ".pptx": "document",
    ".txt": "document",
    ".zip": "document",
}


def _looks_like_phone(name: str) -> bool:
    """Check if a contact name is just a phone number (not saved in address book)."""
    from whatskeep.utils.phone import is_phone_number

    return is_phone_number(name)


class Organizer:
    """Ties together scanning, DB correlation, dedup, and file movement."""

    def __init__(self, config: dict | None = None) -> None:
        self.config = config or load_config()
        self.download_dir = resolve_download_dir(self.config)
        self.backup_dir = resolve_backup_dir(self.config)
        self._db_reader: BaseDBReader | None = None
        self._tracker: Tracker | None = None
        self._lookup: dict[
            tuple[int, str],
            tuple[str, str | None, bool, str | None, str | None, str | None],
        ] = {}

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(self, dry_run: bool = False) -> OrganizationResult:
        """Run one organization pass."""
        result = OrganizationResult()

        # 0. Init tracker
        if not dry_run and self._tracker is None:
            self._tracker = Tracker()

        # 1. Load DB lookup
        self._init_db()

        # 2. Scan downloads for WhatsApp files
        files = self._scan_downloads()
        result.total_files = len(files)

        # 3. Process each file
        for media_file in files:
            try:
                self._process_file(media_file, result, dry_run)
            except Exception as e:
                result.errors += 1
                result.error_details.append(f"{media_file.path.name}: {e}")
                logger.error(f"Error processing {media_file.path.name}: {e}")

        # 4. Check for deleted messages
        if not dry_run and self._tracker and self._db_reader:
            db_path = self._db_reader.db_path()
            if db_path:
                deleted = self._tracker.check_deletions(db_path)
                if deleted:
                    logger.info(
                        f"Detected {len(deleted)} file(s) deleted from WhatsApp chats"
                    )

        return result

    def export_all(self, dry_run: bool = False) -> OrganizationResult:
        """Export ALL media from WhatsApp's internal storage.

        Copies (not moves) files from WhatsApp's internal ``Message/Media/``
        directory, organizing them by contact/group using DB metadata.
        """
        import platform
        import shutil
        from pathlib import Path

        result = OrganizationResult()

        if not dry_run and self._tracker is None:
            self._tracker = Tracker()

        self._init_db()
        if not self._db_reader or not self._db_reader.is_available():
            logger.error("WhatsApp DB not available — cannot export")
            return result

        # Locate WhatsApp internal media storage
        if platform.system() != "Darwin":
            logger.error("Export currently only supported on macOS")
            return result

        wa_base = (
            Path.home()
            / "Library"
            / "Group Containers"
            / "group.net.whatsapp.WhatsApp.shared"
        )
        media_base = wa_base / "Message" / "Media"
        if not media_base.is_dir():
            logger.error(f"WhatsApp media directory not found: {media_base}")
            return result

        org_config = self.config.get("organization", {})
        exported = 0
        skipped = 0

        import sqlite3

        db_path = self._db_reader.db_path()
        if not db_path:
            return result

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.execute("PRAGMA busy_timeout=5000")
        rows = conn.execute("""
            SELECT
                mi.ZMEDIALOCALPATH,
                m.ZMESSAGEDATE,
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
        """).fetchall()
        conn.close()

        media_types_config = self.config.get("media_types", {})
        result.total_files = len(rows)
        logger.info(f"Processing {len(rows)} media records")

        sticker_msg_type = 15

        for (
            media_path, msg_date, partner_name, contact_jid,
            push_name, member_jid, contact_push_name, msg_type,
        ) in rows:
            try:
                # Build source path (DB stores "Media/..." but files are in "Message/Media/...")
                src = wa_base / "Message" / media_path
                # Validate source stays within WhatsApp storage (prevent path traversal)
                wa_message_root = wa_base / "Message"
                if not validate_dest_within_root(src, wa_message_root):
                    result.errors += 1
                    continue
                if not src.exists():
                    skipped += 1
                    continue

                # Skip thumbnails
                if src.suffix == ".thumb":
                    skipped += 1
                    continue

                # Determine media type — stickers identified by message type 15
                if msg_type == sticker_msg_type:
                    media_group: str = "sticker"
                else:
                    ext = src.suffix.lower()
                    resolved_group = EXT_TO_GROUP.get(ext)
                    if not resolved_group:
                        skipped += 1
                        continue
                    media_group = resolved_group

                # Apply media type filter from config
                if not media_types_config.get(media_group, True):
                    skipped += 1
                    continue

                # Build contact info
                is_group = "@g.us" in (contact_jid or "")

                # Use WhatsApp push name as fallback when contact not in address book
                display_name = partner_name
                if not is_group and _looks_like_phone(partner_name) and contact_push_name:
                    display_name = contact_push_name

                contact = Contact(
                    name=display_name,
                    phone=format_phone(contact_jid),
                    is_group=is_group,
                    jid=contact_jid,
                    sender_name=push_name if is_group else None,
                    sender_phone=format_phone(member_jid) if is_group and member_jid else None,
                )

                # Build destination — Contacts/ or Groups/ prefix
                category = "Groups" if is_group else "Contacts"
                folder = contact.folder_name(
                    show_phone=org_config.get("show_phone", True),
                    group_suffix="",
                )
                type_folder = media_group.capitalize()
                dest_dir = self.backup_dir / category / folder / type_folder

                # Filename: use original UUID name but prefix sender for groups
                filename = src.name
                if is_group and push_name:
                    from whatskeep.utils.fs import sanitize_dirname as _sanitize

                    safe_sender = _sanitize(push_name)
                    sender_phone = format_phone(member_jid) if member_jid else None
                    if sender_phone:
                        filename = f"[{safe_sender} ({sender_phone})] {filename}"
                    else:
                        filename = f"[{safe_sender}] {filename}"

                dest = dest_dir / filename

                if not validate_dest_within_root(dest, self.backup_dir):
                    result.errors += 1
                    continue

                # Skip if already exported
                if dest.exists():
                    skipped += 1
                    continue

                if not dry_run:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(src), str(dest))

                    # Track
                    if self._tracker:
                        core_data_ts = msg_date or 0
                        self._tracker.track_file(
                            original_name=src.name,
                            dest_path=dest,
                            media_type=media_group,
                            contact_name=partner_name,
                            sender_name=push_name,
                            wa_message_date=core_data_ts,
                        )

                exported += 1
                result.organized += 1
                result.bytes_organized += src.stat().st_size

                # Stats
                result.by_contact[display_name] = result.by_contact.get(display_name, 0) + 1
                result.by_type[media_group] = result.by_type.get(media_group, 0) + 1

            except Exception as exc:
                result.errors += 1
                result.error_details.append(f"{media_path}: {exc}")

        result.skipped = skipped
        logger.info(
            f"Export complete: {exported} exported, {skipped} skipped, "
            f"{result.errors} errors"
        )
        return result

    def close(self) -> None:
        """Release resources held by the DB reader and tracker."""
        if self._db_reader:
            self._db_reader.close()
        if self._tracker:
            self._tracker.close()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Initialize DB reader and build lookup."""
        # Close only the DB reader (not the tracker)
        if self._db_reader:
            self._db_reader.close()
        self._db_reader = get_db_reader()
        if self._db_reader and self._db_reader.is_available():
            self._lookup = self._db_reader.build_lookup()
            logger.info(f"DB lookup loaded: {len(self._lookup)} entries")
        else:
            self._lookup = {}
            logger.warning("WhatsApp DB not available — organizing by type/date only")

    def _scan_downloads(self) -> list[MediaFile]:
        """Scan downloads folder for WhatsApp files."""
        files: list[MediaFile] = []
        if not self.download_dir.is_dir():
            logger.warning(f"Downloads dir not found: {self.download_dir}")
            return files

        media_types_config = self.config.get("media_types", {})

        for entry in sorted(self.download_dir.iterdir()):
            if not entry.is_file():
                continue

            parsed = parse_whatsapp_filename(entry.name)
            if not parsed:
                continue

            # Skip files modified very recently (likely still downloading)
            try:
                import time as _time

                age = _time.time() - entry.stat().st_mtime
                if age < 2.0:
                    logger.debug(f"Skipping recently modified file: {entry.name}")
                    continue
            except OSError:
                continue

            # Chat exports are always included (handled separately later)
            if not parsed.is_chat_export and not media_types_config.get(
                parsed.media_type, True
            ):
                continue

            mt = (
                MediaType.DOCUMENT
                if parsed.is_chat_export
                else MediaType(parsed.media_type)
            )
            media_file = MediaFile(
                path=entry,
                media_type=mt,
                timestamp=parsed.timestamp,
                extension=parsed.extension,
                duplicate_index=parsed.duplicate_index,
                size_bytes=entry.stat().st_size,
            )
            # Stash chat-export metadata for later use
            media_file.is_chat_export = parsed.is_chat_export
            media_file.chat_contact = parsed.contact_name
            files.append(media_file)

        return files

    def _process_file(
        self,
        media_file: MediaFile,
        result: OrganizationResult,
        dry_run: bool,
    ) -> None:
        """Process a single media file: correlate, build path, move."""
        org_config = self.config.get("organization", {})
        backup_config = self.config.get("backup", {})
        dedup_config = self.config.get("deduplication", {})

        is_chat_export: bool = media_file.is_chat_export
        chat_contact: str | None = media_file.chat_contact

        # 1. Try to correlate with contact via DB lookup (skip for chat exports)
        if not is_chat_export:
            contact = self._lookup_contact(media_file)
            media_file.contact = contact
        else:
            media_file.contact = None

        contact = media_file.contact

        # 2. Check allowlist/blocklist (chat exports bypass filtering)
        if not is_chat_export and not self._should_process(contact, backup_config):
            result.skipped += 1
            return

        # 3. Build destination path
        if is_chat_export:
            dest = self._build_chat_export_path(media_file, chat_contact, org_config)
        else:
            dest = self._build_dest_path(media_file, org_config)

        # 3b. Validate destination stays within backup root (path traversal guard)
        if not validate_dest_within_root(dest, self.backup_dir):
            result.errors += 1
            result.error_details.append(
                f"{media_file.path.name}: destination escapes backup dir"
            )
            logger.warning(
                f"Path traversal blocked: {media_file.path.name} → {dest}"
            )
            return

        # 4. Handle duplicates
        if dest.exists():
            algo = dedup_config.get("algorithm", "sha256")
            if dedup_config.get("enabled", True) and files_are_duplicates(
                media_file.path, dest, algo
            ):
                result.duplicates += 1
                result.bytes_saved += media_file.size_bytes
                if not dry_run:
                    # Safety: verify source still exists and is stable
                    if media_file.path.exists() and file_is_stable(
                        media_file.path, wait=0.5
                    ):
                        media_file.path.unlink()
                        logger.info(
                            f"Duplicate removed: {media_file.path.name} "
                            f"(identical to {dest.name}, {algo} verified)"
                        )
                    else:
                        logger.warning(
                            f"Skipped deletion of {media_file.path.name} "
                            f"— file unstable or missing"
                        )
                else:
                    logger.info(
                        f"[DRY-RUN] Would remove duplicate: {media_file.path.name}"
                    )
                return
            dest = resolve_duplicate(dest)

        # 5. Move file
        if not dry_run:
            safe_move(media_file.path, dest)

            # 5b. Track file for deletion detection
            if self._tracker and contact:
                ts_unix = int(media_file.timestamp.timestamp())
                # Recover the Core Data timestamp for DB matching
                core_data_ts = ts_unix - 978307200
                self._tracker.track_file(
                    original_name=media_file.path.name,
                    dest_path=dest,
                    media_type=media_file.media_type.value,
                    contact_name=contact.name,
                    sender_name=contact.sender_name,
                    wa_message_date=core_data_ts,
                    file_hash=None,
                )

        result.organized += 1
        result.bytes_organized += media_file.size_bytes

        # Track stats
        if is_chat_export:
            contact_key = chat_contact or "_Chat Exports"
        else:
            contact_key = contact.name if contact else "_Unidentified"
        result.by_contact[contact_key] = result.by_contact.get(contact_key, 0) + 1
        result.by_type[media_file.media_type.value] = (
            result.by_type.get(media_file.media_type.value, 0) + 1
        )

        logger.info(
            f"{'[DRY-RUN] ' if dry_run else ''}"
            f"{media_file.path.name} → {dest.relative_to(self.backup_dir)}"
        )

    def _lookup_contact(self, media_file: MediaFile) -> Contact | None:
        """Try to find the contact for a media file via DB lookup."""
        if not self._lookup:
            return None

        ts = int(media_file.timestamp.timestamp())
        ext_group = EXT_TO_GROUP.get(f".{media_file.extension}", "unknown")

        key = (ts, ext_group)
        if key in self._lookup:
            name, phone, is_group, jid, sender_name, sender_jid = self._lookup[key]
            return Contact(
                name=name,
                phone=format_phone(jid),
                is_group=is_group,
                jid=jid,
                sender_name=sender_name,
                sender_phone=format_phone(sender_jid) if sender_jid else None,
            )

        return None

    def _should_process(self, contact: Contact | None, backup_config: dict) -> bool:
        """Check allowlist/blocklist rules."""
        mode = BackupMode(backup_config.get("mode", "all"))
        if mode == BackupMode.ALL:
            return True

        if contact is None:
            return True  # Always process unidentified files

        name = contact.name
        if mode == BackupMode.ALLOWLIST:
            return name in backup_config.get("allowlist", [])
        if mode == BackupMode.BLOCKLIST:
            return name not in backup_config.get("blocklist", [])

        return True

    def _build_dest_path(self, media_file: MediaFile, org_config: dict) -> Path:
        """Build the destination file path for a regular media file."""
        filename = media_file.path.name

        if media_file.contact:
            # Has contact — use Contacts/ or Groups/ prefix
            contact = media_file.contact
            category = "Groups" if contact.is_group else "Contacts"
            folder = contact.folder_name(
                show_phone=org_config.get("show_phone", True),
                group_suffix="",  # No suffix needed — Groups/ prefix is enough
            )
            type_folder = media_file.media_type.value.capitalize()
            dest_dir = self.backup_dir / category / folder / type_folder

            # For group messages, prefix filename with sender name + phone
            if contact.is_group and contact.sender_name:
                from whatskeep.utils.fs import sanitize_dirname

                safe_sender = sanitize_dirname(contact.sender_name)
                if contact.sender_phone:
                    filename = f"[{safe_sender} ({contact.sender_phone})] {filename}"
                else:
                    filename = f"[{safe_sender}] {filename}"
        else:
            # Unidentified
            unid_folder = org_config.get("unidentified_folder", "_Unidentified")
            type_folder = media_file.media_type.value.capitalize()
            if org_config.get("unidentified_by_date", True):
                date_folder = media_file.timestamp.strftime("%Y-%m")
                dest_dir = self.backup_dir / unid_folder / type_folder / date_folder
            else:
                dest_dir = self.backup_dir / unid_folder / type_folder

        return dest_dir / filename

    def _build_chat_export_path(
        self,
        media_file: MediaFile,
        contact_name: str | None,
        org_config: dict,
    ) -> Path:
        """Build the destination path for a chat export file.

        Chat exports go to ``_Chat Exports/{contact_name}/``.
        """
        exports_folder: str = org_config.get("chat_exports_folder", "_Chat Exports")
        subfolder = contact_name or "_Unknown"
        dest_dir = self.backup_dir / exports_folder / subfolder
        return dest_dir / media_file.path.name
