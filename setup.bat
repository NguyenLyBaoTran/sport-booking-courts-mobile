@echo off
setlocal
where py >nul 2>nul
if not errorlevel 1 goto use_py
where python >nul 2>nul
if not errorlevel 1 goto use_python
echo Python 3 was not found. Install Python 3 or run setup.sh from a compatible shell.
exit /b 1

:use_py
py -3 -c "import sys" >nul 2>nul
if errorlevel 1 goto use_python
py -3 "%~dp0setup_config.py"
exit /b %ERRORLEVEL%

:use_python
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 goto no_python
python "%~dp0setup_config.py"
exit /b %ERRORLEVEL%

:no_python
echo Python 3.10 or newer was not found. Install Python and retry.
exit /b 1
