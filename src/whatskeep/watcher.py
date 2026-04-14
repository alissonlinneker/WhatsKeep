"""Real-time file watcher — captures WhatsApp media instantly before messages can be deleted."""

from __future__ import annotations

import shutil
import threading
import time
from pathlib import Path

from loguru import logger
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from whatskeep.config import load_config, resolve_backup_dir, resolve_download_dir
from whatskeep.db import get_db_reader
from whatskeep.models import Contact
from whatskeep.patterns import ParsedWhatsAppFile, is_whatsapp_file, parse_whatsapp_filename
from whatskeep.tracker import Tracker
from whatskeep.utils.fs import resolve_duplicate, sanitize_dirname, validate_dest_within_root
from whatskeep.utils.phone import format_phone

# Extension → media type group for DB lookup
_EXT_TO_GROUP: dict[str, str] = {
    ".jpg": "image", ".jpeg": "image", ".png": "image", ".webp": "image",
    ".gif": "image", ".heic": "image",
    ".opus": "audio", ".ogg": "audio", ".m4a": "audio", ".mp3": "audio",
    ".aac": "audio", ".wav": "audio",
    ".mp4": "video", ".mov": "video", ".avi": "video", ".3gp": "video",
    ".pdf": "document", ".docx": "document", ".xlsx": "document",
    ".pptx": "document", ".txt": "document", ".zip": "document",
}


class RealtimeHandler(FileSystemEventHandler):
    """Process each WhatsApp file instantly on creation.

    Strategy:
    1. File appears → copy immediately to backup (preserve before deletion)
    2. Query DB for contact info (before "delete for everyone" removes record)
    3. Move copy to final organized path
    4. Delete source from Downloads
    5. Track in tracking DB
    """

    def __init__(
        self,
        config: dict,
        backup_dir: Path,
        lookup: dict,
        tracker: Tracker,
    ) -> None:
        self._config = config
        self._backup_dir = backup_dir
        self._lookup = lookup
        self._tracker = tracker
        self._org_config = config.get("organization", {})
        self._media_config = config.get("media_types", {})
        self._processing: set[str] = set()
        self._lock = threading.Lock()
        self._db_reader: object | None = None  # Set by watch() after DB loads

    def update_lookup(self, lookup: dict) -> None:
        """Refresh the DB lookup cache."""
        self._lookup = lookup

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        src = Path(str(event.src_path))
        filename = src.name

        if not is_whatsapp_file(filename):
            return

        # Prevent duplicate processing of same file (use full path, not just name)
        file_key = str(src)
        with self._lock:
            if file_key in self._processing:
                return
            self._processing.add(file_key)

        # Process in a thread to not block the observer
        threading.Thread(
            target=self._process_file,
            args=(src, file_key),
            daemon=True,
        ).start()

    def _process_file(self, src: Path, file_key: str) -> None:
        """Process a single file — speed is critical."""
        filename = src.name
        try:
            # Step 0: Wait briefly for file to finish writing (minimal)
            self._wait_for_write(src, max_wait=3.0)

            if not src.exists():
                logger.debug(f"File vanished before processing: {filename}")
                return

            # Step 1: IMMEDIATE COPY to temp location in backup dir
            # This preserves the file before WhatsApp or user can delete it
            staging_dir = self._backup_dir / "_staging"
            staging_dir.mkdir(parents=True, exist_ok=True)
            staged = staging_dir / filename
            shutil.copy2(str(src), str(staged))
            logger.debug(f"Staged: {filename}")

            # Step 2: Parse filename
            parsed = parse_whatsapp_filename(filename)
            if not parsed:
                staged.unlink(missing_ok=True)
                return

            # Step 3: Query DB for contact — BEFORE message gets deleted
            contact = self._lookup_contact(parsed)

            # Step 4: Build final destination
            dest = self._build_dest(parsed, contact, filename)

            if not validate_dest_within_root(dest, self._backup_dir):
                logger.warning(f"Path traversal blocked: {filename}")
                staged.unlink(missing_ok=True)
                return

            # Step 5: Handle duplicate
            if dest.exists():
                from whatskeep.utils.dedup import files_are_duplicates

                if files_are_duplicates(staged, dest):
                    staged.unlink(missing_ok=True)
                    # Also remove source
                    src.unlink(missing_ok=True)
                    logger.info(f"Duplicate skipped: {filename}")
                    return
                dest = resolve_duplicate(dest)

            # Step 6: Move staged file to final destination (cross-device safe)
            dest.parent.mkdir(parents=True, exist_ok=True)
            from whatskeep.utils.fs import safe_move

            safe_move(staged, dest)

            # Step 7: Remove source from Downloads
            src.unlink(missing_ok=True)

            # Step 8: Track for deletion detection
            ts_unix = int(parsed.timestamp.timestamp())
            core_data_ts = ts_unix - 978307200
            self._tracker.track_file(
                original_name=filename,
                dest_path=dest,
                media_type=parsed.media_type,
                contact_name=contact.name if contact else None,
                sender_name=contact.sender_name if contact else None,
                wa_message_date=core_data_ts,
            )

            contact_label = contact.name if contact else "_Unidentified"
            logger.info(f"[REALTIME] {filename} → {contact_label}")

        except Exception as exc:
            logger.error(f"Error processing {filename}: {exc}")
        finally:
            with self._lock:
                self._processing.discard(file_key)

    def _wait_for_write(self, path: Path, max_wait: float = 3.0) -> None:
        """Wait until file size stabilizes (download complete)."""
        deadline = time.monotonic() + max_wait
        prev_size = -1
        while time.monotonic() < deadline:
            try:
                size = path.stat().st_size
                if size > 0 and size == prev_size:
                    return  # Stable
                prev_size = size
            except OSError:
                return
            time.sleep(0.3)

    def _lookup_contact(self, parsed: ParsedWhatsAppFile) -> Contact | None:
        """Instant contact lookup from cached DB data."""
        if not self._lookup:
            return None

        ts = int(parsed.timestamp.timestamp())
        ext_group = _EXT_TO_GROUP.get(f".{parsed.extension}", "unknown")

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

    def _build_dest(
        self,
        parsed: ParsedWhatsAppFile,
        contact: Contact | None,
        filename: str,
    ) -> Path:
        """Build destination path for the file."""
        # Chat exports
        if parsed.is_chat_export:
            exports: str = self._org_config.get("chat_exports_folder", "_Chat Exports")
            subfolder = parsed.contact_name or "_Unknown"
            return self._backup_dir / exports / subfolder / filename

        result_filename = filename

        if contact:
            category = "Groups" if contact.is_group else "Contacts"
            folder = contact.folder_name(
                show_phone=self._org_config.get("show_phone", True),
                group_suffix="",
            )
            type_folder = parsed.media_type.capitalize()
            dest_dir = self._backup_dir / category / folder / type_folder

            # Prefix sender for group messages
            if contact.is_group and contact.sender_name:
                safe_sender = sanitize_dirname(contact.sender_name)
                if contact.sender_phone:
                    result_filename = f"[{safe_sender} ({contact.sender_phone})] {filename}"
                else:
                    result_filename = f"[{safe_sender}] {filename}"
        else:
            unid = self._org_config.get("unidentified_folder", "_Unidentified")
            type_folder = parsed.media_type.capitalize()
            if self._org_config.get("unidentified_by_date", True):
                date = parsed.timestamp.strftime("%Y-%m")
                dest_dir = self._backup_dir / unid / type_folder / date
            else:
                dest_dir = self._backup_dir / unid / type_folder

        return dest_dir / result_filename


