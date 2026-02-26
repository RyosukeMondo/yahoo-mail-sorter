"""CLI integration tests using Typer's CliRunner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from yahoo_mail_sorter.cli import app
from yahoo_mail_sorter.config import AppConfig, IMAPConfig
from yahoo_mail_sorter.exceptions import ConfigError
from yahoo_mail_sorter.models import (
    Category,
    ClassificationResult,
    Email,
    SortReport,
)

runner = CliRunner()


def _make_config() -> AppConfig:
    return AppConfig(
        imap=IMAPConfig(host="imap.test", port=993, user="u", password="p"),
        rules_path=Path("rules.yaml"),
    )


def _make_report(*categories: Category) -> SortReport:
    report = SortReport()
    for i, cat in enumerate(categories):
        email = Email(uid=str(i), subject=f"Subject {i}", sender=f"s{i}@test.com")
        result = ClassificationResult(email=email, category=cat, folder=cat.value)
        report.add(result, was_moved=False)
    return report


class TestScanCommand:
    @patch("yahoo_mail_sorter.cli.load_config")
    @patch("yahoo_mail_sorter.cli.load_rules")
    @patch("yahoo_mail_sorter.cli.IMAPClient")
    def test_scan_basic(
        self,
        mock_imap_cls: MagicMock,
        mock_load_rules: MagicMock,
        mock_load_config: MagicMock,
    ) -> None:
        mock_load_config.return_value = _make_config()
        mock_load_rules.return_value = []

        mock_imap = MagicMock()
        mock_imap_cls.return_value = mock_imap
        mock_imap.__enter__ = MagicMock(return_value=mock_imap)
        mock_imap.__exit__ = MagicMock(return_value=False)
        mock_imap.fetch_emails.return_value = []

        result = runner.invoke(app, ["scan"])
        assert result.exit_code == 0
        assert "DRY RUN" in result.output

    @patch("yahoo_mail_sorter.cli.load_config")
    def test_scan_config_error(self, mock_load_config: MagicMock) -> None:
        mock_load_config.side_effect = ConfigError("missing vars")
        result = runner.invoke(app, ["scan"])
        assert result.exit_code == 1
        assert "missing vars" in result.output


class TestSortCommand:
    @patch("yahoo_mail_sorter.cli.load_config")
    @patch("yahoo_mail_sorter.cli.load_rules")
    @patch("yahoo_mail_sorter.cli.IMAPClient")
    def test_sort_dry_run(
        self,
        mock_imap_cls: MagicMock,
        mock_load_rules: MagicMock,
        mock_load_config: MagicMock,
    ) -> None:
        mock_load_config.return_value = _make_config()
        mock_load_rules.return_value = []

        mock_imap = MagicMock()
        mock_imap_cls.return_value = mock_imap
        mock_imap.__enter__ = MagicMock(return_value=mock_imap)
        mock_imap.__exit__ = MagicMock(return_value=False)
        mock_imap.fetch_emails.return_value = []

        result = runner.invoke(app, ["sort"])
        assert result.exit_code == 0
        assert "DRY RUN" in result.output

    @patch("yahoo_mail_sorter.cli.load_config")
    @patch("yahoo_mail_sorter.cli.load_rules")
    @patch("yahoo_mail_sorter.cli.IMAPClient")
    def test_sort_execute(
        self,
        mock_imap_cls: MagicMock,
        mock_load_rules: MagicMock,
        mock_load_config: MagicMock,
    ) -> None:
        mock_load_config.return_value = _make_config()
        mock_load_rules.return_value = []

        mock_imap = MagicMock()
        mock_imap_cls.return_value = mock_imap
        mock_imap.__enter__ = MagicMock(return_value=mock_imap)
        mock_imap.__exit__ = MagicMock(return_value=False)
        mock_imap.fetch_emails.return_value = []

        result = runner.invoke(app, ["sort", "--execute"])
        assert result.exit_code == 0
        assert "EXECUTED" in result.output


class TestCleanCommand:
    @patch("yahoo_mail_sorter.cli.load_config")
    @patch("yahoo_mail_sorter.cli.load_rules")
    @patch("yahoo_mail_sorter.cli.IMAPClient")
    def test_clean_dry_run(
        self,
        mock_imap_cls: MagicMock,
        mock_load_rules: MagicMock,
        mock_load_config: MagicMock,
    ) -> None:
        mock_load_config.return_value = _make_config()
        mock_load_rules.return_value = []

        mock_imap = MagicMock()
        mock_imap_cls.return_value = mock_imap
        mock_imap.__enter__ = MagicMock(return_value=mock_imap)
        mock_imap.__exit__ = MagicMock(return_value=False)
        mock_imap.fetch_emails.return_value = []

        result = runner.invoke(app, ["clean"])
        assert result.exit_code == 0


class TestFoldersCommand:
    @patch("yahoo_mail_sorter.cli.load_config")
    @patch("yahoo_mail_sorter.cli.IMAPClient")
    def test_folders_lists(
        self, mock_imap_cls: MagicMock, mock_load_config: MagicMock
    ) -> None:
        mock_load_config.return_value = _make_config()

        mock_imap = MagicMock()
        mock_imap_cls.return_value = mock_imap
        mock_imap.__enter__ = MagicMock(return_value=mock_imap)
        mock_imap.__exit__ = MagicMock(return_value=False)
        mock_imap.list_folders.return_value = ["INBOX", "Sent", "Trash"]

        result = runner.invoke(app, ["folders"])
        assert result.exit_code == 0
        assert "INBOX" in result.output


class TestHelpOutput:
    def test_no_args_shows_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "scan" in result.output
        assert "sort" in result.output
        assert "clean" in result.output
        assert "folders" in result.output
