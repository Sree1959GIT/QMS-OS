@echo off
call "%~dp0env.bat"
echo Project : %QMSOS_HOME%
echo Temp    : %TEMP%
echo PipCache: %PIP_CACHE_DIR%
echo PyCache : %PYTHONPYCACHEPREFIX%
if exist "%QMSOS_HOME%\.venv\Scripts\python.exe" ("%QMSOS_HOME%\.venv\Scripts\python.exe" -c "import sys;print('Venv    :',sys.prefix)") else echo Venv    : not created yet
echo Docker  : volume *_qmsos_pgdata; disk image location is set in Docker Desktop (see docs/LOCAL-RUNTIME.md)
