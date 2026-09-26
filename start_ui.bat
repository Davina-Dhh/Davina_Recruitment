@echo off
chcp 65001 >nul
cd /d "%~dp0dashboard"
echo Starting Qiuxun dashboard...
set PYTHONIOENCODING=utf-8
python -m pip install streamlit pandas pycryptodome -q
python -m streamlit run app.py --server.headless true
pause
