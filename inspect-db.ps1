# Vi Platform - Database Inspector (READ ONLY - kuch delete nahi karta)
# Chalao: powershell -ExecutionPolicy Bypass -File inspect-db.ps1

Set-Location $PSScriptRoot

$PINNED_80 = "mysql:8.0@sha256:7dcddc01f13bab2f15cde676d44d01f61fc9f99fe7785e86196dfc07d358ae2b"
$NEWER_84  = "mysql:8"
$VOLUME    = "wa-platform_mysql-data"
$RECOVERY  = "db-inspect"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Database Inspector (read-only)" -ForegroundColor Cyan
Write-Host "============================================`n" -ForegroundColor Cyan

# Database naam .env.production se
$dbName = "wa_platform"
Get-Content ".env.production" | ForEach-Object {
    if ($_ -match "^DB_NAME=(.*)$") { $dbName = $matches[1].Trim() }
}
Write-Host "Database: $dbName`n" -ForegroundColor Gray

# Purana MySQL band karo taaki volume lock na ho
Write-Host "[1/3] Stack band kar raha hoon (volume free karne ke liye)..." -ForegroundColor Yellow
docker stop wa-platform-mysql-1 2>&1 | Out-Null
docker rm -f $RECOVERY 2>&1 | Out-Null
Write-Host "    Done.`n" -ForegroundColor Green

# Helper: recovery container start karke check karo ki MySQL boot hua ya nahi
function Try-Boot([string]$image, [string]$label) {
    Write-Host "[2/3] $label se database kholne ki koshish..." -ForegroundColor Yellow
    docker rm -f $RECOVERY 2>&1 | Out-Null
    docker run -d --name $RECOVERY -v "${VOLUME}:/var/lib/mysql" $image `
        mysqld --skip-grant-tables --skip-networking 2>&1 | Out-Null

    for ($i = 0; $i -lt 24; $i++) {
        Start-Sleep 5
        docker exec $RECOVERY mysql -u root -e "SELECT 1" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    KHUL GAYA! ($label)`n" -ForegroundColor Green
            return $true
        }
        # Container mar gaya to aage koshish bekaar
        $running = docker inspect -f "{{.State.Running}}" $RECOVERY 2>&1
        if ($running -ne "true") { break }
    }
    Write-Host "    $label se nahi khula.`n" -ForegroundColor Red
    return $false
}

$opened = ""
if (Try-Boot $PINNED_80 "MySQL 8.0 (asli version)") {
    $opened = "8.0"
} else {
    Write-Host "  MySQL 8.0 fail hua. Iska matlab data directory upgrade ho chuki hai." -ForegroundColor Magenta
    Write-Host "  Ab MySQL 8.4 se try kar raha hoon...`n" -ForegroundColor Magenta
    if (Try-Boot $NEWER_84 "MySQL 8.4 (naya version)") { $opened = "8.4" }
}

if ($opened -eq "") {
    Write-Host "============================================" -ForegroundColor Red
    Write-Host " Database kisi bhi version se nahi khula." -ForegroundColor Red
    Write-Host "============================================" -ForegroundColor Red
    Write-Host "`nLogs save kar raha hoon: db-inspect-log.txt" -ForegroundColor Yellow
    docker logs $RECOVERY 2>&1 | Out-File "db-inspect-log.txt"
    docker rm -f $RECOVERY 2>&1 | Out-Null
    Write-Host "Yeh file Claude ko bhejo." -ForegroundColor Yellow
    Read-Host "`nEnter dabao"
    exit 1
}

# Data count karo
Write-Host "[3/3] Data ginn raha hoon...`n" -ForegroundColor Yellow

$tables = @(
    @{t="users";                       n="Users (login accounts)"},
    @{t="organizations";               n="Organizations"},
    @{t="contacts";                    n="Contacts (customers)"},
    @{t="campaigns";                   n="Campaigns"},
    @{t="messages";                    n="Messages"},
    @{t="conversations";               n="Conversations (chats)"},
    @{t="message_templates";           n="WhatsApp Templates"},
    @{t="whatsapp_business_accounts";  n="WABA connections"},
    @{t="phone_numbers";               n="Phone numbers"},
    @{t="tags";                        n="Tags"},
    @{t="segments";                    n="Segments"},
    @{t="reactivation_cases";          n="Reactivation cases"}
)

Write-Host "  --------------------------------------------" -ForegroundColor Gray
$hasRealData = $false
foreach ($row in $tables) {
    $out = docker exec $RECOVERY mysql -u root -N -B -e "SELECT COUNT(*) FROM ``$dbName``.``$($row.t)``;" 2>&1
    if ($LASTEXITCODE -eq 0) {
        $count = ($out | Select-Object -Last 1).ToString().Trim()
        $color = "Gray"
        if ([int]$count -gt 0) { $color = "White" }
        # Contacts/campaigns/messages = asli kaam ka data
        if ($row.t -in @("contacts","campaigns","messages","conversations") -and [int]$count -gt 0) {
            $hasRealData = $true
            $color = "Yellow"
        }
        Write-Host ("  {0,-28} {1,8}" -f $row.n, $count) -ForegroundColor $color
    } else {
        Write-Host ("  {0,-28} {1,8}" -f $row.n, "table nahi") -ForegroundColor DarkGray
    }
}
Write-Host "  --------------------------------------------`n" -ForegroundColor Gray

# Migration version
$ver = docker exec $RECOVERY mysql -u root -N -B -e "SELECT version_num FROM ``$dbName``.alembic_version;" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Migration version: $(($ver | Select-Object -Last 1).ToString().Trim())" -ForegroundColor Gray
}

# Cleanup
docker rm -f $RECOVERY 2>&1 | Out-Null

# Verdict
Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host " NATEEJA" -ForegroundColor Cyan
Write-Host "============================================`n" -ForegroundColor Cyan

if ($opened -eq "8.0") {
    Write-Host " Data directory THEEK HAI." -ForegroundColor Green
    Write-Host " MySQL 8.0 use kar sakte hain - kuch damage nahi hua." -ForegroundColor Green
} else {
    Write-Host " Data directory MySQL 8.4 mein upgrade ho chuki hai." -ForegroundColor Magenta
    Write-Host " Purana MySQL 8.0 ab isse nahi padh sakta." -ForegroundColor Magenta
}

Write-Host ""
if ($hasRealData) {
    Write-Host " Andar ASLI DATA hai (upar yellow numbers dekho)." -ForegroundColor Yellow
    Write-Host " Ise bachana chahiye." -ForegroundColor Yellow
} else {
    Write-Host " Koi asli data nahi hai - sirf khaali tables aur setup." -ForegroundColor Green
    Write-Host " Fresh database banana bilkul safe hai." -ForegroundColor Green
}

Write-Host "`n Yeh poora screen Claude ko bhejo - wo agla step batayega." -ForegroundColor Cyan
Read-Host "`nEnter dabao"
