"""Tests for file_saver module.

Covers the bug reported in issue #1724: saving files larger than 64KB
containing multibyte UTF-8 characters caused a crash due to buffer
sizing using character count instead of byte count.
"""

import os
import tempfile

import pytest

from src.file_saver import CHUNK_SIZE, save_file


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory for test output files."""
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestSaveFile:
    """Tests for save_file function."""

    def test_save_small_ascii_file(self, tmp_dir):
        """Small ASCII files save correctly."""
        path = os.path.join(tmp_dir, "small.txt")
        content = "Hello, world!"
        save_file(content, path)
        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content

    def test_save_large_ascii_file(self, tmp_dir):
        """ASCII files larger than 64KB save correctly."""
        path = os.path.join(tmp_dir, "large_ascii.txt")
        content = "A" * (CHUNK_SIZE + 1024)
        save_file(content, path)
        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content

    def test_save_large_file_with_emoji(self, tmp_dir):
        """Files >64KB with emoji (4-byte UTF-8) save correctly.

        This is the primary regression test for issue #1724.
        """
        path = os.path.join(tmp_dir, "emoji.txt")
        # Each emoji is 4 bytes in UTF-8; generate >64KB of emoji content
        emoji_char = "\U0001f600"  # grinning face
        count = (CHUNK_SIZE // len(emoji_char.encode("utf-8"))) + 256
        content = emoji_char * count
        assert len(content.encode("utf-8")) > CHUNK_SIZE
        save_file(content, path)
        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content

    def test_save_large_file_with_cjk(self, tmp_dir):
        """Files >64KB with CJK characters (3-byte UTF-8) save correctly."""
        path = os.path.join(tmp_dir, "cjk.txt")
        # CJK characters are 3 bytes in UTF-8
        cjk_char = "世"  # Chinese character for "world"
        count = (CHUNK_SIZE // len(cjk_char.encode("utf-8"))) + 256
        content = cjk_char * count
        assert len(content.encode("utf-8")) > CHUNK_SIZE
        save_file(content, path)
        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content

    def test_save_file_exactly_at_boundary(self, tmp_dir):
        """File with multibyte chars exactly at 64KB boundary saves."""
        path = os.path.join(tmp_dir, "boundary.txt")
        emoji_char = "\U0001f600"
        byte_len = len(emoji_char.encode("utf-8"))
        # Fill to exactly CHUNK_SIZE bytes
        count = CHUNK_SIZE // byte_len
        content = emoji_char * count
        assert len(content.encode("utf-8")) == CHUNK_SIZE
        save_file(content, path)
        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content

    def test_save_multibyte_spanning_boundary(self, tmp_dir):
        """Multibyte character spanning the 64KB boundary saves."""
        path = os.path.join(tmp_dir, "spanning.txt")
        emoji_char = "\U0001f600"  # 4 bytes
        byte_len = len(emoji_char.encode("utf-8"))
        # Create content where a multibyte char spans the chunk boundary
        ascii_pad = "A" * (CHUNK_SIZE - 2)
        content = ascii_pad + emoji_char * 256
        encoded = content.encode("utf-8")
        assert encoded[CHUNK_SIZE - 2:CHUNK_SIZE + 2] != b"AAAA"
        assert len(encoded) > CHUNK_SIZE
        save_file(content, path)
        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content

    def test_save_mixed_ascii_and_multibyte(self, tmp_dir):
        """Mixed ASCII and multibyte content >64KB saves correctly."""
        path = os.path.join(tmp_dir, "mixed.txt")
        # Mix ASCII and emoji to exceed 64KB
        block = "Hello \U0001f600 World 世界 "
        count = (CHUNK_SIZE // len(block.encode("utf-8"))) + 100
        content = block * count
        assert len(content.encode("utf-8")) > CHUNK_SIZE
        save_file(content, path)
        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content

    def test_save_empty_file(self, tmp_dir):
        """Empty content saves correctly."""
        path = os.path.join(tmp_dir, "empty.txt")
        save_file("", path)
        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == ""

    def test_save_overwrites_existing_file(self, tmp_dir):
        """Saving to an existing file replaces its content."""
        path = os.path.join(tmp_dir, "overwrite.txt")
        save_file("original", path)
        save_file("updated", path)
        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == "updated"
