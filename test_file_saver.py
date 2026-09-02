"""Tests for file_saver module.

Covers the UTF-8 multibyte boundary conditions that previously caused a
segmentation fault when saving files larger than 64 KB containing emoji
or CJK characters (issue #1901).
"""

import os
import tempfile

import pytest

from file_saver import DEFAULT_CHUNK_SIZE, read_file, save_file


@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a temporary directory for test files."""
    return tmp_path


# ---------------------------------------------------------------------------
# Boundary tests from the triage-proposed test plan
# ---------------------------------------------------------------------------


def test_save_64kb_multibyte(tmp_dir):
    """Save a 64 KB file with multibyte UTF-8 chars (emoji/CJK)."""
    # Each emoji is 4 bytes in UTF-8; build content whose encoded size is
    # exactly 64 KiB.
    emoji = "\U0001F600"  # 😀, 4 bytes in UTF-8
    count = DEFAULT_CHUNK_SIZE // len(emoji.encode("utf-8"))
    content = emoji * count
    assert len(content.encode("utf-8")) == DEFAULT_CHUNK_SIZE

    path = str(tmp_dir / "64kb_emoji.txt")
    save_file(content, path)

    assert read_file(path) == content


def test_save_65kb_multibyte(tmp_dir):
    """Save a 65 KB file with multibyte UTF-8 chars — previously segfaulted."""
    emoji = "\U0001F600"
    byte_target = 65 * 1024
    count = byte_target // len(emoji.encode("utf-8"))
    content = emoji * count
    assert len(content.encode("utf-8")) >= 65 * 1024

    path = str(tmp_dir / "65kb_emoji.txt")
    save_file(content, path)

    assert read_file(path) == content


def test_save_70kb_multibyte(tmp_dir):
    """Save a 70 KB+ file with multibyte UTF-8 chars."""
    # Mix of CJK (3-byte) and emoji (4-byte) characters.
    cjk_block = "漢字テスト"  # 15 bytes
    emoji_block = "😀🎉🚀"  # 12 bytes
    unit = cjk_block + emoji_block  # 27 bytes
    repeats = (70 * 1024 // len(unit.encode("utf-8"))) + 1
    content = unit * repeats
    assert len(content.encode("utf-8")) > 70 * 1024

    path = str(tmp_dir / "70kb_mixed.txt")
    save_file(content, path)

    assert read_file(path) == content


def test_save_70kb_ascii(tmp_dir):
    """Save a 70 KB+ ASCII-only file — regression guard."""
    content = "A" * (70 * 1024 + 1)

    path = str(tmp_dir / "70kb_ascii.txt")
    save_file(content, path)

    assert read_file(path) == content


def test_round_trip_multibyte(tmp_dir):
    """Round-trip verify: saved content matches original for multibyte."""
    # Diverse Unicode: Latin, CJK, emoji, combining characters.
    content = (
        "Hello, world! "
        "こんにちは世界 "
        "😀🎉🚀💻🌍 "
        "café résumé naïve "
        "Ωαβγδ "
    ) * 5000  # well above 64 KiB when encoded

    path = str(tmp_dir / "round_trip.txt")
    save_file(content, path)

    result = read_file(path)
    assert result == content
    assert len(result) == len(content)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_file(tmp_dir):
    """Saving an empty string produces an empty file."""
    path = str(tmp_dir / "empty.txt")
    save_file("", path)
    assert read_file(path) == ""


def test_exactly_one_chunk(tmp_dir):
    """Content whose byte length is exactly one chunk boundary."""
    content = "x" * DEFAULT_CHUNK_SIZE
    path = str(tmp_dir / "one_chunk.txt")
    save_file(content, path)
    assert read_file(path) == content


def test_chunk_boundary_splits_multibyte_sequence(tmp_dir):
    """Ensure chunk boundary does not corrupt a multibyte sequence.

    Because chunking operates on already-encoded bytes (not characters),
    splitting at any byte offset is safe — the decoder reconstructs the
    original characters from the full byte stream.
    """
    # Create content where the 64 KiB boundary falls inside a 4-byte
    # emoji sequence (if chunked by character count instead of bytes).
    filler = "A" * (DEFAULT_CHUNK_SIZE - 2)
    emoji = "😀"  # 4 bytes
    content = filler + emoji + "B" * 1024
    assert len(content.encode("utf-8")) > DEFAULT_CHUNK_SIZE

    path = str(tmp_dir / "boundary_split.txt")
    save_file(content, path)
    assert read_file(path) == content


def test_invalid_chunk_size(tmp_dir):
    """chunk_size must be positive."""
    with pytest.raises(ValueError, match="chunk_size must be positive"):
        save_file("test", str(tmp_dir / "bad.txt"), chunk_size=0)

    with pytest.raises(ValueError, match="chunk_size must be positive"):
        save_file("test", str(tmp_dir / "bad.txt"), chunk_size=-1)
