@echo off
echo === Rebuilding Proactive Sentinel ===
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
timeout /t 20 /nobreak
docker-compose logs app --tail=50
pause
