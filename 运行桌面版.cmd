@echo off
wsl.exe -e sh -lc "cd ~/projects/yf-artifact && exec python3 scripts/run_desktop.py --lan"
if errorlevel 1 pause
