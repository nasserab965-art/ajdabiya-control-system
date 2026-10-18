@echo off
chcp 65001 >nul
title تشغيل تطبيق النهر الصناعي العظيم

cd /d "E:\firstpy"
python -m streamlit run app_main.py --server.address 0.0.0.0 --server.port 8501
pause