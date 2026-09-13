"""Tests for the file_saver module.

Covers the UTF-8 multibyte buffer-boundary bug described in issue #358.
"""

import os
import tempfile

import pytest

from src.file_saver import BUFFER_SIZE, _find_safe_split, save_file


class TestFindSafeSplit:
    """Unit tests for _find_safe_split."""

    def test_ascii_only(self):
        data = b"hello world"
        assert _find_safe_split(data, 5) == 5

    def test_split_before_multibyte(self):
        # 'é' is 2 bytes: 0xC3 0xA9
        data = b"aaa\xc3\xa9bbb"
        # Splitting at byte 4 would land on 0xA9 (continuation byte).
        # Should back up to byte 3.
        assert _find_safe_split(data, 4) == 3

    def test_split_on_char_boundary(self):
        # 'é' is bytes 3-4; splitting at 5 is safe (after the é).
        data = b"aaa\xc3\xa9bbb"
        assert _find_safe_split(data, 5) == 5

    def test_four_byte_char(self):
        # U+1F600 (😀) is 4 bytes: F0 9F 98 80
        data = b"aa\xf0\x9f\x98\x80bb"
        # Splitting at 3,4,5 should all back up to 2
        assert _find_safe_split(data, 3) == 2
        assert _find_safe_split(data, 4) == 2
        assert _find_safe_split(data, 5) == 2
        # Splitting at 6 is safe (after the emoji)
        assert _find_safe_split(data, 6) == 6

    def test_max_exceeds_length(self):
        data = b"short"
        assert _find_safe_split(data, 100) == 5


class TestSaveFile:
    """Integration tests for save_file."""

    def test_small_ascii_file(self, tmp_path):
        path = str(tmp_path / "test.txt")
        content = "Hello, world!"
        save_file(content, path)
        assert open(path, "r", encoding="utf-8").read() == content

    def test_file_under_64kb_with_emoji(self, tmp_path):
        """File just under 64KB with multibyte characters saves OK."""
        path = str(tmp_path / "test.txt")
        # Each emoji is 4 bytes; fill to just under 64KB
        emoji_count = (BUFFER_SIZE // 4) - 10
        content = "😀" * emoji_count
        save_file(content, path)
        result = open(path, "r", encoding="utf-8").read()
        assert result == content

    def test_file_over_64kb_with_emoji(self, tmp_path):
        """File just over 64KB with multibyte characters saves OK.

        This is the exact scenario that triggered the segfault in #358.
        """
        path = str(tmp_path / "test.txt")
        # Each emoji is 4 bytes; exceed 64KB
        emoji_count = (BUFFER_SIZE // 4) + 100
        content = "😀" * emoji_count
        save_file(content, path)
        result = open(path, "r", encoding="utf-8").read()
        assert result == content

    def test_large_mixed_content(self, tmp_path):
        """Large file with mixed ASCII and multibyte characters."""
        path = str(tmp_path / "test.txt")
        # Build ~100KB of mixed content
        block = "Hello 世界! 🎉 Testing ñ café\n"
        repeat = (100 * 1024) // len(block.encode("utf-8")) + 1
        content = block * repeat
        save_file(content, path)
        result = open(path, "r", encoding="utf-8").read()
        assert result == content

    def test_multibyte_at_exact_boundary(self, tmp_path):
        """Multibyte character straddling exactly the 64KB boundary."""
        path = str(tmp_path / "test.txt")
        # Fill with ASCII up to BUFFER_SIZE - 1, then a 4-byte emoji
        # so the emoji straddles the boundary.
        content = "a" * (BUFFER_SIZE - 1) + "😀" + "b" * 100
        save_file(content, path)
        result = open(path, "r", encoding="utf-8").read()
        assert result == content

    def test_atomic_write_on_failure(self, tmp_path):
        """If the write fails, the original file is not corrupted."""
        path = str(tmp_path / "test.txt")
        original = "original content"
        save_file(original, path)

        # Try saving to a read-only directory to trigger an error
        bad_path = "/proc/nonexistent/test.txt"
        with pytest.raises(OSError):
            save_file("new content", bad_path)

        # Original file should be untouched
        assert open(path, "r", encoding="utf-8").read() == original

    def test_content_roundtrip_cjk(self, tmp_path):
        """CJK characters round-trip correctly through save/load."""
        path = str(tmp_path / "test.txt")
        content = "漢字テスト " * 20000  # ~180KB of CJK text
        save_file(content, path)
        result = open(path, "r", encoding="utf-8").read()
        assert result == content
