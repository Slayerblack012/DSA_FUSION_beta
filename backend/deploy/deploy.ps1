# ===========================================
# DSA AutoGrader - Windows Deployment Script
# ===========================================
# Deploy to Windows Server without Docker
# ===========================================

param(
    [string]$InstallDir = "C:\DSA_AutoGrader",
    [string]$PythonVersion = "3.11",
    [switch]$InstallRedis,
    [switch]$CreateService
)

$ErrorActionPreference = "Stop"

# Colors
function Write-Info { Write-Host "[INFO] $args" -ForegroundColor Green }
function Write-Warn { Write-Host "[WARN] $args" -ForegroundColor Yellow }
function Write-Error { Write-Host "[ERROR] $args" -ForegroundColor Red }

# ===========================================
# 1. Check Prerequisites
# ===========================================
Write-Info "Checking prerequisites..."

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Info "Python found: $pythonVersion"
} catch {
    Write-Error "Python not found. Please install Python 3.11+"
    exit 1
}

# Check Redis (optional)
$redisInstalled = Get-Service Redis -ErrorAction SilentlyContinue
if ($redisInstalled) {
    Write-Info "Redis found: $($redisInstalled.Status)"
} else {
    Write-Warn "Redis not found. Install with: choco install redis-64"
}

# ===========================================
# 2. Create Installation Directory
# ===========================================
Write-Info "Creating installation directory: $InstallDir"

if (!(Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir | Out-Null
}

Set-Location $InstallDir

# Copy application files
Write-Info "Copying application files..."
Copy-Item -Path ".\*" -Destination $InstallDir -Recurse -Force

# ===========================================
# 3. Create Virtual Environment
# ===========================================
Write-Info "Creating virtual environment..."

python -m venv venv
.\venv\Scripts\Activate.ps1

# ===========================================
# 4. Install Dependencies
# ===========================================
Write-Info "Installing dependencies..."

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pywin32

# ===========================================
# 5. Create .env file
# ===========================================
if (!(Test-Path ".env")) {
    Write-Warn ".env file not found. Please create it manually."
    Copy-Item .env.example .env
}

# ===========================================
# 6. Create Windows Service (NSSM)
# ===========================================
if ($CreateService) {
    Write-Info "Creating Windows service..."
    
    # Download NSSM if not exists
    if (!(Test-Path "nssm.exe")) {
        Write-Info "Downloading NSSM..."
        Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile "nssm.zip"
        Expand-Archive nssm.zip -DestinationPath .
        Copy-Item "nssm-2.24\win64\nssm.exe" .
    }
    
    # Create service
    $serviceName = "DSA_AutoGrader"
    .\nssm.exe install $serviceName "C:\DSA_AutoGrader\venv\Scripts\python.exe"
    .\nssm.exe set $serviceName ApplicationParameters "-m uvicorn app.main:app --host 0.0.0.0 --port 8000"
    .\nssm.exe set $serviceName AppDirectory $InstallDir
    .\nssm.exe set $serviceName AppStdout "$InstallDir\logs\service.log"
    .\nssm.exe set $serviceName AppStderr "$InstallDir\logs\service.error.log"
    .\nssm.exe set $serviceName AppRotateFiles 1
    .\nssm.exe set $serviceName AppRotateBytes 10485760
    
    Start-Service $serviceName
    Write-Info "Service '$serviceName' created and started"
}

# ===========================================
# 7. Create Startup Script
# ===========================================
Write-Info "Creating startup script..."

$startupScript = @"
# DSA AutoGrader Startup Script
cd $InstallDir
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"@

$startupScript | Out-File -FilePath "start.ps1" -Encoding UTF8

# ===========================================
# 8. Create IIS Configuration (Optional)
# ===========================================
Write-Info "Creating IIS configuration..."

# Create web.config for IIS (if using httpPlatform)
$webConfig = @"
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <system.webServer>
    <handlers>
      <add name="httpPlatformHandler" path="*" verb="*" modules="httpPlatformHandler" resourceType="Unspecified" />
    </handlers>
    <httpPlatform processPath="%ProgramFiles%\Python311\python.exe"
                  arguments="-m uvicorn app.main:app --host 127.0.0.1 --port 8000"
                  stdoutLogEnabled="true"
                  stdoutLogFile=".\logs\stdout.log"
                  startupTimeLimit="60" />
  </system.webServer>
</configuration>
"@

$webConfig | Out-File -FilePath "web.config" -Encoding UTF8

# ===========================================
# 9. Setup Firewall Rule
# ===========================================
Write-Info "Creating firewall rule..."

New-NetFirewallRule -DisplayName "DSA AutoGrader" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue

# ===========================================
# 10. Summary
# ===========================================
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Info "DEPLOYMENT COMPLETED!"
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Application URLs:"
Write-Host "  - Web UI: http://localhost:8000"
Write-Host "  - API Docs: http://localhost:8000/docs"
Write-Host "  - Health: http://localhost:8000/health"
Write-Host ""
Write-Host "Commands:"
Write-Host "  - Start: .\start.ps1"
if ($CreateService) {
    Write-Host "  - Service: Start-Service DSA_AutoGrader"
}
Write-Host ""
Write-Host "============================================"
