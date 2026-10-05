@echo off
setlocal
call "%~dp0env.bat"
cd /d "%QMSOS_HOME%"
py -3.12 --version >nul 2>&1 || (echo Python 3.12 not found. Install 3.12.x, then retry. & exit /b 1)
if not exist ".venv\Scripts\python.exe" py -3.12 -m venv ".venv" || exit /b 1
set "PY=%QMSOS_HOME%\.venv\Scripts\python.exe"
"%PY%" -m pip install --upgrade pip || exit /b 1
cd apps\api
"%PY%" -m pip install -c constraints-ci.txt -e ".[dev]" 2>nul
if errorlevel 1 (
  echo No [dev] extra found, installing app plus test tools.
  "%PY%" -m pip install -c constraints-ci.txt -e . pytest httpx || exit /b 1
)
"%PY%" -c "import sys; print('Venv:', sys.prefix)"
endlocal