def _load_db_lookup(handler: RealtimeHandler) -> None:
    """Load DB lookup in background thread — watcher starts immediately."""
    try:
        db_reader = get_db_reader()
        if db_reader and db_reader.is_available():
            lookup = db_reader.build_lookup()
            handler.update_lookup(lookup)
            handler._db_reader = db_reader  # Keep reference for refresh
            logger.info(f"DB lookup ready: {len(lookup)} entries")
        else:
            logger.warning("WhatsApp DB not available — files go to _Unidentified")
    except Exception as exc:
        logger.error(f"DB lookup failed: {exc}")


def watch(config: dict | None = None) -> None:
    """Start real-time monitoring. Blocks until interrupted."""
    cfg: dict = config or load_config()
    download_dir: Path = resolve_download_dir(cfg)
    backup_dir: Path = resolve_backup_dir(cfg)

    tracker = Tracker()
    handler = RealtimeHandler(cfg, backup_dir, {}, tracker)
    handler._db_reader = None  # type: ignore[attr-defined]

    # Start watcher IMMEDIATELY — don't wait for DB
    observer = Observer()
    observer.schedule(handler, str(download_dir), recursive=False)
    observer.start()
    logger.info(f"REALTIME watcher active on {download_dir}")

    # Load DB in background thread (files captured before DB loads go to _Unidentified
    # but are still SAVED — we can re-correlate later)
    db_thread = threading.Thread(target=_load_db_lookup, args=(handler,), daemon=True)
    db_thread.start()

    # Refresh DB lookup every 5 minutes
    refresh_interval = 300
    last_refresh = time.monotonic()

    try:
        while True:
            time.sleep(1)

            elapsed = time.monotonic() - last_refresh
            db_reader = getattr(handler, "_db_reader", None)
            if elapsed >= refresh_interval and db_reader and db_reader.is_available():
                try:
                    new_lookup = db_reader.build_lookup()
                    handler.update_lookup(new_lookup)
                    last_refresh = time.monotonic()
                    logger.debug(f"DB lookup refreshed: {len(new_lookup)} entries")
                except Exception as exc:
                    logger.warning(f"DB refresh failed: {exc}")

    except KeyboardInterrupt:
        logger.info("Stopping realtime watcher...")
    finally:
        observer.stop()
        db_reader = getattr(handler, "_db_reader", None)
        if db_reader:
            db_reader.close()
        tracker.close()
        observer.join()
        logger.info("Realtime watcher stopped")
