@echo off
rem One-command runner for Windows: double-click this file, or from a
rem terminal run:  run.bat [--experiments] [--slides] [--skip-tests]
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 run.py %*
) else (
  python run.py %*
)
pause
