@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%\sci-illust-system\web_app;%CD%\sci-illust-system;%CD%"
C:\ProgramData\anaconda3\python.exe sci-illust-system\web_app\app.py


