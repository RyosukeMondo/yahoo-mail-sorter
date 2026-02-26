"""Shared fixtures for Yahoo Mail Sorter tests."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from yahoo_mail_sorter.models import (
    Category,
    CategoryConfig,
    Email,
    Rule,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def sample_email() -> Email:
    return Email(
        uid="100",
        subject="テスト件名",
        sender="test@example.com",
        to="user@yahoo.co.jp",
        date="Thu, 01 Jan 2025 09:00:00 +0900",
    )


@pytest.fixture()
def finance_email() -> Email:
    return Email(
        uid="200",
        subject="お取引明細のお知らせ",
        sender="info@smbc.co.jp",
        to="user@yahoo.co.jp",
        date="Fri, 02 Jan 2025 10:00:00 +0900",
    )


@pytest.fixture()
def shopping_email() -> Email:
    return Email(
        uid="300",
        subject="ご注文の確認 - Amazon.co.jp",
        sender="auto-confirm@amazon.co.jp",
        to="user@yahoo.co.jp",
        date="Sat, 03 Jan 2025 11:00:00 +0900",
    )


@pytest.fixture()
def newsletter_email() -> Email:
    return Email(
        uid="400",
        subject="今週のメルマガ",
        sender="newsletter@example.com",
        to="user@yahoo.co.jp",
        date="Sun, 04 Jan 2025 12:00:00 +0900",
        list_unsubscribe="<mailto:unsub@example.com>",
    )


@pytest.fixture()
def spam_email() -> Email:
    return Email(
        uid="500",
        subject="おめでとうございます！当選しました",
        sender="winner@sketchy.com",
        to="user@yahoo.co.jp",
        date="Mon, 05 Jan 2025 13:00:00 +0900",
    )


@pytest.fixture()
def social_email() -> Email:
    return Email(
        uid="600",
        subject="新しいフォロワーがいます",
        sender="notification@facebookmail.com",
        to="user@yahoo.co.jp",
        date="Tue, 06 Jan 2025 14:00:00 +0900",
    )


@pytest.fixture()
def important_email() -> Email:
    return Email(
        uid="700",
        subject="重要なお知らせ",
        sender="boss@company.com",
        to="user@yahoo.co.jp",
        date="Wed, 07 Jan 2025 15:00:00 +0900",
        x_priority="1",
    )


def _rule(field: str, pattern: str) -> Rule:
    return Rule(field=field, pattern=re.compile(pattern, re.IGNORECASE), raw_pattern=pattern)


@pytest.fixture()
def sample_categories() -> list[CategoryConfig]:
    return [
        CategoryConfig(
            category=Category.IMPORTANT, priority=1, folder="Important",
            rules=(_rule("x_priority", r"^[12]$"),),
        ),
        CategoryConfig(
            category=Category.FINANCE, priority=2, folder="Finance",
            rules=(
                _rule("sender", r"smbc|mufg|mizuho"),
                _rule("subject", r"お取引|入金|出金|振込|口座|明細"),
            ),
        ),
        CategoryConfig(
            category=Category.SHOPPING, priority=3, folder="Shopping",
            rules=(
                _rule("sender", r"amazon\.co\.jp|rakuten\.co\.jp|mercari"),
                _rule("subject", r"ご注文|発送|配送|お届け"),
            ),
        ),
        CategoryConfig(
            category=Category.NEWSLETTER, priority=4, folder="Newsletter",
            rules=(
                _rule("list_unsubscribe", r".+"),
                _rule("subject", r"メルマガ|ニュースレター"),
            ),
        ),
        CategoryConfig(
            category=Category.SOCIAL, priority=5, folder="Social",
            rules=(
                _rule("sender", r"facebookmail|twitter|discord"),
                _rule("subject", r"フォロー|いいね"),
            ),
        ),
        CategoryConfig(
            category=Category.SPAM, priority=6, folder="Spam",
            rules=(
                _rule("subject", r"当選|おめでとう|無料|副業"),
            ),
        ),
        CategoryConfig(
            category=Category.OTHER, priority=99, folder="INBOX",
            rules=(),
        ),
    ]


@pytest.fixture()
def rules_yaml_path(tmp_path: Path) -> Path:
    content = """\
categories:
  - name: important
    priority: 1
    folder: Important
    rules:
      - field: x_priority
        pattern: "^[12]$"
  - name: finance
    priority: 2
    folder: Finance
    rules:
      - field: sender
        pattern: "smbc|mufg"
  - name: shopping
    priority: 3
    folder: Shopping
    rules:
      - field: sender
        pattern: "amazon\\\\.co\\\\.jp"
  - name: newsletter
    priority: 4
    folder: Newsletter
    rules:
      - field: list_unsubscribe
        pattern: ".+"
  - name: social
    priority: 5
    folder: Social
    rules:
      - field: sender
        pattern: "facebookmail"
  - name: spam
    priority: 6
    folder: Spam
    rules:
      - field: subject
        pattern: "当選|おめでとう"
  - name: other
    priority: 99
    folder: INBOX
    rules: []
"""
    p = tmp_path / "rules.yaml"
    p.write_text(content, encoding="utf-8")
    return p
