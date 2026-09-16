@echo off
setlocal
cd /d "%~dp0"
title Jira Test Case Generator

echo ============================================================
echo  Jira -^> Test Case Generator
echo  Starting Streamlit and opening your browser...
echo ============================================================

rem --- Pick the Python interpreter (venv first, then system python) ---
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if exist "venv\Scripts\python.exe" set "PY=venv\Scripts\python.exe"

echo Using: %PY%
echo.

rem --- Quick dependency check so a broken launch is not a mystery ---
"%PY%" -c "import streamlit" >nul 2>&1
if errorlevel 1 goto :missing_dep

goto :run

:missing_dep
    echo [ERROR] streamlit is not installed for %PY%.
    echo         Run:  "%PY%" -m pip install -r requirements.txt
    echo.
    echo --- last lines of app.log (if any) ---
    if exist "app.log" powershell -NoProfile -Command "Get-Content 'app.log' -Tail 30" 2>nul
    echo.
    echo Press any key to close this window.
    pause >nul
    exit /b 1

:run
echo Launching app.py ... if this is your first run, give it a few seconds.
echo Close this window (or press Ctrl+C) to stop the app.
echo.
"%PY%" src\run_app.py

echo.
echo The app stopped. Press any key to close this window.
pause >nul
exit /b 0
