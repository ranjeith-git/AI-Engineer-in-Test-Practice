"""Tests for the output validator."""

from pathlib import Path

from src.core.output_validator import validate
from src.core.template_loader import TemplateFile

TEMPLATE_WITH_TABLE = TemplateFile(
    path=Path("templates/test cases creator.md"),
    raw_text="""RULES:
1. Use these exact column headers: | Test ID | Description | Pre-conditions | Steps | Expected Result | Priority |
2. Priority must be one of: High, Medium, Low.
3. Test ID format: TC-001, TC-002, etc.

| Test ID | Description | Pre-conditions | Steps | Expected Result | Priority |
|---------|-------------|----------------|-------|-----------------|----------|
| TC-001 | Verify login | User is on the login page | 1. Enter valid email. 2. Enter password. 3. Click Login. | User is redirected to the dashboard | High |
""",
    ok=True,
    expected_headers=[
        "Test ID",
        "Description",
        "Pre-conditions",
        "Steps",
        "Expected Result",
        "Priority",
    ],
)

GOOD_OUTPUT = """| Test ID | Description | Pre-conditions | Steps | Expected Result | Priority |
|---------|-------------|----------------|-------|-----------------|----------|
| TC-001 | Verify login with valid creds | User is on the login page | 1. Enter email. 2. Enter password. 3. Click Login. | User is redirected to the dashboard | High |
| TC-002 | Verify login with invalid password | User is on the login page | 1. Enter email. 2. Enter wrong password. 3. Click Login. | Error message is shown | Medium |
"""


def test_valid_output_passes() -> None:
    result = validate(GOOD_OUTPUT, TEMPLATE_WITH_TABLE)
    assert result.valid is True
    assert result.reasons == []


def test_missing_column_fails() -> None:
    bad = GOOD_OUTPUT.replace("| Expected Result | Priority |", "| Expected Result |")
    result = validate(bad, TEMPLATE_WITH_TABLE)
    assert result.valid is False
    assert any("missing required column" in r for r in result.reasons)


def test_no_table_fails() -> None:
    result = validate("Here is a paragraph without a markdown table.", TEMPLATE_WITH_TABLE)
    assert result.valid is False
    assert any("no markdown table" in r for r in result.reasons)


def test_bad_test_id_fails() -> None:
    bad = GOOD_OUTPUT.replace("TC-001", "XX-001")
    result = validate(bad, TEMPLATE_WITH_TABLE)
    assert result.valid is False
    assert any("Test ID" in r for r in result.reasons)


def test_bad_priority_fails() -> None:
    bad = GOOD_OUTPUT.replace("| High |", "| Critical |")
    result = validate(bad, TEMPLATE_WITH_TABLE)
    assert result.valid is False
    assert any("Priority" in r for r in result.reasons)


def test_empty_output_fails() -> None:
    result = validate("   ", TEMPLATE_WITH_TABLE)
    assert result.valid is False
    assert any("empty" in r for r in result.reasons)


def test_fenced_table_passes() -> None:
    fenced = "```markdown\n" + GOOD_OUTPUT + "\n```"
    result = validate(fenced, TEMPLATE_WITH_TABLE)
    assert result.valid is True


def test_headerless_table_passes() -> None:
    """Ollama often emits data rows first (copies the template's EXAMPLE ROW)
    with no header row. The validator should substitute the template headers."""
    headerless_with_sep = (
        "| TC-001 | Verify login with valid creds | User is on the login page | "
        "1. Enter email. 2. Enter password. 3. Click Login. | User is redirected "
        "to the dashboard | High |\n"
        "|---|---|---|---|---|---|\n"
        "| TC-002 | Verify login with invalid password | User is on the login "
        "page | 1. Enter email. 2. Enter wrong password. 3. Click Login. | Error "
        "message is shown | Medium |\n"
    )
    result = validate(headerless_with_sep, TEMPLATE_WITH_TABLE)
    assert result.valid is True, result.reasons


def test_template_without_headers_is_pass_through() -> None:
    plain = TemplateFile(path=Path("x.md"), raw_text="no table here", ok=True)
    result = validate("anything at all", plain)
    assert result.valid is True


def test_reordered_columns_fail() -> None:
    """Column ORDER is part of the template contract: a reordered table must be
    flagged even when every expected column is present."""
    reordered = (
        "| Test ID | Description | Steps | Pre-conditions | Expected Result | Priority |\n"
        "|---------|-------------|-------|----------------|-----------------|----------|\n"
        "| TC-001 | Verify login | 1. Enter email. 2. Enter password. | User is on the "
        "login page | User is redirected to the dashboard | High |\n"
    )
    result = validate(reordered, TEMPLATE_WITH_TABLE)
    assert result.valid is False
    assert any("column order does not match" in r for r in result.reasons)


def test_extra_unknown_column_fails() -> None:
    """A column outside the template's set must be flagged, not silently shown."""
    extra = (
        "| Test ID | Description | Pre-conditions | Steps | Expected Result | Priority | Notes |\n"
        "|---------|-------------|----------------|-------|-----------------|----------|-------|\n"
        "| TC-001 | Verify login | User is on the login page | 1. Enter email. | User is "
        "redirected to the dashboard | High | whatever |\n"
    )
    result = validate(extra, TEMPLATE_WITH_TABLE)
    assert result.valid is False
    assert any("column(s) not in the template" in r for r in result.reasons)
