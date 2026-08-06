@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%\sci-illust-system\web_app;%CD%\sci-illust-system;%CD%"
set "SCI_WEB_MODE=stable"
set "PYTHON_EXE="
if exist "C:\Program Files\Python312\python.exe" set "PYTHON_EXE=C:\Program Files\Python312\python.exe"
if not defined PYTHON_EXE (
  for /f "delims=" %%I in ('where python 2^>nul') do if not defined PYTHON_EXE set "PYTHON_EXE=%%I"
)
if not defined PYTHON_EXE (
  echo Python executable not found.
  exit /b 1
)
for /f "delims=" %%P in ('powershell -NoProfile -Command "Get-CimInstance Win32_Process ^| Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*sci-illust-system\\web_app\\app.py*' } ^| Select-Object -ExpandProperty ProcessId"') do (
  taskkill /PID %%P /F >nul 2>nul
)
"%PYTHON_EXE%" sci-illust-system\web_app\app.py


