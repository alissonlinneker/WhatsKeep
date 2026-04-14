"""Tests for WhatsApp filename pattern detection and parsing."""

from __future__ import annotations

from datetime import datetime

import pytest

from whatskeep.patterns import ParsedWhatsAppFile, is_whatsapp_file, parse_whatsapp_filename

# ── Modern pattern — all media types ────────────────────────────────────────


class TestModernTypes:
    """Modern desktop naming (space separator)."""

    def test_image(self) -> None:
        result = parse_whatsapp_filename("WhatsApp Image 2026-04-08 at 14.20.43.jpeg")
        assert result is not None
        assert result.media_type == "image"
        assert result.timestamp == datetime(2026, 4, 8, 14, 20, 43)
        assert result.extension == "jpeg"
        assert result.duplicate_index is None
        assert result.is_chat_export is False
        assert result.contact_name is None

    def test_audio(self) -> None:
        result = parse_whatsapp_filename("WhatsApp Audio 2026-04-01 at 07.41.04.opus")
        assert result is not None
        assert result.media_type == "audio"
        assert result.timestamp == datetime(2026, 4, 1, 7, 41, 4)
        assert result.extension == "opus"

    def test_video(self) -> None:
        result = parse_whatsapp_filename("WhatsApp Video 2025-02-21 at 12.41.20.mp4")
        assert result is not None
        assert result.media_type == "video"
        assert result.timestamp == datetime(2025, 2, 21, 12, 41, 20)
        assert result.extension == "mp4"

    def test_ptt(self) -> None:
        result = parse_whatsapp_filename("WhatsApp Ptt 2024-01-23 at 23.54.40.ogg")
        assert result is not None
        assert result.media_type == "voice_note"
        assert result.timestamp == datetime(2024, 1, 23, 23, 54, 40)
        assert result.extension == "ogg"

    def test_document(self) -> None:
        result = parse_whatsapp_filename("WhatsApp Document 2024-01-15 at 10.30.00.pdf")
        assert result is not None
        assert result.media_type == "document"
        assert result.timestamp == datetime(2024, 1, 15, 10, 30, 0)
        assert result.extension == "pdf"

    def test_sticker(self) -> None:
        result = parse_whatsapp_filename("WhatsApp Sticker 2026-01-01 at 12.00.00.webp")
        assert result is not None
        assert result.media_type == "sticker"
        assert result.timestamp == datetime(2026, 1, 1, 12, 0, 0)
        assert result.extension == "webp"


# ── Modern pattern — separator variants ─────────────────────────────────────


class TestModernVariants:
    """Hyphenated and underscored variants."""

    def test_hyphenated(self) -> None:
        result = parse_whatsapp_filename("WhatsApp-Image-2024-01-15-at-21.34.04.jpg")
        assert result is not None
        assert result.media_type == "image"
        assert result.timestamp == datetime(2024, 1, 15, 21, 34, 4)
        assert result.extension == "jpg"

    def test_underscored(self) -> None:
        result = parse_whatsapp_filename("WhatsApp_Image_2024-06-24_at_18.54.07.png")
        assert result is not None
        assert result.media_type == "image"
        assert result.timestamp == datetime(2024, 6, 24, 18, 54, 7)
        assert result.extension == "png"


# ── Modern pattern — duplicates ─────────────────────────────────────────────


class TestModernDuplicates:
    """Duplicate suffix ``(N)``."""

    def test_duplicate_1(self) -> None:
        result = parse_whatsapp_filename("WhatsApp Image 2026-04-08 at 14.20.43 (1).jpeg")
        assert result is not None
        assert result.duplicate_index == 1

    def test_duplicate_2(self) -> None:
        result = parse_whatsapp_filename("WhatsApp Image 2026-04-08 at 14.20.43 (2).jpeg")
        assert result is not None
        assert result.duplicate_index == 2

    def test_no_duplicate(self) -> None:
        result = parse_whatsapp_filename("WhatsApp Image 2026-04-08 at 14.20.43.jpeg")
        assert result is not None
        assert result.duplicate_index is None


# ── Legacy pattern — all media types ────────────────────────────────────────


