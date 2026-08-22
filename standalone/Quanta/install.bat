@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

rem Enable ANSI colors on Windows 10+
for /f "delims=" %%A in ('echo prompt $E^| cmd') do set "ESC=%%A"
set "C_ACCENT=%ESC%[38;2;217;119;87m"
set "C_OK=%ESC%[38;2;61;154;110m"
set "C_ERR=%ESC%[38;2;196;74;74m"
set "C_DIM=%ESC%[2m"
set "C_BOLD=%ESC%[1m"
set "C_RESET=%ESC%[0m"

echo.
echo %C_ACCENT%%C_BOLD%  +----------------------------------------------+
echo   ^|                                              ^|
echo   ^|   Quanta                                     ^|
echo   ^|   Setup from scratch                         ^|
echo   ^|                                              ^|
echo   +----------------------------------------------+%C_RESET%
echo %C_DIM%  Gaussian DFT -^> Delta-SCF XPS workflow%C_RESET%
echo.

echo %C_ACCENT%[1/7]%C_RESET% %C_BOLD%Ensure application files%C_RESET%
if exist app.py if exist src (
  echo   %C_OK%✓%C_RESET% Application files present
  goto :after_fetch
)
set "DL_REPO=cyril-ver-mar/quanta"
set "DL_TAG=v1.0.2"
if exist VERSION (
  for /f "usebackq delims=" %%V in ("VERSION") do set "DL_TAG=v%%V"
)
if exist GITHUB_REPO (
  for /f "usebackq delims=" %%R in ("GITHUB_REPO") do set "DL_REPO=%%R"
)
set "DL_SRC="
if exist _quanta_dl rmdir /s /q _quanta_dl
where git >nul 2>&1
if !ERRORLEVEL!==0 (
  git clone --depth 1 --branch !DL_TAG! "https://github.com/!DL_REPO!/quanta.git" _quanta_dl >nul 2>&1
  if exist _quanta_dl\standalone\Quanta\app.py set "DL_SRC=_quanta_dl\standalone\Quanta"
  if not defined DL_SRC if exist _quanta_dl\app.py set "DL_SRC=_quanta_dl"
)
if not defined DL_SRC (
  echo   %C_ACCENT%→%C_RESET% Downloading from GitHub (!DL_TAG!)...
  powershell -NoProfile -Command ^
    "try { Invoke-WebRequest -Uri 'https://github.com/!DL_REPO!/archive/refs/tags/!DL_TAG!.zip' -OutFile '_quanta.zip' -UseBasicParsing; Expand-Archive -Path '_quanta.zip' -DestinationPath '_quanta_unzip' -Force } catch { exit 1 }"
  if errorlevel 1 goto :fetch_failed
  for /d %%D in (_quanta_unzip\quanta-*) do (
    if exist "%%D\standalone\Quanta\app.py" set "DL_SRC=%%D\standalone\Quanta"
    if not defined DL_SRC if exist "%%D\app.py" set "DL_SRC=%%D"
  )
)
if not defined DL_SRC goto :fetch_failed
xcopy /E /I /Y /Q "!DL_SRC!\*" . >nul
if exist _quanta_dl rmdir /s /q _quanta_dl
if exist _quanta_unzip rmdir /s /q _quanta_unzip
if exist _quanta.zip del /q _quanta.zip
echo   %C_OK%✓%C_RESET% Downloaded Quanta !DL_TAG! from GitHub
goto :after_fetch

:fetch_failed
if exist _quanta_dl rmdir /s /q _quanta_dl
if exist _quanta_unzip rmdir /s /q _quanta_unzip
if exist _quanta.zip del /q _quanta.zip
echo.
echo %C_ERR%+-- Error ------------------------------------------+%C_RESET%
echo %C_ERR%^|%C_RESET% Could not download Quanta application               %C_ERR%^|%C_RESET%
echo %C_ERR%+----------------------------------------------------+%C_RESET%
echo.
echo %C_BOLD%How to fix%C_RESET%
echo   %C_ACCENT%·%C_RESET% Check internet access
echo   %C_ACCENT%·%C_RESET% Install Git for Windows, or ensure PowerShell works
echo   %C_ACCENT%·%C_RESET% Clone full repo: git clone https://github.com/cyril-ver-mar/quanta.git
echo.
exit /b 1

