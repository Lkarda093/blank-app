@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Instale Python 3.12 de https://www.python.org/downloads/windows/ e execute novamente.
  pause
  exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
  echo Instale Node.js LTS 22.12 ou superior de https://nodejs.org/ e execute novamente.
  pause
  exit /b 1
)
py -3.12 -m venv .venv-desktop
if errorlevel 1 goto failed
".venv-desktop\Scripts\python.exe" -m pip install -r desktop\requirements.txt
if errorlevel 1 goto failed
call npm --prefix frontend ci
if errorlevel 1 goto failed
call npm --prefix frontend run build
if errorlevel 1 goto failed
echo Instalacao concluida. Abra Iniciar-Aurora.cmd.
pause
exit /b 0
:failed
echo A instalacao nao terminou. Copie a mensagem acima para verificarmos.
pause
exit /b 1
