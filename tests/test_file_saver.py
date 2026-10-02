"""Tests for the UTF-8 byte-aware file save utility.

Covers the scenarios from the issue:
1. Files under 64KB with multibyte characters save correctly.
2. Files over 64KB with multibyte characters save correctly (was segfault).
3. Large files with mixed ASCII and multibyte content save correctly.
4. Byte-level round-trip integrity is preserved in all cases.
"""

import os
import tempfile

import pytest

from src.file_saver import BUFFER_SIZE, save_file


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as d:
        yield d


def _round_trip(tmp_dir: str, content: str) -> None:
    """Save content and verify it reads back identically."""
    path = os.path.join(tmp_dir, "output.txt")
    save_file(path, content)
    with open(path, "r", encoding="utf-8") as f:
        assert f.read() == content


class TestUtf8SaveUnder64KB:
    """Files under 64KB with multibyte characters should save correctly."""

    def test_emoji_content_under_boundary(self, tmp_dir):
        # ~63KB of emoji (each emoji is 4 bytes in UTF-8)
        char_count = (BUFFER_SIZE - 1024) // 4
        content = "\U0001F600" * char_count  # 😀
        assert len(content.encode("utf-8")) < BUFFER_SIZE
        _round_trip(tmp_dir, content)

    def test_cjk_content_under_boundary(self, tmp_dir):
        # CJK characters are 3 bytes each in UTF-8
        char_count = (BUFFER_SIZE - 1024) // 3
        content = "世" * char_count  # 世
        assert len(content.encode("utf-8")) < BUFFER_SIZE
        _round_trip(tmp_dir, content)


class TestUtf8SaveOver64KB:
    """Files over 64KB with multibyte characters must save without crashing.

    This was the crash scenario reported in the issue: content whose byte
    length exceeds 64KB due to multibyte characters caused a segfault
    because the buffer was sized by character count, not byte count.
    """

    def test_emoji_content_over_boundary(self, tmp_dir):
        # ~65KB of emoji text
        char_count = (BUFFER_SIZE + 1024) // 4
        content = "\U0001F600" * char_count
        assert len(content.encode("utf-8")) > BUFFER_SIZE
        _round_trip(tmp_dir, content)

    def test_cjk_content_over_boundary(self, tmp_dir):
        # ~65KB of CJK text
        char_count = (BUFFER_SIZE + 1024) // 3
        content = "世" * char_count
        assert len(content.encode("utf-8")) > BUFFER_SIZE
        _round_trip(tmp_dir, content)

    def test_large_emoji_file(self, tmp_dir):
        # ~128KB of emoji
        char_count = (BUFFER_SIZE * 2) // 4
        content = "\U0001F600" * char_count
        _round_trip(tmp_dir, content)


class TestMixedContent:
    """Mixed ASCII and multibyte content over 64KB must save correctly."""

    def test_mixed_ascii_and_emoji(self, tmp_dir):
        # Build ~128KB of mixed content
        block = "Hello World! \U0001F600\U0001F389 "  # ASCII + emoji
        repetitions = (BUFFER_SIZE * 2) // len(block.encode("utf-8")) + 1
        content = block * repetitions
        assert len(content.encode("utf-8")) > BUFFER_SIZE
        _round_trip(tmp_dir, content)

    def test_mixed_ascii_and_cjk(self, tmp_dir):
        block = "test 世界 "
        repetitions = (BUFFER_SIZE * 2) // len(block.encode("utf-8")) + 1
        content = block * repetitions
        assert len(content.encode("utf-8")) > BUFFER_SIZE
        _round_trip(tmp_dir, content)


class TestEdgeCases:
    """Edge cases for buffer boundary behavior."""

    def test_empty_file(self, tmp_dir):
        _round_trip(tmp_dir, "")

    def test_exactly_at_boundary(self, tmp_dir):
        # Content whose byte length is exactly BUFFER_SIZE
        content = "a" * BUFFER_SIZE
        assert len(content.encode("utf-8")) == BUFFER_SIZE
        _round_trip(tmp_dir, content)

    def test_ascii_over_boundary(self, tmp_dir):
        # ASCII-only content over 64KB should still work
        content = "a" * (BUFFER_SIZE + 1024)
        _round_trip(tmp_dir, content)
