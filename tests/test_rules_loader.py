"""Tests for YAML rules loading."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from yahoo_mail_sorter.exceptions import RulesLoadError
from yahoo_mail_sorter.models import Category
from yahoo_mail_sorter.rules_loader import load_rules

if TYPE_CHECKING:
    from pathlib import Path


class TestLoadRules:
    def test_loads_valid_yaml(self, rules_yaml_path: Path) -> None:
        configs = load_rules(rules_yaml_path)
        assert len(configs) == 7
        # Sorted by priority
        assert configs[0].category == Category.IMPORTANT
        assert configs[0].priority == 1
        assert configs[-1].category == Category.OTHER

    def test_rules_are_compiled(self, rules_yaml_path: Path) -> None:
        configs = load_rules(rules_yaml_path)
        finance = next(c for c in configs if c.category == Category.FINANCE)
        assert len(finance.rules) == 1
        assert finance.rules[0].pattern.pattern == "smbc|mufg"

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(RulesLoadError, match="not found"):
            load_rules(tmp_path / "nonexistent.yaml")

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text(": : : invalid", encoding="utf-8")
        with pytest.raises(RulesLoadError, match="Invalid YAML"):
            load_rules(bad)

    def test_missing_categories_key_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "nocats.yaml"
        p.write_text("rules: []", encoding="utf-8")
        with pytest.raises(RulesLoadError, match="categories"):
            load_rules(p)

    def test_invalid_category_name_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "badcat.yaml"
        p.write_text(
            "categories:\n  - name: nonexistent\n    priority: 1\n    rules: []\n",
            encoding="utf-8",
        )
        with pytest.raises(RulesLoadError, match="Invalid category"):
            load_rules(p)

    def test_invalid_regex_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "badregex.yaml"
        p.write_text(
            "categories:\n"
            "  - name: spam\n"
            "    priority: 1\n"
            "    rules:\n"
            "      - field: subject\n"
            '        pattern: "[invalid"\n',
            encoding="utf-8",
        )
        with pytest.raises(RulesLoadError, match="Invalid regex"):
            load_rules(p)

    def test_rule_missing_field_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "nofield.yaml"
        p.write_text(
            "categories:\n"
            "  - name: spam\n"
            "    priority: 1\n"
            "    rules:\n"
            '      - pattern: "test"\n',
            encoding="utf-8",
        )
        with pytest.raises(RulesLoadError, match="missing"):
            load_rules(p)
