"""Tests for the pipeline: prompt assembly and fail-fast error paths.

Network and LLM calls are avoided: we test _build_user_message stripping and
the error paths that trigger before any engine call.
"""

from pathlib import Path

import pytest

from src.core.pipeline import (
    PipelineError,
    _build_user_message,
    _parse_or_raise,
    run_generation,
)


def test_build_user_message_includes_template_and_digest() -> None:
    msg = _build_user_message("Rule line", "JIRA-1: login bug")
    assert "=== TEMPLATE (single source of truth) ===" in msg
    assert "Rule line" in msg
    assert "=== JIRA TICKET ===" in msg
    assert "JIRA-1: login bug" in msg


def test_build_user_message_receives_cleaned_template() -> None:
    """The template fed into the prompt should already be stripped of the
    human-facing example scaffolding by the caller (template.prompt_text)."""
    from src.core.template_loader import TemplateFile

    t = TemplateFile(
        path=Path("t.md"),
        raw_text=(
            "RULES:\n"
            "1. Use these exact column headers: | Test ID | Description | Priority |\n"
            "EXAMPLE ROW (for format reference only - do NOT copy the content): "
            "| TC-001 | Verify login | High |\n"
            "REQUIREMENTS/JIRA ID : [PASTE REQUIREMENTS HERE]\n"
        ),
        ok=True,
    )
    msg = _build_user_message(t.prompt_text(), "digest")
    assert "[PASTE REQUIREMENTS HERE]" not in msg
    assert "EXAMPLE ROW" not in msg
    assert "| Test ID | Description | Priority |" in msg


def test_parse_or_raise_requires_key() -> None:
    assert _parse_or_raise("create test cases for JIRA-42") == "JIRA-42"
    with pytest.raises(PipelineError, match="No Jira issue key"):
        _parse_or_raise("hello there")


def test_run_generation_fails_when_jira_unconfigured(monkeypatch) -> None:
    class Unconfigured:
        def is_jira_configured(self) -> bool:
            return False

    with pytest.raises(PipelineError, match="Jira is not configured"):
        run_generation("create test cases for JIRA-1", settings=Unconfigured())
