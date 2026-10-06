@echo off
setlocal
call "%~dp0env.bat" || exit /b 1
cd /d "%QMSOS_HOME%\apps\api"
"%QMSOS_HOME%\.venv\Scripts\python.exe" -m pytest -q -p no:cacheprovider
set "RC=%ERRORLEVEL%"
endlocal & exit /b %RC%
