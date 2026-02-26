"""Configuration loading from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from yahoo_mail_sorter.exceptions import ConfigError


@dataclass(frozen=True)
class IMAPConfig:
    """IMAP connection settings."""

    host: str
    port: int
    user: str
    password: str


@dataclass(frozen=True)
class AppConfig:
    """Full application configuration."""

    imap: IMAPConfig
    rules_path: Path


def load_config(env_path: Path | None = None) -> AppConfig:
    """Load configuration from .env file and environment variables.

    Args:
        env_path: Explicit path to .env file. If None, searches cwd upward.

    Raises:
        ConfigError: When required environment variables are missing.
    """
    load_dotenv(dotenv_path=env_path)

    missing = [
        var
        for var in ("YAHOO_IMAP_HOST", "YAHOO_MAIL_USER", "YAHOO_MAIL_PASSWORD")
        if not os.getenv(var)
    ]
    if missing:
        raise ConfigError(f"Missing required env vars: {', '.join(missing)}")

    host = os.environ["YAHOO_IMAP_HOST"]
    port = int(os.getenv("YAHOO_IMAP_PORT", "993"))
    user = os.environ["YAHOO_MAIL_USER"]
    password = os.environ["YAHOO_MAIL_PASSWORD"]
    rules_path = Path(os.getenv("RULES_PATH", "rules.yaml"))

    return AppConfig(
        imap=IMAPConfig(host=host, port=port, user=user, password=password),
        rules_path=rules_path,
    )
