@echo off
echo Starting AI Interview Application...

echo Starting Backend Server...
start cmd /k "cd /d E:\generative_ai_engineer\backend && E:\generative_ai_engineer\backend\venv\Scripts\python.exe main.py"

echo Starting Frontend Server...
start cmd /k "cd /d E:\generative_ai_engineer\frontend && npm run dev -- --port 3000"

echo Servers are starting! Please wait a few seconds, then open http://localhost:3000 in your browser.
pause
