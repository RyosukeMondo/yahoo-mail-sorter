"""Domain models — frozen dataclasses and enums, zero external deps."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import re


class Category(StrEnum):
    """Email categories in priority order (lower value = higher priority)."""

    IMPORTANT = "important"
    FINANCE = "finance"
    SHOPPING = "shopping"
    NEWSLETTER = "newsletter"
    SOCIAL = "social"
    SPAM = "spam"
    OTHER = "other"


# Maps each category to its IMAP target folder name.
CATEGORY_FOLDERS: dict[Category, str] = {
    Category.IMPORTANT: "Important",
    Category.FINANCE: "Finance",
    Category.SHOPPING: "Shopping",
    Category.NEWSLETTER: "Newsletter",
    Category.SOCIAL: "Social",
    Category.SPAM: "Spam",
    Category.OTHER: "INBOX",
}


@dataclass(frozen=True)
class Email:
    """Parsed email metadata (headers only — no body fetch)."""

    uid: str
    subject: str
    sender: str
    to: str = ""
    date: str = ""
    x_priority: str = ""
    list_unsubscribe: str = ""


@dataclass(frozen=True)
class Rule:
    """A single matching rule: field, compiled regex pattern, and original text."""

    field: str  # "subject", "sender", "x_priority", "list_unsubscribe"
    pattern: re.Pattern[str]
    raw_pattern: str

    def matches(self, email: Email) -> bool:
        value = getattr(email, self.field, "")
        return bool(self.pattern.search(value))


@dataclass(frozen=True)
class CategoryConfig:
    """Classification config for one category: priority + rules."""

    category: Category
    priority: int
    rules: tuple[Rule, ...]
    folder: str

    def matches(self, email: Email) -> bool:
        return any(rule.matches(email) for rule in self.rules)


@dataclass(frozen=True)
class ClassificationResult:
    """Result of classifying a single email."""

    email: Email
    category: Category
    folder: str


@dataclass
class SortReport:
    """Aggregated results of a sort/scan operation."""

    total: int = 0
    moved: int = 0
    skipped: int = 0
    errors: int = 0
    by_category: dict[Category, list[ClassificationResult]] = field(default_factory=dict)

    def add(self, result: ClassificationResult, *, was_moved: bool) -> None:
        self.total += 1
        if was_moved:
            self.moved += 1
        else:
            self.skipped += 1
        self.by_category.setdefault(result.category, []).append(result)
