"""Tests for the file_saver module.

Covers UTF-8 multibyte handling at buffer boundaries, round-trip
correctness for various character types, and atomic write safety.
"""

import os
import tempfile

import pytest

from src.file_saver import BUFFER_SIZE, _find_safe_split, save_file


class TestFindSafeSplit:
    """Unit tests for _find_safe_split helper."""

    def test_ascii_only(self):
        data = b"hello world"
        assert _find_safe_split(data, 5) == 5

    def test_max_bytes_beyond_length(self):
        data = b"short"
        assert _find_safe_split(data, 100) == len(data)

    def test_split_before_2byte_char(self):
        # U+00E9 (e-acute) encodes to 0xC3 0xA9 (2 bytes)
        data = b"aaa" + "\u00e9".encode("utf-8")  # 3 + 2 = 5 bytes
        # Splitting at pos 4 would land on continuation byte 0xA9
        assert _find_safe_split(data, 4) == 3

    def test_split_before_4byte_char(self):
        # U+1F600 (grinning face) encodes to 4 bytes
        prefix = b"a" * 10
        emoji = "\U0001f600".encode("utf-8")
        data = prefix + emoji  # 10 + 4 = 14 bytes
        # Splitting at 11, 12, or 13 should back up to 10
        for split_at in (11, 12, 13):
            assert _find_safe_split(data, split_at) == 10

    def test_split_exactly_on_char_boundary(self):
        prefix = b"a" * 10
        emoji = "\U0001f600".encode("utf-8")
        data = prefix + emoji
        # Splitting at 10 is exactly on the boundary — safe
        assert _find_safe_split(data, 10) == 10


class TestSaveFile:
    """Integration tests for save_file."""

    def test_small_ascii_file(self, tmp_path):
        content = "Hello, world!"
        path = str(tmp_path / "test.txt")
        save_file(content, path)
        assert open(path, "r", encoding="utf-8").read() == content

    def test_small_file_with_emoji(self, tmp_path):
        content = "Hello \U0001f600 world \U0001f389!"
        path = str(tmp_path / "emoji.txt")
        save_file(content, path)
        assert open(path, "r", encoding="utf-8").read() == content

    def test_large_ascii_file(self, tmp_path):
        """ASCII file larger than BUFFER_SIZE saves correctly."""
        content = "A" * (BUFFER_SIZE + 1000)
        path = str(tmp_path / "large_ascii.txt")
        save_file(content, path)
        assert open(path, "r", encoding="utf-8").read() == content

    def test_large_emoji_file(self, tmp_path):
        """File >64KB consisting entirely of 4-byte emoji saves."""
        # Each emoji is 4 bytes; we need >64KB = >16384 emoji
        emoji_count = (BUFFER_SIZE // 4) + 500
        content = "\U0001f600" * emoji_count
        path = str(tmp_path / "large_emoji.txt")
        save_file(content, path)
        result = open(path, "r", encoding="utf-8").read()
        assert result == content

    def test_mixed_content_over_boundary(self, tmp_path):
        """Mixed ASCII and multibyte content totaling ~100KB."""
        # Build content that crosses the 64KB boundary with emoji
        ascii_part = "x" * (BUFFER_SIZE - 2)
        emoji_part = "\U0001f600" * 500  # 2000 bytes of emoji
        content = ascii_part + emoji_part
        path = str(tmp_path / "mixed.txt")
        save_file(content, path)
        result = open(path, "r", encoding="utf-8").read()
        assert result == content

    def test_multibyte_straddling_boundary(self, tmp_path):
        """A multibyte sequence that sits exactly at the 64KB split."""
        # Place a 4-byte emoji so it straddles the BUFFER_SIZE offset
        prefix = "a" * (BUFFER_SIZE - 2)  # 2 bytes short of boundary
        content = prefix + "\U0001f600" + "tail"
        path = str(tmp_path / "straddle.txt")
        save_file(content, path)
        result = open(path, "r", encoding="utf-8").read()
        assert result == content

    def test_cjk_characters(self, tmp_path):
        """CJK characters (3-byte UTF-8) round-trip correctly."""
        cjk = "\u4e16\u754c\u4f60\u597d"  # 世界你好
        content = cjk * 6000  # ~72KB of 3-byte characters
        path = str(tmp_path / "cjk.txt")
        save_file(content, path)
        result = open(path, "r", encoding="utf-8").read()
        assert result == content

    def test_atomic_write_no_partial_on_error(self, tmp_path):
        """If writing fails, no partial file is left behind."""
        path = str(tmp_path / "atomic.txt")
        # Write initial content
        save_file("initial", path)

        # Attempt to save to a read-only directory child
        bad_path = str(tmp_path / "nodir" / "file.txt")
        with pytest.raises(OSError):
            save_file("should fail", bad_path)

        # Original file unchanged
        assert open(path, "r", encoding="utf-8").read() == "initial"
        # No temp file left
        assert not os.path.exists(bad_path + ".tmp")

    def test_empty_content(self, tmp_path):
        """Empty string saves as an empty file."""
        path = str(tmp_path / "empty.txt")
        save_file("", path)
        assert open(path, "r", encoding="utf-8").read() == ""
