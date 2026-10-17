@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-desktop\Scripts\python.exe" (
  echo Execute Instalar-Aurora.cmd primeiro.
  pause
  exit /b 1
)
".venv-desktop\Scripts\python.exe" desktop\launcher.py --configure
if errorlevel 1 pause
