"""Tests for config load/save and defaults.

These avoid touching the real src/.env by monkeypatching ENV_PATH to a
tmp_path file, so they are safe to run on a machine with real credentials.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

import src.core.config as config
from src.core.paths import DEFAULT_TEMPLATE_FILE

_ENV_KEYS = (
    config.KEY_JIRA_URL,
    config.KEY_JIRA_EMAIL,
    config.KEY_JIRA_API_TOKEN,
    config.KEY_GROQ_API_KEY,
    config.KEY_OLLAMA_BASE_URL,
    config.KEY_OLLAMA_MODEL,
    config.KEY_GROQ_MODEL,
    config.KEY_TEMPLATE_FILE,
)


@pytest.fixture
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Point config at a throwaway .env so tests never read/write the real one.

    load_settings() calls load_dotenv(..., override=False), which writes into
    os.environ, and it merges os.environ OVER the file. Any value left behind
    would therefore outrank the real src/.env in a later test. monkeypatch
    cannot undo those writes — delenv records nothing when a key is already
    absent — so snapshot the keys and restore them here.
    """
    env_file = tmp_path / ".env"
    monkeypatch.setattr(config, "ENV_PATH", env_file)
    saved = {key: os.environ.pop(key, None) for key in _ENV_KEYS}
    yield env_file
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _load_via_env(isolated_env: Path, content: str):
    isolated_env.write_text(content, encoding="utf-8")
    return config.load_settings()


def test_default_groq_model_is_20b() -> None:
    """The dataclass default must match the canonical -20b value used by
    load_settings, save_settings, and .env.example."""
    assert config.Settings().groq_model == "openai/gpt-oss-20b"


def test_default_template_path_is_spec_file() -> None:
    assert DEFAULT_TEMPLATE_FILE.name == "test cases creator.md"
    assert DEFAULT_TEMPLATE_FILE.exists()


def test_load_settings_applies_defaults(isolated_env: Path) -> None:
    isolated_env.write_text("", encoding="utf-8")
    settings = config.load_settings()
    assert settings.ollama_model == "gemma3:1b"
    assert settings.groq_model == "openai/gpt-oss-20b"
    assert settings.ollama_base_url == "http://localhost:11434"


def test_save_settings_round_trip(isolated_env: Path) -> None:
    config.save_settings(
        jira_url="https://x.atlassian.net",
        jira_email="a@b.com",
        jira_api_token="tok123",
        groq_api_key="gsk_abc",
    )
    settings = config.load_settings()
    assert settings.jira_url == "https://x.atlassian.net"
    assert settings.jira_email == "a@b.com"
    assert settings.jira_api_token == "tok123"
    assert settings.groq_api_key == "gsk_abc"


def test_save_settings_never_blanks_secrets(isolated_env: Path) -> None:
    config.save_settings(
        jira_url="https://x.atlassian.net",
        jira_email="a@b.com",
        jira_api_token="tok123",
        groq_api_key="gsk_abc",
    )
    # A later save with blank secret fields must NOT wipe the stored secrets.
    config.save_settings(
        jira_url="https://y.atlassian.net",
        jira_email="",
        jira_api_token="",
        groq_api_key="",
    )
    settings = config.load_settings()
    assert settings.jira_api_token == "tok123"
    assert settings.groq_api_key == "gsk_abc"
    assert settings.jira_url == "https://y.atlassian.net"


def test_save_settings_preserves_custom_template_file(isolated_env: Path) -> None:
    """save_settings must write the passed template_file through, not clobber it
    with the default (the Settings-page bug this guards against)."""
    config.save_settings(
        jira_url="https://x.atlassian.net",
        jira_email="a@b.com",
        jira_api_token="tok123",
        groq_api_key="gsk_abc",
        template_file=str(DEFAULT_TEMPLATE_FILE),
    )
    raw = isolated_env.read_text(encoding="utf-8")
    assert "test cases creator.md" in raw
