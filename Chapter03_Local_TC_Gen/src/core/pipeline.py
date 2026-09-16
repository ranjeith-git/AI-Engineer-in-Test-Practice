"""End-to-end generation pipeline.

Framework-agnostic: the Streamlit pages call run_generation() and render the
result. Keeps all business logic testable without Streamlit.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import Settings, load_settings
from .paths import PROMPTS_DIR
from .jira_client import (
    JiraAuthError,
    JiraConnectionError,
    JiraError,
    JiraNotFoundError,
    build_digest,
    fetch_ticket,
    parse_jira_key,
)
from .llm_client import EngineError, GenerationResult, generate
from .logger import get_logger
from .template_loader import load_template

log = get_logger()

_SYSTEM_PROMPT_FILE = PROMPTS_DIR / "system_prompt.md"


class PipelineError(Exception):
    """User-facing pipeline failure with a clean message."""


@dataclass
class PipelineResult:
    jira_key: str
    digest: str
    generation: GenerationResult
    template_path: Path


def _load_system_prompt() -> str:
    try:
        return _SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
    except OSError as exc:
        raise PipelineError(
            f"System prompt file is missing or unreadable: {_SYSTEM_PROMPT_FILE} ({exc})"
        ) from exc


def _build_user_message(template_raw: str, digest: str) -> str:
    return (
        "=== TEMPLATE (single source of truth) ===\n"
        f"{template_raw}\n\n"
        "=== JIRA TICKET ===\n"
        f"{digest}\n\n"
        "Generate the test cases for the Jira ticket above, following the "
        "template exactly."
    )


def _parse_or_raise(message: str) -> str:
    key = parse_jira_key(message)
    if not key:
        raise PipelineError(
            "No Jira issue key found in your message. Include one, e.g. "
            "'create test cases for JIRA-123'."
        )
    return key


def _load_template_or_raise(settings: Settings):
    template = load_template(settings.template_path)
    if not template.ok:
        raise PipelineError(template.error)
    if not template.expected_headers:
        log.warning("template has no markdown-table header row: %s",
                    settings.template_path)
    return template


def run_generation(user_message: str, settings: Settings | None = None) -> PipelineResult:
    """Run the full pipeline and return the result."""
    settings = settings or load_settings()

    if not settings.is_jira_configured():
        raise PipelineError(
            "Jira is not configured. Open the Settings page and save your Jira "
            "URL, email, and API token first."
        )

    jira_key = _parse_or_raise(user_message)
    template = _load_template_or_raise(settings)

    try:
        issue = fetch_ticket(
            settings.jira_url,
            settings.jira_email,
            settings.jira_api_token,
            jira_key,
        )
    except (JiraAuthError, JiraNotFoundError, JiraConnectionError) as exc:
        log.info("jira fetch failed for %s: %s", jira_key, type(exc).__name__)
        raise PipelineError(str(exc)) from exc

    digest = build_digest(issue)
    system_prompt = _load_system_prompt()
    user_prompt = _build_user_message(template.prompt_text(), digest)

    try:
        generation = generate(settings, system_prompt, user_prompt, template)
    except EngineError as exc:
        raise PipelineError(str(exc)) from exc

    return PipelineResult(
        jira_key=jira_key,
        digest=digest,
        generation=generation,
        template_path=settings.template_path,
    )
