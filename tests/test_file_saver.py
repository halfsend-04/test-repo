"""Tests for the file_saver module.

Covers the bug where files >64KB containing UTF-8 multibyte characters
caused a segmentation fault due to buffer sizing in characters instead
of bytes (issue #2318).
"""

import os
import tempfile
import unittest

from src.file_saver import BUFFER_SIZE, _align_utf8_boundary, save_file


class TestSaveFile(unittest.TestCase):
    """Test save_file with various sizes and encodings."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        for f in os.listdir(self.tmpdir):
            os.unlink(os.path.join(self.tmpdir, f))
        os.rmdir(self.tmpdir)

    def _path(self, name: str) -> str:
        return os.path.join(self.tmpdir, name)

    def test_small_ascii_file(self):
        """Files under 64KB with ASCII save correctly."""
        content = "hello world\n" * 100
        path = self._path("small_ascii.txt")
        save_file(content, path)
        with open(path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content)

    def test_small_utf8_file(self):
        """Files under 64KB with multibyte UTF-8 save correctly."""
        content = "Hello 🌍🎉 日本語テスト\n" * 100
        path = self._path("small_utf8.txt")
        save_file(content, path)
        with open(path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content)

    def test_large_ascii_file(self):
        """Files over 64KB with only ASCII save correctly."""
        content = "A" * (BUFFER_SIZE + 10000)
        path = self._path("large_ascii.txt")
        save_file(content, path)
        with open(path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content)

    def test_large_utf8_file(self):
        """Files over 64KB with multibyte UTF-8 save correctly (issue #2318)."""
        # ~70KB of text with emoji characters
        emoji_line = "🎉🌍🚀💡🔥" * 20 + "\n"  # Each emoji is 4 bytes
        content = emoji_line * 200  # Well over 64KB in bytes
        byte_size = len(content.encode("utf-8"))
        self.assertGreater(byte_size, BUFFER_SIZE)

        path = self._path("large_utf8.txt")
        save_file(content, path)
        with open(path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content)

    def test_multibyte_at_64kb_boundary(self):
        """A multibyte character spanning the 64KB byte offset saves correctly."""
        # Fill up to just before the 64KB boundary, then place an emoji
        padding = "A" * (BUFFER_SIZE - 2)
        content = padding + "🎉" + "B" * 1000
        byte_size = len(content.encode("utf-8"))
        self.assertGreater(byte_size, BUFFER_SIZE)

        path = self._path("boundary_utf8.txt")
        save_file(content, path)
        with open(path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content)

    def test_cjk_large_file(self):
        """Large files with CJK characters (3-byte UTF-8) save correctly."""
        cjk_line = "日本語テストデータ" * 50 + "\n"
        content = cjk_line * 200
        byte_size = len(content.encode("utf-8"))
        self.assertGreater(byte_size, BUFFER_SIZE)

        path = self._path("large_cjk.txt")
        save_file(content, path)
        with open(path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content)

    def test_empty_file(self):
        """Saving an empty string creates an empty file."""
        path = self._path("empty.txt")
        save_file("", path)
        with open(path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "")


class TestAlignUtf8Boundary(unittest.TestCase):
    """Test the UTF-8 boundary alignment helper."""

    def test_ascii_boundary(self):
        """ASCII bytes are not continuation bytes; position stays."""
        data = b"ABCDEF"
        self.assertEqual(_align_utf8_boundary(data, 3), 3)

    def test_continuation_byte_backs_up(self):
        """Landing on a continuation byte backs up to the leading byte."""
        # U+1F389 = F0 9F 8E 89 (4-byte emoji)
        data = b"AA" + "🎉".encode("utf-8") + b"BB"
        # data = b'AA\xf0\x9f\x8e\x89BB'
        # Indices: 0=A 1=A 2=F0 3=9F 4=8E 5=89 6=B 7=B
        self.assertEqual(_align_utf8_boundary(data, 3), 2)  # backs to F0
        self.assertEqual(_align_utf8_boundary(data, 4), 2)  # backs to F0
        self.assertEqual(_align_utf8_boundary(data, 5), 2)  # backs to F0

    def test_leading_byte_stays(self):
        """Position on a leading byte stays put."""
        data = b"AA" + "🎉".encode("utf-8") + b"BB"
        self.assertEqual(_align_utf8_boundary(data, 2), 2)

    def test_two_byte_sequence(self):
        """2-byte UTF-8 sequence boundary alignment."""
        # U+00E9 (é) = C3 A9
        data = b"A" + "é".encode("utf-8") + b"B"
        # Indices: 0=A 1=C3 2=A9 3=B
        self.assertEqual(_align_utf8_boundary(data, 2), 1)

    def test_pos_zero(self):
        """Position 0 is always safe."""
        data = b"\x80\x80\x80"
        self.assertEqual(_align_utf8_boundary(data, 0), 0)


if __name__ == "__main__":
    unittest.main()
