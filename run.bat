@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Starting RAG demo from project venv...
".venv\Scripts\streamlit.exe" run app.py
pause
