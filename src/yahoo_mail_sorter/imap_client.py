"""IMAP client — thin wrapper around imaplib with protocol-based DI."""

from __future__ import annotations

import imaplib
import logging
from typing import TYPE_CHECKING, Protocol

from yahoo_mail_sorter.decoder import decode_header_value
from yahoo_mail_sorter.exceptions import IMAPConnectionError, IMAPOperationError
from yahoo_mail_sorter.models import Email

if TYPE_CHECKING:
    from yahoo_mail_sorter.config import IMAPConfig

logger = logging.getLogger(__name__)

# Headers to fetch (BODY.PEEK to avoid marking as read)
FETCH_HEADERS = (
    "BODY.PEEK[HEADER.FIELDS"
    " (SUBJECT FROM TO DATE X-PRIORITY LIST-UNSUBSCRIBE)]"
)


class IMAPClientProtocol(Protocol):
    """Protocol for IMAP operations — enables DI for testing."""

    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def list_folders(self) -> list[str]: ...
    def fetch_emails(self, folder: str, limit: int | None) -> list[Email]: ...
    def move_email(self, uid: str, dest_folder: str) -> None: ...
    def ensure_folder(self, folder: str) -> None: ...


class IMAPClient:
    """Real IMAP client using imaplib.IMAP4_SSL."""

    def __init__(self, config: IMAPConfig) -> None:
        self._config = config
        self._conn: imaplib.IMAP4_SSL | None = None

    def __enter__(self) -> IMAPClient:
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.disconnect()

    def connect(self) -> None:
        try:
            self._conn = imaplib.IMAP4_SSL(self._config.host, self._config.port)
            self._conn.login(self._config.user, self._config.password)
            logger.info("Connected to %s as %s", self._config.host, self._config.user)
        except imaplib.IMAP4.error as exc:
            raise IMAPConnectionError(f"IMAP login failed: {exc}") from exc
        except OSError as exc:
            raise IMAPConnectionError(f"Cannot reach IMAP server: {exc}") from exc

    def disconnect(self) -> None:
        if self._conn is None:
            return
        try:
            self._conn.logout()
        except Exception:
            pass
        finally:
            self._conn = None

    @property
    def conn(self) -> imaplib.IMAP4_SSL:
        if self._conn is None:
            raise IMAPConnectionError("Not connected — call connect() first")
        return self._conn

    def list_folders(self) -> list[str]:
        status, data = self.conn.list()
        if status != "OK":
            raise IMAPOperationError(f"LIST failed: {status}")
        folders: list[str] = []
        for item in data:
            if item is None:
                continue
            line = item.decode("utf-7", errors="replace") if isinstance(item, bytes) else str(item)
            # Format: (\\flags) "delimiter" "name"
            parts = line.rsplit('" "', 1)
            if len(parts) == 2:
                name = parts[1].rstrip('"')
            else:
                # Try alternate parsing: rsplit on delimiter
                parts = line.rsplit(" ", 1)
                name = parts[-1].strip('"')
            folders.append(name)
        return sorted(folders)

    def fetch_emails(self, folder: str = "INBOX", limit: int | None = None) -> list[Email]:
        status, _count = self.conn.select(folder, readonly=True)
        if status != "OK":
            raise IMAPOperationError(f"SELECT {folder} failed: {status}")

        status, uids_data = self.conn.uid("SEARCH", None, "ALL")  # type: ignore[arg-type]
        if status != "OK":
            raise IMAPOperationError(f"SEARCH failed: {status}")

        raw_uids = uids_data[0]
        if not raw_uids:
            return []
        uid_list = raw_uids.split()
        if limit is not None:
            uid_list = uid_list[-limit:]  # most recent

        # Batch fetch in chunks to avoid server timeout
        emails: list[Email] = []
        batch_size = 50
        for i in range(0, len(uid_list), batch_size):
            batch = uid_list[i : i + batch_size]
            batch_emails = self._fetch_batch(batch)
            emails.extend(batch_emails)
            logger.info("Fetched %d/%d emails", len(emails), len(uid_list))

        return emails

    def _fetch_batch(self, uid_list: list[bytes]) -> list[Email]:
        """Fetch headers for a batch of UIDs in a single IMAP command."""
        uid_set = b",".join(uid_list)
        try:
            status, data = self.conn.uid(
                "FETCH", uid_set.decode(), f"({FETCH_HEADERS})"
            )
        except (imaplib.IMAP4.abort, imaplib.IMAP4.error) as exc:
            logger.warning("Batch fetch failed, reconnecting: %s", exc)
            self._reconnect()
            status, data = self.conn.uid(
                "FETCH", uid_set.decode(), f"({FETCH_HEADERS})"
            )
        if status != "OK":
            logger.warning("FETCH batch failed: %s", status)
            return []

        emails: list[Email] = []
        for item in data:
            if item is None or not isinstance(item, tuple):
                continue
            # Extract UID from response line like b'123 (UID 456 BODY[...]'
            uid = _extract_uid(item[0])
            if uid is None:
                continue
            try:
                email = _parse_headers(uid, item[1])
                emails.append(email)
            except Exception:
                logger.warning("Failed to parse headers for UID %s", uid)
        return emails

    def _reconnect(self) -> None:
        """Drop current connection and reconnect."""
        logger.info("Reconnecting to IMAP server...")
        try:
            if self._conn is not None:
                self._conn.logout()
        except Exception:
            pass
        self._conn = None
        self.connect()
        self.conn.select("INBOX", readonly=True)

    def move_email(self, uid: str, dest_folder: str) -> None:
        # Select INBOX as writable
        status, _ = self.conn.select("INBOX")
        if status != "OK":
            raise IMAPOperationError(f"SELECT INBOX failed: {status}")

        # Copy then mark deleted (MOVE not universally supported)
        status, _ = self.conn.uid("COPY", uid, dest_folder)
        if status != "OK":
            raise IMAPOperationError(f"COPY UID {uid} to {dest_folder} failed: {status}")

        self.conn.uid("STORE", uid, "+FLAGS", "(\\Deleted)")
        self.conn.expunge()
        logger.debug("Moved UID %s → %s", uid, dest_folder)

    def ensure_folder(self, folder: str) -> None:
        status, _ = self.conn.create(folder)
        # "already exists" is fine
        if status != "OK":
            # Check if it already exists by trying select
            check_status, _ = self.conn.select(folder, readonly=True)
            if check_status != "OK":
                raise IMAPOperationError(f"Cannot create folder {folder}: {status}")
            self.conn.select("INBOX", readonly=True)


def _extract_uid(response_line: bytes) -> str | None:
    """Extract UID from an IMAP FETCH response line like b'1 (UID 42 BODY[...]'."""
    import re

    match = re.search(rb"UID (\d+)", response_line)
    if match:
        return match.group(1).decode()
    return None


def _parse_headers(uid: str, raw: bytes) -> Email:
    """Parse raw IMAP header bytes into an Email model."""
    import email

    msg = email.message_from_bytes(raw)
    return Email(
        uid=uid,
        subject=decode_header_value(msg.get("Subject")),
        sender=decode_header_value(msg.get("From")),
        to=decode_header_value(msg.get("To")),
        date=decode_header_value(msg.get("Date")),
        x_priority=decode_header_value(msg.get("X-Priority")),
        list_unsubscribe=decode_header_value(msg.get("List-Unsubscribe")),
    )
