"""File saving module with proper UTF-8 multibyte character handling.

This module provides chunked file writing that correctly sizes buffers
in bytes rather than characters, preventing buffer overruns when saving
files containing multibyte UTF-8 characters (emoji, CJK, etc.).
"""

import os
import tempfile

# Buffer size in bytes (64 KiB)
BUFFER_SIZE = 65536


def save_file(content: str, path: str) -> None:
    """Save content to a file using chunked writes with byte-aware buffering.

    The content is encoded to UTF-8 and written in chunks of BUFFER_SIZE
    bytes. Chunk boundaries are aligned to UTF-8 code-point boundaries
    to avoid splitting multibyte sequences.

    Args:
        content: The text content to save.
        path: The destination file path.

    Raises:
        OSError: If the file cannot be written.
    """
    data = content.encode("utf-8")
    dir_name = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_name)
    try:
        offset = 0
        while offset < len(data):
            end = min(offset + BUFFER_SIZE, len(data))
            # Align to a UTF-8 code-point boundary: if we land in the
            # middle of a multibyte sequence, back up to its start.
            if end < len(data):
                end = _align_utf8_boundary(data, end)
            os.write(fd, data[offset:end])
            offset = end
        os.fsync(fd)
    except BaseException:
        os.close(fd)
        os.unlink(tmp_path)
        raise
    else:
        os.close(fd)
        os.rename(tmp_path, path)


def _align_utf8_boundary(data: bytes, pos: int) -> int:
    """Move pos backward to a UTF-8 code-point boundary.

    In UTF-8, continuation bytes have the form 10xxxxxx (0x80..0xBF).
    If pos lands on a continuation byte, back up until we reach a
    leading byte (or the start of the buffer).

    Args:
        data: The full byte buffer.
        pos: The candidate split position.

    Returns:
        A position <= pos that does not split a multibyte sequence.
    """
    # Back up at most 3 bytes (max UTF-8 sequence is 4 bytes)
    for _ in range(3):
        if pos <= 0:
            break
        # A continuation byte has bits 10xxxxxx
        if (data[pos] & 0xC0) != 0x80:
            break
        pos -= 1
    return pos
