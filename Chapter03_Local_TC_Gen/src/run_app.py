"""Launcher entry point.

Used by start_app.bat / start_app.sh so the run command lives in ONE place
instead of being duplicated across launchers. It:

1. Imports the real app (import-time failures — missing dependency, broken
   syntax — print to stdout/stderr, which the launcher shows).
2. Delegates to Streamlit's own runner, which starts the server and opens the
   browser (--server.headless=false by default).

Run directly (project root):
    .venv\\Scripts\\python src\\run_app.py          # Windows
    .venv/bin/python src/run_app.py                 # macOS / Linux
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Project root = Chapter03_Local_TC_Gen/ (parent of src/).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_PATH = Path(__file__).resolve().parent / "app.py"


def main() -> int:
    os.chdir(PROJECT_ROOT)  # streamlit resolves paths relative to cwd.

    # Fail loudly (before Streamlit hides the traceback) if deps are missing.
    try:
        import streamlit  # noqa: F401
    except ImportError as exc:
        print(f"[start] streamlit is not installed in this Python: {exc}", file=sys.stderr)
        print(
            "[start] Run:  python -m pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 1

    # `streamlit run` is a console script; calling it via python -m keeps the
    # same interpreter that just validated the import above.
    from streamlit.web import cli as stcli

    sys.argv = [
        "streamlit",
        "run",
        str(APP_PATH),
        # Keep the terminal attached so Ctrl+C stops the server cleanly.
        "--server.headless=false",
    ]
    # streamlit.run() does not return until the server stops.
    stcli.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
