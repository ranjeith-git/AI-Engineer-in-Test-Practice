"""Deep UI rerun-cycle regression test.

Proves the generated test-case cards SURVIVE the st.rerun that Streamlit
performs after chat input — the original bug where the page went idle and the
output vanished. The cards are drawn with st.html, so they surface as "html"
elements rather than markdown. Runs the REAL pipeline (Jira fetch + Ollama), so
it needs Ollama running and takes ~35-40s.
"""
import os

from streamlit.testing.v1 import AppTest

APP = os.path.abspath("src/app.py")


def test_generated_table_survives_rerun() -> None:
    # Run 1: initial load.
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    assert not at.exception, f"initial load failed: {list(at.exception)}"

    # Run 2: type the prompt (triggers _process -> real generation).
    at.chat_input[0].set_value("create test cases for SCRUM-5")
    at.run()
    assert not at.exception, f"generation failed: {list(at.exception)}"

    def cards():
        return [e.value for e in at.get("html") if e.value and "TC-001" in e.value]

    assert cards(), "generated cards must render after generation"

    # Run 3: simulate the app's st.rerun() (empty chat_input) — the bug case.
    at.chat_input[0].set_value("")
    at.run()
    assert not at.exception, f"rerun failed: {list(at.exception)}"

    visible = cards()
    assert visible, "cards must STILL be visible after rerun (original bug)"
    assert "TC-001" in visible[0]
