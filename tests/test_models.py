"""Tests for domain models."""

from __future__ import annotations

import re

from yahoo_mail_sorter.models import (
    CATEGORY_FOLDERS,
    Category,
    CategoryConfig,
    ClassificationResult,
    Email,
    Rule,
    SortReport,
)


class TestCategory:
    def test_priority_order(self) -> None:
        cats = list(Category)
        assert cats[0] == Category.IMPORTANT
        assert cats[-1] == Category.OTHER

    def test_str_value(self) -> None:
        assert Category.FINANCE.value == "finance"
        assert Category("shopping") == Category.SHOPPING

    def test_all_categories_have_folders(self) -> None:
        for cat in Category:
            assert cat in CATEGORY_FOLDERS


class TestEmail:
    def test_frozen(self, sample_email: Email) -> None:
        try:
            sample_email.uid = "999"  # type: ignore[misc]
            raise AssertionError("Should be frozen")
        except AttributeError:
            pass

    def test_defaults(self) -> None:
        email = Email(uid="1", subject="test", sender="a@b.com")
        assert email.to == ""
        assert email.x_priority == ""
        assert email.list_unsubscribe == ""


class TestRule:
    def test_matches_subject(self, sample_email: Email) -> None:
        rule = Rule(
            field="subject",
            pattern=re.compile("テスト", re.IGNORECASE),
            raw_pattern="テスト",
        )
        assert rule.matches(sample_email)

    def test_no_match(self, sample_email: Email) -> None:
        rule = Rule(
            field="subject",
            pattern=re.compile("amazon", re.IGNORECASE),
            raw_pattern="amazon",
        )
        assert not rule.matches(sample_email)

    def test_matches_sender(self, finance_email: Email) -> None:
        rule = Rule(
            field="sender",
            pattern=re.compile("smbc", re.IGNORECASE),
            raw_pattern="smbc",
        )
        assert rule.matches(finance_email)


class TestCategoryConfig:
    def test_matches_any_rule(self, finance_email: Email) -> None:
        config = CategoryConfig(
            category=Category.FINANCE,
            priority=2,
            folder="Finance",
            rules=(
                Rule("sender", re.compile("nomatch"), "nomatch"),
                Rule("sender", re.compile("smbc", re.IGNORECASE), "smbc"),
            ),
        )
        assert config.matches(finance_email)

    def test_no_match_empty_rules(self, sample_email: Email) -> None:
        config = CategoryConfig(
            category=Category.OTHER,
            priority=99,
            folder="INBOX",
            rules=(),
        )
        assert not config.matches(sample_email)


class TestSortReport:
    def test_add_moved(self, sample_email: Email) -> None:
        report = SortReport()
        result = ClassificationResult(
            email=sample_email, category=Category.FINANCE, folder="Finance"
        )
        report.add(result, was_moved=True)
        assert report.total == 1
        assert report.moved == 1
        assert report.skipped == 0
        assert Category.FINANCE in report.by_category

    def test_add_skipped(self, sample_email: Email) -> None:
        report = SortReport()
        result = ClassificationResult(
            email=sample_email, category=Category.OTHER, folder="INBOX"
        )
        report.add(result, was_moved=False)
        assert report.total == 1
        assert report.moved == 0
        assert report.skipped == 1
