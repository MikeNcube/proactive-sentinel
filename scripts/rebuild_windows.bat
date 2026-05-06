@echo off
echo Rebuilding Proactive Sentinel...
echo.

echo Stopping and removing containers...
docker-compose down -v

echo Rebuilding images...
docker-compose build --no-cache

echo Starting services...
docker-compose up -d

echo Waiting for services...
timeout /t 15 /nobreak

echo Running setup...
python scripts/setup.py

echo.
echo Rebuild complete!
echo Test API: curl.exe http://localhost:5001/health
