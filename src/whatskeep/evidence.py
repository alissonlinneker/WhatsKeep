"""Digital chain of custody and evidence preservation for WhatsKeep.

Provides hash-based integrity verification, chronological event logging,
per-file custody metadata, and exportable evidence packages suitable for
legal proceedings in Brazil (based on Art. 158-A CPP and ISO 27037).

IMPORTANT DISCLAIMER: This module assists with evidence preservation but
does NOT replace ata notarial, forensic analysis, or certified platforms
(such as Verifact). Consult an attorney for legal guidance.
"""

from __future__ import annotations

import hashlib
import json
import platform
import socket
from datetime import datetime, timezone
from getpass import getuser
from pathlib import Path

from loguru import logger

from whatskeep.config import get_config_dir

_CUSTODY_DB = "tracking.db"
_EVIDENCE_DIR = "_Evidence"
_HASH_ALGORITHM = "sha256"
_CHUNK_SIZE = 8 * 1024 * 1024


# ---------------------------------------------------------------------------
# Schema additions for custody tracking
# ---------------------------------------------------------------------------

_CUSTODY_SCHEMA = """\
CREATE TABLE IF NOT EXISTS custody_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    file_path TEXT,
    file_hash TEXT,
    details TEXT,
    hostname TEXT,
    username TEXT,
    platform TEXT
);

CREATE TABLE IF NOT EXISTS integrity_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    checked_at TEXT NOT NULL,
    file_path TEXT NOT NULL,
    expected_hash TEXT NOT NULL,
    actual_hash TEXT,
    status TEXT NOT NULL,
    details TEXT
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _file_sha256(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(_CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _system_info() -> dict:
    return {
        "hostname": socket.gethostname(),
        "username": getuser(),
        "platform": platform.platform(),
        "python": platform.python_version(),
    }


# ---------------------------------------------------------------------------
# Custody Manager
# ---------------------------------------------------------------------------


class CustodyManager:
    """Manages chain of custody records and evidence export."""

    def __init__(self, backup_dir: Path) -> None:
        import sqlite3

        self._backup_dir = backup_dir
        self._db_path = get_config_dir() / _CUSTODY_DB
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.executescript(_CUSTODY_SCHEMA)
        self._conn.commit()
        self._sys = _system_info()

    # ----- Event Logging -----

    def log_event(
        self,
        event_type: str,
        file_path: str | None = None,
        file_hash: str | None = None,
        details: str | None = None,
    ) -> None:
        """Record a custody event."""
        self._conn.execute(
            """INSERT INTO custody_events
            (timestamp, event_type, file_path, file_hash, details,
             hostname, username, platform)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                _now_iso(),
                event_type,
                file_path,
                file_hash,
                details,
                self._sys["hostname"],
                self._sys["username"],
                self._sys["platform"],
            ),
        )
        self._conn.commit()

    def record_file_custody(self, src: Path, dest: Path) -> str:
        """Record full custody metadata when a file is organized.

        Returns the SHA-256 hash of the destination file.
        """
        file_hash = _file_sha256(dest)

        # Store hash in tracked_files if column exists
        self._conn.execute(
            "UPDATE tracked_files SET file_hash = ? WHERE dest_path = ?",
            (file_hash, str(dest)),
        )

        self.log_event(
            event_type="FILE_ORGANIZED",
            file_path=str(dest),
            file_hash=file_hash,
            details=json.dumps({
                "original_name": src.name,
                "original_size": src.stat().st_size if src.exists() else None,
                "dest_size": dest.stat().st_size,
                "algorithm": _HASH_ALGORITHM,
            }),
        )

        # Write per-file sidecar
        self._write_sidecar(dest, file_hash, src.name)

        self._conn.commit()
        return file_hash

    def _write_sidecar(self, dest: Path, file_hash: str, original_name: str) -> None:
        """Write a .custody.json sidecar alongside the media file."""
        sidecar = dest.parent / f"{dest.name}.custody.json"
        data = {
            "file": dest.name,
            "original_name": original_name,
            "sha256": file_hash,
            "size_bytes": dest.stat().st_size,
            "organized_at": _now_iso(),
            "system": self._sys,
            "algorithm": _HASH_ALGORITHM,
            "disclaimer": (
                "This metadata was generated automatically by WhatsKeep. "
                "It assists with evidence preservation but does NOT replace "
                "ata notarial or certified forensic analysis."
            ),
        }
        sidecar.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # ----- Integrity Verification -----

    def verify_all(self) -> dict:
        """Re-check SHA-256 of all tracked files.

        Returns dict with counts: ok, corrupted, missing, total.
        """
        rows = self._conn.execute(
            "SELECT dest_path, file_hash FROM tracked_files WHERE file_hash IS NOT NULL"
        ).fetchall()

        results: dict = {"ok": 0, "corrupted": 0, "missing": 0, "total": len(rows), "details": []}
        now = _now_iso()

        for dest_path, expected_hash in rows:
            path = Path(dest_path)
            if not path.exists():
                status = "MISSING"
                actual = None
                results["missing"] += 1
            else:
                actual = _file_sha256(path)
                if actual == expected_hash:
                    status = "OK"
                    results["ok"] += 1
                else:
                    status = "CORRUPTED"
                    results["corrupted"] += 1
                    results["details"].append({
                        "file": dest_path,
                        "expected": expected_hash,
                        "actual": actual,
                    })

            self._conn.execute(
                """INSERT INTO integrity_checks
                (checked_at, file_path, expected_hash, actual_hash, status, details)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (now, dest_path, expected_hash, actual, status, None),
            )

        self._conn.commit()
        self.log_event(
            "INTEGRITY_CHECK",
            details=json.dumps({
                "ok": results["ok"],
                "corrupted": results["corrupted"],
                "missing": results["missing"],
            }),
        )
        return results

    # ----- Evidence Export -----

    def export_evidence(
        self,
        contact_name: str | None = None,
        output_dir: Path | None = None,
    ) -> Path:
        """Export an evidence package ready for legal use.

        If *contact_name* is given, exports only that contact's files.
        Otherwise exports everything.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")

        if contact_name and output_dir is None:
            # Find the contact's folder (search Contacts/ then Groups/)
            safe = _safe_name(contact_name)
            for category in ("Contacts", "Groups"):
                cat_dir = self._backup_dir / category
                if not cat_dir.is_dir():
                    continue
                for d in cat_dir.iterdir():
                    if d.is_dir() and (d.name == contact_name or safe in d.name):
                        pkg_dir = d / "_evidence" / timestamp
                        break
                else:
                    continue
                break
            else:
                # Fallback: global evidence
                pkg_dir = self._backup_dir / _EVIDENCE_DIR / _safe_name(contact_name) / timestamp
        elif output_dir:
            pkg_dir = output_dir / f"export_{timestamp}"
        else:
            pkg_dir = self._backup_dir / _EVIDENCE_DIR / f"full_export_{timestamp}"

        pkg_dir.mkdir(parents=True, exist_ok=True)

        # Query tracked files
        if contact_name:
            rows = self._conn.execute(
                """SELECT dest_path, file_hash, original_name, contact_name,
                          sender_name, wa_message_date, organized_at,
                          deleted_from_chat, deleted_detected_at
                FROM tracked_files WHERE contact_name = ?""",
                (contact_name,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """SELECT dest_path, file_hash, original_name, contact_name,
                          sender_name, wa_message_date, organized_at,
                          deleted_from_chat, deleted_detected_at
                FROM tracked_files"""
            ).fetchall()

        # Build manifest
        manifest: dict = {
            "generated_at": _now_iso(),
            "generator": "WhatsKeep Evidence Export",
            "version": "1.0",
            "system": self._sys,
            "filter": contact_name or "ALL",
            "total_files": len(rows),
            "hash_algorithm": _HASH_ALGORITHM,
            "disclaimer": (
                "This evidence package was generated by WhatsKeep, an open-source "
                "media backup tool. SHA-256 hashes verify file integrity since "
                "the moment of capture. This does NOT replace ata notarial, "
                "certified platforms (Verifact, e-Not Provas), or forensic "
                "analysis. Consult an attorney for legal guidance."
            ),
            "files": [],
        }

        # Hash file for bulk verification
        hash_lines: list[str] = []

        for (
            dest_path, file_hash, orig_name, contact, sender,
            wa_date, organized_at, deleted, deleted_at,
        ) in rows:
            path = Path(dest_path)
            entry = {
                "original_name": orig_name,
                "current_path": dest_path,
                "contact": contact,
                "sender": sender,
                "sha256": file_hash,
                "organized_at": organized_at,
                "wa_message_date": wa_date,
                "deleted_from_chat": bool(deleted),
                "deleted_detected_at": deleted_at,
                "exists": path.exists(),
                "current_size": path.stat().st_size if path.exists() else None,
            }

            # Verify hash is still valid
            if path.exists() and file_hash:
                current = _file_sha256(path)
                entry["integrity_verified"] = current == file_hash
                entry["current_sha256"] = current
            else:
                entry["integrity_verified"] = None

            manifest["files"].append(entry)

            if file_hash:
                hash_lines.append(f"{file_hash}  {orig_name}")

        # Write manifest
        manifest_path = pkg_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Write hash file (compatible with sha256sum -c)
        hash_path = pkg_dir / "SHA256SUMS.txt"
        hash_path.write_text("\n".join(hash_lines) + "\n", encoding="utf-8")

        # Write custody event log
        events = self._conn.execute(
            "SELECT timestamp, event_type, file_path, file_hash, details, "
            "hostname, username, platform FROM custody_events ORDER BY timestamp"
        ).fetchall()

        events_data = [
            {
                "timestamp": e[0], "event_type": e[1], "file_path": e[2],
                "file_hash": e[3], "details": e[4], "hostname": e[5],
                "username": e[6], "platform": e[7],
            }
            for e in events
        ]
        events_path = pkg_dir / "chain_of_custody.json"
        events_path.write_text(
            json.dumps(events_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Log the export itself
        self.log_event(
            "EVIDENCE_EXPORTED",
            details=json.dumps({
                "contact": contact_name,
                "files_count": len(rows),
                "package_dir": str(pkg_dir),
            }),
        )

        logger.info(f"Evidence package exported to {pkg_dir}")
        return pkg_dir

    # ----- Stats -----

    def get_custody_stats(self) -> dict:
        """Return custody statistics."""
        total = self._conn.execute(
            "SELECT COUNT(*) FROM tracked_files"
        ).fetchone()[0]
        with_hash = self._conn.execute(
            "SELECT COUNT(*) FROM tracked_files WHERE file_hash IS NOT NULL"
        ).fetchone()[0]
        deleted = self._conn.execute(
            "SELECT COUNT(*) FROM tracked_files WHERE deleted_from_chat = 1"
        ).fetchone()[0]
        events = self._conn.execute(
            "SELECT COUNT(*) FROM custody_events"
        ).fetchone()[0]
        checks = self._conn.execute(
            "SELECT COUNT(*) FROM integrity_checks"
        ).fetchone()[0]
        last_check = self._conn.execute(
            "SELECT checked_at FROM integrity_checks ORDER BY id DESC LIMIT 1"
        ).fetchone()

        return {
            "total_tracked": total,
            "with_hash": with_hash,
            "without_hash": total - with_hash,
            "deleted_from_chat": deleted,
            "custody_events": events,
            "integrity_checks": checks,
            "last_check": last_check[0] if last_check else None,
        }

    def hash_pending_files(self) -> int:
        """Generate SHA-256 hashes for tracked files that don't have one yet.

        Returns the number of files hashed.
        """
        rows = self._conn.execute(
            "SELECT id, dest_path FROM tracked_files WHERE file_hash IS NULL"
        ).fetchall()

        hashed = 0
        for row_id, dest_path in rows:
            path = Path(dest_path)
            if path.exists():
                h = _file_sha256(path)
                self._conn.execute(
                    "UPDATE tracked_files SET file_hash = ? WHERE id = ?",
                    (h, row_id),
                )
                self.log_event("HASH_GENERATED", file_path=dest_path, file_hash=h)
                hashed += 1

        self._conn.commit()
        return hashed

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None  # type: ignore[assignment]


def _safe_name(name: str) -> str:
    """Sanitize a name for use as a directory name."""
    import re

    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(". ") or "_"
