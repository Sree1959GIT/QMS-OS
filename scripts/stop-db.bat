@echo off
cd /d "%~dp0.."
docker compose down
echo Stopped. Data is kept in the Docker volume ending in qmsos_pgdata.
