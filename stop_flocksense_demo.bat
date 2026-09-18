@echo off
REM FlockSense Quick Stopper (Batch Wrapper)
echo =================================================
echo  FLOCKSENSE HACKATHON DEMO STOPPER
echo =================================================

powershell -ExecutionPolicy Bypass -File %~dp0scripts\stop_demo.ps1
pause
