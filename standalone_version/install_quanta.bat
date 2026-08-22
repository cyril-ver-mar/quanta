@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM Quanta Windows bootstrap — download app from GitHub, then run install.bat inside Quanta\
REM Usage: double-click install_quanta.bat  OR  install_quanta.bat from cmd

set "ERR=0"

where powershell >nul 2>&1
if errorlevel 1 (
  echo ERROR: PowerShell not found.
  set "ERR=1"
  goto :failed
)

set "QUANTA_SUGGESTED_DIR=%CD%"
set "BAT_DIR=%~dp0"
if "%BAT_DIR:~-1%"=="\" set "BAT_DIR=%BAT_DIR:~0,-1%"
set "QUANTA_INSTALL_DIR=%BAT_DIR%"

set "PS1=%TEMP%\quanta_install_fresh.ps1"

if exist "%~dp0install_quanta.ps1" (
  echo.
  echo   Quanta bootstrap launcher
  echo   Using local install_quanta.ps1
  copy /Y "%~dp0install_quanta.ps1" "%PS1%" >nul
  goto :run_ps1
)

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
  if exist "%~dp0install_quanta.ps1" (
    copy /Y "%~dp0install_quanta.ps1" "%PS1%" >nul
  ) else (
    echo   No local install_quanta.ps1 found. Check network / GitHub.
    set "ERR=1"
    goto :failed
  )
)

:run_ps1
echo   Running installer...
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
set "ERR=%ERRORLEVEL%"
del "%PS1%" >nul 2>&1

if not "%ERR%"=="0" goto :failed

echo.
echo   Bootstrap OK. Next: cd Quanta ^&^& install.bat ^&^& run.bat
goto :done

:failed
if not defined ERR set ERR=1
echo.
echo   Bootstrap FAILED (exit code %ERR%). Read the messages above.
echo   You can also open cmd here and run: install_quanta.bat
echo.

:done
echo.
pause
endlocal
exit /b %ERR%
