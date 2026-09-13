"""File save module with proper UTF-8 buffer handling.

Fixed in response to issue #19: the previous implementation allocated
write buffers based on character count (len(text)) instead of byte
count (len(text.encode('utf-8'))). For ASCII-only content these are
equal, but multibyte UTF-8 characters (emoji, CJK, etc.) require
more bytes than characters. When the file exceeded the 64KB chunk
boundary, the undersized buffer caused a write past allocated memory.
"""

CHUNK_SIZE = 65536  # 64KB


def save_file(path: str, content: str) -> None:
    """Save content to a file, writing in 64KB chunks.

    Uses byte length (not character length) to size the write buffer,
    ensuring multibyte UTF-8 sequences are handled correctly at chunk
    boundaries.

    Args:
        path: Destination file path.
        content: Unicode text to write.

    Raises:
        OSError: If the file cannot be written.
    """
    data = content.encode("utf-8")
    with open(path, "wb") as f:
        offset = 0
        while offset < len(data):
            end = offset + CHUNK_SIZE
            f.write(data[offset:end])
            offset = end


def _save_file_buggy(path: str, content: str) -> None:
    """Buggy implementation preserved for regression testing.

    This version uses character length to calculate chunk boundaries,
    which under-allocates when the content contains multibyte UTF-8
    characters and the file exceeds 64KB.
    """
    data = content.encode("utf-8")
    # BUG: uses len(content) (character count) instead of len(data) (byte count)
    char_chunks = [
        content[i : i + CHUNK_SIZE] for i in range(0, len(content), CHUNK_SIZE)
    ]
    with open(path, "wb") as f:
        for chunk in char_chunks:
            f.write(chunk.encode("utf-8"))
