# FlockSense Windows PowerShell Demo Launcher
# Starts FastAPI backend and React frontend Vite dev server

Write-Host ================================================= -ForegroundColor Cyan
Write-Host  FLOCKSENSE HACKATHON DEMO LAUNCHER (PowerShell) -ForegroundColor Cyan
Write-Host ================================================= -ForegroundColor Cyan

$WorkspaceRoot = Resolve-Path $PSScriptRoot\..

# 1. Start Backend in separate window
Write-Host 
[1/2] Starting FastAPI Backend on http://127.0.0.1:8000 ... -ForegroundColor Yellow
$backendProcess = Start-Process powershell -ArgumentList -NoExit, -Command, cd '$WorkspaceRoot'; Write-Host 'FlockSense Backend Server' -ForegroundColor Green; python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 -PassThru

# 2. Start Frontend in separate window
Write-Host [2/2] Starting React + Vite Frontend on http://localhost:5173 ... -ForegroundColor Yellow
$frontendProcess = Start-Process powershell -ArgumentList -NoExit, -Command, cd '$WorkspaceRoot\frontend'; Write-Host 'FlockSense React Dashboard' -ForegroundColor Green; npm run dev -PassThru

# Store PIDs for clean shutdown
$pids = @{
    BackendPid = $backendProcess.Id
    FrontendPid = $frontendProcess.Id
}
$pids | ConvertTo-Json | Out-File -FilePath $WorkspaceRoot\scripts\.demo_pids.json -Encoding utf8

Write-Host 
Waiting for services to become responsive... -ForegroundColor Gray
Start-Sleep -Seconds 3

Write-Host 
Both services launched! -ForegroundColor Green
Write-Host Backend API: http://127.0.0.1:8000/docs -ForegroundColor White
Write-Host Frontend App: http://localhost:5173 -ForegroundColor White
Write-Host 
Run 'scripts/stop_demo.ps1' or 'stop_flocksense_demo.bat' to stop them.
 -ForegroundColor Cyan
