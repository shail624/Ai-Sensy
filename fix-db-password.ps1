# Vi Platform - MySQL Password Recovery
# Run this from the project folder as: powershell -ExecutionPolicy Bypass -File fix-db-password.ps1

Set-Location $PSScriptRoot
$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Vi Platform - MySQL Password Recovery" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Read .env.production
Write-Host "[1/6] .env.production padh raha hoon..." -ForegroundColor Yellow
$envVars = @{}
Get-Content ".env.production" | Where-Object { $_ -notmatch "^#" -and $_ -match "=" } | ForEach-Object {
    $parts = $_ -split "=", 2
    if ($parts.Count -eq 2) {
        $envVars[$parts[0].Trim()] = $parts[1].Trim()
    }
}

$rootPass  = $envVars["MYSQL_ROOT_PASSWORD"]
$appUser   = $envVars["DB_USER"]
$appPass   = $envVars["DB_PASSWORD"]

if (-not $rootPass -or -not $appPass) {
    Write-Host "ERROR: MYSQL_ROOT_PASSWORD ya DB_PASSWORD .env.production mein blank hai." -ForegroundColor Red
    Write-Host "File check karo aur dobara run karo." -ForegroundColor Red
    Read-Host "Enter dabao"
    exit 1
}
Write-Host "    Passwords padh liye." -ForegroundColor Green

# Stop MySQL container
Write-Host "[2/6] MySQL band kar raha hoon..." -ForegroundColor Yellow
docker stop wa-platform-mysql-1 2>$null | Out-Null
Write-Host "    Done." -ForegroundColor Green

# Start recovery container with skip-grant-tables using same volume
Write-Host "[3/6] Recovery mode mein start kar raha hoon (30 sec)..." -ForegroundColor Yellow
docker rm -f mysql-recovery 2>$null | Out-Null
docker run -d --name mysql-recovery `
    -v wa-platform_mysql-data:/var/lib/mysql `
    mysql:8 `
    mysqld --skip-grant-tables --skip-networking | Out-Null
Start-Sleep 30
Write-Host "    MySQL recovery ready." -ForegroundColor Green

# Reset passwords
Write-Host "[4/6] Passwords reset kar raha hoon..." -ForegroundColor Yellow
$sql = "FLUSH PRIVILEGES; ALTER USER 'root'@'localhost' IDENTIFIED BY '$rootPass'; ALTER USER '$appUser'@'%' IDENTIFIED BY '$appPass'; FLUSH PRIVILEGES;"
docker exec mysql-recovery mysql -u root -e $sql
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Password reset fail hua. Recovery container ki output dekho." -ForegroundColor Red
    docker stop mysql-recovery; docker rm mysql-recovery | Out-Null
    Read-Host "Enter dabao"
    exit 1
}
Write-Host "    Passwords reset ho gaye." -ForegroundColor Green

# Stop recovery, start normal MySQL
Write-Host "[5/6] Normal MySQL start kar raha hoon..." -ForegroundColor Yellow
docker stop mysql-recovery | Out-Null
docker rm mysql-recovery | Out-Null
docker start wa-platform-mysql-1 | Out-Null
Write-Host "    30 seconds wait kar raha hoon MySQL ke liye..." -ForegroundColor Yellow
Start-Sleep 30
Write-Host "    MySQL ready." -ForegroundColor Green

# Run migrations
Write-Host "[6/6] Migrations aur services start kar raha hoon..." -ForegroundColor Yellow
& docker compose -f docker-compose.production.yml --env-file .env.production up migrate
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Migration fail hui. Upar ka output Claude ko bhejo." -ForegroundColor Red
    Read-Host "Enter dabao"
    exit 1
}

& docker compose -f docker-compose.production.yml --env-file .env.production up -d

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " COMPLETE! Platform ready hai." -ForegroundColor Green
Write-Host " Browser mein kholo: http://localhost" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Read-Host "Enter dabao"
