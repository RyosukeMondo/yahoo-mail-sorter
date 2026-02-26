"""Load and parse classification rules from YAML."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import yaml

from yahoo_mail_sorter.exceptions import RulesLoadError
from yahoo_mail_sorter.models import (
    CATEGORY_FOLDERS,
    Category,
    CategoryConfig,
    Rule,
)

if TYPE_CHECKING:
    from pathlib import Path


def load_rules(path: Path) -> list[CategoryConfig]:
    """Parse rules.yaml into a priority-ordered list of CategoryConfig.

    Args:
        path: Path to the YAML rules file.

    Returns:
        List of CategoryConfig sorted by priority (ascending = highest first).

    Raises:
        RulesLoadError: When the file is missing, malformed, or has invalid rules.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RulesLoadError(f"Rules file not found: {path}") from exc
    except OSError as exc:
        raise RulesLoadError(f"Cannot read rules file: {path}: {exc}") from exc

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise RulesLoadError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(data, dict) or "categories" not in data:
        raise RulesLoadError(f"Rules file must have a top-level 'categories' key: {path}")

    configs: list[CategoryConfig] = []
    for entry in data["categories"]:
        try:
            category = Category(entry["name"])
        except (KeyError, ValueError) as exc:
            raise RulesLoadError(f"Invalid category entry: {entry}") from exc

        priority = int(entry.get("priority", 99))
        folder = entry.get("folder", CATEGORY_FOLDERS.get(category, "INBOX"))
        rules = _parse_rules(entry.get("rules", []), category)
        configs.append(CategoryConfig(
            category=category, priority=priority, rules=tuple(rules), folder=folder
        ))

    configs.sort(key=lambda c: c.priority)
    return configs


def _parse_rules(raw_rules: list[dict[str, str]], category: Category) -> list[Rule]:
    """Compile raw rule dicts into Rule objects with pre-compiled regex."""
    rules: list[Rule] = []
    for raw in raw_rules:
        field = raw.get("field", "")
        pattern_str = raw.get("pattern", "")
        if not field or not pattern_str:
            raise RulesLoadError(
                f"Rule in {category.value} missing 'field' or 'pattern': {raw}"
            )
        try:
            compiled = re.compile(pattern_str, re.IGNORECASE)
        except re.error as exc:
            raise RulesLoadError(
                f"Invalid regex in {category.value}: {pattern_str!r}: {exc}"
            ) from exc
        rules.append(Rule(field=field, pattern=compiled, raw_pattern=pattern_str))
    return rules