class TestLegacyTypes:
    """Legacy Android naming."""

    def test_img(self) -> None:
        result = parse_whatsapp_filename("IMG-20220331-WA0076.jpg")
        assert result is not None
        assert result.media_type == "image"
        assert result.timestamp == datetime(2022, 3, 31)
        assert result.extension == "jpg"
        assert result.duplicate_index is None

    def test_vid(self) -> None:
        result = parse_whatsapp_filename("VID-20230313-WA0064.mp4")
        assert result is not None
        assert result.media_type == "video"
        assert result.timestamp == datetime(2023, 3, 13)
        assert result.extension == "mp4"

    def test_doc(self) -> None:
        result = parse_whatsapp_filename("DOC-20230928-WA0001.pdf")
        assert result is not None
        assert result.media_type == "document"
        assert result.timestamp == datetime(2023, 9, 28)
        assert result.extension == "pdf"

    def test_aud(self) -> None:
        result = parse_whatsapp_filename("AUD-20231018-WA0013.opus")
        assert result is not None
        assert result.media_type == "audio"
        assert result.timestamp == datetime(2023, 10, 18)
        assert result.extension == "opus"

    def test_ptt(self) -> None:
        result = parse_whatsapp_filename("PTT-20231018-WA0013.ogg")
        assert result is not None
        assert result.media_type == "voice_note"
        assert result.timestamp == datetime(2023, 10, 18)
        assert result.extension == "ogg"

    def test_stk(self) -> None:
        result = parse_whatsapp_filename("STK-20231018-WA0013.webp")
        assert result is not None
        assert result.media_type == "sticker"
        assert result.timestamp == datetime(2023, 10, 18)
        assert result.extension == "webp"


# ── Chat exports ────────────────────────────────────────────────────────────


class TestChatExports:
    """``WhatsApp Chat - <contact>.zip`` pattern."""

    def test_chat_export(self) -> None:
        result = parse_whatsapp_filename("WhatsApp Chat - Family Group.zip")
        assert result is not None
        assert result.is_chat_export is True
        assert result.contact_name == "Family Group"
        assert result.media_type == "document"
        assert result.extension == "zip"

    def test_chat_export_single_contact(self) -> None:
        result = parse_whatsapp_filename("WhatsApp Chat - John Doe.zip")
        assert result is not None
        assert result.is_chat_export is True
        assert result.contact_name == "John Doe"


# ── Non-WhatsApp files ──────────────────────────────────────────────────────


class TestNonWhatsApp:
    """Files that are NOT WhatsApp media should return ``None``."""

    @pytest.mark.parametrize(
        "filename",
        [
            "photo.jpg",
            "screenshot_2024-01-15.png",
            "video_recording.mp4",
            "notes.pdf",
            "random.zip",
            "IMG_1234.jpg",
            "Document.docx",
            "",
        ],
    )
    def test_returns_none(self, filename: str) -> None:
        assert parse_whatsapp_filename(filename) is None


# ── is_whatsapp_file helper ─────────────────────────────────────────────────


class TestIsWhatsAppFile:
    """Quick boolean check."""

    def test_modern_true(self) -> None:
        assert is_whatsapp_file("WhatsApp Image 2026-04-08 at 14.20.43.jpeg") is True

    def test_legacy_true(self) -> None:
        assert is_whatsapp_file("IMG-20220331-WA0076.jpg") is True

    def test_chat_true(self) -> None:
        assert is_whatsapp_file("WhatsApp Chat - Someone.zip") is True

    def test_random_false(self) -> None:
        assert is_whatsapp_file("vacation_photo.jpg") is False


# ── Datetime correctness ────────────────────────────────────────────────────


class TestDatetimeParsing:
    """Verify timestamp fields are correctly extracted."""

    def test_modern_full_timestamp(self) -> None:
        result = parse_whatsapp_filename("WhatsApp Video 2025-12-31 at 23.59.59.mp4")
        assert result is not None
        assert result.timestamp == datetime(2025, 12, 31, 23, 59, 59)

    def test_legacy_date_only(self) -> None:
        result = parse_whatsapp_filename("IMG-20240101-WA0001.jpg")
        assert result is not None
        assert result.timestamp == datetime(2024, 1, 1, 0, 0, 0)

    def test_chat_export_uses_epoch(self) -> None:
        result = parse_whatsapp_filename("WhatsApp Chat - Test.zip")
        assert result is not None
        assert result.timestamp == datetime(1970, 1, 1)


# ── Extension normalisation ─────────────────────────────────────────────────


class TestExtensionNormalisation:
    """Extensions are always returned in lowercase."""

    def test_uppercase_ext(self) -> None:
        result = parse_whatsapp_filename("WhatsApp Image 2026-04-08 at 14.20.43.JPEG")
        assert result is not None
        assert result.extension == "jpeg"

    def test_legacy_uppercase_ext(self) -> None:
        result = parse_whatsapp_filename("IMG-20220331-WA0076.JPG")
        assert result is not None
        assert result.extension == "jpg"


# ── ParsedWhatsAppFile dataclass ────────────────────────────────────────────


class TestDataclass:
    """Verify the dataclass is frozen and has the expected fields."""

    def test_frozen(self) -> None:
        result = parse_whatsapp_filename("WhatsApp Image 2026-04-08 at 14.20.43.jpeg")
        assert result is not None
        with pytest.raises(AttributeError):
            result.media_type = "video"  # type: ignore[misc]

    def test_is_instance(self) -> None:
        result = parse_whatsapp_filename("WhatsApp Image 2026-04-08 at 14.20.43.jpeg")
        assert isinstance(result, ParsedWhatsAppFile)
