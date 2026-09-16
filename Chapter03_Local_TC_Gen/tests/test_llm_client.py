"""Tests for the LLM router's fallback logic (Ollama primary -> GROQ).

The network calls are monkeypatched out; these tests exercise the routing
decisions only. `validate` is left real, so a small TemplateFile fixture is
enough to drive valid/invalid outcomes.
"""

from pathlib import Path

import pytest

from src.core.llm_client import EngineError, GenerationResult, generate
from src.core.template_loader import TemplateFile

VALID_TEXT = """| Test ID | Description | Priority |
|---|---|---|
| TC-001 | Verify login | High |
"""

INVALID_TEXT = "I cannot do that."

TEMPLATE = TemplateFile(
    path=Path("t.md"),
    raw_text=(
        "Use these exact column headers: | Test ID | Description | Priority |\n"
        "Priority must be one of: High, Medium, Low.\n"
        "Test ID format: TC-001.\n"
    ),
    ok=True,
    expected_headers=["Test ID", "Description", "Priority"],
)

SYSTEM = "system"
USER = "user"


class _FakeSettings:
    """Minimal stand-in for Settings with the fields generate() touches."""

    def __init__(self, *, groq_key: str = "gsk_test", force_groq: bool = False):
        self.groq_api_key = groq_key
        self.groq_model = "openai/gpt-oss-20b"
        self.ollama_model = "gemma3:1b"
        self.force_groq = force_groq

    def is_groq_configured(self) -> bool:
        return bool(self.groq_api_key)


def test_ollama_valid_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.core.llm_client.ollama_generate",
        lambda s, sys, u: VALID_TEXT,
    )

    result = generate(_FakeSettings(), SYSTEM, USER, TEMPLATE)

    assert isinstance(result, GenerationResult)
    assert result.engine == "ollama"
    assert result.validation.valid is True


def test_ollama_unreachable_falls_back_to_groq(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(s, sys, u):
        raise EngineError("Ollama down")

    monkeypatch.setattr("src.core.llm_client.ollama_generate", boom)
    monkeypatch.setattr(
        "src.core.llm_client.groq_generate",
        lambda s, sys, u: VALID_TEXT,
    )

    result = generate(_FakeSettings(), SYSTEM, USER, TEMPLATE)

    assert result.engine == "groq"
    assert result.validation.valid is True


def test_ollama_invalid_structure_falls_back_to_groq(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.core.llm_client.ollama_generate",
        lambda s, sys, u: INVALID_TEXT,
    )
    monkeypatch.setattr(
        "src.core.llm_client.groq_generate",
        lambda s, sys, u: VALID_TEXT,
    )

    result = generate(_FakeSettings(), SYSTEM, USER, TEMPLATE)

    assert result.engine == "groq"
    assert result.validation.valid is True


def test_no_groq_key_returns_flagged_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.core.llm_client.ollama_generate",
        lambda s, sys, u: INVALID_TEXT,
    )

    result = generate(_FakeSettings(groq_key=""), SYSTEM, USER, TEMPLATE)

    assert result.engine == "ollama"
    assert result.validation.valid is False


def test_both_engines_fail_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def ollama_boom(s, sys, u):
        raise EngineError("Ollama down")

    def groq_boom(s, sys, u):
        raise EngineError("GROQ down")

    monkeypatch.setattr("src.core.llm_client.ollama_generate", ollama_boom)
    monkeypatch.setattr("src.core.llm_client.groq_generate", groq_boom)

    with pytest.raises(EngineError, match="Both LLM engines failed"):
        generate(_FakeSettings(), SYSTEM, USER, TEMPLATE)
