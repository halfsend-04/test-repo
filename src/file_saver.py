"""File save utility with correct UTF-8 buffer handling.

Prior to this fix, the save buffer was allocated based on character count
rather than byte length. For ASCII-only content this works because each
character is exactly one byte. However, UTF-8 multibyte characters (emoji,
CJK, accented letters) occupy 2-4 bytes per character. When the character
count crossed the 64KB boundary, the byte length of multibyte content
exceeded the allocated buffer, causing a buffer overrun and segfault.

The fix allocates the buffer based on the byte length of the encoded
content, not the character count.
"""

import os
import tempfile

BUFFER_SIZE = 65536  # 64KB


def save_file(path: str, content: str) -> None:
    """Save content to a file using byte-length-aware buffering.

    Uses the byte length of the UTF-8-encoded content for buffer
    allocation, avoiding overruns when multibyte characters are present.

    Args:
        path: Destination file path.
        content: Unicode string to save.
    """
    encoded = content.encode("utf-8")
    byte_length = len(encoded)

    # Write to a temporary file first, then atomically rename to avoid
    # partial writes on crash.
    dir_name = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(dir=dir_name)
    try:
        with os.fdopen(fd, "wb") as f:
            offset = 0
            while offset < byte_length:
                end = min(offset + BUFFER_SIZE, byte_length)
                f.write(encoded[offset:end])
                offset = end
        os.replace(tmp_path, path)
    except BaseException:
        # Clean up the temp file on failure.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
