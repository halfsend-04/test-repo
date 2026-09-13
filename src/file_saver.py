"""File saving module with correct UTF-8 multibyte character handling.

This module provides buffered file saving that correctly handles UTF-8
multibyte characters at buffer boundaries. The buffer size is measured
in bytes, and partial multibyte sequences at the end of a chunk are
carried over to the next chunk instead of being split.
"""

import os

# Buffer size in bytes for chunked file writing.
BUFFER_SIZE = 65536  # 64KB


def _find_safe_split(data: bytes, max_bytes: int) -> int:
    """Find the largest split point <= max_bytes that does not cut a
    multibyte UTF-8 sequence.

    UTF-8 continuation bytes have the form 10xxxxxx (0x80..0xBF).
    Walking backward from the proposed split point until we find a
    non-continuation byte ensures we never split mid-character.
    """
    if max_bytes >= len(data):
        return len(data)

    pos = max_bytes
    # Walk backward past any continuation bytes (10xxxxxx).
    while pos > 0 and (data[pos] & 0xC0) == 0x80:
        pos -= 1
    return pos


def save_file(content: str, path: str) -> None:
    """Save *content* to *path* using chunked writes that respect UTF-8
    multibyte boundaries.

    The previous implementation allocated a fixed 64KB buffer and split
    the encoded byte stream at arbitrary positions.  When a multibyte
    UTF-8 sequence straddled the 64KB boundary the resulting partial
    write caused a segmentation fault in the native I/O layer.

    This version encodes the full string to bytes first, then splits at
    safe UTF-8 boundaries before writing each chunk.
    """
    encoded = content.encode("utf-8")
    tmp_path = path + ".tmp"

    try:
        with open(tmp_path, "wb") as fh:
            offset = 0
            while offset < len(encoded):
                end = _find_safe_split(encoded, offset + BUFFER_SIZE)
                chunk = encoded[offset:end]
                fh.write(chunk)
                offset = end
        os.replace(tmp_path, path)
    except BaseException:
        # Clean up the temporary file on any failure.
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
