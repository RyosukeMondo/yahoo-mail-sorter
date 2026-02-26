"""Tests for IMAP client — all IMAP operations are mocked."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from yahoo_mail_sorter.config import IMAPConfig
from yahoo_mail_sorter.exceptions import IMAPConnectionError, IMAPOperationError
from yahoo_mail_sorter.imap_client import IMAPClient


@pytest.fixture()
def imap_config() -> IMAPConfig:
    return IMAPConfig(
        host="imap.test.com",
        port=993,
        user="testuser",
        password="testpass",
    )


@pytest.fixture()
def mock_imap4():
    with patch("yahoo_mail_sorter.imap_client.imaplib.IMAP4_SSL") as mock_cls:
        mock_conn = MagicMock()
        mock_cls.return_value = mock_conn
        mock_conn.login.return_value = ("OK", [b"LOGIN completed"])
        yield mock_conn


class TestIMAPClientConnect:
    def test_connect_success(self, imap_config: IMAPConfig, mock_imap4: MagicMock) -> None:
        client = IMAPClient(imap_config)
        client.connect()
        mock_imap4.login.assert_called_once_with("testuser", "testpass")

    def test_connect_login_failure(self, imap_config: IMAPConfig) -> None:
        import imaplib

        with patch("yahoo_mail_sorter.imap_client.imaplib.IMAP4_SSL") as mock_cls:
            mock_conn = MagicMock()
            mock_cls.return_value = mock_conn
            mock_conn.login.side_effect = imaplib.IMAP4.error("auth failed")
            client = IMAPClient(imap_config)
            with pytest.raises(IMAPConnectionError, match="login failed"):
                client.connect()

    def test_connect_network_failure(self, imap_config: IMAPConfig) -> None:
        with patch("yahoo_mail_sorter.imap_client.imaplib.IMAP4_SSL") as mock_cls:
            mock_cls.side_effect = OSError("connection refused")
            client = IMAPClient(imap_config)
            with pytest.raises(IMAPConnectionError, match="Cannot reach"):
                client.connect()

    def test_context_manager(self, imap_config: IMAPConfig, mock_imap4: MagicMock) -> None:
        client = IMAPClient(imap_config)
        with client:
            assert client.conn is not None
        mock_imap4.logout.assert_called_once()

    def test_disconnect_when_not_connected(self, imap_config: IMAPConfig) -> None:
        client = IMAPClient(imap_config)
        client.disconnect()  # should not raise


class TestIMAPClientOperations:
    def test_conn_property_raises_when_disconnected(self, imap_config: IMAPConfig) -> None:
        client = IMAPClient(imap_config)
        with pytest.raises(IMAPConnectionError, match="Not connected"):
            _ = client.conn

    def test_list_folders(self, imap_config: IMAPConfig, mock_imap4: MagicMock) -> None:
        mock_imap4.list.return_value = (
            "OK",
            [
                b'(\\HasNoChildren) "/" "INBOX"',
                b'(\\HasNoChildren) "/" "Sent"',
                b'(\\HasNoChildren) "/" "Trash"',
            ],
        )
        client = IMAPClient(imap_config)
        client.connect()
        folders = client.list_folders()
        assert "INBOX" in folders
        assert "Sent" in folders

    def test_list_folders_failure(self, imap_config: IMAPConfig, mock_imap4: MagicMock) -> None:
        mock_imap4.list.return_value = ("NO", [])
        client = IMAPClient(imap_config)
        client.connect()
        with pytest.raises(IMAPOperationError, match="LIST failed"):
            client.list_folders()

    def test_fetch_emails_empty_inbox(
        self, imap_config: IMAPConfig, mock_imap4: MagicMock
    ) -> None:
        mock_imap4.select.return_value = ("OK", [b"0"])
        mock_imap4.uid.return_value = ("OK", [b""])
        client = IMAPClient(imap_config)
        client.connect()
        emails = client.fetch_emails("INBOX")
        assert emails == []

    def test_fetch_emails_parses_headers(
        self, imap_config: IMAPConfig, mock_imap4: MagicMock
    ) -> None:
        mock_imap4.select.return_value = ("OK", [b"1"])
        # First uid call = SEARCH, second = FETCH
        raw_headers = (
            b"Subject: Test Subject\r\n"
            b"From: sender@test.com\r\n"
            b"To: user@yahoo.co.jp\r\n"
            b"Date: Thu, 01 Jan 2025 09:00:00 +0900\r\n"
            b"\r\n"
        )
        mock_imap4.uid.side_effect = [
            ("OK", [b"42"]),  # SEARCH
            ("OK", [(b"1 (UID 42 BODY[HEADER.FIELDS ...])", raw_headers)]),  # FETCH
        ]
        client = IMAPClient(imap_config)
        client.connect()
        emails = client.fetch_emails("INBOX", limit=1)
        assert len(emails) == 1
        assert emails[0].uid == "42"
        assert emails[0].subject == "Test Subject"
        assert emails[0].sender == "sender@test.com"

    def test_move_email(self, imap_config: IMAPConfig, mock_imap4: MagicMock) -> None:
        mock_imap4.select.return_value = ("OK", [b"1"])
        mock_imap4.uid.side_effect = [
            ("OK", [b"COPY done"]),  # COPY
            ("OK", [b"STORE done"]),  # STORE flags
        ]
        mock_imap4.expunge.return_value = ("OK", [])
        client = IMAPClient(imap_config)
        client.connect()
        client.move_email("42", "Finance")
        # Verify COPY was called
        assert mock_imap4.uid.call_count == 2

    def test_ensure_folder_already_exists(
        self, imap_config: IMAPConfig, mock_imap4: MagicMock
    ) -> None:
        mock_imap4.create.return_value = ("NO", [b"already exists"])
        mock_imap4.select.return_value = ("OK", [b"0"])
        client = IMAPClient(imap_config)
        client.connect()
        client.ensure_folder("Finance")  # should not raise

    def test_ensure_folder_create_failure(
        self, imap_config: IMAPConfig, mock_imap4: MagicMock
    ) -> None:
        mock_imap4.create.return_value = ("NO", [b"permission denied"])
        mock_imap4.select.return_value = ("NO", [b"not found"])
        client = IMAPClient(imap_config)
        client.connect()
        with pytest.raises(IMAPOperationError, match="Cannot create folder"):
            client.ensure_folder("Forbidden")
