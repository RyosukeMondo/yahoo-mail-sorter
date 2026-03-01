"""Orchestrator — scan, sort, and clean operations with dry-run default."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from yahoo_mail_sorter.models import Category, ClassificationResult, SortReport

if TYPE_CHECKING:
    from yahoo_mail_sorter.classifier import Classifier
    from yahoo_mail_sorter.imap_client import IMAPClientProtocol

logger = logging.getLogger(__name__)

MOVE_BATCH_SIZE = 200


class Sorter:
    """Orchestrates email classification and sorting.

    All operations default to dry-run (preview only).
    Pass execute=True to actually move emails.
    """

    def __init__(
        self,
        imap: IMAPClientProtocol,
        classifier: Classifier,
    ) -> None:
        self._imap = imap
        self._classifier = classifier

    def scan(self, limit: int | None = None) -> SortReport:
        """Fetch and classify emails without moving anything."""
        emails = self._imap.fetch_emails("INBOX", limit=limit)
        results = self._classifier.classify_batch(emails)
        report = SortReport()
        for result in results:
            report.add(result, was_moved=False)
        return report

    def sort(self, *, execute: bool = False, limit: int | None = None) -> SortReport:
        """Classify and optionally move emails to category folders.

        Args:
            execute: If True, actually move emails. If False, dry-run only.
            limit: Max number of emails to process.
        """
        emails = self._imap.fetch_emails("INBOX", limit=limit)
        results = self._classifier.classify_batch(emails)
        report = SortReport()

        to_move = [r for r in results if r.category != Category.OTHER]
        others = [r for r in results if r.category == Category.OTHER]

        for result in others:
            report.add(result, was_moved=False)

        if not execute:
            for result in to_move:
                report.add(result, was_moved=False)
            return report

        self._move_batch(to_move, report)
        return report

    def clean(self, *, execute: bool = False, limit: int | None = None) -> SortReport:
        """Move spam emails to the Spam folder.

        Args:
            execute: If True, actually move emails. If False, dry-run only.
            limit: Max number of emails to process.
        """
        emails = self._imap.fetch_emails("INBOX", limit=limit)
        results = self._classifier.classify_batch(emails)
        report = SortReport()

        spam = [r for r in results if r.category == Category.SPAM]

        if not execute:
            for result in spam:
                report.add(result, was_moved=False)
            return report

        self._move_batch(spam, report)
        return report

    def _move_batch(
        self, results: list[ClassificationResult], report: SortReport
    ) -> None:
        """Move emails in batches, reconnecting between batches."""
        for i in range(0, len(results), MOVE_BATCH_SIZE):
            batch = results[i : i + MOVE_BATCH_SIZE]
            consecutive_failures = 0

            for result in batch:
                moved = self._move_one(result)
                report.add(result, was_moved=moved)

                if moved:
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= 3:
                        logger.warning("3 consecutive failures, reconnecting...")
                        self._reconnect()
                        consecutive_failures = 0

            if i + MOVE_BATCH_SIZE < len(results):
                logger.info(
                    "Batch done: %d/%d moved so far. Reconnecting...",
                    report.moved, len(results),
                )
                self._reconnect()

    def _move_one(self, result: ClassificationResult) -> bool:
        """Move a single email. Returns True on success."""
        try:
            self._imap.ensure_folder(result.folder)
            self._imap.move_email(result.email.uid, result.folder)
            return True
        except Exception:
            logger.warning("Failed to move UID %s to %s", result.email.uid, result.folder)
            return False

    def _reconnect(self) -> None:
        """Reconnect IMAP client."""
        try:
            self._imap.disconnect()
        except Exception:
            pass
        try:
            self._imap.connect()
        except Exception:
            logger.exception("Reconnect failed")
