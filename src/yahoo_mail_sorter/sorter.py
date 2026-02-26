"""Orchestrator — scan, sort, and clean operations with dry-run default."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from yahoo_mail_sorter.models import Category, ClassificationResult, SortReport

if TYPE_CHECKING:
    from yahoo_mail_sorter.classifier import Classifier
    from yahoo_mail_sorter.imap_client import IMAPClientProtocol

logger = logging.getLogger(__name__)


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

        for result in results:
            if result.category == Category.OTHER:
                report.add(result, was_moved=False)
                continue

            if execute:
                moved = self._move_email(result)
                report.add(result, was_moved=moved)
            else:
                report.add(result, was_moved=False)

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

        for result in results:
            if result.category != Category.SPAM:
                continue

            if execute:
                moved = self._move_email(result)
                report.add(result, was_moved=moved)
            else:
                report.add(result, was_moved=False)

        return report

    def _move_email(self, result: ClassificationResult) -> bool:
        """Move a single email to its target folder. Returns True on success."""
        try:
            self._imap.ensure_folder(result.folder)
            self._imap.move_email(result.email.uid, result.folder)
            return True
        except Exception:
            logger.exception("Failed to move UID %s to %s", result.email.uid, result.folder)
            return False
