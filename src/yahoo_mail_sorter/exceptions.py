"""Custom exception hierarchy for Yahoo Mail Sorter."""


class YahooMailSorterError(Exception):
    """Base exception for all Yahoo Mail Sorter errors."""


class ConfigError(YahooMailSorterError):
    """Missing or invalid configuration (env vars, rules file)."""


class IMAPConnectionError(YahooMailSorterError):
    """Failed to connect or authenticate with IMAP server."""


class IMAPOperationError(YahooMailSorterError):
    """IMAP command failed (fetch, move, folder creation)."""


class RulesLoadError(YahooMailSorterError):
    """Failed to load or parse the rules YAML file."""


class DecodingError(YahooMailSorterError):
    """Failed to decode an email header."""
