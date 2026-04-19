"""Tests for the raw-message SQLite dumper."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from yahoo_mail_sorter.dumper import Dumper


class FakeIMAP:
    def __init__(self, messages: list[tuple[str, int, bytes]]) -> None:
        self._messages = messages
        self.fetch_calls: list[tuple[str, int | None, str | None]] = []

    # Unused protocol methods — kept as no-ops so FakeIMAP satisfies IMAPClientProtocol.
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def list_folders(self) -> list[str]:
        return []
    def fetch_emails(self, folder: str, limit: int | None) -> list[Any]:
        return []
    def move_email(self, uid: str, dest_folder: str) -> None: ...
    def ensure_folder(self, folder: str) -> None: ...

    def fetch_raw(
        self, folder: str, limit: int | None, search: str | None
    ) -> Iterator[tuple[str, int, bytes]]:
        self.fetch_calls.append((folder, limit, search))
        for uid, uidvalidity, raw in self._messages:
            yield uid, uidvalidity, raw


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "dump.sqlite"


def test_dump_writes_all_messages_to_sqlite(db_path: Path) -> None:
    messages = [
        ("1", 42, b"From: a@example.com\r\nSubject: one\r\n\r\nbody1"),
        ("2", 42, b"From: b@example.com\r\nSubject: two\r\n\r\nbody2"),
    ]
    imap = FakeIMAP(messages)

    report = Dumper(imap, db_path).dump(folder="INBOX")

    assert report.fetched == 2
    assert report.skipped == 0
    assert report.folder == "INBOX"

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT uid, uidvalidity, raw FROM emails ORDER BY uid"
    ).fetchall()
    conn.close()

    assert rows == [
        ("1", 42, messages[0][2]),
        ("2", 42, messages[1][2]),
    ]


def test_dump_is_idempotent_on_rerun(db_path: Path) -> None:
    messages = [("1", 42, b"raw-bytes")]
    imap = FakeIMAP(messages)

    first = Dumper(imap, db_path).dump(folder="INBOX")
    second = Dumper(imap, db_path).dump(folder="INBOX")

    assert first.fetched == 1 and first.skipped == 0
    assert second.fetched == 0 and second.skipped == 1

    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
    conn.close()
    assert count == 1


def test_dump_passes_search_criteria_to_imap(db_path: Path) -> None:
    imap = FakeIMAP([])
    Dumper(imap, db_path).dump(
        folder="INBOX", limit=10, search='FROM "auctions.yahoo.co.jp"'
    )
    assert imap.fetch_calls == [("INBOX", 10, 'FROM "auctions.yahoo.co.jp"')]


def test_dump_keeps_rows_with_same_uid_across_different_uidvalidity(
    db_path: Path,
) -> None:
    imap = FakeIMAP([("1", 42, b"old")])
    Dumper(imap, db_path).dump(folder="INBOX")

    imap2 = FakeIMAP([("1", 99, b"new")])
    Dumper(imap2, db_path).dump(folder="INBOX")

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT uidvalidity, raw FROM emails ORDER BY uidvalidity"
    ).fetchall()
    conn.close()
    assert rows == [(42, b"old"), (99, b"new")]
