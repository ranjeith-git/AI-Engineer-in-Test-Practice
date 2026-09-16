"""Application settings loaded from src/.env.

Credentials are read here and handed to callers at call time; they are never
printed, logged, or echoed. `save_settings` writes back to the same .env file
using python-dotenv's set_key so the Settings page can persist edits.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values, load_dotenv, set_key

from .logger import remember_secret
from .paths import DEFAULT_TEMPLATE_FILE, ENV_PATH

# Canonical env var names — used both when reading and when writing .env.
KEY_JIRA_URL = "JIRA_URL"
KEY_JIRA_EMAIL = "JIRA_EMAIL"
KEY_JIRA_API_TOKEN = "JIRA_API_TOKEN"
KEY_GROQ_API_KEY = "GROQ_API_KEY"
KEY_OLLAMA_BASE_URL = "OLLAMA_BASE_URL"
KEY_OLLAMA_MODEL = "OLLAMA_MODEL"
KEY_GROQ_MODEL = "GROQ_MODEL"
KEY_TEMPLATE_FILE = "TEMPLATE_FILE"

_SECRET_KEYS = {KEY_JIRA_API_TOKEN, KEY_GROQ_API_KEY, KEY_JIRA_EMAIL}


@dataclass(frozen=True)
class Settings:
    jira_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""
    groq_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:1b"
    groq_model: str = "openai/gpt-oss-20b"
    template_path: Path = DEFAULT_TEMPLATE_FILE

    # Runtime knob: disable Ollama to force the GROQ fallback (used for
    # testing the fallback path without stopping the local server).
    force_groq: bool = False

    _secrets_registered: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "template_path", Path(self.template_path))

    def register_secrets(self) -> None:
        """Tell the logger which live values to redact."""
        for value in (
            self.jira_api_token,
            self.groq_api_key,
            self.jira_email,
        ):
            remember_secret(value)
        object.__setattr__(self, "_secrets_registered", True)

    def is_jira_configured(self) -> bool:
        return bool(self.jira_url and self.jira_email and self.jira_api_token)

    def is_groq_configured(self) -> bool:
        return bool(self.groq_api_key)

    def has_credentials_placeholder(self) -> bool:
        """True if any credential looks like an unfilled .env.example value."""
        placeholders = {
            "your_jira_api_token",
            "you@example.com",
            "gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "your-domain.atlassian.net",
        }
        return any(v in placeholders for v in (
            self.jira_url,
            self.jira_email,
            self.jira_api_token,
            self.groq_api_key,
        ))


def _resolve_template_path(raw: str | None) -> Path:
    if not raw:
        return DEFAULT_TEMPLATE_FILE
    p = Path(raw)
    if p.is_absolute():
        return p
    # Anchor any template-folder relative value to the project root's
    # templates/ dir, regardless of the filename spelling used in .env.
    first = (p.parts[0] if p.parts else "").lower().rstrip("/\\")
    if first == "templates" or (first == "template" and len(p.parts) == 2 and p.parts[1].lower().endswith(".md")):
        return (DEFAULT_TEMPLATE_FILE.parent / p.name).resolve()
    return Path(raw).resolve()


def load_settings() -> Settings:
    """Load src/.env into a Settings object (env vars override file values)."""
    load_dotenv(dotenv_path=ENV_PATH, override=False)
    values = {**dotenv_values(ENV_PATH), **{k: os.getenv(k) for k in (
        KEY_JIRA_URL,
        KEY_JIRA_EMAIL,
        KEY_JIRA_API_TOKEN,
        KEY_GROQ_API_KEY,
        KEY_OLLAMA_BASE_URL,
        KEY_OLLAMA_MODEL,
        KEY_GROQ_MODEL,
        KEY_TEMPLATE_FILE,
    ) if os.getenv(k)}}

    def get(key: str, default: str = "") -> str:
        return (values.get(key) or default).strip()

    settings = Settings(
        jira_url=get(KEY_JIRA_URL),
        jira_email=get(KEY_JIRA_EMAIL),
        jira_api_token=get(KEY_JIRA_API_TOKEN),
        groq_api_key=get(KEY_GROQ_API_KEY),
        ollama_base_url=get(KEY_OLLAMA_BASE_URL, "http://localhost:11434"),
        ollama_model=get(KEY_OLLAMA_MODEL, "gemma3:1b"),
        groq_model=get(KEY_GROQ_MODEL, "openai/gpt-oss-20b"),
        template_path=_resolve_template_path(values.get(KEY_TEMPLATE_FILE)),
    )
    settings.register_secrets()
    return settings


def save_settings(
    *,
    jira_url: str,
    jira_email: str,
    jira_api_token: str,
    groq_api_key: str,
    ollama_base_url: str | None = None,
    ollama_model: str | None = None,
    groq_model: str | None = None,
    template_file: str | None = None,
) -> None:
    """Persist settings to src/.env (creates it if missing). Blank credential
    values are skipped so the Settings page never wipes an existing secret with
    an empty field."""
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)

    updates = {
        KEY_JIRA_URL: jira_url.strip(),
        KEY_JIRA_EMAIL: jira_email.strip(),
        KEY_JIRA_API_TOKEN: jira_api_token.strip(),
        KEY_GROQ_API_KEY: groq_api_key.strip(),
        KEY_OLLAMA_BASE_URL: (ollama_base_url or "http://localhost:11434").strip(),
        KEY_OLLAMA_MODEL: (ollama_model or "gemma3:1b").strip(),
        KEY_GROQ_MODEL: (groq_model or "openai/gpt-oss-20b").strip(),
        KEY_TEMPLATE_FILE: (template_file or str(DEFAULT_TEMPLATE_FILE)).strip(),
    }

    for key, value in updates.items():
        if key in _SECRET_KEYS and not value:
            # Never blank out a stored secret with an empty form field.
            continue
        set_key(str(ENV_PATH), key, value, quote_mode="never")
