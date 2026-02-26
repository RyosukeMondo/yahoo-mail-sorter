"""Tests for configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from yahoo_mail_sorter.config import load_config
from yahoo_mail_sorter.exceptions import ConfigError


class TestLoadConfig:
    def test_loads_from_env_file(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text(
            "YAHOO_IMAP_HOST=imap.mail.yahoo.co.jp\n"
            "YAHOO_IMAP_PORT=993\n"
            "YAHOO_MAIL_USER=testuser\n"
            "YAHOO_MAIL_PASSWORD=secret\n"
            "RULES_PATH=my_rules.yaml\n"
        )
        config = load_config(env_path=env)
        assert config.imap.host == "imap.mail.yahoo.co.jp"
        assert config.imap.port == 993
        assert config.imap.user == "testuser"
        assert config.imap.password == "secret"
        assert config.rules_path == Path("my_rules.yaml")

    def test_default_port_and_rules_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env = tmp_path / ".env"
        env.write_text(
            "YAHOO_IMAP_HOST=imap.test\n"
            "YAHOO_MAIL_USER=u\n"
            "YAHOO_MAIL_PASSWORD=p\n"
        )
        # Clear any existing env vars that might interfere
        monkeypatch.delenv("YAHOO_IMAP_PORT", raising=False)
        monkeypatch.delenv("RULES_PATH", raising=False)
        config = load_config(env_path=env)
        assert config.imap.port == 993
        assert config.rules_path == Path("rules.yaml")

    def test_missing_required_vars_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env = tmp_path / ".env"
        env.write_text("")
        # Clear any env vars that might be set from previous tests
        monkeypatch.delenv("YAHOO_IMAP_HOST", raising=False)
        monkeypatch.delenv("YAHOO_MAIL_USER", raising=False)
        monkeypatch.delenv("YAHOO_MAIL_PASSWORD", raising=False)
        with pytest.raises(ConfigError, match="Missing required env vars"):
            load_config(env_path=env)
