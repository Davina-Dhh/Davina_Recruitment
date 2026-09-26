@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
python -m streamlit run davina_workbench.py --server.port 8501
