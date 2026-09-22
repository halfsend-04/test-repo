"""File saving module with proper UTF-8 buffer handling."""

import os

# Maximum buffer size for chunked writes (64KB)
BUFFER_SIZE = 65536


def save_file(filepath, content):
    """Save content to a file, handling UTF-8 multibyte characters correctly.

    The buffer is allocated based on the byte length of the encoded content,
    not the character count. This prevents buffer overflows when the content
    contains multibyte UTF-8 characters (e.g., emoji, CJK characters) that
    occupy more than one byte per character.

    Args:
        filepath: Path to the output file.
        content: String content to write.

    Raises:
        OSError: If the file cannot be written.
        TypeError: If content is not a string.
    """
    if not isinstance(content, str):
        raise TypeError("content must be a string")

    encoded = content.encode("utf-8")
    byte_length = len(encoded)

    dirpath = os.path.dirname(filepath)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)

    with open(filepath, "wb") as f:
        offset = 0
        while offset < byte_length:
            chunk = encoded[offset : offset + BUFFER_SIZE]
            f.write(chunk)
            offset += len(chunk)
