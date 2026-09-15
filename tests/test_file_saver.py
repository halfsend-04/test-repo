"""Tests for file_saver module, covering UTF-8 multibyte buffer handling."""

import os
import tempfile

import pytest

from src.file_saver import BUFFER_SIZE, save_file


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory for test output files."""
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestSaveFile:
    """Tests for save_file function."""

    def test_save_small_ascii_file(self, tmp_dir):
        """Small ASCII-only file saves correctly."""
        path = os.path.join(tmp_dir, "small.txt")
        content = "Hello, world!"
        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content

    def test_save_file_under_64kb_with_emoji(self, tmp_dir):
        """File just under 64KB containing emoji saves correctly."""
        path = os.path.join(tmp_dir, "under_64kb_emoji.txt")
        # Each emoji is 4 bytes in UTF-8; build content just under 64KB
        emoji = "\U0001f600"  # 😀 — 4 bytes in UTF-8
        repeat_count = (BUFFER_SIZE // len(emoji.encode("utf-8"))) - 1
        content = emoji * repeat_count

        encoded_size = len(content.encode("utf-8"))
        assert encoded_size < BUFFER_SIZE

        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content

    def test_save_file_over_64kb_with_emoji(self, tmp_dir):
        """File over 64KB containing emoji saves correctly (regression)."""
        path = os.path.join(tmp_dir, "over_64kb_emoji.txt")
        # Each emoji is 4 bytes in UTF-8; build content over 64KB
        emoji = "\U0001f600"  # 😀 — 4 bytes in UTF-8
        repeat_count = (BUFFER_SIZE // len(emoji.encode("utf-8"))) + 1000
        content = emoji * repeat_count

        encoded_size = len(content.encode("utf-8"))
        assert encoded_size > BUFFER_SIZE

        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content

    def test_save_file_over_64kb_with_cjk(self, tmp_dir):
        """File over 64KB with mixed ASCII and CJK saves correctly."""
        path = os.path.join(tmp_dir, "over_64kb_cjk.txt")
        # CJK characters are 3 bytes each in UTF-8
        cjk_block = "你好世界"  # 4 chars, 12 bytes
        ascii_block = "Hello "  # 6 chars, 6 bytes
        # Mix ASCII and CJK to exceed 64KB
        unit = ascii_block + cjk_block  # 10 chars, 18 bytes
        repeat_count = (BUFFER_SIZE // len(unit.encode("utf-8"))) + 100
        content = unit * repeat_count

        encoded_size = len(content.encode("utf-8"))
        assert encoded_size > BUFFER_SIZE

        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content

    def test_save_large_ascii_file(self, tmp_dir):
        """File over 64KB with only ASCII saves correctly."""
        path = os.path.join(tmp_dir, "large_ascii.txt")
        content = "A" * (BUFFER_SIZE + 10000)

        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content

    def test_round_trip_preserves_content(self, tmp_dir):
        """Saved content matches when reloaded (round-trip integrity)."""
        path = os.path.join(tmp_dir, "roundtrip.txt")
        # Mixed content with various multibyte characters
        content = "ASCII text 🎉 中文 العربية café naïve 🚀" * 5000

        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            loaded = f.read()

        assert loaded == content

    def test_empty_content(self, tmp_dir):
        """Empty string produces an empty file."""
        path = os.path.join(tmp_dir, "empty.txt")
        save_file(path, "")

        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == ""

    def test_non_string_raises_type_error(self, tmp_dir):
        """Passing non-string content raises TypeError."""
        path = os.path.join(tmp_dir, "bad.txt")
        with pytest.raises(TypeError):
            save_file(path, 12345)

    def test_creates_parent_directories(self, tmp_dir):
        """Parent directories are created if they do not exist."""
        path = os.path.join(tmp_dir, "nested", "dir", "file.txt")
        save_file(path, "nested content")

        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == "nested content"