:after_fetch

echo %C_ACCENT%[2/7]%C_RESET% %C_BOLD%Locate Python 3.11%C_RESET%
set "PY="
where py >nul 2>&1
if %ERRORLEVEL%==0 (
  py -3.11 -c "import sys" >nul 2>&1
  if !ERRORLEVEL!==0 set "PY=py -3.11"
)
if not defined PY (
  where python3.11 >nul 2>&1
  if !ERRORLEVEL!==0 set "PY=python3.11"
)
if not defined PY (
  where python >nul 2>&1
  if !ERRORLEVEL!==0 (
    for /f "tokens=*" %%V in ('python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2^>nul') do (
      if "%%V"=="3.11" set "PY=python"
    )
  )
)
if not defined PY (
  echo.
  echo %C_ERR%+-- Error ------------------------------------------+%C_RESET%
  echo %C_ERR%^|%C_RESET% Python 3.11 was not found on PATH                 %C_ERR%^|%C_RESET%
  echo %C_ERR%+----------------------------------------------------+%C_RESET%
  echo.
  echo %C_BOLD%How to fix%C_RESET%
  echo   %C_ACCENT%·%C_RESET% Install Python 3.11 from https://www.python.org/downloads/
  echo   %C_ACCENT%·%C_RESET% Tick "Add python.exe to PATH" during setup
  echo   %C_ACCENT%·%C_RESET% Open a NEW terminal and run: py -3.11 --version
  echo   %C_ACCENT%·%C_RESET% Then re-run: install.bat
  echo.
  exit /b 1
)
echo   %C_OK%✓%C_RESET% Using %PY%
%PY% --version

echo %C_ACCENT%[3/7]%C_RESET% %C_BOLD%Check venv module%C_RESET%
%PY% -c "import venv" >nul 2>&1
if errorlevel 1 (
  echo.
  echo %C_ERR%+-- Error ------------------------------------------+%C_RESET%
  echo %C_ERR%^|%C_RESET% Python venv module is missing                     %C_ERR%^|%C_RESET%
  echo %C_ERR%+----------------------------------------------------+%C_RESET%
  echo.
  echo %C_BOLD%How to fix%C_RESET%
  echo   %C_ACCENT%·%C_RESET% Reinstall Python 3.11 with standard library / pip
  echo   %C_ACCENT%·%C_RESET% Then re-run: install.bat
  echo.
  exit /b 1
)
echo   %C_OK%✓%C_RESET% venv module available

echo %C_ACCENT%[4/7]%C_RESET% %C_BOLD%Create / refresh virtualenv%C_RESET%
if not exist "venv\Scripts\python.exe" (
  %PY% -m venv venv
  if errorlevel 1 (
    echo.
    echo %C_ERR%+-- Error ------------------------------------------+%C_RESET%
    echo %C_ERR%^|%C_RESET% Could not create .\venv                           %C_ERR%^|%C_RESET%
    echo %C_ERR%+----------------------------------------------------+%C_RESET%
    echo.
    echo %C_BOLD%How to fix%C_RESET%
    echo   %C_ACCENT%·%C_RESET% Delete broken folder: rmdir /s /q venv
    echo   %C_ACCENT%·%C_RESET% Ensure write permission in this folder
    echo   %C_ACCENT%·%C_RESET% Re-run: install.bat
    echo.
    exit /b 1
  )
  echo   %C_OK%✓%C_RESET% Created .\venv
) else (
  echo   %C_OK%✓%C_RESET% Reusing existing .\venv
)

call "venv\Scripts\activate.bat"
if errorlevel 1 (
  echo %C_ERR%Failed to activate venv%C_RESET%
  exit /b 1
)

