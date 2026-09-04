"""File saving module with buffered UTF-8-safe writes.

Provides chunked file saving that correctly sizes buffers using byte
length rather than character count.  When a multibyte UTF-8 character
straddles a chunk boundary, the split point is moved back to the
nearest character boundary to avoid splitting a multibyte sequence.
"""

import os

# Buffer size in bytes for chunked file writing.
BUFFER_SIZE = 65536  # 64 KB


def _find_safe_split(data: bytes, max_bytes: int) -> int:
    """Return the largest split point <= *max_bytes* that does not
    cut a multibyte UTF-8 sequence.

    UTF-8 continuation bytes have the bit pattern ``10xxxxxx``
    (``0x80``..``0xBF``).  Walking backward from *max_bytes* until a
    non-continuation byte is found guarantees the split falls on a
    character boundary.
    """
    if max_bytes >= len(data):
        return len(data)

    pos = max_bytes
    while pos > 0 and (data[pos] & 0xC0) == 0x80:
        pos -= 1
    return pos


def save_file(content: str, path: str) -> None:
    """Save *content* to *path* using chunked, UTF-8-safe writes.

    The content is encoded to bytes first so the buffer is sized by
    actual byte length rather than character count.  Each chunk is
    split at a safe UTF-8 boundary.  A temporary file is used so
    that the target path is updated atomically via :func:`os.replace`.
    """
    encoded = content.encode("utf-8")
    tmp_path = path + ".tmp"

    try:
        with open(tmp_path, "wb") as fh:
            offset = 0
            while offset < len(encoded):
                end = _find_safe_split(encoded, offset + BUFFER_SIZE)
                fh.write(encoded[offset:end])
                offset = end
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
