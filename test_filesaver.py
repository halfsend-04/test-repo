"""Tests for filesaver module — regression tests for issue #594.

Verifies that save_file handles multibyte UTF-8 characters correctly
when the file size exceeds the 64KB chunk boundary.
"""

import os
import tempfile

import pytest

from filesaver import CHUNK_SIZE, save_file


@pytest.fixture
def tmp_path_file():
    """Yield a temporary file path that is cleaned up after the test."""
    fd, path = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


class TestSaveFileUTF8:
    """Regression tests for issue #594: crash on >64KB UTF-8 files."""

    def test_large_file_with_emoji(self, tmp_path_file):
        """File >64KB containing emoji saves without error."""
        # Each emoji is 4 bytes in UTF-8; 20000 emoji = 80KB
        content = "\U0001f600" * 20000
        assert len(content.encode("utf-8")) > CHUNK_SIZE

        save_file(tmp_path_file, content)

        with open(tmp_path_file, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")

    def test_large_file_with_cjk(self, tmp_path_file):
        """File >64KB containing CJK characters saves without error."""
        # CJK characters are 3 bytes each in UTF-8
        content = "\u4e16\u754c\u4f60\u597d" * 6000  # ~72KB
        assert len(content.encode("utf-8")) > CHUNK_SIZE

        save_file(tmp_path_file, content)

        with open(tmp_path_file, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")

    def test_large_file_ascii_only(self, tmp_path_file):
        """File >64KB with ASCII-only content saves correctly (control)."""
        content = "A" * (CHUNK_SIZE + 1024)

        save_file(tmp_path_file, content)

        with open(tmp_path_file, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")

    def test_exact_boundary_multibyte(self, tmp_path_file):
        """File of exactly 64KB of multibyte characters saves correctly."""
        # 4-byte emoji: need exactly CHUNK_SIZE / 4 = 16384 characters
        char_count = CHUNK_SIZE // 4
        content = "\U0001f600" * char_count
        assert len(content.encode("utf-8")) == CHUNK_SIZE

        save_file(tmp_path_file, content)

        with open(tmp_path_file, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")

    def test_boundary_plus_one_multibyte(self, tmp_path_file):
        """File of 64KB + one multibyte char spanning the boundary."""
        char_count = CHUNK_SIZE // 4 + 1
        content = "\U0001f600" * char_count
        assert len(content.encode("utf-8")) == CHUNK_SIZE + 4

        save_file(tmp_path_file, content)

        with open(tmp_path_file, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")

    def test_small_file_multibyte(self, tmp_path_file):
        """File <64KB with multibyte characters saves correctly."""
        content = "\U0001f600" * 100
        assert len(content.encode("utf-8")) < CHUNK_SIZE

        save_file(tmp_path_file, content)

        with open(tmp_path_file, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")

    def test_empty_file(self, tmp_path_file):
        """Empty content saves correctly."""
        save_file(tmp_path_file, "")

        with open(tmp_path_file, "rb") as f:
            saved = f.read()
        assert saved == b""

    def test_mixed_ascii_and_multibyte(self, tmp_path_file):
        """File >64KB with mixed ASCII and multibyte characters."""
        # Mix ASCII and emoji to create >64KB
        unit = "Hello \U0001f600 World \u4e16\u754c "  # 22 bytes in UTF-8
        repeat = (CHUNK_SIZE // len(unit.encode("utf-8"))) + 100
        content = unit * repeat
        assert len(content.encode("utf-8")) > CHUNK_SIZE

        save_file(tmp_path_file, content)

        with open(tmp_path_file, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")
