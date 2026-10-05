@echo off
setlocal
call "%~dp0env.bat"
cd /d "%QMSOS_HOME%\apps\api"
"%QMSOS_HOME%\.venv\Scripts\python.exe" -m pytest -q -p no:cacheprovider
endlocal
