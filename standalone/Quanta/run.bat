@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist venv (
  echo Missing venv. Run install.bat first.
  exit /b 1
)

if not exist app.py (
  echo app.py not found — run install.bat to download the application.
  exit /b 1
)

call venv\Scripts\activate.bat
set "PYTHONPATH=%CD%"
python -m src.utils.deps_check --ensure
if errorlevel 1 (
  echo Package check failed — run install.bat
  exit /b 1
)
python launch.py
endlocal