echo %C_ACCENT%[5/7]%C_RESET% %C_BOLD%Install Python packages%C_RESET%
set "REQ=requirements-runtime.txt"
if not exist "%REQ%" set "REQ=requirements.txt"
if not exist "%REQ%" (
  echo.
  echo %C_ERR%+-- Error ------------------------------------------+%C_RESET%
  echo %C_ERR%^|%C_RESET% requirements file not found                     %C_ERR%^|%C_RESET%
  echo %C_ERR%+----------------------------------------------------+%C_RESET%
  echo.
  echo %C_BOLD%How to fix%C_RESET%
  echo   %C_ACCENT%·%C_RESET% Run install.bat from the Quanta folder (project or standalone zip root)
  echo.
  exit /b 1
)
python -m pip install --upgrade pip
if errorlevel 1 (
  echo.
  echo %C_ERR%+-- Error ------------------------------------------+%C_RESET%
  echo %C_ERR%^|%C_RESET% Failed to upgrade pip                             %C_ERR%^|%C_RESET%
  echo %C_ERR%+----------------------------------------------------+%C_RESET%
  echo.
  echo %C_BOLD%How to fix%C_RESET%
  echo   %C_ACCENT%·%C_RESET% Check network / proxy
  echo   %C_ACCENT%·%C_RESET% Retry: install.bat
  echo.
  exit /b 1
)
echo   %C_OK%✓%C_RESET% pip upgraded
pip install -r %REQ%
if errorlevel 1 (
  echo.
  echo %C_ERR%+-- Error ------------------------------------------+%C_RESET%
  echo %C_ERR%^|%C_RESET% pip install failed                                %C_ERR%^|%C_RESET%
  echo %C_ERR%+----------------------------------------------------+%C_RESET%
  echo.
  echo %C_BOLD%How to fix%C_RESET%
  echo   %C_ACCENT%·%C_RESET% Check network access to PyPI
  echo   %C_ACCENT%·%C_RESET% RDKit may take several minutes on first install
  echo   %C_ACCENT%·%C_RESET% Try: venv\Scripts\activate ^&^& pip install -r requirements.txt
  echo.
  exit /b 1
)
echo   %C_OK%✓%C_RESET% Dependencies installed

echo %C_ACCENT%[6/7]%C_RESET% %C_BOLD%Create data folders ^& smoke-test imports%C_RESET%
if not exist data\jobs mkdir data\jobs
if not exist data\compounds mkdir data\compounds
if not exist data\logs mkdir data\logs
if not exist exports mkdir exports
set "PYTHONPATH=%CD%"
python -m src.utils.deps_check
if errorlevel 1 (
  echo.
  echo %C_ERR%+-- Error ------------------------------------------+%C_RESET%
  echo %C_ERR%^|%C_RESET% Dependency import smoke-test failed               %C_ERR%^|%C_RESET%
  echo %C_ERR%+----------------------------------------------------+%C_RESET%
  echo.
  echo %C_BOLD%How to fix%C_RESET%
  echo   %C_ACCENT%·%C_RESET% Re-run install.bat after fixing pip errors
  echo   %C_ACCENT%·%C_RESET% Or: venv\Scripts\activate ^&^& pip install -r requirements.txt
  echo.
  exit /b 1
)
echo   %C_OK%✓%C_RESET% All runtime packages import OK (streamlit, rdkit, ...)
echo   %C_OK%✓%C_RESET% Folders: data\, data\jobs, exports

echo %C_ACCENT%[7/7]%C_RESET% %C_BOLD%Finish%C_RESET%
echo   %C_OK%✓%C_RESET% Install complete
echo.
echo %C_DIM%  -- next --%C_RESET%
echo   %C_BOLD%run.bat%C_RESET%
echo %C_DIM%  Set Gaussian path on Settings page (Windows run mode)%C_RESET%
echo.
echo %C_BOLD%  If the browser does not open by itself:%C_RESET%
echo   %C_ACCENT%·%C_RESET% open http://localhost:8501
echo   %C_ACCENT%·%C_RESET% or http://127.0.0.1:8501
echo.
endlocal
