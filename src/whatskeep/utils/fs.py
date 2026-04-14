"""File system helpers for safe file operations."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

# Characters not allowed in filenames across platforms
UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_dirname(name: str) -> str:
    """Remove/replace characters unsafe for directory names.

    Preserves emojis and Unicode letters. Strips leading/trailing dots
    and spaces (Windows compatibility). Collapses multiple underscores.
    Blocks ``..`` to prevent path traversal.
    Returns ``_unnamed`` when the result would be empty.
    """
    if not name:
        return "_unnamed"

    sanitized = UNSAFE_CHARS.sub("_", name)
    # Block path traversal sequences
    sanitized = sanitized.replace("..", "_")
    sanitized = sanitized.strip(". ")
    sanitized = re.sub(r"_+", "_", sanitized)
    sanitized = sanitized.strip("_")

    return sanitized or "_unnamed"


def validate_dest_within_root(dest: Path, root: Path) -> bool:
    """Verify that *dest* resolves to a path inside *root*.

    Prevents path traversal attacks via symlinks or ``..`` components.
    """
    try:
        resolved = dest.resolve()
        root_resolved = root.resolve()
        return resolved == root_resolved or resolved.is_relative_to(root_resolved)
    except (OSError, ValueError):
        return False


def safe_move(src: Path, dest: Path) -> Path:
    """Move *src* to *dest* safely.

    Same filesystem uses :pymeth:`Path.rename` (atomic).
    Cross-filesystem falls back to :pyfunc:`shutil.move` (copy + delete).
    Parent directories are created automatically.

    Returns the final destination path.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        return src.rename(dest)
    except OSError:
        # Cross-device link — copy then delete
        result = Path(shutil.move(str(src), str(dest)))
        return result


def resolve_duplicate(dest: Path) -> Path:
    """Return a non-colliding path by appending a counter.

    ``photo.jpg`` → ``photo (1).jpg`` → ``photo (2).jpg`` …
    If *dest* does not exist it is returned unchanged.
    """
    if not dest.exists():
        return dest

    stem = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    counter = 1

    max_attempts = 10000
    while counter <= max_attempts:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1

    msg = f"Could not resolve duplicate after {max_attempts} attempts: {dest}"
    raise OSError(msg)


def files_are_identical(a: Path, b: Path) -> bool:
    """Quick identity check based on file size.

    Two files with different sizes are guaranteed to differ. Equal sizes
    are *potentially* identical — use :func:`dedup.files_are_duplicates`
    for a definitive answer via hash comparison.
    """
    try:
        return a.stat().st_size == b.stat().st_size
    except OSError:
        return False


def get_file_size_human(size_bytes: int) -> str:
    """Format *size_bytes* as a human-readable string.

    Examples: ``1.2 GB``, ``456 KB``, ``128 B``.
    """
    if size_bytes < 0:
        return "0 B"

    units = ("B", "KB", "MB", "GB", "TB")
    value = float(size_bytes)

    for unit in units[:-1]:
        if abs(value) < 1024.0:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024.0

    return f"{value:.1f} {units[-1]}"
