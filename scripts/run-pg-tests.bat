@echo off
rem PostgreSQL test runs against the local test database (synthetic data only; not used in CI).
rem The URL is read from the git-ignored .private\pg-test-url.txt into this process only and is never echoed.
rem   run-pg-tests.bat                PostgreSQL integration tests (marker "postgres")
rem   run-pg-tests.bat full           the whole suite on the PostgreSQL test database (opt-in rerun)
rem   run-pg-tests.bat alembic ARGS   Alembic against the test database, e.g. alembic revision --autogenerate -m "baseline"
rem --tb=short: pytest's long tracebacks print function arguments, which could include the URL.
setlocal DisableDelayedExpansion
call "%~dp0env.bat" || exit /b 1
set "URLFILE=%QMSOS_HOME%\.private\pg-test-url.txt"
if not exist "%URLFILE%" (echo Missing .private\pg-test-url.txt & exit /b 1)
set "QMS_TEST_POSTGRES_URL="
set /p QMS_TEST_POSTGRES_URL=<"%URLFILE%"
if not defined QMS_TEST_POSTGRES_URL (echo .private\pg-test-url.txt is empty & exit /b 1)
set "PY=%QMSOS_HOME%\.venv\Scripts\python.exe"
cd /d "%QMSOS_HOME%\apps\api"
if /i "%~1"=="alembic" goto alembic
if /i "%~1"=="full" goto full
"%PY%" -m pytest -q -p no:cacheprovider --tb=short -m postgres
goto done

:full
set "QMS_TEST_FULL_SUITE_ON_POSTGRES=1"
"%PY%" -m pytest -q -p no:cacheprovider --tb=short
goto done

:alembic
set "ARGS=%*"
set "ARGS=%ARGS:*alembic=%"
set "QMS_DATABASE_URL=%QMS_TEST_POSTGRES_URL%"
"%PY%" -m alembic %ARGS%

:done
set "RC=%ERRORLEVEL%"
endlocal & exit /b %RC%
