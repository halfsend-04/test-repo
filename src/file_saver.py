"""File saving module with correct UTF-8 buffer handling.

Handles saving file content to disk using chunked writes. All buffer
sizing uses byte lengths (not character counts) to correctly handle
multibyte UTF-8 characters such as emoji and CJK characters.
"""

import os
import tempfile

# Buffer size for chunked writes (64KB)
CHUNK_SIZE = 65536


def save_file(content: str, path: str) -> None:
    """Save text content to a file using chunked writes.

    Encodes content to UTF-8 bytes first, then writes in fixed-size
    chunks based on byte length. This avoids the buffer overflow that
    occurs when sizing buffers by character count, since multibyte
    UTF-8 characters (emoji = 4 bytes, CJK = 3 bytes) require more
    space than their character count implies.

    Writes to a temporary file first, then atomically replaces the
    target to avoid partial writes on failure.

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
            chunk = encoded[offset : offset + CHUNK_SIZE]
            os.write(fd, chunk)
            offset += len(chunk)
        os.close(fd)
        os.replace(tmp_path, path)
    except Exception:
        os.close(fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
