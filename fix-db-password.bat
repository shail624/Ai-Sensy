@echo off
title Fix DB Password
color 0E

echo ============================================
echo  Database Password Fix
echo ============================================
echo.
echo Pehle apna .env.production file kholo.
echo Notepad mein: C:\Users\Admin\Documents\Claude Code\Ai Sensy Project\.env.production
echo.
echo Yahan se 2 values chahiye:
echo   DB_ROOT_PASSWORD=????
echo   DB_PASSWORD=????
echo.

cd /d "%~dp0"

set /p ROOT_PASS=DB_ROOT_PASSWORD ka value type karo:
echo.
set /p APP_PASS=DB_PASSWORD ka value type karo:
echo.

echo Fixing password...
docker compose -f docker-compose.production.yml exec mysql mysql -u root -p%ROOT_PASS% -e "ALTER USER 'wa_app'@'%%' IDENTIFIED BY '%APP_PASS%'; FLUSH PRIVILEGES;"

if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ERROR: Root password galat hai ya MySQL band hai.
    echo DB_ROOT_PASSWORD dobara check karo.
    pause
    exit /b 1
)

echo.
echo Password fix ho gaya! Ab migration chala raha hoon...
echo.

docker compose -f docker-compose.production.yml --env-file .env.production up migrate

if %errorlevel% neq 0 (
    color 0C
    echo.
    echo Migration fail hui. Upar ki output copy karo aur Claude ko bhejo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  DONE! Ab redeploy.bat dobara chalao.
echo ============================================
pause
