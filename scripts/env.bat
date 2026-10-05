@echo off
rem Keeps temp files and tool caches inside the project folder, not AppData.
for %%I in ("%~dp0..") do set "QMSOS_HOME=%%~fI"
set "QMSOS_CACHE=%QMSOS_HOME%\.cache"
set "TEMP=%QMSOS_HOME%\.tmp"
set "TMP=%QMSOS_HOME%\.tmp"
set "PIP_CACHE_DIR=%QMSOS_CACHE%\pip"
set "PYTHONPYCACHEPREFIX=%QMSOS_CACHE%\pycache"
set "PIP_REQUIRE_VIRTUALENV=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
if not exist "%TEMP%" mkdir "%TEMP%"
if not exist "%PIP_CACHE_DIR%" mkdir "%PIP_CACHE_DIR%"
