"""Error Log page — surfaces app.log in the UI.

The generator writes to <root>/app.log (see core/logger.py). This page lets a
user who just launched the app see what happened (engine used, Jira/Ollama/
GROQ errors, validation flags) without opening a terminal — the launcher opens
the app, and this page is the first stop when something looks broken.

The log may contain redacted credential values (the logger redacts secrets),
so it is safe to display. No credential values are ever written here.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

# Keep importable whether run via `streamlit run src/app.py` (cwd = project
# root) or directly from within src/.
_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.paths import LOG_PATH  # noqa: E402

_MAX_TAIL_CHARS = 200_000
_MAX_TAIL_LINES = 5_000


def _read_tail() -> str:
    """Return the last portion of app.log (missing file -> friendly note)."""
    if not LOG_PATH.exists():
        return "(app.log does not exist yet — nothing has been logged.)"
    try:
        size = LOG_PATH.stat().st_size
        with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as fh:
            if size <= _MAX_TAIL_CHARS:
                text = fh.read()
            else:
                fh.seek(size - _MAX_TAIL_CHARS)
                # Skip a partial first line so we never show a torn record.
                fh.readline()
                text = fh.read()
    except OSError as exc:
        return f"(could not read app.log: {exc})"

    lines = text.splitlines()
    if len(lines) > _MAX_TAIL_LINES:
        lines = lines[-_MAX_TAIL_LINES:]
    return "\n".join(lines)


def _clear_log() -> None:
    """Truncate app.log. Best-effort; failures are shown, not raised."""
    try:
        LOG_PATH.write_text("", encoding="utf-8")
        st.toast("app.log cleared.")
    except OSError as exc:
        st.error(f"Could not clear app.log: {exc}")


def render() -> None:
    st.title("Error Log")
    st.caption(
        f"Tailing `{LOG_PATH}` — engine activity, Jira/Ollama/GROQ errors, and "
        "output-validation flags land here. Credentials are redacted before "
        "writing, so it is safe to view."
    )

    col_refresh, col_clear = st.columns([1, 1])
    with col_refresh:
        refresh = st.button("Refresh", use_container_width=True)
    with col_clear:
        clear = st.button("Clear log", use_container_width=True)

    # Refresh is the natural Streamlit rerun; the button just makes it explicit.
    if refresh:
        st.rerun()
    if clear:
        _clear_log()

    text = _read_tail()
    st.caption(f"Last updated {datetime.now():%H:%M:%S} · {len(text.splitlines())} lines")

    if text.strip():
        st.code(text, language="text", line_numbers=False)
    else:
        st.info("app.log is empty — no errors or activity recorded yet.")
