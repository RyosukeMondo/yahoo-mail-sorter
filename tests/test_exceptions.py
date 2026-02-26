"""Tests for the exception hierarchy."""

from yahoo_mail_sorter.exceptions import (
    ConfigError,
    DecodingError,
    IMAPConnectionError,
    IMAPOperationError,
    RulesLoadError,
    YahooMailSorterError,
)


def test_base_exception_hierarchy() -> None:
    assert issubclass(ConfigError, YahooMailSorterError)
    assert issubclass(IMAPConnectionError, YahooMailSorterError)
    assert issubclass(IMAPOperationError, YahooMailSorterError)
    assert issubclass(RulesLoadError, YahooMailSorterError)
    assert issubclass(DecodingError, YahooMailSorterError)


def test_exceptions_carry_message() -> None:
    exc = ConfigError("missing YAHOO_MAIL_USER")
    assert "missing YAHOO_MAIL_USER" in str(exc)

    exc2 = IMAPConnectionError("connection refused")
    assert "connection refused" in str(exc2)
