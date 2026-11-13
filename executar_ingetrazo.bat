@echo off
cd /d "%~dp0"
"%~dp0venv\Scripts\python.exe" main.py %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo O IngeTrazo encerrou com erro: %ERRORLEVEL%
    pause
)
