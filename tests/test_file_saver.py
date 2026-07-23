"""Tests for src.file_saver — UTF-8-safe buffered file saving."""

import os

import pytest

from src.file_saver import BUFFER_SIZE, _find_safe_split, save_file


# ---------------------------------------------------------------------------
# _find_safe_split
# ---------------------------------------------------------------------------


class TestFindSafeSplit:
    """Unit tests for the UTF-8-aware split helper."""

    def test_ascii_only(self):
        data = b"hello world"
        assert _find_safe_split(data, 5) == 5

    def test_max_bytes_beyond_length(self):
        data = b"short"
        assert _find_safe_split(data, 100) == len(data)

    def test_split_before_2byte_char(self):
        # U+00E9 (e-acute) -> 0xC3 0xA9 (2 bytes)
        data = b"aaa" + "é".encode("utf-8")
        # Splitting at byte 4 lands on the continuation byte
        assert _find_safe_split(data, 4) == 3

    def test_split_before_4byte_char(self):
        prefix = b"a" * 10
        emoji = "\U0001f600".encode("utf-8")
        data = prefix + emoji  # 14 bytes total
        for split_at in (11, 12, 13):
            assert _find_safe_split(data, split_at) == 10

    def test_split_on_char_boundary(self):
        prefix = b"a" * 10
        emoji = "\U0001f600".encode("utf-8")
        data = prefix + emoji
        assert _find_safe_split(data, 10) == 10


# ---------------------------------------------------------------------------
# save_file
# ---------------------------------------------------------------------------


class TestSaveFile:
    """Integration tests for save_file."""

    def test_small_ascii(self, tmp_path):
        content = "Hello, world!"
        path = str(tmp_path / "test.txt")
        save_file(content, path)
        assert open(path, encoding="utf-8").read() == content

    def test_small_emoji(self, tmp_path):
        content = "Hello \U0001f600 world \U0001f389!"
        path = str(tmp_path / "emoji.txt")
        save_file(content, path)
        assert open(path, encoding="utf-8").read() == content

    def test_large_ascii(self, tmp_path):
        content = "A" * (BUFFER_SIZE + 1000)
        path = str(tmp_path / "large_ascii.txt")
        save_file(content, path)
        assert open(path, encoding="utf-8").read() == content

    def test_large_emoji_file(self, tmp_path):
        """File >64KB consisting entirely of 4-byte emoji."""
        emoji_count = (BUFFER_SIZE // 4) + 500
        content = "\U0001f600" * emoji_count
        path = str(tmp_path / "large_emoji.txt")
        save_file(content, path)
        assert open(path, encoding="utf-8").read() == content

    def test_multibyte_straddling_boundary(self, tmp_path):
        """4-byte emoji placed so it straddles the 64KB boundary."""
        prefix = "a" * (BUFFER_SIZE - 2)
        content = prefix + "\U0001f600" + "tail"
        path = str(tmp_path / "straddle.txt")
        save_file(content, path)
        assert open(path, encoding="utf-8").read() == content

    def test_cjk_characters(self, tmp_path):
        """CJK characters (3-byte UTF-8) round-trip over boundary."""
        content = "世界你好" * 6000
        path = str(tmp_path / "cjk.txt")
        save_file(content, path)
        assert open(path, encoding="utf-8").read() == content

    def test_mixed_content_over_boundary(self, tmp_path):
        ascii_part = "x" * (BUFFER_SIZE - 2)
        emoji_part = "\U0001f600" * 500
        content = ascii_part + emoji_part
        path = str(tmp_path / "mixed.txt")
        save_file(content, path)
        assert open(path, encoding="utf-8").read() == content

    def test_empty_content(self, tmp_path):
        path = str(tmp_path / "empty.txt")
        save_file("", path)
        assert open(path, encoding="utf-8").read() == ""

    def test_atomic_no_partial_on_error(self, tmp_path):
        """Failed write leaves no partial file behind."""
        path = str(tmp_path / "atomic.txt")
        save_file("initial", path)

        bad_path = str(tmp_path / "nodir" / "file.txt")
        with pytest.raises(OSError):
            save_file("should fail", bad_path)

        assert open(path, encoding="utf-8").read() == "initial"
        assert not os.path.exists(bad_path + ".tmp")
