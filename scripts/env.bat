@echo off
rem Keeps temp files and tool caches out of the user profile (AppData).
rem Default: inside the project folder (.tmp and .cache, both git-ignored).
rem Optional: QMS_TEMP_ROOT = an absolute folder on a drive other than C:, e.g. D:\QMS-OS-TEMP. Then TEMP/TMP (and
rem pytest's temporary folders) go to <root>\tmp, and the pip cache and pycache to <root>\cache.
rem Never falls back to C: - a bad QMS_TEMP_ROOT or a folder that cannot be created stops with exit code 1, and every
rem caller stops too ("call env.bat || exit /b 1").
for %%I in ("%~dp0..") do set "QMSOS_HOME=%%~fI"
set "QMSOS_TMPBASE=%QMSOS_HOME%\.tmp"
set "QMSOS_CACHE=%QMSOS_HOME%\.cache"
if not defined QMS_TEMP_ROOT goto apply
if not "%QMS_TEMP_ROOT:~1,1%"==":" goto bad_root
for %%I in ("%QMS_TEMP_ROOT%") do set "QMSOS_ROOT=%%~fI"
if /i "%QMSOS_ROOT:~0,2%"=="C:" goto bad_root
set "QMSOS_TMPBASE=%QMSOS_ROOT%\tmp"
set "QMSOS_CACHE=%QMSOS_ROOT%\cache"
:apply
set "TEMP=%QMSOS_TMPBASE%"
set "TMP=%QMSOS_TMPBASE%"
set "PIP_CACHE_DIR=%QMSOS_CACHE%\pip"
set "PYTHONPYCACHEPREFIX=%QMSOS_CACHE%\pycache"
set "PIP_REQUIRE_VIRTUALENV=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
if not exist "%TEMP%" mkdir "%TEMP%" || goto mkdir_failed
if not exist "%PIP_CACHE_DIR%" mkdir "%PIP_CACHE_DIR%" || goto mkdir_failed
if not exist "%PYTHONPYCACHEPREFIX%" mkdir "%PYTHONPYCACHEPREFIX%" || goto mkdir_failed
exit /b 0

:bad_root
echo env.bat: QMS_TEMP_ROOT must be an absolute folder on a drive other than C: (got "%QMS_TEMP_ROOT%"). 1>&2
exit /b 1

:mkdir_failed
echo env.bat: could not create the temp or cache folders under "%QMSOS_TMPBASE%" and "%QMSOS_CACHE%". 1>&2
exit /b 1
