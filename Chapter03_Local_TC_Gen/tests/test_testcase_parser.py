"""Tests for the test-case table parser."""

from src.core.testcase_parser import (
    field_order,
    parse_test_cases,
    split_cells,
    split_steps,
)

HEADERS = [
    "Test ID",
    "Description",
    "Pre-conditions",
    "Steps",
    "Expected Result",
    "Priority",
]

TABLE = """| Test ID | Description | Pre-conditions | Steps | Expected Result | Priority |
|---------|-------------|----------------|-------|-----------------|----------|
| TC-001 | Verify login with valid creds | User is on the login page | 1. Enter email. 2. Enter password. 3. Click Login. | User is redirected to the dashboard | High |
| TC-002 | Verify login with invalid password | User is on the login page | 1. Enter email. 2. Enter wrong password. | Error message is shown | Medium |
"""


def test_parses_each_row_into_a_case() -> None:
    table = parse_test_cases(TABLE, HEADERS)
    assert table.ok is True
    assert table.headers == HEADERS
    assert [c.get("Test ID") for c in table.cases] == ["TC-001", "TC-002"]
    assert table.cases[0].get("Priority") == "High"
    assert table.cases[1].get("Expected Result") == "Error message is shown"


def test_get_is_case_insensitive() -> None:
    case = parse_test_cases(TABLE, HEADERS).cases[0]
    assert case.get("test id") == "TC-001"
    assert case.get("PRIORITY") == "High"
    assert case.get("Notes") == ""


def test_strips_code_fence() -> None:
    table = parse_test_cases("```markdown\n" + TABLE + "\n```", HEADERS)
    assert len(table.cases) == 2


def test_headerless_table_labels_rows_from_template() -> None:
    """A model that copies the example data row and drops the header row still
    produces labelled cards."""
    headerless = (
        "| TC-001 | Verify login | User is on the login page | "
        "1. Enter email. 2. Click Login. | Redirected to the dashboard | High |\n"
        "|---|---|---|---|---|---|\n"
        "| TC-002 | Verify logout | User is signed in | 1. Click Logout. | "
        "Signed out | Low |\n"
    )
    table = parse_test_cases(headerless, HEADERS)
    assert table.headers == HEADERS
    assert [c.get("Test ID") for c in table.cases] == ["TC-001", "TC-002"]
    assert table.cases[1].get("Priority") == "Low"


def test_renamed_columns_still_get_template_labels() -> None:
    renamed = (
        "| Test ID | Description | Preconditions | Steps | Expected Result | Priority |\n"
        "|---|---|---|---|---|---|\n"
        "| TC-001 | Verify login | On the login page | 1. Click Login. | Dashboard | High |\n"
    )
    table = parse_test_cases(renamed, HEADERS)
    assert table.headers == HEADERS
    assert table.cases[0].get("Pre-conditions") == "On the login page"


def test_preamble_is_kept_separate() -> None:
    text = "Here are the test cases:\n\n" + TABLE
    table = parse_test_cases(text, HEADERS)
    assert table.preamble == "Here are the test cases:"
    assert len(table.cases) == 2


def test_no_table_returns_not_ok() -> None:
    table = parse_test_cases("No table here, just a sentence.", HEADERS)
    assert table.ok is False
    assert table.cases == []


def test_empty_text_returns_not_ok() -> None:
    assert parse_test_cases("", HEADERS).ok is False


def test_split_cells_keeps_escaped_pipe() -> None:
    cells = split_cells("| TC-001 | Verify A \\| B | High |")
    assert cells == ["TC-001", "Verify A | B", "High"]


def test_field_order_drops_meta_and_puts_steps_last() -> None:
    assert field_order(HEADERS) == ["Pre-conditions", "Expected Result", "Steps"]


def test_split_steps_numbered_inline() -> None:
    assert split_steps("1. Enter email. 2. Enter password. 3. Click Login.") == [
        "Enter email.",
        "Enter password.",
        "Click Login.",
    ]


def test_split_steps_newlines_and_parens() -> None:
    assert split_steps("1) Open the page\n2) Click Save") == ["Open the page", "Click Save"]


def test_split_steps_plain_sentence_is_single_step() -> None:
    assert split_steps("Open the settings page.") == ["Open the settings page."]


def test_split_steps_empty() -> None:
    assert split_steps("") == []
