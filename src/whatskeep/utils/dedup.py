"""SHA-256 based file deduplication utilities."""
from __future__ import annotations

import hashlib
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_CHUNK_SIZE = 8 * 1024 * 1024  # 8 MiB


def file_hash(path: Path, algorithm: str = "sha256") -> str:
    """Calculate the hex-digest hash of a file.

    Reads in chunks of 8 MiB so large files never load entirely into memory.
    """
    h = hashlib.new(algorithm)
    with path.open("rb") as f:
        while True:
            chunk = f.read(_CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def file_is_stable(path: Path, wait: float = 1.0) -> bool:
    """Check that a file is not actively being written to.

    Compares the file size before and after a short delay.  Returns
    ``False`` if the size changed (file still downloading) or if the
    file cannot be read.
    """
    try:
        size_before = path.stat().st_size
        time.sleep(wait)
        size_after = path.stat().st_size
        return size_before == size_after and size_after > 0
    except OSError:
        return False


def files_are_duplicates(
    a: Path,
    b: Path,
    algorithm: str = "sha256",
) -> bool:
    """Return ``True`` if *a* and *b* are exact duplicates.

    Safety checks:
    1. Quick-reject: different sizes are never duplicates.
    2. Full content hash comparison (SHA-256 by default).
    3. Double-check: recompute hash of *a* to guard against partial
       writes or corruption during the first pass.
    """
    try:
        size_a = a.stat().st_size
        size_b = b.stat().st_size
        if size_a != size_b or size_a == 0:
            return False
    except OSError:
        return False

    hash_a = file_hash(a, algorithm)
    hash_b = file_hash(b, algorithm)
    if hash_a != hash_b:
        return False

    # Double-check: re-read source to confirm the hash is stable
    # (guards against the file being written to during the first hash)
    hash_a_verify = file_hash(a, algorithm)
    return hash_a == hash_a_verify
