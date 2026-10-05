@echo off
setlocal
cd /d "%~dp0.."
docker version >nul 2>&1 || (echo Docker is not running. Start Docker Desktop and retry. & exit /b 1)
if not exist .env (
  copy .env.example .env >nul
  for /f %%P in ('powershell -NoProfile -Command "[guid]::NewGuid().ToString('N')+[guid]::NewGuid().ToString('N')"') do >>.env echo POSTGRES_PASSWORD=%%P
  echo Created .env with a generated password. Keep it private.
)
docker compose up -d --wait || (echo Failed to start. Run: docker compose logs postgres & exit /b 1)
docker compose ps
echo PostgreSQL is healthy on 127.0.0.1:5432 (database qmsos).
endlocal
