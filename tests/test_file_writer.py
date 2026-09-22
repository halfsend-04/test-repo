"""Tests for file_writer — verifies correct handling of UTF-8 multibyte
content around the 64 KB buffer boundary.

Each test writes content to a temporary file and reads it back to confirm
the round-trip is lossless.
"""

import os
import tempfile

from src.file_writer import BUFFER_SIZE, read_file, save_file


def _roundtrip(content):
    """Write *content* via save_file, read it back, and assert equality."""
    fd, path = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    try:
        save_file(path, content)
        result = read_file(path)
        assert result == content, "round-trip content mismatch"
        # Also verify raw byte length on disk matches the UTF-8 encoding.
        with open(path, "rb") as fh:
            raw = fh.read()
        assert raw == content.encode("utf-8"), "raw bytes mismatch"
    finally:
        os.unlink(path)


def test_ascii_over_64kb():
    """65 KB of pure ASCII must save and reload correctly."""
    content = "A" * (BUFFER_SIZE + 1024)
    _roundtrip(content)


def test_multibyte_char_count_under_64k_byte_count_over():
    """~20 K emoji (each 4 bytes) → ~80 KB on disk, but only 20 K chars.

    This is the scenario that triggered the original segfault: the
    character count fits in one buffer, but the byte count does not.
    """
    emoji = "\U0001F600"  # 😀 — 4 bytes in UTF-8
    count = 20_000
    content = emoji * count
    assert len(content) < BUFFER_SIZE  # char count fits
    assert len(content.encode("utf-8")) > BUFFER_SIZE  # byte count does not
    _roundtrip(content)


def test_mixed_emoji_ascii_70kb():
    """70 KB of mixed emoji + ASCII must save correctly."""
    unit = "Hello 😀🌍🚀 world! "
    repeats = (70 * 1024) // len(unit.encode("utf-8")) + 1
    content = unit * repeats
    assert len(content.encode("utf-8")) >= 70 * 1024
    _roundtrip(content)


def test_exact_64kb_of_4byte_emoji():
    """Exactly 64 KB of 4-byte emoji must save correctly."""
    emoji = "\U0001F680"  # 🚀 — 4 bytes in UTF-8
    count = BUFFER_SIZE // 4  # exactly fills the buffer in bytes
    content = emoji * count
    assert len(content.encode("utf-8")) == BUFFER_SIZE
    _roundtrip(content)


def test_small_ascii():
    """A small ASCII file (well under 64 KB) must still work."""
    _roundtrip("hello world")


def test_empty_file():
    """An empty string must produce a zero-byte file."""
    _roundtrip("")


def test_cjk_over_64kb():
    """CJK characters (3 bytes each) spanning the buffer boundary."""
    char = "世"  # 世 — 3 bytes in UTF-8
    count = BUFFER_SIZE // 3 + 1000  # pushes past one buffer
    content = char * count
    assert len(content.encode("utf-8")) > BUFFER_SIZE
    _roundtrip(content)
