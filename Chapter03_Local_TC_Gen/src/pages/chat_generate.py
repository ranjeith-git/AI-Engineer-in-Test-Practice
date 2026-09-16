"""Chat/Generate page — ChatGPT-style single column.

User types e.g. "create test cases for JIRA-123", hits Send, and the generated
test-case table renders inline with an engine badge below it.

History is stored in st.session_state["messages"] and re-rendered on every
rerun so the conversation (including the latest result) stays visible.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

# Allow `from core...` imports whether run via `streamlit run src/app.py`
# (cwd = Chapter03_Local_TC_Gen) or from within src/.
_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
_ROOT = _SRC.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.config import load_settings  # noqa: E402
from core.pipeline import PipelineError, run_generation  # noqa: E402


def _engine_badge(engine: str, model: str, latency_s: float) -> str:
    icon = "🟢" if engine == "ollama" else "🟣"
    return f"{icon} **Served by:** {engine} · `{model}` · {latency_s:.1f}s"


def _render_message(msg: dict) -> None:
    """Draw one stored chat message."""
    role = msg.get("role", "assistant")
    with st.chat_message(role):
        kind = msg.get("kind")
        content = msg.get("content", "")

        if kind == "error":
            st.error(content)
        elif kind == "warning":
            st.warning(content)
        elif kind == "text":
            st.markdown(content)
        elif kind == "success":
            st.markdown(content)
            if msg.get("engine"):
                st.caption(_engine_badge(msg["engine"], msg.get("model", ""),
                                         msg.get("latency_s", 0.0)))
            if msg.get("download"):
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    "⬇️ Download .md",
                    data=msg["content"].encode("utf-8"),
                    file_name=f"test_cases_{msg.get('jira_key', 'ticket')}_{stamp}.md",
                    mime="text/markdown",
                    key=f"dl_{id(msg)}",
                )
        else:
            # plain user/assistant text
            st.markdown(content)


def _process(prompt: str) -> None:
    # Record the user message and redraw it.
    st.session_state.setdefault("messages", []).append(
        {"role": "user", "content": prompt, "kind": "text"}
    )
    with st.chat_message("user"):
        st.markdown(prompt)

    # A placeholder assistant bubble that we update after generation finishes.
    with st.chat_message("assistant"):
        with st.spinner("Fetching Jira ticket and generating test cases..."):
            try:
                result = run_generation(prompt)
            except PipelineError as exc:
                st.error(str(exc))
                st.session_state.setdefault("messages", []).append(
                    {"role": "assistant", "content": str(exc), "kind": "error"}
                )
                return

        gen = result.generation
        st.markdown(gen.text)

        # Validation flag: never silently show malformed output.
        if not gen.validation.valid:
            st.warning(
                "⚠️ Output did not fully match the template. Reasons:\n\n"
                + "\n".join(f"- {r}" for r in gen.validation.reasons)
            )

        st.caption(_engine_badge(gen.engine, gen.model, gen.latency_s))

        # Persist the full assistant response (table + engine + download flag).
        entry: dict = {
            "role": "assistant",
            "content": gen.text,
            "kind": "success",
            "engine": gen.engine,
            "model": gen.model,
            "latency_s": gen.latency_s,
            "jira_key": result.jira_key,
        }
        if gen.validation.valid:
            entry["download"] = True
        st.session_state.setdefault("messages", []).append(entry)


def render() -> None:
    st.title("Jira → Test Case Generator")

    settings = load_settings()
    if not settings.is_jira_configured():
        st.info(
            "Jira is not configured yet. Open **Settings** (sidebar) and save your "
            "Jira URL, email, and API token before generating."
        )
    elif settings.has_credentials_placeholder():
        st.info(
            "Your .env still contains example placeholder values. Replace them in "
            "**Settings**."
        )

    # Fresh chat history only when not already in session state.
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if st.session_state.messages and st.sidebar.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()

    # Draw the full conversation history on every run.
    for msg in st.session_state.messages:
        _render_message(msg)

    # Handle new input.
    if prompt := st.chat_input(
        'Ask for test cases — e.g. "create test cases for JIRA-123"'
    ):
        _process(prompt)
        st.rerun()
