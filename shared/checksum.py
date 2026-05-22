"""Checksum validation helpers."""

import hashlib


def md5_hex(data: bytes) -> str:
    """Return the lowercase MD5 hex digest for blob content."""
    return hashlib.md5(data, usedforsecurity=False).hexdigest()


def checksum_matches(expected: str, *, content_md5: bytes | None = None, data: bytes | None = None) -> bool:
    """Compare a client checksum against blob MD5 metadata or raw content."""
    if content_md5 is not None:
        actual = content_md5.hex()
    elif data is not None:
        actual = md5_hex(data)
    else:
        return False

    return actual.lower() == expected.lower()
