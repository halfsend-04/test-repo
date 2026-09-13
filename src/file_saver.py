"""File saving module with correct UTF-8 buffer handling.

This module handles saving file content to disk using chunked writes.
All buffer sizing uses byte lengths (not character counts) to correctly
handle multibyte UTF-8 characters such as emoji and CJK characters.
"""

import os
import tempfile

# Buffer size for chunked writes (64KB)
CHUNK_SIZE = 65536


def save_file(content: str, path: str) -> None:
    """Save text content to a file using chunked writes.

    Uses byte-length buffer sizing to correctly handle multibyte UTF-8
    characters. Writes to a temporary file first, then atomically renames
    to the target path to avoid partial writes on failure.

    Args:
        content: The text content to save.
        path: The file path to write to.

    Raises:
        OSError: If the file cannot be written.
    """
    encoded = content.encode("utf-8")
    dir_name = os.path.dirname(os.path.abspath(path))

    fd, tmp_path = tempfile.mkstemp(dir=dir_name)
    try:
        offset = 0
        while offset < len(encoded):
            chunk = encoded[offset:offset + CHUNK_SIZE]
            os.write(fd, chunk)
            offset += len(chunk)
        os.close(fd)
        os.replace(tmp_path, path)
    except Exception:
        os.close(fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
