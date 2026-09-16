"""Tests for the runtime template loader."""

from pathlib import Path

import pytest

from src.core.template_loader import TemplateFile, load_template

SAMPLE_TEMPLATE = """ROLE - You are a Senior QA Engineer.

TASK - Generate exactly 20 test cases.

RULES:
1. Output ONLY the markdown table.
2. Use these exact column headers: | Test ID | Description | Pre-conditions | Steps | Expected Result | Priority |
3. Priority must be one of: High, Medium, Low.
4. Test ID format: TC-001, TC-002, etc.

| Test ID | Description | Pre-conditions | Steps | Expected Result | Priority |
|---------|-------------|----------------|-------|-----------------|----------|
| TC-001 | Verify login | User is on login page | 1. Enter email | User redirected | High |
"""


def test_loads_valid_template(tmp_path: Path) -> None:
    f = tmp_path / "tc.md"
    f.write_text(SAMPLE_TEMPLATE, encoding="utf-8")

    result = load_template(f)

    assert result.ok is True
    assert result.error == ""
    assert "TC-001" in result.raw_text
    assert result.expected_headers == [
        "Test ID",
        "Description",
        "Pre-conditions",
        "Steps",
        "Expected Result",
        "Priority",
    ]


def test_missing_template_fails_gracefully(tmp_path: Path) -> None:
    result = load_template(tmp_path / "does_not_exist.md")

    assert result.ok is False
    assert "not found" in result.error.lower()
    assert result.raw_text == ""


def test_empty_template_fails_gracefully(tmp_path: Path) -> None:
    f = tmp_path / "empty.md"
    f.write_text("   \n\n  ", encoding="utf-8")

    result = load_template(f)

    assert result.ok is False
    assert "empty" in result.error.lower()


def test_unreadable_template(tmp_path: Path) -> None:
    # A directory path makes read_text raise IsADirectoryError/OSError on
    # every platform (chmod 0o000 is not enforced for reads on Windows).
    result = load_template(tmp_path)
    assert result.ok is False
    assert result.error != ""


def test_inline_column_header_rule(tmp_path: Path) -> None:
    # Mirrors the real templates/TC_template.md format: columns are declared
    # in an inline rule, not as an actual markdown table.
    f = tmp_path / "inline.md"
    f.write_text(
        "RULES:\n"
        "2.Use these exact column headers: | Test ID | Description | "
        "Pre-conditions | Steps | Expected Result | Priority |\n"
        "3.Priority must be one of: High, Medium, Low.\n",
        encoding="utf-8",
    )

    result = load_template(f)

    assert result.ok is True
    assert result.expected_headers == [
        "Test ID",
        "Description",
        "Pre-conditions",
        "Steps",
        "Expected Result",
        "Priority",
    ]


def test_template_without_table_parses_to_no_headers(tmp_path: Path) -> None:
    f = tmp_path / "plain.md"
    f.write_text("Just some prose, no markdown table.", encoding="utf-8")

    result = load_template(f)

    assert result.ok is True
    assert result.expected_headers == []


def test_template_object_defaults() -> None:
    t = TemplateFile(path=Path("x.md"), raw_text="hi")
    assert t.ok is True
    assert t.error == ""
    assert t.header_text() == ""


def test_prompt_text_strips_example_scaffolding() -> None:
    """prompt_text() must remove the EXAMPLE ROW and the
    REQUIREMENTS/JIRA ID : [PASTE REQUIREMENTS HERE] placeholder so the model
    cannot echo or copy them, while keeping the real rules + headers intact."""
    raw = (
        "ROLE - You are a Senior QA Engineer.\n"
        "TASK - Generate exactly 20 test cases.\n"
        "RULES:\n"
        "1. Output ONLY the markdown table.\n"
        "2. Use these exact column headers: | Test ID | Description | Priority |\n"
        "EXAMPLE ROW (for format reference only - do NOT copy the content): "
        "| TC-001 | Verify login | High |\n"
        "\n"
        "REQUIREMENTS/JIRA ID : [PASTE REQUIREMENTS HERE]\n"
    )
    t = TemplateFile(path=Path("x.md"), raw_text=raw, ok=True)

    cleaned = t.prompt_text()

    assert "[PASTE REQUIREMENTS HERE]" not in cleaned
    assert "EXAMPLE ROW" not in cleaned
    assert "REQUIREMENTS/JIRA ID" not in cleaned
    # Real content must survive.
    assert "Use these exact column headers:" in cleaned
    assert "ROLE - You are a Senior QA Engineer." in cleaned
    # raw_text is the untouched source of truth.
    assert "PASTE REQUIREMENTS HERE" in t.raw_text


def test_prompt_text_leaves_plain_template_unchanged() -> None:
    raw = "1. Use these exact column headers: | Test ID | Description | Priority |\n"
    t = TemplateFile(path=Path("x.md"), raw_text=raw, ok=True)
    assert t.prompt_text() == raw.strip()
