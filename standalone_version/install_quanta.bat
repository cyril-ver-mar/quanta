@echo off
setlocal EnableExtensions
REM Quanta Windows bootstrap (ONE file is enough).
REM Downloads latest install_quanta.ps1 from GitHub and runs it.
REM
REM Usage:
REM   .\install_quanta.bat

where powershell >nul 2>&1
if errorlevel 1 (
  echo ERROR: PowerShell not found.
  exit /b 1
)

set "QUANTA_SUGGESTED_DIR=%CD%"
set "BAT_DIR=%~dp0"
if "%BAT_DIR:~-1%"=="\" set "BAT_DIR=%BAT_DIR:~0,-1%"
set "QUANTA_INSTALL_DIR=%BAT_DIR%"

set "PS1=%TEMP%\quanta_install_fresh.ps1"
set "RAW=https://raw.githubusercontent.com/cyril-ver-mar/quanta/master/standalone_version/install_quanta.ps1"

echo.
echo   Quanta bootstrap launcher
echo   Suggested folder: %QUANTA_SUGGESTED_DIR%
echo   Downloading latest installer script from GitHub...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command ^
  "try { $u='%RAW%?t=' + [guid]::NewGuid().ToString(); Invoke-WebRequest -UseBasicParsing -Uri $u -OutFile '%PS1%'; if (-not (Test-Path '%PS1%')) { exit 1 }; exit 0 } catch { Write-Host $_.Exception.Message; exit 1 }"
if errorlevel 1 (
  echo.
  echo   Download from GitHub failed.
  echo   If you have install_quanta.ps1 next to this .bat, trying local copy...
  if exist "%~dp0install_quanta.ps1" (
    copy /Y "%~dp0install_quanta.ps1" "%PS1%" >nul
  ) else (
    echo   No local install_quanta.ps1 found. Check network / GitHub.
    exit /b 1
  )
)

echo   Running installer...
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
set "ERR=%ERRORLEVEL%"
del "%PS1%" >nul 2>&1
exit /b %ERR%
