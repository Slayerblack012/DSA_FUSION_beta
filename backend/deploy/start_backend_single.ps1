param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

Write-Host "[INFO] Ensuring single backend runtime on port $Port..."

$connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($connections) {
    $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($pidVal in $pids) {
        try {
            Stop-Process -Id $pidVal -Force -ErrorAction Stop
            Write-Host "[INFO] Stopped PID $pidVal"
        } catch {
            Write-Host "[WARN] Could not stop PID $pidVal"
        }
    }
}

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$pythonExe = "d:/DSA_Fusion_Final/.venv/Scripts/python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found at $pythonExe"
}

Write-Host "[INFO] Starting backend on http://127.0.0.1:$Port"
& $pythonExe -m uvicorn app.main:app --host 127.0.0.1 --port $Port
