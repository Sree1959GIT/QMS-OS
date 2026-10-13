@echo off
rem Benchmark harness (ROADMAP MVP-0 slice 4b; docs\BENCHMARK-PLAN.md, section 7). Forwards every argument to
rem python -m qms_bench, run from apps\api. Example: scripts\run-benchmark.bat --list-models
setlocal
call "%~dp0env.bat" || exit /b 1
cd /d "%QMSOS_HOME%\apps\api"
"%QMSOS_HOME%\.venv\Scripts\python.exe" -m qms_bench %*
set "RC=%ERRORLEVEL%"
endlocal & exit /b %RC%
