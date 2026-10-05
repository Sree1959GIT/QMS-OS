@echo off
setlocal
cd /d "%~dp0.."
if not exist backups mkdir backups
for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set TS=%%T
docker compose exec -T postgres sh -c "pg_dump -U $POSTGRES_USER -d $POSTGRES_DB -Fc" > backups\qmsos-%TS%.dump
for %%F in (backups\qmsos-%TS%.dump) do if %%~zF EQU 0 (echo Backup failed, empty file. & del %%F & exit /b 1)
echo Wrote backups\qmsos-%TS%.dump
endlocal
