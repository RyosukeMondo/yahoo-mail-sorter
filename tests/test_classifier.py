"""Tests for the classifier rule engine — the most critical test file."""

from __future__ import annotations

from yahoo_mail_sorter.classifier import Classifier
from yahoo_mail_sorter.models import (
    Category,
    CategoryConfig,
    Email,
)


class TestClassifier:
    def test_finance_email(
        self, sample_categories: list[CategoryConfig], finance_email: Email
    ) -> None:
        clf = Classifier(sample_categories)
        result = clf.classify(finance_email)
        assert result.category == Category.FINANCE
        assert result.folder == "Finance"

    def test_shopping_email(
        self, sample_categories: list[CategoryConfig], shopping_email: Email
    ) -> None:
        clf = Classifier(sample_categories)
        result = clf.classify(shopping_email)
        assert result.category == Category.SHOPPING
        assert result.folder == "Shopping"

    def test_newsletter_email(
        self, sample_categories: list[CategoryConfig], newsletter_email: Email
    ) -> None:
        clf = Classifier(sample_categories)
        result = clf.classify(newsletter_email)
        assert result.category == Category.NEWSLETTER
        assert result.folder == "Newsletter"

    def test_spam_email(
        self, sample_categories: list[CategoryConfig], spam_email: Email
    ) -> None:
        clf = Classifier(sample_categories)
        result = clf.classify(spam_email)
        assert result.category == Category.SPAM
        assert result.folder == "Spam"

    def test_social_email(
        self, sample_categories: list[CategoryConfig], social_email: Email
    ) -> None:
        clf = Classifier(sample_categories)
        result = clf.classify(social_email)
        assert result.category == Category.SOCIAL
        assert result.folder == "Social"

    def test_important_email(
        self, sample_categories: list[CategoryConfig], important_email: Email
    ) -> None:
        clf = Classifier(sample_categories)
        result = clf.classify(important_email)
        assert result.category == Category.IMPORTANT
        assert result.folder == "Important"

    def test_fallback_to_other(
        self, sample_categories: list[CategoryConfig], sample_email: Email
    ) -> None:
        clf = Classifier(sample_categories)
        result = clf.classify(sample_email)
        assert result.category == Category.OTHER
        assert result.folder == "INBOX"

    def test_priority_ordering_important_beats_newsletter(
        self, sample_categories: list[CategoryConfig]
    ) -> None:
        """An email with X-Priority: 1 AND List-Unsubscribe should be IMPORTANT."""
        email = Email(
            uid="999",
            subject="重要メルマガ",
            sender="news@example.com",
            x_priority="1",
            list_unsubscribe="<mailto:unsub@example.com>",
        )
        clf = Classifier(sample_categories)
        result = clf.classify(email)
        assert result.category == Category.IMPORTANT

    def test_priority_ordering_finance_beats_shopping(
        self, sample_categories: list[CategoryConfig]
    ) -> None:
        """An email from smbc about an order should be FINANCE (higher priority)."""
        email = Email(
            uid="888",
            subject="ご注文のお取引明細",
            sender="info@smbc.co.jp",
        )
        clf = Classifier(sample_categories)
        result = clf.classify(email)
        assert result.category == Category.FINANCE

    def test_classify_batch(
        self,
        sample_categories: list[CategoryConfig],
        finance_email: Email,
        spam_email: Email,
        sample_email: Email,
    ) -> None:
        clf = Classifier(sample_categories)
        results = clf.classify_batch([finance_email, spam_email, sample_email])
        assert len(results) == 3
        assert results[0].category == Category.FINANCE
        assert results[1].category == Category.SPAM
        assert results[2].category == Category.OTHER

    def test_empty_batch(self, sample_categories: list[CategoryConfig]) -> None:
        clf = Classifier(sample_categories)
        results = clf.classify_batch([])
        assert results == []
