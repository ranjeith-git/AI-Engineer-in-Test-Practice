"""Settings page — persist Jira + GROQ credentials to src/.env."""

from __future__ import annotations

import streamlit as st

from core.config import KEY_JIRA_URL, load_settings, save_settings
from core.paths import ENV_PATH

_OLLAMA_HEALTH_URL = "/api/tags"


def _ollama_status(base_url: str) -> tuple[bool, str]:
    """Return (reachable, message) for the local Ollama server."""
    try:
        import requests

        resp = requests.get(base_url.rstrip("/") + _OLLAMA_HEALTH_URL, timeout=3)
        if resp.ok:
            return True, f"Reachable at {base_url} (HTTP {resp.status_code})."
        return False, f"Responded with HTTP {resp.status_code} at {base_url}."
    except Exception:
        return False, (
            f"Not reachable at {base_url}. Start it with 'ollama serve' or check "
            "the URL."
        )


def render() -> None:
    st.title("Settings")

    settings = load_settings()

    with st.expander("Why a .env file?", expanded=False):
        st.markdown(
            f"Credentials are stored locally in `{ENV_PATH}` (gitignored — never "
            "committed). They are loaded at generation time and are never printed "
            "in the UI, logs, or chat history."
        )

    st.subheader("Jira")
    jira_url = st.text_input(
        "Jira URL",
        value=settings.jira_url,
        placeholder="https://your-domain.atlassian.net",
        key="jira_url",
    )
    jira_email = st.text_input(
        "Jira email",
        value=settings.jira_email,
        placeholder="you@example.com",
        key="jira_email",
    )
    jira_token = st.text_input(
        "Jira API token",
        type="password",
        value=settings.jira_api_token,
        placeholder="Paste your Jira API token",
        key="jira_api_token",
    )

    st.subheader("LLM engines")
    ollama_base_url = st.text_input(
        "Ollama base URL (local)",
        value=settings.ollama_base_url,
        key="ollama_base_url",
    )
    ollama_model = st.text_input(
        "Ollama model",
        value=settings.ollama_model,
        key="ollama_model",
    )
    groq_api_key = st.text_input(
        "GROQ API key (fallback)",
        type="password",
        value=settings.groq_api_key,
        placeholder="gsk_...",
        key="groq_api_key",
    )
    groq_model = st.text_input(
        "GROQ model (fallback)",
        value=settings.groq_model,
        key="groq_model",
    )

    col_save, col_test = st.columns([1, 1])
    with col_save:
        saved = st.button("Save settings", type="primary")
    with col_test:
        test_ollama = st.button("Test Ollama connection")

    if test_ollama:
        with st.spinner("Checking Ollama..."):
            reachable, message = _ollama_status(ollama_base_url.strip() or ollama_base_url)
        if reachable:
            st.success(message)
        else:
            st.warning(message)

    if saved:
        save_settings(
            jira_url=jira_url,
            jira_email=jira_email,
            jira_api_token=jira_token,
            groq_api_key=groq_api_key,
            ollama_base_url=ollama_base_url,
            ollama_model=ollama_model,
            groq_model=groq_model,
            # Pass the current value through so saving does not silently reset a
            # custom TEMPLATE_FILE back to the default.
            template_file=str(settings.template_path),
        )
        st.success(f"Settings saved to {ENV_PATH}. New values apply to the next generation.")
