@echo off
echo === Container Logs ===
echo --- APP ---
docker-compose logs app --tail=30
echo.
echo --- POSTGRES ---
docker-compose logs postgres --tail=10
echo.
echo --- REDIS ---
docker-compose logs redis --tail=10
pause
