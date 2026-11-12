@echo off
setlocal
cd /d "%~dp0"

if not exist "backend\.venv\Scripts\python.exe" (
    echo Backend virtual environment was not found.
    echo Create it with: cd backend ^&^& python -m venv .venv ^&^& .venv\Scripts\python -m pip install -r requirements.txt
    exit /b 1
)

"backend\.venv\Scripts\python.exe" "backend\scripts\setup_local.py"
exit /b %errorlevel%
