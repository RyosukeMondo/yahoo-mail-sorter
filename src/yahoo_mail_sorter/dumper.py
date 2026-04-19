"""Dump raw RFC822 messages from an IMAP folder into a local SQLite database."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from yahoo_mail_sorter.imap_client import IMAPClientProtocol

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS emails (
    folder      TEXT    NOT NULL,
    uidvalidity INTEGER NOT NULL,
    uid         TEXT    NOT NULL,
    fetched_at  TEXT    NOT NULL,
    raw         BLOB    NOT NULL,
    PRIMARY KEY (folder, uidvalidity, uid)
);
CREATE INDEX IF NOT EXISTS idx_emails_folder ON emails(folder);
"""


@dataclass(frozen=True)
class DumpReport:
    folder: str
    db_path: str
    fetched: int
    skipped: int


class Dumper:
    """Write raw messages from an IMAP folder to a SQLite DB (idempotent)."""

    def __init__(self, imap: IMAPClientProtocol, db_path: Path) -> None:
        self._imap = imap
        self._db_path = db_path

    def dump(
        self,
        folder: str = "INBOX",
        limit: int | None = None,
        search: str | None = None,
    ) -> DumpReport:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.executescript(SCHEMA)
            conn.commit()

            existing = self._existing_uids(conn, folder)

            fetched = 0
            skipped = 0
            now = datetime.now(timezone.utc).isoformat()

            for uid, uidvalidity, raw in self._imap.fetch_raw(folder, limit, search):
                if (uidvalidity, uid) in existing:
                    skipped += 1
                    continue
                conn.execute(
                    "INSERT OR REPLACE INTO emails"
                    " (folder, uidvalidity, uid, fetched_at, raw)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (folder, uidvalidity, uid, now, raw),
                )
                fetched += 1
                if fetched % 50 == 0:
                    conn.commit()
                    logger.info("Dumped %d messages from %s", fetched, folder)

            conn.commit()
            return DumpReport(
                folder=folder,
                db_path=str(self._db_path),
                fetched=fetched,
                skipped=skipped,
            )
        finally:
            conn.close()

    @staticmethod
    def _existing_uids(conn: sqlite3.Connection, folder: str) -> set[tuple[int, str]]:
        cur = conn.execute(
            "SELECT uidvalidity, uid FROM emails WHERE folder = ?", (folder,)
        )
        return {(row[0], row[1]) for row in cur.fetchall()}
