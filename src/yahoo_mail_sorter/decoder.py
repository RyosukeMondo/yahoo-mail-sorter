"""Japanese email header decoding (ISO-2022-JP, Shift_JIS, UTF-8, etc.)."""

from __future__ import annotations

import logging
from email.header import decode_header, make_header

from yahoo_mail_sorter.exceptions import DecodingError

logger = logging.getLogger(__name__)


def decode_header_value(raw: str | bytes | None) -> str:
    """Decode an RFC 2047 encoded header value into a unicode string.

    Handles ISO-2022-JP, Shift_JIS, EUC-JP, UTF-8, and plain ASCII.

    Args:
        raw: Raw header value (may contain =?charset?encoding?...?= tokens).

    Returns:
        Decoded unicode string, or empty string for None/empty input.

    Raises:
        DecodingError: When decoding fails after all fallback attempts.
    """
    if raw is None:
        return ""

    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")

    raw = raw.strip()
    if not raw:
        return ""

    try:
        return str(make_header(decode_header(raw)))
    except Exception:
        pass

    # Fallback: try common Japanese encodings on the raw bytes
    for encoding in ("utf-8", "iso-2022-jp", "shift_jis", "euc-jp"):
        try:
            if isinstance(raw, str):
                return raw.encode("raw_unicode_escape").decode(encoding)
            return raw.decode(encoding)
        except (UnicodeDecodeError, UnicodeEncodeError, LookupError):
            continue

    # Last resort: return with replacement characters
    logger.warning("Could not decode header, using replacement: %r", raw[:80])
    raise DecodingError(f"Failed to decode header: {raw[:80]!r}")
