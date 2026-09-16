"""Tests for the Jira client: key parsing and digest building."""

from src.core.jira_client import (
    _description_to_text,
    build_digest,
    parse_jira_key,
)


def test_parse_key_from_plain_message() -> None:
    assert parse_jira_key("create test cases for JIRA-123") == "JIRA-123"


def test_parse_key_lowercase_normalized() -> None:
    assert parse_jira_key("please handle proj-42 please") == "PROJ-42"


def test_parse_key_with_url() -> None:
    assert (
        parse_jira_key("https://x.atlassian.net/browse/TICKET-999 details")
        == "TICKET-999"
    )


def test_parse_key_without_key_returns_none() -> None:
    assert parse_jira_key("create test cases for the login page") is None


def test_parse_key_ignores_plain_numbers() -> None:
    assert parse_jira_key("the issue is 12345") is None


def test_build_digest_with_adf_description() -> None:
    issue = {
        "key": "JIRA-1",
        "fields": {
            "summary": "Login page fails",
            "issuetype": {"name": "Bug"},
            "status": {"name": "Open"},
            "priority": {"name": "High"},
            "labels": ["ui", "p1"],
            "components": [{"name": "Frontend"}],
            "creator": {"displayName": "Alice"},
            "assignee": {"displayName": "Bob"},
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {"type": "paragraph", "content": [
                        {"type": "text", "text": "Login button unresponsive. "},
                    ]},
                    {"type": "heading", "attrs": {"level": 2}, "content": [
                        {"type": "text", "text": "Acceptance Criteria"},
                    ]},
                    {"type": "paragraph", "content": [
                        {"type": "text", "text": "User can log in with valid creds."},
                    ]},
                ],
            },
            "comment": {"comments": [
                {"author": {"displayName": "Carol"},
                 "body": {"type": "doc", "version": 1, "content": [
                     {"type": "paragraph", "content": [
                         {"type": "text", "text": "Reproduced on Chrome."},
                     ]},
                 ]}},
            ]},
        },
    }
    digest = build_digest(issue)
    assert "JIRA-1" in digest
    assert "Login page fails" in digest
    assert "Bug" in digest
    assert "Open" in digest
    assert "High" in digest
    assert "ui, p1" in digest
    assert "Frontend" in digest
    assert "Alice" in digest
    assert "Bob" in digest
    assert "Login button unresponsive" in digest
    assert "## Acceptance Criteria" in digest
    assert "User can log in with valid creds." in digest
    assert "Reproduced on Chrome." in digest


def test_build_digest_without_description() -> None:
    issue = {
        "key": "JIRA-2",
        "fields": {
            "summary": "No desc ticket",
            "issuetype": {"name": "Task"},
            "status": {"name": "In Progress"},
            "priority": {"name": "Medium"},
            "labels": [],
            "components": [],
            "creator": {"displayName": "A"},
            "assignee": None,
            "description": None,
            "comment": {"comments": []},
        },
    }
    digest = build_digest(issue)
    assert "No description provided." in digest
    assert "Unassigned" in digest


def test_legacy_wiki_description() -> None:
    assert _description_to_text("h2. Heading\nplain text") == "h2. Heading\nplain text"
