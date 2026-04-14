"""Shared fixtures for WhatsKeep tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def tmp_downloads(tmp_path: Path) -> Path:
    """Create a temporary downloads directory."""
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    return downloads


@pytest.fixture
def tmp_backup(tmp_path: Path) -> Path:
    """Create a temporary backup directory."""
    backup = tmp_path / "WhatsKeep"
    backup.mkdir()
    return backup


@pytest.fixture
def sample_whatsapp_files(tmp_downloads: Path) -> list[Path]:
    """Create sample WhatsApp files in the downloads directory."""
    files = [
        "WhatsApp Image 2026-04-08 at 14.20.43.jpeg",
        "WhatsApp Audio 2026-04-01 at 07.41.04.opus",
        "WhatsApp Video 2025-02-21 at 12.41.20.mp4",
        "WhatsApp Ptt 2024-01-23 at 23.54.40.ogg",
        "WhatsApp Document 2024-01-15 at 10.30.00.pdf",
        "WhatsApp Sticker 2026-01-01 at 12.00.00.webp",
        "WhatsApp-Image-2024-01-15-at-21.34.04.jpg",
        "WhatsApp_Image_2024-06-24_at_18.54.07.png",
        "WhatsApp Image 2026-04-08 at 14.20.43 (1).jpeg",
        "IMG-20220331-WA0076.jpg",
        "VID-20230313-WA0064.mp4",
        "DOC-20230928-WA0001.pdf",
        "AUD-20231018-WA0013.opus",
        "PTT-20231018-WA0013.ogg",
        "STK-20231018-WA0013.webp",
        "WhatsApp Chat - Family Group.zip",
    ]
    paths = []
    for name in files:
        p = tmp_downloads / name
        p.write_bytes(b"fake content")
        paths.append(p)
    return paths


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Create a temporary config directory."""
    d = tmp_path / ".whatskeep"
    d.mkdir()
    return d
