@echo off
REM FlockSense Quick Launcher (Batch Wrapper)
echo =================================================
echo  FLOCKSENSE HACKATHON DEMO LAUNCHER
echo =================================================

powershell -ExecutionPolicy Bypass -File %~dp0scripts\start_demo.ps1
pause
