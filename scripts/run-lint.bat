@echo off
rem Lint (ruff check) and type check (mypy on qms_os) with the configuration in apps\api\pyproject.toml - the same
rem checks as the CI jobs lint and types. Needs the lint extra once:
rem   .venv\Scripts\python.exe -m pip install -c apps\api\constraints-ci.txt -e "apps\api[dev,lint]"
rem Caches go under the env.bat cache folder (.cache or QMS_TEMP_ROOT\cache), never into the repository.
setlocal
call "%~dp0env.bat" || exit /b 1
cd /d "%QMSOS_HOME%\apps\api"
set "PY=%QMSOS_HOME%\.venv\Scripts\python.exe"
"%PY%" -m ruff --version >nul 2>&1 || (echo ruff not installed: install the lint extra first, see this file. & exit /b 1)
"%PY%" -m mypy --version >nul 2>&1 || (echo mypy not installed: install the lint extra first, see this file. & exit /b 1)
set "RC=0"
echo == ruff check
"%PY%" -m ruff check --cache-dir "%QMSOS_CACHE%\ruff" . || set "RC=1"
echo == mypy
"%PY%" -m mypy --cache-dir "%QMSOS_CACHE%\mypy" || set "RC=1"
endlocal & exit /b %RC%
