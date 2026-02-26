"""Rule engine — classifies emails into categories using pre-compiled regex rules."""

from __future__ import annotations

import logging

from yahoo_mail_sorter.models import (
    CATEGORY_FOLDERS,
    Category,
    CategoryConfig,
    ClassificationResult,
    Email,
)

logger = logging.getLogger(__name__)


class Classifier:
    """Classifies emails against priority-ordered category rules.

    Categories are evaluated in priority order (lowest number first).
    First match wins. No match → OTHER.
    """

    def __init__(self, categories: list[CategoryConfig]) -> None:
        # Ensure sorted by priority (should already be, but enforce)
        self._categories = sorted(categories, key=lambda c: c.priority)

    def classify(self, email: Email) -> ClassificationResult:
        for cat_config in self._categories:
            if cat_config.category == Category.OTHER:
                continue  # OTHER is the fallback, not a match target
            if cat_config.matches(email):
                logger.debug(
                    "UID %s → %s (priority %d)",
                    email.uid, cat_config.category.value, cat_config.priority,
                )
                return ClassificationResult(
                    email=email,
                    category=cat_config.category,
                    folder=cat_config.folder,
                )

        return ClassificationResult(
            email=email,
            category=Category.OTHER,
            folder=CATEGORY_FOLDERS[Category.OTHER],
        )

    def classify_batch(self, emails: list[Email]) -> list[ClassificationResult]:
        return [self.classify(email) for email in emails]
