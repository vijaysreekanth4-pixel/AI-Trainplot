@echo off
title AI Interview Coach - Starting...

echo ====================================
echo   AI Interview Coach - Starting Up
echo ====================================
echo.

REM Kill any old processes on ports 8001 and 3000
echo Clearing old server processes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8001') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000') do taskkill /PID %%a /F >nul 2>&1

echo Starting Backend Server...
start "" /min cmd /c "cd /d E:\generative_ai_engineer\backend && venv\Scripts\python.exe main.py"

echo Waiting for backend to initialize...
timeout /t 6 /nobreak >nul

echo Starting Frontend Server...
start "" /min cmd /c "cd /d E:\generative_ai_engineer\frontend && npm.cmd run dev -- --port 3000"

echo Waiting for frontend to initialize...
timeout /t 8 /nobreak >nul

echo Opening App in Chrome...
start msedge --app=http://localhost:3000 --window-size=1280,800

echo.
echo ====================================
echo   App is running at localhost:3000
echo ====================================
exit
