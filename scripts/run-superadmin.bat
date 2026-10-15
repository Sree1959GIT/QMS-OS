@echo off
rem Read-only super admin scripts behind the Claude Code skills (R-38, R-46). Forwards every argument to
rem python -m qms_superadmin, run from apps\api. Example: scripts\run-superadmin.bat housekeeping
rem review-org, access-segregation and knowledge-integrity need QMS_MODE=demo or test and QMS_DATABASE_URL naming
rem the synthetic database; knowledge-integrity also needs QMS_EVIDENCE_DIR naming the interim evidence store.
setlocal
call "%~dp0env.bat" || exit /b 1
cd /d "%QMSOS_HOME%\apps\api"
"%QMSOS_HOME%\.venv\Scripts\python.exe" -m qms_superadmin %*
set "RC=%ERRORLEVEL%"
endlocal & exit /b %RC%
