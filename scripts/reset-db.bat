@echo off
cd /d "%~dp0.."
echo This DELETES all local database data (synthetic dev only).
set /p OK=Type DELETE to continue: 
if /i not "%OK%"=="DELETE" (echo Cancelled. & exit /b 1)
docker compose down -v
