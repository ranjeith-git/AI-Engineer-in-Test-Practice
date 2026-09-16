#!/usr/bin/env bash
# One-click launcher for the Jira -> Test Case Generator.
# Usage:  ./start_app.sh    (or double-click in a file manager)
set -u
cd "$(dirname "$0")" || exit 1

echo "============================================================"
echo " Jira -> Test Case Generator"
echo " Starting Streamlit and opening your browser..."
echo "============================================================"

# --- Pick the Python interpreter (venv first, then system python3) ---
PY="python3"
if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"; fi
if [ -x "venv/bin/python" ]; then PY="venv/bin/python"; fi

echo "Using: $PY"
echo

# --- Quick dependency check so a broken launch is not a mystery ---
if ! "$PY" -c "import streamlit" >/dev/null 2>&1; then
    echo "[ERROR] streamlit is not installed for $PY."
    echo "        Run:  $PY -m pip install -r requirements.txt"
    echo
    echo "--- last lines of app.log (if any) ---"
    if [ -f "app.log" ]; then tail -n 30 "app.log"; fi
    echo
    read -r -p "Press Enter to close this window..." _
    exit 1
fi

echo "Launching app.py ... if this is your first run, give it a few seconds."
echo "Close this window (or press Ctrl+C) to stop the app."
echo
"$PY" src/run_app.py

echo
read -r -p "The app stopped. Press Enter to close this window..." _
exit 0
