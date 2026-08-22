@echo off
REM Quanta bootstrap — works from Explorer double-click AND from terminal
cd /d "%~dp0"
title Quanta Bootstrap
setlocal EnableExtensions EnableDelayedExpansion

set "ERR=0"
set "LOG=%~dp0quanta_bootstrap.log"
set "QUANTA_SUGGESTED_DIR=%~dp0"
set "QUANTA_INSTALL_DIR=%~dp0"
if "%QUANTA_INSTALL_DIR:~-1%"=="\" set "QUANTA_INSTALL_DIR=%QUANTA_INSTALL_DIR:~0,-1%"

echo.
echo   Quanta bootstrap
echo   Folder: %~dp0
echo.
echo. > "%LOG%"
echo [%date% %time%] started >> "%LOG%"

where powershell >nul 2>&1
if errorlevel 1 (
  echo ERROR: PowerShell not found. >> "%LOG%"
  echo ERROR: PowerShell not found.
  set "ERR=1"
  goto :finish
)

if not exist "%~dp0install_quanta.ps1" (
  echo ERROR: install_quanta.ps1 not found >> "%LOG%"
  echo.
  echo ERROR: install_quanta.ps1 must be in the same folder as this .bat
  echo Expected: %~dp0install_quanta.ps1
  set "ERR=1"
  goto :finish
)

set "PS1=%TEMP%\quanta_install_%RANDOM%.ps1"
copy /Y "%~dp0install_quanta.ps1" "%PS1%" >nul

echo Running installer — answer the prompts below...
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
set "ERR=!ERRORLEVEL!"
echo exit !ERR! >> "%LOG%"
del "%PS1%" >nul 2>&1

echo.
if not "!ERR!"=="0" (
  echo Bootstrap FAILED — exit code !ERR!
  echo Log: %LOG%
) else (
  echo Bootstrap OK.
  echo.
  echo Next steps:
  echo   cd "%~dp0Quanta"
  echo   install.bat
  echo   run.bat
)

:finish
echo.
pause
exit /b !ERR!
