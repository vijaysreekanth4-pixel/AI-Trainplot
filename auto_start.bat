@echo off
:: Wait for network to be ready
timeout /t 10 /nobreak > nul

:: Start Backend
start "" /min "E:\generative_ai_engineer\backend\venv\Scripts\python.exe" "E:\generative_ai_engineer\backend\main.py"

:: Wait for backend to start
timeout /t 5 /nobreak > nul

:: Start Frontend
start "" /min cmd /c "cd /d E:\generative_ai_engineer\frontend && npm run dev -- --port 3000"
