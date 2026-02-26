"""Tests for the sorter orchestrator."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from yahoo_mail_sorter.classifier import Classifier
from yahoo_mail_sorter.sorter import Sorter

if TYPE_CHECKING:
    from yahoo_mail_sorter.models import (
        CategoryConfig,
        Email,
    )


def _mock_imap(emails: list[Email]) -> MagicMock:
    mock = MagicMock()
    mock.fetch_emails.return_value = emails
    mock.ensure_folder.return_value = None
    mock.move_email.return_value = None
    return mock


class TestSorterScan:
    def test_scan_returns_all(
        self,
        sample_categories: list[CategoryConfig],
        finance_email: Email,
        spam_email: Email,
        sample_email: Email,
    ) -> None:
        imap = _mock_imap([finance_email, spam_email, sample_email])
        clf = Classifier(sample_categories)
        sorter = Sorter(imap, clf)

        report = sorter.scan()
        assert report.total == 3
        assert report.moved == 0  # scan never moves
        assert report.skipped == 3

    def test_scan_with_limit(
        self, sample_categories: list[CategoryConfig], finance_email: Email
    ) -> None:
        imap = _mock_imap([finance_email])
        clf = Classifier(sample_categories)
        sorter = Sorter(imap, clf)

        sorter.scan(limit=10)
        imap.fetch_emails.assert_called_once_with("INBOX", limit=10)


class TestSorterSort:
    def test_sort_dry_run(
        self,
        sample_categories: list[CategoryConfig],
        finance_email: Email,
        spam_email: Email,
    ) -> None:
        imap = _mock_imap([finance_email, spam_email])
        clf = Classifier(sample_categories)
        sorter = Sorter(imap, clf)

        report = sorter.sort(execute=False)
        assert report.total == 2
        assert report.moved == 0
        imap.move_email.assert_not_called()

    def test_sort_execute(
        self,
        sample_categories: list[CategoryConfig],
        finance_email: Email,
        spam_email: Email,
    ) -> None:
        imap = _mock_imap([finance_email, spam_email])
        clf = Classifier(sample_categories)
        sorter = Sorter(imap, clf)

        report = sorter.sort(execute=True)
        assert report.total == 2
        assert report.moved == 2
        assert imap.move_email.call_count == 2

    def test_sort_skips_other_category(
        self,
        sample_categories: list[CategoryConfig],
        sample_email: Email,
    ) -> None:
        imap = _mock_imap([sample_email])
        clf = Classifier(sample_categories)
        sorter = Sorter(imap, clf)

        report = sorter.sort(execute=True)
        assert report.total == 1
        assert report.moved == 0
        imap.move_email.assert_not_called()

    def test_sort_handles_move_failure(
        self,
        sample_categories: list[CategoryConfig],
        finance_email: Email,
    ) -> None:
        imap = _mock_imap([finance_email])
        imap.move_email.side_effect = Exception("IMAP error")
        clf = Classifier(sample_categories)
        sorter = Sorter(imap, clf)

        report = sorter.sort(execute=True)
        assert report.total == 1
        assert report.moved == 0  # failed


class TestSorterClean:
    def test_clean_dry_run(
        self,
        sample_categories: list[CategoryConfig],
        spam_email: Email,
        finance_email: Email,
    ) -> None:
        imap = _mock_imap([spam_email, finance_email])
        clf = Classifier(sample_categories)
        sorter = Sorter(imap, clf)

        report = sorter.clean(execute=False)
        assert report.total == 1  # only spam counted
        assert report.moved == 0
        imap.move_email.assert_not_called()

    def test_clean_execute(
        self,
        sample_categories: list[CategoryConfig],
        spam_email: Email,
        finance_email: Email,
    ) -> None:
        imap = _mock_imap([spam_email, finance_email])
        clf = Classifier(sample_categories)
        sorter = Sorter(imap, clf)

        report = sorter.clean(execute=True)
        assert report.total == 1
        assert report.moved == 1
        imap.move_email.assert_called_once()
