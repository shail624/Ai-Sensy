@echo off
title Fix DB Password - Auto
color 0E
cd /d "%~dp0"

echo ============================================
echo  Vi Platform - Database Password Auto-Fix
echo ============================================
echo.
echo .env.production se passwords padh raha hoon...

:: Read DB_ROOT_PASSWORD, DB_USER, DB_PASSWORD from .env.production
set ROOT_PASS=
set APP_USER=
set APP_PASS=

for /f "usebackq tokens=1,* delims==" %%a in (".env.production") do (
    if "%%a"=="DB_ROOT_PASSWORD" set "ROOT_PASS=%%b"
    if "%%a"=="DB_USER"          set "APP_USER=%%b"
    if "%%a"=="DB_PASSWORD"      set "APP_PASS=%%b"
)

if "%ROOT_PASS%"=="" (
    color 0C
    echo ERROR: DB_ROOT_PASSWORD nahi mila .env.production mein.
    pause
    exit /b 1
)
if "%APP_PASS%"=="" (
    color 0C
    echo ERROR: DB_PASSWORD nahi mila .env.production mein.
    pause
    exit /b 1
)

echo Passwords mil gaye. MySQL user reset ho raha hai...
echo.

docker compose -f docker-compose.production.yml exec mysql ^
    mysql -u root -p%ROOT_PASS% -e ^
    "ALTER USER '%APP_USER%'@'%%' IDENTIFIED BY '%APP_PASS%'; FLUSH PRIVILEGES; SELECT 'Password reset OK' AS status;"

if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ERROR: MySQL reset fail hua.
    echo Possible reason: MySQL abhi bhi start ho raha hai, ya DB_ROOT_PASSWORD galat hai.
    echo 30 second baad dobara try karo.
    pause
    exit /b 1
)

echo.
echo Password reset ho gaya! Migration chala raha hoon...
echo.

docker compose -f docker-compose.production.yml --env-file .env.production up migrate

if %errorlevel% neq 0 (
    color 0C
    echo.
    echo Migration fail hui. Upar ka output copy karo aur Claude ko bhejo.
    pause
    exit /b 1
)

echo.
color 0A
echo ============================================
echo  COMPLETE! Ab services restart ho rahi hain.
echo ============================================
echo.

docker compose -f docker-compose.production.yml --env-file .env.production up -d

echo.
echo Sab ho gaya. Browser mein reload karo: http://localhost
pause
