@echo off
cd /d "%~dp0"
title Quanta Install
setlocal EnableExtensions EnableDelayedExpansion

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

echo %C_ACCENT%[1/6]%C_RESET% %C_BOLD%Locate Python 3.11%C_RESET%
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
  echo   %C_ACCENT%*%C_RESET% Install Python 3.11 from https://www.python.org/downloads/
  echo   %C_ACCENT%*%C_RESET% Tick "Add python.exe to PATH" during setup
  echo   %C_ACCENT%*%C_RESET% Open a NEW terminal and run: py -3.11 --version
  echo   %C_ACCENT%*%C_RESET% Then re-run: install.bat
  echo.
  exit /b 1
)
echo   %C_OK%OK%C_RESET% Using %PY%
%PY% --version

echo %C_ACCENT%[2/6]%C_RESET% %C_BOLD%Check venv module%C_RESET%
%PY% -c "import venv" >nul 2>&1
if errorlevel 1 (
  echo.
  echo %C_ERR%+-- Error ------------------------------------------+%C_RESET%
  echo %C_ERR%^|%C_RESET% Python venv module is missing                     %C_ERR%^|%C_RESET%
  echo %C_ERR%+----------------------------------------------------+%C_RESET%
  echo.
  echo %C_BOLD%How to fix%C_RESET%
  echo   %C_ACCENT%*%C_RESET% Reinstall Python 3.11 with standard library / pip
  echo   %C_ACCENT%*%C_RESET% Then re-run: install.bat
  echo.
  exit /b 1
)
echo   %C_OK%OK%C_RESET% venv module available

echo %C_ACCENT%[3/6]%C_RESET% %C_BOLD%Create / refresh virtualenv%C_RESET%
if not exist "venv\Scripts\python.exe" (
  %PY% -m venv venv
  if errorlevel 1 (
    echo.
    echo %C_ERR%+-- Error ------------------------------------------+%C_RESET%
    echo %C_ERR%^|%C_RESET% Could not create .\venv                           %C_ERR%^|%C_RESET%
    echo %C_ERR%+----------------------------------------------------+%C_RESET%
    echo.
    echo %C_BOLD%How to fix%C_RESET%
    echo   %C_ACCENT%*%C_RESET% Delete broken folder: rmdir /s /q venv
    echo   %C_ACCENT%*%C_RESET% Ensure write permission in this folder
    echo   %C_ACCENT%*%C_RESET% Re-run: install.bat
    echo.
    exit /b 1
  )
  echo   %C_OK%OK%C_RESET% Created .\venv
) else (
  echo   %C_OK%OK%C_RESET% Reusing existing .\venv
)

call "venv\Scripts\activate.bat"
if errorlevel 1 (
  echo %C_ERR%Failed to activate venv%C_RESET%
  exit /b 1
)

echo %C_ACCENT%[4/6]%C_RESET% %C_BOLD%Install Python packages%C_RESET%
if not exist requirements.txt (
  echo.
  echo %C_ERR%+-- Error ------------------------------------------+%C_RESET%
  echo %C_ERR%^|%C_RESET% requirements.txt not found                        %C_ERR%^|%C_RESET%
  echo %C_ERR%+----------------------------------------------------+%C_RESET%
  echo.
  echo %C_BOLD%How to fix%C_RESET%
  echo   %C_ACCENT%*%C_RESET% Run install.bat from the Quanta project root
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
  echo   %C_ACCENT%*%C_RESET% Check network / proxy
  echo   %C_ACCENT%*%C_RESET% Retry: install.bat
  echo.
  exit /b 1
)
echo   %C_OK%OK%C_RESET% pip upgraded
pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo %C_ERR%+-- Error ------------------------------------------+%C_RESET%
  echo %C_ERR%^|%C_RESET% pip install -r requirements.txt failed            %C_ERR%^|%C_RESET%
  echo %C_ERR%+----------------------------------------------------+%C_RESET%
  echo.
  echo %C_BOLD%How to fix%C_RESET%
  echo   %C_ACCENT%*%C_RESET% Check network access to PyPI
  echo   %C_ACCENT%*%C_RESET% RDKit may take several minutes on first install
  echo   %C_ACCENT%*%C_RESET% Try: venv\Scripts\activate ^&^& pip install -r requirements.txt
  echo.
  exit /b 1
)
echo   %C_OK%OK%C_RESET% Dependencies installed

echo %C_ACCENT%[5/6]%C_RESET% %C_BOLD%Create data folders ^& smoke-test imports%C_RESET%
if not exist data\jobs mkdir data\jobs
if not exist data\compounds mkdir data\compounds
if not exist data\logs mkdir data\logs
if not exist exports mkdir exports
python -c "import importlib; [importlib.import_module(m) for m in ('streamlit','rdkit','pandas','numpy','matplotlib','plotly','py3Dmol','scipy','openpyxl','PIL')]"
if errorlevel 1 (
  echo.
  echo %C_ERR%+-- Error ------------------------------------------+%C_RESET%
  echo %C_ERR%^|%C_RESET% Dependency import smoke-test failed               %C_ERR%^|%C_RESET%
  echo %C_ERR%+----------------------------------------------------+%C_RESET%
  echo.
  echo %C_BOLD%How to fix%C_RESET%
  echo   %C_ACCENT%*%C_RESET% Re-run install.bat after fixing pip errors
  echo   %C_ACCENT%*%C_RESET% Or: venv\Scripts\activate ^&^& pip install -r requirements.txt
  echo.
  exit /b 1
)
echo   %C_OK%OK%C_RESET% All runtime packages import OK (streamlit, rdkit, ...)
echo   %C_OK%OK%C_RESET% Folders: data\jobs, data\compounds, exports

echo %C_ACCENT%[6/6]%C_RESET% %C_BOLD%Finish%C_RESET%
echo   %C_OK%OK%C_RESET% Install complete
echo.
echo %C_DIM%  -- next --%C_RESET%
echo   %C_BOLD%run.bat%C_RESET%
echo %C_DIM%  Settings -^> Gaussian path (Windows run mode)%C_RESET%
echo.
echo %C_BOLD%  If the browser does not open by itself:%C_RESET%
echo   %C_ACCENT%*%C_RESET% open http://localhost:8501
echo   %C_ACCENT%*%C_RESET% or http://127.0.0.1:8501
echo.
echo   Removing install.bat (no longer needed)...
set "DEL_ME=%~f0"
start "" /min cmd /c "ping -n 2 127.0.0.1 >nul & del /f /q "%DEL_ME%""
if /I "%QUANTA_INSTALL_NOPAUSE%"=="1" (
  endlocal
  exit /b 0
)
pause
endlocal
