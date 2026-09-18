# FlockSense Windows PowerShell Demo Stopper
# Stops FlockSense development processes started by the demo launcher

Write-Host ================================================= -ForegroundColor Cyan
Write-Host  FLOCKSENSE DEMO STOPPER -ForegroundColor Cyan
Write-Host ================================================= -ForegroundColor Cyan

$WorkspaceRoot = Resolve-Path $PSScriptRoot\..
$pidFile = $WorkspaceRoot\scripts\.demo_pids.json

if (Test-Path $pidFile) {
    try {
        $pids = Get-Content $pidFile | ConvertFrom-Json
        if ($pids.BackendPid) {
            Write-Host Stopping Backend process (PID $($pids.BackendPid))... -ForegroundColor Yellow
            Stop-Process -Id $pids.BackendPid -Force -ErrorAction SilentlyContinue
        }
        if ($pids.FrontendPid) {
            Write-Host Stopping Frontend process (PID $($pids.FrontendPid))... -ForegroundColor Yellow
            Stop-Process -Id $pids.FrontendPid -Force -ErrorAction SilentlyContinue
        }
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
        Write-Host FlockSense demo processes stopped. -ForegroundColor Green
    } catch {
        Write-Host Failed to clean processes via PID file: $_ -ForegroundColor Red
    }
} else {
    Write-Host No .demo_pids.json file found. Searching port 8000 and 5173 listeners... -ForegroundColor Yellow
}

# Also ensure any lingering listeners on 8000 or 5173 are cleaned up if needed
$ports = @(8000, 5173)
foreach ($port in $ports) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($conn in $conns) {
        Write-Host Stopping process $($conn.OwningProcess) listening on port $port... -ForegroundColor Yellow
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    }
}

Write-Host Shutdown complete. -ForegroundColor Green
