@echo off
cd /d C:\Users\jordi\Desktop\app_tennis

venv\Scripts\python.exe -m uvicorn app.main:app --reload

pause