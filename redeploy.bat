@echo off
title Vi Reactivation Platform - Redeploy
color 0A

echo ============================================
echo  Vi Reactivation Platform - Update Deploy
echo ============================================
echo.

:: Go to the folder where this .bat file is located
cd /d "%~dp0"

echo [1/4] Latest code download ho raha hai...
git pull origin main
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ERROR: git pull fail hua. Internet check karo.
    pause
    exit /b 1
)
echo     Done!
echo.

echo [2/4] Docker images build ho rahi hain (5-10 min lag sakte hain)...
docker compose -f docker-compose.production.yml --env-file .env.production build
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ERROR: Build fail hua. Docker Desktop open hai? Check karo.
    pause
    exit /b 1
)
echo     Done!
echo.

echo [3/4] Database migrations apply ho rahi hain...
docker compose -f docker-compose.production.yml --env-file .env.production up migrate
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ERROR: Migration fail hui. Upar ka output copy karo aur Claude ko bhejo.
    pause
    exit /b 1
)
echo     Done!
echo.

echo [4/4] Sab services restart ho rahi hain...
docker compose -f docker-compose.production.yml --env-file .env.production up -d
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ERROR: Services start nahi hui. Upar ka output copy karo aur Claude ko bhejo.
    pause
    exit /b 1
)
echo     Done!
echo.

echo ============================================
echo  COMPLETE! Platform update ho gaya.
echo  Browser mein reload karo: http://localhost
echo ============================================
echo.
pause
