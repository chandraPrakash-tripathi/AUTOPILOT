@echo off
echo Starting Autopilot...
start "Telegram Bot + Scheduler" cmd /k "venv\Scripts\activate && python main.py"
timeout /t 3
start "Streamlit Dashboard" cmd /k "venv\Scripts\activate && streamlit run dashboard/app.py"
echo Both services started!