"""File writer module with correct UTF-8 buffer handling.

Provides buffered file writing that correctly handles multibyte UTF-8
characters by sizing buffers based on byte length rather than character
count.
"""

# Default buffer size in bytes (64 KiB).
BUFFER_SIZE = 65536


def save_file(path, content):
    """Write *content* to *path* using buffered binary I/O.

    The buffer boundary is calculated in **bytes** (after UTF-8
    encoding), not in characters.  Using the character count would
    under-allocate the buffer when multibyte characters are present,
    leading to a write past the end of the buffer — the root cause of
    the segfault reported in v2.3.1 for files larger than 64 KB
    containing emoji or CJK text.
    """
    encoded = content.encode("utf-8")
    with open(path, "wb") as fh:
        offset = 0
        while offset < len(encoded):
            end = min(offset + BUFFER_SIZE, len(encoded))
            fh.write(encoded[offset:end])
            offset = end
