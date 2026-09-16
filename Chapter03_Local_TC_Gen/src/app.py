"""Streamlit entry point — three-page app: Chat/Generate, Settings, Error Log.

Run from Chapter03_Local_TC_Gen/:
    streamlit run src/app.py
Or double-click the launcher: start_app.bat (Windows) / start_app.sh (macOS/Linux).
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Make `src` importable regardless of the working directory Streamlit uses.
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pages import chat_generate, error_log, settings  # noqa: E402

st.set_page_config(
    page_title="Jira Test Case Generator",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _make_nav() -> None:
    pages = {
        "Chat / Generate": [
            st.Page(chat_generate.render, title="Chat / Generate", url_path="chat"),
        ],
        "Configuration": [
            st.Page(settings.render, title="Settings", url_path="settings"),
        ],
        "Support": [
            st.Page(error_log.render, title="Error Log", url_path="error-log"),
        ],
    }
    nav = st.navigation(pages, position="sidebar")
    nav.run()


if __name__ == "__main__":
    _make_nav()
