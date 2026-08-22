@echo off
REM Quanta bootstrap - works from Explorer double-click AND from terminal
cd /d "%~dp0"
title Quanta Installer
setlocal EnableExtensions EnableDelayedExpansion

set "ERR=0"
set "QUANTA_SUGGESTED_DIR=%~dp0"
set "QUANTA_INSTALL_DIR=%~dp0"
if "%QUANTA_INSTALL_DIR:~-1%"=="\" set "QUANTA_INSTALL_DIR=%QUANTA_INSTALL_DIR:~0,-1%"

echo.
echo   Quanta installer
echo   Folder: %~dp0
echo.

where powershell >nul 2>&1
if errorlevel 1 (
  echo ERROR: PowerShell not found.
  set "ERR=1"
  goto :finish
)

if not exist "%~dp0install_quanta.ps1" (
  echo.
  echo ERROR: install_quanta.ps1 must be in the same folder as this .bat
  echo Expected: %~dp0install_quanta.ps1
  set "ERR=1"
  goto :finish
)

set "PS1=%TEMP%\quanta_install_%RANDOM%.ps1"
copy /Y "%~dp0install_quanta.ps1" "%PS1%" >nul

echo Running installer - answer the prompts below...
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
set "ERR=!ERRORLEVEL!"
del "%PS1%" >nul 2>&1

echo.
if not "!ERR!"=="0" (
  echo Installer FAILED - exit code !ERR!
) else (
  echo Installer finished.
  echo Start the app with run.bat inside the Quanta folder.
)

:finish
echo.
pause
exit /b !ERR!
