"""File saving module with proper UTF-8 multibyte character handling.

This module handles saving files of arbitrary size, correctly accounting
for UTF-8 encoded byte length rather than character count when sizing
internal buffers. Prior to this fix (v2.3.1 regression), the buffer was
sized based on character count, which caused out-of-bounds writes and
segmentation faults when multibyte characters (emoji, CJK, etc.) pushed
the encoded byte length past the buffer boundary.
"""

import os
import tempfile

# Default chunk size for buffered writes (64 KiB).
DEFAULT_CHUNK_SIZE = 64 * 1024


def save_file(content: str, path: str, chunk_size: int = DEFAULT_CHUNK_SIZE) -> None:
    """Save text content to a file, handling UTF-8 multibyte characters.

    Writes content in chunks, sizing each chunk by *encoded byte length*
    rather than character count to prevent buffer overflows when content
    contains multibyte UTF-8 characters.

    Args:
        content: The text content to save.
        path: Destination file path.
        chunk_size: Maximum bytes per write chunk. Defaults to 64 KiB.

    Raises:
        OSError: If the file cannot be written.
        ValueError: If chunk_size is not positive.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    encoded = content.encode("utf-8")

    # Write atomically via a temp file to avoid partial writes on failure.
    dir_name = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(dir=dir_name)
    try:
        offset = 0
        while offset < len(encoded):
            end = offset + chunk_size
            chunk = encoded[offset:end]
            os.write(fd, chunk)
            offset = end
        os.fsync(fd)
        os.close(fd)
        fd = -1
        os.replace(tmp_path, path)
    except Exception:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def read_file(path: str) -> str:
    """Read a UTF-8 encoded text file.

    Args:
        path: Source file path.

    Returns:
        The decoded text content.

    Raises:
        OSError: If the file cannot be read.
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
